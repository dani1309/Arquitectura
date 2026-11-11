"""Pruebas de integración local para T3 (`lambda_handlers.py`).

Verifica los criterios de terminado de T3 y T4 del plan (`docs/plan/04_plan_construccion.md`):
1. Un CSV de prueba con varios chunks y una fila malformada (`CHV-9999999`) recorre la cadena
   completa: `saom-raw` -> `particionador_handler` -> `chunks-adjudicacion` -> `worker_adjudicador_handler`.
2. Al finalizar, `chunks_completados == chunks_totales`, `estado == PROCESADO`, la fila malformada
   está aislada en `rechazos/` sin abortar el chunk, y existe `manifiestos/lote=<id>.json` con
   `raiz_hash_lote` y las `raiz_hash_chunk`.
3. Reenviar un mensaje SQS ya procesado activa la condición de `TransactWriteItems` en DynamoDB y
   NO altera `chunks_completados`, `ordenes_validas`, `ordenes_rechazadas` ni las sumas en `META` (RNF-06).
4. Un CSV con cabecera inválida se marca `RECHAZADO` en `META` y no emite chunks (sección 9).
5. La verificación criptográfica de tres niveles (orden en staging, recibo en WORM y manifiesto del lote)
   se cumple para el 100 % de las órdenes válidas (RF-05, RNF-04).
6. El escaneo de PII sobre `saom-curated`, `saom-audit`, DynamoDB y los logs EMF da cero coincidencias (RNF-05).
"""
from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import os
import re
import tempfile
import unittest
import urllib.parse
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import lambda_handlers
from lambda_handlers import (
    BUCKET_AUDIT,
    BUCKET_CURATED,
    BUCKET_RAW,
    BUCKET_REF,
    DDB_TABLE_CONTROL,
    configurar_clientes_aws,
    particionador_handler,
    particionar_stream_csv,
    radicacion_api_handler,
    worker_adjudicador_handler,
)
from saom_core import (
    COLUMNAS_ESPERADAS,
    calcular_hash_decision,
    calcular_raiz_lote,
    particionar_csv_en_chunks,
)
from test_bdd_rf01_rf05 import (
    CLAVE_SECRETA_TEST,
    DNO,
    FILAS_RF04,
    GLOSA_CHV1,
    NOMBRE,
    REF_DIR,
    SS,
    coincidencias_pii,
    fila_coil,
)


class FakeTransactionCanceledException(Exception):
    def __init__(self, message: str = "TransactionCanceledException") -> None:
        super().__init__(message)
        self.response = {"Error": {"Code": "TransactionCanceledException", "Message": message}}


class FakeS3Client:
    """Simulador en memoria de Amazon S3 con soporte para `Range=bytes=inicio-fin`."""

    def __init__(self) -> None:
        self.objects: Dict[Tuple[str, str], bytes] = {}

    def put_object(self, Bucket: str, Key: str, Body: bytes | str, **kwargs: Any) -> Dict[str, Any]:
        data = Body.encode("utf-8") if isinstance(Body, str) else bytes(Body)
        self.objects[(Bucket, Key)] = data
        return {"ETag": f'"{hashlib.md5(data).hexdigest()}"'}

    def get_object(self, Bucket: str, Key: str, Range: Optional[str] = None) -> Dict[str, Any]:
        if (Bucket, Key) not in self.objects:
            raise KeyError(f"S3 NoSuchKey: s3://{Bucket}/{Key}")
        data = self.objects[(Bucket, Key)]
        if Range is not None:
            assert Range.startswith("bytes="), f"Range inválido: {Range}"
            ini_str, fin_str = Range.replace("bytes=", "").split("-")
            ini, fin = int(ini_str), int(fin_str)
            data = data[ini : fin + 1]
        return {"Body": io.BytesIO(data), "ContentLength": len(data)}

    def download_file(self, Bucket: str, Key: str, Filename: str) -> None:
        if (Bucket, Key) not in self.objects:
            raise KeyError(f"S3 NoSuchKey: s3://{Bucket}/{Key}")
        Path(Filename).parent.mkdir(parents=True, exist_ok=True)
        Path(Filename).write_bytes(self.objects[(Bucket, Key)])

    def generate_presigned_url(
        self, ClientMethod: str, Params: Dict[str, Any], ExpiresIn: int = 900
    ) -> str:
        return f"https://{Params['Bucket']}.s3.amazonaws.com/{Params['Key']}?expires={ExpiresIn}"


