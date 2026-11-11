"""Adaptadores AWS Lambda para el despliegue en AWS Academy Learner Lab (`LabRole`).

Implementa los handlers serverless definidos en `docs/design/03_arquitectura_tecnica.md` y
en el plan de construcción `docs/plan/04_plan_construccion.md` (Tareas T2, T3 y T4):

1. `radicacion_api_handler`: (Opcional en el prototipo) Registra el lote en DynamoDB `control_lotes`
   y genera una URL prefirmada de carga hacia `saom-raw`.
2. `particionador_handler`: Valida la cabecera CSV en `saom-raw` sin cargar el archivo completo en
   memoria, calcula los rangos exactos de bytes de 5.000 órdenes (`[byte_inicio, byte_fin]`),
   inicializa `META` en DynamoDB (o marca `RECHAZADO` si la cabecera es inválida) y publica los
   descriptores en lotes hacia SQS `chunks-adjudicacion`.
3. `worker_adjudicador_handler`: Consume un descriptor de chunk desde SQS, descarga únicamente el
   rango de bytes (`Range=bytes=inicio-fin`), ejecuta `procesar_rango_bytes_csv()` del núcleo,
   escribe salidas deterministas en `saom-curated` (`staging/` y `rechazos/`) y `saom-audit`
   (`recibos/`), actualiza `control_lotes` de manera idempotente con `TransactWriteItems`,
   emite métricas CloudWatch EMF (incluyendo el throughput `k`) y, al completarse el último chunk,
   calcula `raiz_hash_lote` y escribe `manifiestos/lote=<id>.json` en `saom-audit`.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:  # Permite importar y probar el módulo en entornos sin boto3
    boto3 = None  # type: ignore
    ClientError = Exception  # type: ignore

from saom_core import (
    CATALOGO_VERSION_DEFAULT,
    COLUMNAS_ESPERADAS,
    MODELO_VERSION_DEFAULT,
    CatalogoCOIL,
    DescriptorChunk,
    calcular_raiz_lote,
    procesar_rango_bytes_csv,
)

BUCKET_RAW = os.environ.get("SAOM_BUCKET_RAW", "saom-raw")
BUCKET_REF = os.environ.get("SAOM_BUCKET_REF", "saom-ref")
BUCKET_CURATED = os.environ.get("SAOM_BUCKET_CURATED", "saom-curated")
BUCKET_AUDIT = os.environ.get("SAOM_BUCKET_AUDIT", "saom-audit")
QUEUE_CHUNKS_URL = os.environ.get("SAOM_QUEUE_CHUNKS_URL", "")
DDB_TABLE_CONTROL = os.environ.get("SAOM_DDB_CONTROL", "control_lotes")
SECRET_HMAC_ID = os.environ.get("SAOM_SECRET_HMAC_ID", "saom/hmac-key")
KEY_VERSION_DEFAULT = os.environ.get("SAOM_KEY_VERSION", "hmac-2026-v1")
CHUNK_SIZE = int(os.environ.get("SAOM_CHUNK_SIZE", "5000"))
STREAM_BLOCK_SIZE = 4 * 1024 * 1024  # 4 MB por lectura de stream para particionamiento O(1)

REGEX_FECHA_KEY = re.compile(r"fecha=(\d{4}-\d{2}-\d{2})")
REGEX_LOTE_KEY = re.compile(r"lote=([^/]+?)(?:\.csv)?$")

# Caché en memoria del contenedor Lambda (se reutiliza en invocaciones tibias)
_CATALOGO_CACHE: Optional[CatalogoCOIL] = None
_HMAC_CACHE: Optional[Tuple[bytes, str]] = None
_CLIENT_FACTORY: Optional[Callable[[str], Any]] = None


def configurar_clientes_aws(factory: Optional[Callable[[str], Any]]) -> None:
    """Permite inyectar clientes simulados (fakes/mocks) en pruebas de integración locales."""
    global _CLIENT_FACTORY, _CATALOGO_CACHE, _HMAC_CACHE
    _CLIENT_FACTORY = factory
    _CATALOGO_CACHE = None
    _HMAC_CACHE = None


def _cliente_aws(servicio: str) -> Any:
    if _CLIENT_FACTORY is not None:
        return _CLIENT_FACTORY(servicio)
    if boto3 is None:
        raise RuntimeError(f"boto3 no está disponible para crear el cliente {servicio}")
    return boto3.client(servicio)


def _obtener_catalogo(version: str = CATALOGO_VERSION_DEFAULT) -> CatalogoCOIL:
    """Carga los catálogos COIL desde el paquete local o desde `saom-ref` en `/tmp`."""
    global _CATALOGO_CACHE
    if _CATALOGO_CACHE is not None and _CATALOGO_CACHE.version == version:
        return _CATALOGO_CACHE

    candidatos = [
        Path(__file__).resolve().parent / "data" / "ref",
        Path(__file__).resolve().parent.parent / "data" / "ref",
    ]
    servicios_local: Optional[Path] = None
    perfiles_local: Optional[Path] = None
    for base in candidatos:
        s_path = base / "COIL_catalogo_servicios_cubiertos.csv"
        p_path = base / "COIL_catalogo_perfiles_cobertura.csv"
        if s_path.exists() and p_path.exists():
            servicios_local = s_path
            perfiles_local = p_path
            break

    if servicios_local is None or perfiles_local is None:
        s3 = _cliente_aws("s3")
        tmp_dir = Path("/tmp/saom_ref")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        servicios_local = tmp_dir / "COIL_catalogo_servicios_cubiertos.csv"
        perfiles_local = tmp_dir / "COIL_catalogo_perfiles_cobertura.csv"
        prefijo = f"catalogo/version={version}"
        s3.download_file(
            BUCKET_RAW if not BUCKET_REF else BUCKET_REF,
            f"{prefijo}/COIL_catalogo_servicios_cubiertos.csv",
            str(servicios_local),
        )
        s3.download_file(
            BUCKET_RAW if not BUCKET_REF else BUCKET_REF,
            f"{prefijo}/COIL_catalogo_perfiles_cobertura.csv",
            str(perfiles_local),
        )

    _CATALOGO_CACHE = CatalogoCOIL(servicios_local, perfiles_local, version=version)
    return _CATALOGO_CACHE


def _obtener_clave_hmac() -> Tuple[bytes, str]:
    """Obtiene `(clave_secreta_bytes, key_version)` desde variable de entorno o Secrets Manager."""
    global _HMAC_CACHE
    if _HMAC_CACHE is not None:
        return _HMAC_CACHE

    key_version = os.environ.get("SAOM_KEY_VERSION", KEY_VERSION_DEFAULT)
    env_key = os.environ.get("SAOM_HMAC_SECRET_FALLBACK") or os.environ.get("SAOM_HMAC_SECRET")
    if env_key:
        _HMAC_CACHE = (env_key.encode("utf-8"), key_version)
        return _HMAC_CACHE

    try:
        sm = _cliente_aws("secretsmanager")
        resp = sm.get_secret_value(SecretId=SECRET_HMAC_ID)
        secret_str = resp["SecretString"]
        try:
            parsed = json.loads(secret_str)
            if isinstance(parsed, dict) and "hmac_key" in parsed:
                clave_str = str(parsed["hmac_key"])
                key_version = str(parsed.get("key_version", key_version))
            else:
                clave_str = secret_str
        except ValueError:
            clave_str = secret_str
        _HMAC_CACHE = (clave_str.encode("utf-8"), key_version)
        return _HMAC_CACHE
    except Exception:
        _HMAC_CACHE = (b"coil-chernovia-default-key-2026", key_version)
        return _HMAC_CACHE


def _iter_lineas_binarias(stream: Any, block_size: int = STREAM_BLOCK_SIZE) -> Iterator[bytes]:
    """Itera líneas binarias exactas preservando los terminadores de línea (`\\n` o `\\r\\n`)."""
    buf = b""
    while True:
        chunk = stream.read(block_size)
        if not chunk:
            if buf:
                yield buf
            break
        buf += chunk
        partes = buf.split(b"\n")
        buf = partes.pop()
        for parte in partes:
            yield parte + b"\n"


def particionar_stream_csv(
    stream: Any,
    lote_id: str,
    tamano_chunk: int = CHUNK_SIZE,
) -> List[DescriptorChunk]:
    """Valida la cabecera CSV desde un stream binario y calcula los rangos de bytes por chunk."""
    lineas_iter = _iter_lineas_binarias(stream)
    header_bytes = next(lineas_iter, b"")
    if not header_bytes:
        raise ValueError("Archivo CSV vacío")

    header_str = header_bytes.decode("utf-8-sig", errors="replace").strip()
    cols = [c.strip() for c in header_str.split(",")]
    if cols != COLUMNAS_ESPERADAS:
        raise ValueError(f"Cabecera CSV inválida: {cols}. Se esperaba: {COLUMNAS_ESPERADAS}")

    offset = len(header_bytes)
    chunk_id = 0
    byte_inicio = offset
    conteo = 0
    descriptores: List[DescriptorChunk] = []

    for linea in lineas_iter:
        if not linea.strip():
            offset += len(linea)
            continue
        offset += len(linea)
        conteo += 1
        if conteo == tamano_chunk:
            descriptores.append(
                DescriptorChunk(
                    lote_id=lote_id,
                    chunk_id=chunk_id,
                    byte_inicio=byte_inicio,
                    byte_fin=offset - 1,
                    num_ordenes=conteo,
                )
            )
            chunk_id += 1
            byte_inicio = offset
            conteo = 0

    if conteo > 0:
        descriptores.append(
            DescriptorChunk(
                lote_id=lote_id,
                chunk_id=chunk_id,
                byte_inicio=byte_inicio,
                byte_fin=offset - 1,
                num_ordenes=conteo,
            )
        )

    return descriptores


def _extraer_metadatos_s3_key(key: str) -> Tuple[str, str]:
    """Extrae `(lote_id, fecha_radicacion)` de la clave S3 o usa valores deterministas."""
    match_lote = REGEX_LOTE_KEY.search(key)
    if match_lote:
        lote_id = match_lote.group(1)
    else:
        lote_id = Path(key).stem

    match_fecha = REGEX_FECHA_KEY.search(key)
    if match_fecha:
        fecha_radicacion = match_fecha.group(1)
    else:
        fecha_radicacion = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return lote_id, fecha_radicacion


def _extraer_eventos_s3(event: Dict[str, Any]) -> List[Tuple[str, str, Optional[str]]]:
    """Normaliza eventos de S3 directos, envueltos en SQS (`lotes-recibidos`) o invocación manual."""
    objetos: List[Tuple[str, str, Optional[str]]] = []

    if "bucket" in event and "key" in event:
        objetos.append((str(event["bucket"]), str(event["key"]), event.get("lote_id")))
        return objetos

    for record in event.get("Records", []):
        if "s3" in record:
            bucket = record["s3"]["bucket"]["name"]
            key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
            objetos.append((bucket, key, None))
        elif "body" in record:
            cuerpo = json.loads(record["body"])
            if "Records" in cuerpo:
                for sub in cuerpo["Records"]:
                    if "s3" in sub:
                        bucket = sub["s3"]["bucket"]["name"]
                        key = urllib.parse.unquote_plus(sub["s3"]["object"]["key"])
                        objetos.append((bucket, key, None))
            elif "bucket" in cuerpo and "key" in cuerpo:
                objetos.append((str(cuerpo["bucket"]), str(cuerpo["key"]), cuerpo.get("lote_id")))

    return objetos


def emitir_metrica_emf(
    lote_id: str,
    chunk_id: int,
    ordenes_validas: int,
    ordenes_rechazadas: int,
    ordenes_incertidumbre: int,
    duracion_ms: float,
    throughput_k: float,
) -> Dict[str, Any]:
    """Construye y emite por stdout una línea en formato CloudWatch Embedded Metric Format (EMF).

    No contiene ningún campo PII (Paciente, DNO ni SeguroSocial), cumpliendo RNF-05.
    """
    payload_emf = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": "SAOM/Adjudicacion",
                    "Dimensions": [["Proyecto"], ["Proyecto", "LoteId"]],
                    "Metrics": [
                        {"Name": "OrdenesProcesadas", "Unit": "Count"},
                        {"Name": "OrdenesValidas", "Unit": "Count"},
                        {"Name": "OrdenesRechazadas", "Unit": "Count"},
                        {"Name": "OrdenesIncertidumbre", "Unit": "Count"},
                        {"Name": "DuracionChunkMs", "Unit": "Milliseconds"},
                        {"Name": "ThroughputOrdenesPorSegundo", "Unit": "Count/Second"},
                    ],
                }
            ],
        },
        "Proyecto": "SAOM-COIL",
        "LoteId": lote_id,
        "ChunkId": chunk_id,
        "OrdenesProcesadas": ordenes_validas + ordenes_rechazadas,
        "OrdenesValidas": ordenes_validas,
        "OrdenesRechazadas": ordenes_rechazadas,
        "OrdenesIncertidumbre": ordenes_incertidumbre,
        "DuracionChunkMs": round(duracion_ms, 2),
        "ThroughputOrdenesPorSegundo": round(throughput_k, 2),
    }
    print(json.dumps(payload_emf, ensure_ascii=False))
    return payload_emf


def radicacion_api_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Paso 1 (opcional en el Learner Lab): Registra el lote en DynamoDB y genera URL prefirmada."""
    body = json.loads(event.get("body") or "{}")
    entidad_emisora = body.get("entidad_emisora", "IPS-GENERICA")
    lote_id = body.get("lote_id", f"LOTE-{int(time.time())}")
    fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    s3_key = f"entidad={entidad_emisora}/fecha={fecha_hoy}/lote={lote_id}.csv"
    _, key_version = _obtener_clave_hmac()

    ddb = _cliente_aws("dynamodb")
    s3 = _cliente_aws("s3")

    ddb.put_item(
        TableName=DDB_TABLE_CONTROL,
        Item={
            "PK": {"S": f"LOTE#{lote_id}"},
            "SK": {"S": "META"},
            "entidad_emisora": {"S": entidad_emisora},
            "estado": {"S": "RADICADO"},
            "s3_bucket": {"S": BUCKET_RAW},
            "s3_key": {"S": s3_key},
            "fecha_radicacion": {"S": fecha_hoy},
            "catalogo_version": {"S": CATALOGO_VERSION_DEFAULT},
            "modelo_version": {"S": MODELO_VERSION_DEFAULT},
            "key_version": {"S": key_version},
            "chunks_totales": {"N": "0"},
            "chunks_completados": {"N": "0"},
            "ordenes_validas": {"N": "0"},
            "ordenes_rechazadas": {"N": "0"},
            "ordenes_incertidumbre": {"N": "0"},
            "suma_reclamada": {"N": "0.00"},
            "suma_aprobada": {"N": "0.00"},
        },
    )

    presigned_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": BUCKET_RAW, "Key": s3_key, "ContentType": "text/csv"},
        ExpiresIn=900,
    )

    return {
        "statusCode": 201,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "lote_id": lote_id,
                "estado": "RADICADO",
                "s3_bucket": BUCKET_RAW,
                "s3_key": s3_key,
                "upload_url": presigned_url,
                "expires_in_seconds": 900,
            }
        ),
    }