class FakeSQSClient:
    """Simulador en memoria de Amazon SQS con soporte para `send_message` y `send_message_batch`."""

    def __init__(self) -> None:
        self.queues: Dict[str, List[Dict[str, Any]]] = {}

    def send_message(self, QueueUrl: str, MessageBody: str) -> Dict[str, Any]:
         cola = self.queues.setdefault(QueueUrl, [])
         msg_id = f"msg-{len(cola) + 1}"
         cola.append({"messageId": msg_id, "body": MessageBody})
         return {"MessageId": msg_id}

    def send_message_batch(
        self, QueueUrl: str, Entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        exitosos = []
        for entry in Entries:
            res = self.send_message(QueueUrl=QueueUrl, MessageBody=entry["MessageBody"])
            exitosos.append({"Id": entry["Id"], "MessageId": res["MessageId"]})
        return {"Successful": exitosos, "Failed": []}


class FakeDynamoDBClient:
    """Simulador en memoria de Amazon DynamoDB con `TransactWriteItems` condicional para `control_lotes`."""

    def __init__(self) -> None:
        self.items: Dict[Tuple[str, str, str], Dict[str, Dict[str, str]]] = {}

    def _clone(self, item: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        return {k: dict(v) for k, v in item.items()}

    def put_item(
        self, TableName: str, Item: Dict[str, Dict[str, str]], **kwargs: Any
    ) -> Dict[str, Any]:
        pk = Item["PK"]["S"]
        sk = Item["SK"]["S"]
        self.items[(TableName, pk, sk)] = self._clone(Item)
        return {}

    def get_item(
        self, TableName: str, Key: Dict[str, Dict[str, str]], **kwargs: Any
    ) -> Dict[str, Any]:
        pk = Key["PK"]["S"]
        sk = Key["SK"]["S"]
        found = self.items.get((TableName, pk, sk))
        return {"Item": self._clone(found)} if found else {}

    def query(
        self,
        TableName: str,
        KeyConditionExpression: str,
        ExpressionAttributeValues: Dict[str, Dict[str, str]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        pk_target = ExpressionAttributeValues[":pk"]["S"]
        sk_prefix = ExpressionAttributeValues.get(":sk_prefix", {}).get("S", "")
        matched = [
            self._clone(item)
            for (tbl, pk, sk), item in sorted(self.items.items())
            if tbl == TableName and pk == pk_target and sk.startswith(sk_prefix)
        ]
        return {"Items": matched}

    def update_item(
        self,
        TableName: str,
        Key: Dict[str, Dict[str, str]],
        UpdateExpression: str,
        ExpressionAttributeValues: Dict[str, Dict[str, str]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        pk = Key["PK"]["S"]
        sk = Key["SK"]["S"]
        actual = self.items.setdefault(
            (TableName, pk, sk),
            {"PK": {"S": pk}, "SK": {"S": sk}},
        )
        self._aplicar_update(actual, UpdateExpression, ExpressionAttributeValues)
        return {}

    def _aplicar_update(
        self,
        item: Dict[str, Dict[str, str]],
        expr: str,
        vals: Dict[str, Dict[str, str]],
    ) -> None:
        expr_limpia = " ".join(expr.strip().split())
        if expr_limpia.startswith("SET "):
            asignaciones = re.split(r",\s*(?![^()]*\))", expr_limpia[4:])
            for asig in asignaciones:
                campo, valor_expr = [p.strip() for p in asig.split("=", 1)]
                if valor_expr.startswith("if_not_exists("):
                    inner = valor_expr[len("if_not_exists(") : -1]
                    attr_existente, token_default = [p.strip() for p in inner.split(",", 1)]
                    if attr_existente not in item:
                        item[campo] = dict(vals[token_default])
                else:
                    item[campo] = dict(vals[valor_expr])
        elif expr_limpia.startswith("ADD "):
            adiciones = expr_limpia[4:].split(",")
            for adic in adiciones:
                campo, token_val = [p.strip() for p in adic.split()]
                delta_str = vals[token_val]["N"]
                actual_str = item.get(campo, {"N": "0"})["N"]
                if "." in delta_str or "." in actual_str:
                    nuevo = f"{Decimal(actual_str) + Decimal(delta_str):.2f}"
                else:
                    nuevo = str(int(actual_str) + int(delta_str))
                item[campo] = {"N": nuevo}
        else:
            raise ValueError(f"UpdateExpression no soportada en simulador: {expr}")

    def transact_write_items(self, TransactItems: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Fase 1: Validar todas las condiciones sin mutar estado
        for op in TransactItems:
            if "Put" in op:
                put = op["Put"]
                tbl = put["TableName"]
                item = put["Item"]
                pk, sk = item["PK"]["S"], item["SK"]["S"]
                cond = put.get("ConditionExpression", "")
                vals = put.get("ExpressionAttributeValues", {})
                existente = self.items.get((tbl, pk, sk))
                if "attribute_not_exists(SK) OR estado <> :comp" in cond:
                    comp_val = vals[":comp"]["S"]
                    if existente is not None and existente.get("estado", {}).get("S") == comp_val:
                        raise FakeTransactionCanceledException(
                            f"Chunk {pk}/{sk} ya está en estado {comp_val}"
                        )

        # Fase 2: Aplicar escrituras atómicamente
        for op in TransactItems:
            if "Put" in op:
                put = op["Put"]
                self.put_item(TableName=put["TableName"], Item=put["Item"])
            elif "Update" in op:
                upd = op["Update"]
                self.update_item(
                    TableName=upd["TableName"],
                    Key=upd["Key"],
                    UpdateExpression=upd["UpdateExpression"],
                    ExpressionAttributeValues=upd["ExpressionAttributeValues"],
                )
        return {}


class FakeSecretsManagerClient:
    def __init__(self, secret_bytes: bytes = CLAVE_SECRETA_TEST) -> None:
        self.secret_str = json.dumps(
            {"hmac_key": secret_bytes.decode("utf-8"), "key_version": "hmac-2026-v1"}
        )

    def get_secret_value(self, SecretId: str) -> Dict[str, Any]:
        return {"SecretString": self.secret_str}


def construir_csv_bytes(filas: List[List[str]], incluir_cabecera: bool = True) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    if incluir_cabecera:
        writer.writerow(COLUMNAS_ESPERADAS)
    writer.writerows(filas)
    return buf.getvalue().encode("utf-8")


class TestLambdaHandlersT3(unittest.TestCase):
    def setUp(self) -> None:
        self.s3 = FakeS3Client()
        self.sqs = FakeSQSClient()
        self.ddb = FakeDynamoDBClient()
        self.sm = FakeSecretsManagerClient()
        self.queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/chunks-adjudicacion"

        os.environ["SAOM_QUEUE_CHUNKS_URL"] = self.queue_url
        os.environ["SAOM_CHUNK_SIZE"] = "3"
        os.environ.pop("SAOM_HMAC_SECRET_FALLBACK", None)
        os.environ.pop("SAOM_HMAC_SECRET", None)

        clientes = {
            "s3": self.s3,
            "sqs": self.sqs,
            "dynamodb": self.ddb,
            "secretsmanager": self.sm,
        }
        configurar_clientes_aws(lambda svc: clientes[svc])

    def tearDown(self) -> None:
        os.environ["SAOM_CHUNK_SIZE"] = "5000"
        configurar_clientes_aws(None)

    def _preparar_lote_prueba(self) -> Tuple[str, str, List[List[str]], List[str]]:
        """Crea un CSV con 7 solicitudes (3 chunks de tamaño 3, 3 y 1) incluyendo 1 fila malformada."""
        filas_validas = [datos[0] for datos in FILAS_RF04.values()]  # 5 órdenes de RF-04
        filas_validas.append(fila_coil(GLOSA_CHV1, valor="120000", id_solicitud="CHV-0000007"))
        fila_malformada = fila_coil(GLOSA_CHV1, valor="", id_solicitud="CHV-9999999")

        # 7 filas totales: 6 válidas + 1 malformada en medio del segundo chunk
        todas_las_filas = [
            filas_validas[0],
            filas_validas[1],
            filas_validas[2],
            fila_malformada,
            filas_validas[3],
            filas_validas[4],
            filas_validas[5],
        ]
        nombres_pii = [datos[5] for datos in FILAS_RF04.values()]
        lote_id = "LOTE-T3-001"
        s3_key = f"entidad=Hospital_Central/fecha=2026-11-11/lote={lote_id}.csv"
        self.s3.put_object(
            Bucket=BUCKET_RAW,
            Key=s3_key,
            Body=construir_csv_bytes(todas_las_filas),
        )
        return lote_id, s3_key, todas_las_filas, nombres_pii

    def test_t3_cadena_completa_multichunk_fila_malformada_e_idempotencia(self) -> None:
        lote_id, s3_key, filas, nombres_pii = self._preparar_lote_prueba()

        # 1. Evento S3 envuelto en SQS (cola `lotes-recibidos`) hacia `particionador_handler`
        evento_s3_en_sqs = {
            "Records": [
                {
                    "body": json.dumps(
                        {
                            "Records": [
                                {
                                    "s3": {
                                        "bucket": {"name": BUCKET_RAW},
                                        "object": {"key": urllib.parse.quote_plus(s3_key)},
                                    }
                                }
                            ]
                        }
                    )
                }
            ]
        }
        res_part = particionador_handler(evento_s3_en_sqs)
        self.assertEqual(res_part["chunks_emitidos"], 3)
        self.assertEqual(res_part["lotes_rechazados"], 0)

        # Verificar que META quedó en EN_PROCESO con chunks_totales = 3
        meta_inicial = self.ddb.get_item(
            TableName=DDB_TABLE_CONTROL,
            Key={"PK": {"S": f"LOTE#{lote_id}"}, "SK": {"S": "META"}},
        )["Item"]
        self.assertEqual(meta_inicial["estado"]["S"], "EN_PROCESO")
        self.assertEqual(meta_inicial["chunks_totales"]["N"], "3")
        self.assertEqual(meta_inicial["chunks_completados"]["N"], "0")

        # 2. Consumir los 3 mensajes de `chunks-adjudicacion` con `worker_adjudicador_handler`
        mensajes_cola = self.sqs.queues[self.queue_url]
        self.assertEqual(len(mensajes_cola), 3)

        buffer_stdout = io.StringIO()
        with contextlib.redirect_stdout(buffer_stdout):
            res_worker = worker_adjudicador_handler({"Records": mensajes_cola})

        self.assertEqual(res_worker["chunks_procesados"], 3)
        self.assertEqual(res_worker["duplicados_ignorados"], 0)
        self.assertEqual(res_worker["lotes_cerrados"], [lote_id])

        # 3. Verificar estado final en DynamoDB (`chunks_completados == chunks_totales`)
        meta_final = self.ddb.get_item(
            TableName=DDB_TABLE_CONTROL,
            Key={"PK": {"S": f"LOTE#{lote_id}"}, "SK": {"S": "META"}},
        )["Item"]
        self.assertEqual(meta_final["estado"]["S"], "PROCESADO")
        self.assertEqual(meta_final["chunks_completados"]["N"], "3")
        self.assertEqual(meta_final["chunks_totales"]["N"], "3")
        self.assertEqual(meta_final["ordenes_validas"]["N"], "6")
        self.assertEqual(meta_final["ordenes_rechazadas"]["N"], "1")
        self.assertEqual(
            int(meta_final["ordenes_validas"]["N"]) + int(meta_final["ordenes_rechazadas"]["N"]),
            len(filas),
        )
        self.assertRegex(meta_final["raiz_hash_lote"]["S"], r"^[0-9a-f]{64}$")

        # 4. Verificar que la fila malformada CHV-9999999 está en `rechazos/` del chunk 1
        rechazos_key = f"rechazos/fecha=2026-11-11/lote={lote_id}/chunk=00001.jsonl"
        self.assertIn((BUCKET_CURATED, rechazos_key), self.s3.objects)
        lineas_rechazo = (
            self.s3.objects[(BUCKET_CURATED, rechazos_key)].decode("utf-8").strip().splitlines()
        )
        self.assertEqual(len(lineas_rechazo), 1)
        obj_rechazo = json.loads(lineas_rechazo[0])
        self.assertEqual(obj_rechazo["id_solicitud"], "CHV-9999999")
        self.assertEqual(obj_rechazo["estado"], "REJECTED_SYNTAX")

        # 5. Prueba de Idempotencia (RNF-06): Reenviar un mensaje ya procesado NO cambia contadores
        suma_aprobada_antes = meta_final["suma_aprobada"]["N"]
        suma_reclamada_antes = meta_final["suma_reclamada"]["N"]

        res_reintento = worker_adjudicador_handler({"Records": [mensajes_cola[1]]})
        self.assertEqual(res_reintento["chunks_procesados"], 0)
        self.assertEqual(res_reintento["duplicados_ignorados"], 1)

        meta_tras_reintento = self.ddb.get_item(
            TableName=DDB_TABLE_CONTROL,
            Key={"PK": {"S": f"LOTE#{lote_id}"}, "SK": {"S": "META"}},
        )["Item"]
        self.assertEqual(meta_tras_reintento["chunks_completados"]["N"], "3")
        self.assertEqual(meta_tras_reintento["ordenes_validas"]["N"], "6")
        self.assertEqual(meta_tras_reintento["ordenes_rechazadas"]["N"], "1")
        self.assertEqual(meta_tras_reintento["suma_aprobada"]["N"], suma_aprobada_antes)
        self.assertEqual(meta_tras_reintento["suma_reclamada"]["N"], suma_reclamada_antes)

        # 6. Verificación de integridad de tres niveles (sección 7.4: staging, recibo WORM y manifiesto)
        manifiesto_key = f"manifiestos/lote={lote_id}.json"
        manifiesto = json.loads(self.s3.objects[(BUCKET_AUDIT, manifiesto_key)].decode("utf-8"))
        self.assertEqual(manifiesto["raiz_hash_lote"], meta_final["raiz_hash_lote"]["S"])
        self.assertEqual(manifiesto["ordenes_totales"], 7)

        raices_para_lote: List[Tuple[int, str]] = []
        for cid in range(3):
            stg_key = f"staging/fecha=2026-11-11/lote={lote_id}/chunk={cid:05d}.jsonl"
            rec_key = f"recibos/fecha=2026-11-11/lote={lote_id}/chunk={cid:05d}.jsonl"
            filas_stg = [
                json.loads(line)
                for line in self.s3.objects[(BUCKET_CURATED, stg_key)]
                .decode("utf-8")
                .strip()
                .splitlines()
            ]
            filas_rec = [
                json.loads(line)
                for line in self.s3.objects[(BUCKET_AUDIT, rec_key)]
                .decode("utf-8")
                .strip()
                .splitlines()
            ]
            self.assertEqual(len(filas_stg), len(filas_rec))

            hashes_chunk: List[Tuple[str, str]] = []
            for stg, rec in zip(filas_stg, filas_rec):
                canon_reconstruido = {
                    "catalogo_version": stg["catalogo_version"],
                    "dictamen": stg["dictamen"],
                    "id_solicitud": stg["id_solicitud"],
                    "modelo_version": stg["modelo_version"],
                    "patient_token": stg["patient_token"],
                    "perfil_cobertura": stg["perfil_cobertura"],
                    "porcentaje": stg["porcentaje"],
                    "regla_ids": sorted(stg["regla_ids"]),
                    "spans": {k: list(v) for k, v in sorted(stg["spans_entidades"].items())},
                    "valor_aprobado": stg["valor_aprobado"],
                    "valor_procedimiento": stg["valor_procedimiento"],
                }
                hash_recalculado = calcular_hash_decision(canon_reconstruido)
                # Nivel 1: fila staging coincide con su propio hash_decision
                self.assertEqual(hash_recalculado, stg["hash_decision"])
                # Nivel 2: coincide con el recibo WORM en saom-audit
                self.assertEqual(hash_recalculado, rec["hash_decision"])
                hashes_chunk.append((stg["id_solicitud"], hash_recalculado))

            hashes_chunk.sort(key=lambda x: x[0])
            raiz_chunk_recalculada = hashlib.sha256(
                "".join(h for _, h in hashes_chunk).encode("utf-8")
            ).hexdigest()
            # Nivel 3: raíz del chunk coincide con el manifiesto del lote
            raiz_en_manifiesto = manifiesto["raices_chunks"][cid]["raiz_hash_chunk"]
            self.assertEqual(raiz_chunk_recalculada, raiz_en_manifiesto)
            raices_para_lote.append((cid, raiz_chunk_recalculada))

        self.assertEqual(calcular_raiz_lote(raices_para_lote), manifiesto["raiz_hash_lote"])

        # 7. Escaneo de PII de RNF-05 sobre saom-curated, saom-audit, DynamoDB y logs EMF
        textos_auditar: List[str] = [buffer_stdout.getvalue()]
        for (bucket, _), contenido in self.s3.objects.items():
            if bucket in (BUCKET_CURATED, BUCKET_AUDIT):
                textos_auditar.append(contenido.decode("utf-8"))
        for _, item in self.ddb.items.items():
            textos_auditar.append(json.dumps(item, ensure_ascii=False))

        todo_el_texto = "\n".join(textos_auditar)
        self.assertEqual(coincidencias_pii(todo_el_texto, nombres_pii), [])

        # Verificar que se emitieron 3 líneas de métricas EMF con ThroughputOrdenesPorSegundo
        lineas_emf = [json.loads(line) for line in buffer_stdout.getvalue().strip().splitlines()]
        self.assertEqual(len(lineas_emf), 3)
        for emf in lineas_emf:
            self.assertEqual(emf["Proyecto"], "SAOM-COIL")
            self.assertEqual(emf["LoteId"], lote_id)
            self.assertGreater(emf["ThroughputOrdenesPorSegundo"], 0)

    def test_t3_cabecera_invalida_marca_lote_rechazado_y_no_crea_chunks(self) -> None:
        s3_key = "entidad=IPS/fecha=2026-11-11/lote=LOTE-MALO.csv"
        self.s3.put_object(
            Bucket=BUCKET_RAW,
            Key=s3_key,
            Body=b"col1,col2,col3\n1,2,3\n",
        )
        res = particionador_handler({"bucket": BUCKET_RAW, "key": s3_key})
        self.assertEqual(res["chunks_emitidos"], 0)
        self.assertEqual(res["lotes_rechazados"], 1)
        self.assertEqual(self.sqs.queues.get(self.queue_url, []), [])

        meta = self.ddb.get_item(
            TableName=DDB_TABLE_CONTROL,
            Key={"PK": {"S": "LOTE#LOTE-MALO"}, "SK": {"S": "META"}},
        )["Item"]
        self.assertEqual(meta["estado"]["S"], "RECHAZADO")
        self.assertEqual(meta["chunks_totales"]["N"], "0")
        self.assertIn("Cabecera CSV inválida", meta["motivo_rechazo"]["S"])

    def test_t3_particionar_stream_equivale_a_particionar_archivo(self) -> None:
        filas = [fila_coil(GLOSA_CHV1, id_solicitud=f"CHV-{i:07d}") for i in range(1, 12)]
        raw_bytes = construir_csv_bytes(filas)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = Path(tmp.name)

        try:
            desde_archivo = particionar_csv_en_chunks(tmp_path, "LOTE-CMP", tamano_chunk=4)
            desde_stream = particionar_stream_csv(io.BytesIO(raw_bytes), "LOTE-CMP", tamano_chunk=4)
            self.assertEqual(desde_archivo, desde_stream)
            self.assertEqual([d.num_ordenes for d in desde_stream], [4, 4, 3])
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_t3_descarga_catalogo_desde_s3_cuando_no_esta_en_disco(self) -> None:
        # Subir los catálogos a FakeS3 en BUCKET_REF y simular que no están en ruta local
        prefijo = "catalogo/version=COIL-2026.9"
        self.s3.put_object(
            Bucket=BUCKET_REF,
            Key=f"{prefijo}/COIL_catalogo_servicios_cubiertos.csv",
            Body=(REF_DIR / "COIL_catalogo_servicios_cubiertos.csv").read_bytes(),
        )
        self.s3.put_object(
            Bucket=BUCKET_REF,
            Key=f"{prefijo}/COIL_catalogo_perfiles_cobertura.csv",
            Body=(REF_DIR / "COIL_catalogo_perfiles_cobertura.csv").read_bytes(),
        )
        # Forzar descarga cambiando temporalmente __file__ de lambda_handlers a un directorio sin data/ref
        orig_file = lambda_handlers.__file__
        try:
            lambda_handlers.__file__ = str(Path(tempfile.gettempdir()) / "fake_dir" / "lh.py")
            lambda_handlers._CATALOGO_CACHE = None
            cat = lambda_handlers._obtener_catalogo(version="COIL-2026.9")
            self.assertEqual(cat.version, "COIL-2026.9")
            self.assertEqual(len(cat.servicios), 20)
            self.assertEqual(cat.perfiles["PRIORITARIO"], 100)
        finally:
            lambda_handlers.__file__ = orig_file
            lambda_handlers._CATALOGO_CACHE = None

    def test_t3_radicacion_api_handler_registra_lote_y_genera_url(self) -> None:
        evento_api = {
            "body": json.dumps(
                {"entidad_emisora": "Hospital Central de Chernovia", "lote_id": "LOTE-API-01"}
            )
        }
        resp = radicacion_api_handler(evento_api)
        self.assertEqual(resp["statusCode"], 201)
        cuerpo = json.loads(resp["body"])
        self.assertEqual(cuerpo["lote_id"], "LOTE-API-01")
        self.assertEqual(cuerpo["estado"], "RADICADO")
        self.assertIn("https://", cuerpo["upload_url"])

    def test_t3_empaquetado_zip_contiene_nucleo_handlers_y_catalogos(self) -> None:
        from aws_learner_lab import crear_paquete_lambda
        import zipfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / "bundle.zip"
            info = crear_paquete_lambda(output_zip=zip_path)
            self.assertTrue(zip_path.exists())
            self.assertGreater(info["size_bytes"], 1000)
            with zipfile.ZipFile(zip_path, "r") as zf:
                nombres = set(zf.namelist())
                self.assertEqual(
                    nombres,
                    {
                        "saom_core.py",
                        "lambda_handlers.py",
                        "data/ref/COIL_catalogo_servicios_cubiertos.csv",
                        "data/ref/COIL_catalogo_perfiles_cobertura.csv",
                    },
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