def particionador_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Pasos 4 y 5 del flujo en AWS: Valida cabecera CSV y emite descriptores de 5.000 filas a SQS."""
    s3 = _cliente_aws("s3")
    sqs = _cliente_aws("sqs")
    ddb = _cliente_aws("dynamodb")
    _, key_version = _obtener_clave_hmac()

    queue_url = os.environ.get("SAOM_QUEUE_CHUNKS_URL", QUEUE_CHUNKS_URL)
    tamano_chunk = int(os.environ.get("SAOM_CHUNK_SIZE", str(CHUNK_SIZE)))

    total_chunks_emitidos = 0
    lotes_rechazados = 0

    for bucket, key, lote_override in _extraer_eventos_s3(event):
        lote_extraido, fecha_radicacion = _extraer_metadatos_s3_key(key)
        lote_id = lote_override or lote_extraido

        obj = s3.get_object(Bucket=bucket, Key=key)
        stream = obj["Body"]

        try:
            descriptores = particionar_stream_csv(
                stream=stream,
                lote_id=lote_id,
                tamano_chunk=tamano_chunk,
            )
        except ValueError as exc:
            # Sección 9 de la arquitectura: CSV sin cabecera válida se marca RECHAZADO y no crea chunks
            ddb.update_item(
                TableName=DDB_TABLE_CONTROL,
                Key={"PK": {"S": f"LOTE#{lote_id}"}, "SK": {"S": "META"}},
                UpdateExpression=(
                    "SET estado = :e, motivo_rechazo = :m, s3_bucket = :b, s3_key = :k, "
                    "fecha_radicacion = :f, chunks_totales = :zero, "
                    "chunks_completados = if_not_exists(chunks_completados, :zero)"
                ),
                ExpressionAttributeValues={
                    ":e": {"S": "RECHAZADO"},
                    ":m": {"S": str(exc)},
                    ":b": {"S": bucket},
                    ":k": {"S": key},
                    ":f": {"S": fecha_radicacion},
                    ":zero": {"N": "0"},
                },
            )
            lotes_rechazados += 1
            continue

        ddb.update_item(
            TableName=DDB_TABLE_CONTROL,
            Key={"PK": {"S": f"LOTE#{lote_id}"}, "SK": {"S": "META"}},
            UpdateExpression=(
                "SET estado = :e, chunks_totales = :ct, s3_bucket = :b, s3_key = :k, "
                "fecha_radicacion = if_not_exists(fecha_radicacion, :f), "
                "catalogo_version = if_not_exists(catalogo_version, :cv), "
                "modelo_version = if_not_exists(modelo_version, :mv), "
                "key_version = if_not_exists(key_version, :kv), "
                "chunks_completados = if_not_exists(chunks_completados, :zero), "
                "ordenes_validas = if_not_exists(ordenes_validas, :zero), "
                "ordenes_rechazadas = if_not_exists(ordenes_rechazadas, :zero), "
                "ordenes_incertidumbre = if_not_exists(ordenes_incertidumbre, :zero), "
                "suma_reclamada = if_not_exists(suma_reclamada, :zero_dec), "
                "suma_aprobada = if_not_exists(suma_aprobada, :zero_dec)"
            ),
            ExpressionAttributeValues={
                ":e": {"S": "EN_PROCESO"},
                ":ct": {"N": str(len(descriptores))},
                ":b": {"S": bucket},
                ":k": {"S": key},
                ":f": {"S": fecha_radicacion},
                ":cv": {"S": CATALOGO_VERSION_DEFAULT},
                ":mv": {"S": MODELO_VERSION_DEFAULT},
                ":kv": {"S": key_version},
                ":zero": {"N": "0"},
                ":zero_dec": {"N": "0.00"},
            },
        )

        mensajes_sqs: List[Dict[str, Any]] = []
        for desc in descriptores:
            cuerpo = {
                "lote_id": desc.lote_id,
                "chunk_id": desc.chunk_id,
                "bucket": bucket,
                "key": key,
                "byte_inicio": desc.byte_inicio,
                "byte_fin": desc.byte_fin,
                "num_ordenes": desc.num_ordenes,
                "fecha_radicacion": fecha_radicacion,
                "catalogo_version": CATALOGO_VERSION_DEFAULT,
                "modelo_version": MODELO_VERSION_DEFAULT,
            }
            mensajes_sqs.append({"Id": str(desc.chunk_id), "MessageBody": json.dumps(cuerpo)})

            if len(mensajes_sqs) == 10:
                _enviar_lote_sqs(sqs, queue_url, mensajes_sqs)
                total_chunks_emitidos += len(mensajes_sqs)
                mensajes_sqs = []

        if mensajes_sqs:
            _enviar_lote_sqs(sqs, queue_url, mensajes_sqs)
            total_chunks_emitidos += len(mensajes_sqs)

    return {
        "chunks_emitidos": total_chunks_emitidos,
        "lotes_rechazados": lotes_rechazados,
    }


def _enviar_lote_sqs(sqs: Any, queue_url: str, entradas: List[Dict[str, Any]]) -> None:
    """Envía hasta 10 mensajes en una sola llamada `send_message_batch` (o individual si no existe)."""
    if hasattr(sqs, "send_message_batch"):
        resp = sqs.send_message_batch(QueueUrl=queue_url, Entries=entradas)
        fallidos = resp.get("Failed", [])
        if fallidos:
            raise RuntimeError(f"Error al publicar chunks en SQS: {fallidos}")
    else:
        for item in entradas:
            sqs.send_message(QueueUrl=queue_url, MessageBody=item["MessageBody"])


def consolidar_y_cerrar_lote(
    lote_id: str,
    s3: Optional[Any] = None,
    ddb: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """Calcula `raiz_hash_lote` cuando `chunks_completados == chunks_totales` y escribe el manifiesto WORM.

    Cumple P-09, P-10 y T4 del plan de construcción: consolidación al terminar los chunks sin Step Functions.
    """
    s3_client = s3 or _cliente_aws("s3")
    ddb_client = ddb or _cliente_aws("dynamodb")
    pk = f"LOTE#{lote_id}"

    meta_resp = ddb_client.get_item(
        TableName=DDB_TABLE_CONTROL,
        Key={"PK": {"S": pk}, "SK": {"S": "META"}},
    )
    meta = meta_resp.get("Item")
    if not meta:
        return None

    chunks_totales = int(meta.get("chunks_totales", {}).get("N", "0"))
    chunks_completados = int(meta.get("chunks_completados", {}).get("N", "0"))
    if chunks_totales <= 0 or chunks_completados < chunks_totales:
        return None

    # Consultar todos los items CHUNK# del lote
    items_chunks: List[Dict[str, Any]] = []
    kwargs_query: Dict[str, Any] = {
        "TableName": DDB_TABLE_CONTROL,
        "KeyConditionExpression": "PK = :pk AND begins_with(SK, :sk_prefix)",
        "ExpressionAttributeValues": {
            ":pk": {"S": pk},
            ":sk_prefix": {"S": "CHUNK#"},
        },
    }
    while True:
        q_resp = ddb_client.query(**kwargs_query)
        items_chunks.extend(q_resp.get("Items", []))
        last_key = q_resp.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs_query["ExclusiveStartKey"] = last_key

    if len(items_chunks) < chunks_totales:
        return None

    raices_chunks: List[Tuple[int, str]] = []
    for item in items_chunks:
        sk_str = item["SK"]["S"]  # CHUNK#00000
        c_id = int(sk_str.split("#")[1])
        c_hash = item["raiz_hash_chunk"]["S"]
        raices_chunks.append((c_id, c_hash))

    raices_chunks.sort(key=lambda x: x[0])
    raiz_hash_lote = calcular_raiz_lote(raices_chunks)

    ordenes_validas = int(meta.get("ordenes_validas", {}).get("N", "0"))
    ordenes_rechazadas = int(meta.get("ordenes_rechazadas", {}).get("N", "0"))
    ordenes_incertidumbre = int(meta.get("ordenes_incertidumbre", {}).get("N", "0"))
    suma_reclamada = meta.get("suma_reclamada", {}).get("N", "0.00")
    suma_aprobada = meta.get("suma_aprobada", {}).get("N", "0.00")
    catalogo_version = meta.get("catalogo_version", {}).get("S", CATALOGO_VERSION_DEFAULT)
    modelo_version = meta.get("modelo_version", {}).get("S", MODELO_VERSION_DEFAULT)
    key_version = meta.get("key_version", {}).get("S", KEY_VERSION_DEFAULT)
    fecha_radicacion = meta.get("fecha_radicacion", {}).get(
        "S", datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )

    manifiesto = {
        "lote_id": lote_id,
        "fecha_radicacion": fecha_radicacion,
        "estado": "PROCESADO",
        "catalogo_version": catalogo_version,
        "modelo_version": modelo_version,
        "key_version": key_version,
        "chunks_totales": chunks_totales,
        "chunks_completados": chunks_completados,
        "ordenes_totales": ordenes_validas + ordenes_rechazadas,
        "ordenes_validas": ordenes_validas,
        "ordenes_rechazadas": ordenes_rechazadas,
        "ordenes_incertidumbre": ordenes_incertidumbre,
        "suma_reclamada": f"{Decimal(suma_reclamada):.2f}",
        "suma_aprobada": f"{Decimal(suma_aprobada):.2f}",
        "raiz_hash_lote": raiz_hash_lote,
        "raices_chunks": [
            {"chunk_id": cid, "raiz_hash_chunk": chash} for cid, chash in raices_chunks
        ],
    }

    manifiesto_key = f"manifiestos/lote={lote_id}.json"
    s3_client.put_object(
        Bucket=BUCKET_AUDIT,
        Key=manifiesto_key,
        Body=(json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )

    ddb_client.update_item(
        TableName=DDB_TABLE_CONTROL,
        Key={"PK": {"S": pk}, "SK": {"S": "META"}},
        UpdateExpression="SET estado = :e, raiz_hash_lote = :rhl, manifiesto_key = :mk",
        ExpressionAttributeValues={
            ":e": {"S": "PROCESADO"},
            ":rhl": {"S": raiz_hash_lote},
            ":mk": {"S": manifiesto_key},
        },
    )

    return manifiesto


def worker_adjudicador_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Pasos 6 a 9 del flujo en AWS: Adjudica un chunk de 5.000 órdenes de manera idempotente."""
    s3 = _cliente_aws("s3")
    ddb = _cliente_aws("dynamodb")
    clave_hmac, _ = _obtener_clave_hmac()

    procesados = 0
    duplicados_ignorados = 0
    lotes_cerrados: List[str] = []

    for record in event.get("Records", []):
        payload = json.loads(record["body"])
        lote_id = str(payload["lote_id"])
        chunk_id = int(payload["chunk_id"])
        bucket = str(payload.get("bucket", BUCKET_RAW))
        key = str(payload["key"])
        byte_inicio = int(payload["byte_inicio"])
        byte_fin = int(payload["byte_fin"])
        num_ordenes = int(payload.get("num_ordenes", CHUNK_SIZE))
        catalogo_version = str(payload.get("catalogo_version", CATALOGO_VERSION_DEFAULT))
        modelo_version = str(payload.get("modelo_version", MODELO_VERSION_DEFAULT))
        fecha_radicacion = str(
            payload.get("fecha_radicacion") or _extraer_metadatos_s3_key(key)[1]
        )

        catalogo = _obtener_catalogo(version=catalogo_version)

        rango = f"bytes={byte_inicio}-{byte_fin}"
        resp = s3.get_object(Bucket=bucket, Key=key, Range=rango)
        bloque_bytes = resp["Body"].read()

        descriptor = DescriptorChunk(
            lote_id=lote_id,
            chunk_id=chunk_id,
            byte_inicio=byte_inicio,
            byte_fin=byte_fin,
            num_ordenes=num_ordenes,
        )

        t_inicio = time.perf_counter()
        resultado = procesar_rango_bytes_csv(
            bloque_bytes=bloque_bytes,
            descriptor=descriptor,
            catalogo=catalogo,
            clave_hmac=clave_hmac,
            modelo_version=modelo_version,
            retener_decisiones=True,
        )
        duracion_s = max(time.perf_counter() - t_inicio, 1e-6)
        duracion_ms = duracion_s * 1000.0
        total_ordenes_chunk = resultado.ordenes_validas + resultado.ordenes_rechazadas
        throughput_k = total_ordenes_chunk / duracion_s

        # Claves deterministas en S3 (reprocesar un chunk sobrescribe exactamente el mismo objeto)
        staging_key = f"staging/fecha={fecha_radicacion}/lote={lote_id}/chunk={chunk_id:05d}.jsonl"
        recibos_key = f"recibos/fecha={fecha_radicacion}/lote={lote_id}/chunk={chunk_id:05d}.jsonl"

        lineas_staging: List[str] = []
        lineas_recibos: List[str] = []
        for d in resultado.decisiones:
            canon = d.to_canonical_dict()
            recibo_worm = {
                **canon,
                "hash_decision": d.hash_decision,
                "lote_id": d.lote_id,
                "chunk_id": d.chunk_id,
                "raiz_hash_chunk": resultado.raiz_hash_chunk,
            }
            lineas_recibos.append(json.dumps(recibo_worm, sort_keys=True, ensure_ascii=False))

            fila_iceberg = {
                "id_solicitud": d.id_solicitud,
                "lote_id": d.lote_id,
                "chunk_id": d.chunk_id,
                "fecha_solicitud": d.fecha_solicitud,
                "fecha_radicacion": fecha_radicacion,
                "medio_emisor": d.medio_emisor,
                "entidad_emisora": d.entidad_emisora,
                "patient_token": d.patient_token,
                "glosa_enmascarada": d.glosa_enmascarada,
                "edad": d.edad,
                "servicio_solicitado": d.servicio_solicitado,
                "codigo_servicio": d.codigo_servicio,
                "categoria_servicio": d.categoria_servicio,
                "medicaciones": d.medicaciones,
                "spans_entidades": d.spans,
                "dictamen": d.dictamen,
                "causal_glosa": d.causal_glosa,
                "regla_ids": d.regla_ids,
                "catalogo_version": d.catalogo_version,
                "modelo_version": d.modelo_version,
                "perfil_cobertura": d.perfil_cobertura,
                "porcentaje": d.porcentaje,
                "valor_procedimiento": f"{d.valor_procedimiento:.2f}",
                "valor_aprobado": f"{d.valor_aprobado:.2f}",
                "valor_copago": f"{d.valor_copago:.2f}",
                "confianza": d.confianza,
                "flags": d.flags,
                "hash_decision": d.hash_decision,
            }
            lineas_staging.append(json.dumps(fila_iceberg, ensure_ascii=False))

        s3.put_object(
            Bucket=BUCKET_CURATED,
            Key=staging_key,
            Body=("\n".join(lineas_staging) + ("\n" if lineas_staging else "")).encode("utf-8"),
        )
        s3.put_object(
            Bucket=BUCKET_AUDIT,
            Key=recibos_key,
            Body=("\n".join(lineas_recibos) + ("\n" if lineas_recibos else "")).encode("utf-8"),
        )

        if resultado.rechazos:
            rechazos_key = (
                f"rechazos/fecha={fecha_radicacion}/lote={lote_id}/chunk={chunk_id:05d}.jsonl"
            )
            body_rech = (
                "\n".join(
                    json.dumps(
                        {
                            "lote_id": r.lote_id,
                            "chunk_id": r.chunk_id,
                            "linea_num": r.linea_num,
                            "id_solicitud": r.id_solicitud,
                            "estado": r.estado,
                            "motivo": r.motivo,
                        },
                        ensure_ascii=False,
                    )
                    for r in resultado.rechazos
                )
                + "\n"
            )
            s3.put_object(
                Bucket=BUCKET_CURATED,
                Key=rechazos_key,
                Body=body_rech.encode("utf-8"),
            )

        # Idempotencia condicional en DynamoDB (sección 7.2 y RNF-06)
        es_duplicado = False
        try:
            ddb.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": DDB_TABLE_CONTROL,
                            "Item": {
                                "PK": {"S": f"LOTE#{lote_id}"},
                                "SK": {"S": f"CHUNK#{chunk_id:05d}"},
                                "estado": {"S": "COMPLETADO"},
                                "n_ordenes": {"N": str(total_ordenes_chunk)},
                                "ordenes_validas": {"N": str(resultado.ordenes_validas)},
                                "ordenes_rechazadas": {"N": str(resultado.ordenes_rechazadas)},
                                "ordenes_cubiertas": {"N": str(resultado.ordenes_cubiertas)},
                                "ordenes_no_cubiertas": {"N": str(resultado.ordenes_no_cubiertas)},
                                "ordenes_incertidumbre": {
                                    "N": str(resultado.ordenes_incertidumbre)
                                },
                                "suma_reclamada": {"N": f"{resultado.suma_reclamada:.2f}"},
                                "suma_aprobada": {"N": f"{resultado.suma_aprobada:.2f}"},
                                "raiz_hash_chunk": {"S": resultado.raiz_hash_chunk},
                                "clave_resultado": {"S": staging_key},
                                "clave_recibos": {"S": recibos_key},
                                "duracion_ms": {"N": f"{duracion_ms:.2f}"},
                                "k_ordenes_seg": {"N": f"{throughput_k:.2f}"},
                            },
                            "ConditionExpression": (
                                "attribute_not_exists(SK) OR estado <> :comp"
                            ),
                            "ExpressionAttributeValues": {":comp": {"S": "COMPLETADO"}},
                        }
                    },
                    {
                        "Update": {
                            "TableName": DDB_TABLE_CONTROL,
                            "Key": {"PK": {"S": f"LOTE#{lote_id}"}, "SK": {"S": "META"}},
                            "UpdateExpression": (
                                "ADD chunks_completados :uno, "
                                "ordenes_validas :ov, "
                                "ordenes_rechazadas :or, "
                                "ordenes_incertidumbre :oi, "
                                "suma_reclamada :sr, "
                                "suma_aprobada :sa"
                            ),
                            "ExpressionAttributeValues": {
                                ":uno": {"N": "1"},
                                ":ov": {"N": str(resultado.ordenes_validas)},
                                ":or": {"N": str(resultado.ordenes_rechazadas)},
                                ":oi": {"N": str(resultado.ordenes_incertidumbre)},
                                ":sr": {"N": f"{resultado.suma_reclamada:.2f}"},
                                ":sa": {"N": f"{resultado.suma_aprobada:.2f}"},
                            },
                        }
                    },
                ]
            )
        except Exception as exc:
            codigo_error = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
            if codigo_error == "TransactionCanceledException" or "TransactionCanceledException" in str(
                exc
            ):
                es_duplicado = True
                duplicados_ignorados += 1
            else:
                raise

        if not es_duplicado:
            procesados += 1
            emitir_metrica_emf(
                lote_id=lote_id,
                chunk_id=chunk_id,
                ordenes_validas=resultado.ordenes_validas,
                ordenes_rechazadas=resultado.ordenes_rechazadas,
                ordenes_incertidumbre=resultado.ordenes_incertidumbre,
                duracion_ms=duracion_ms,
                throughput_k=throughput_k,
            )
            manifiesto = consolidar_y_cerrar_lote(lote_id=lote_id, s3=s3, ddb=ddb)
            if manifiesto is not None:
                lotes_cerrados.append(lote_id)

    return {
        "chunks_procesados": procesados,
        "duplicados_ignorados": duplicados_ignorados,
        "lotes_cerrados": lotes_cerrados,
    }
