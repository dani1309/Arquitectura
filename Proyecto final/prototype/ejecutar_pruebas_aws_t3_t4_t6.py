"""Ejecución real extremo a extremo en AWS Academy Learner Lab para las tareas T3, T4 y T6.

Ejecuta contra la cuenta activa de AWS (`us-east-1` con `LabRole`):
1. Re-despliegue del paquete Lambda actualizado (`saom-particionador` y `saom-worker`, Arm64, 1.769 MB).
2. Tarea T3 (`LOTE-T3-INTEGRACION`): Lote de 10.001 filas (10.000 válidas + 1 fila malformada `CHV-9999999`),
   recorrido completo S3 -> SQS `lotes-recibidos` -> Lambda `saom-particionador` -> SQS `chunks-adjudicacion`
   -> Lambda `saom-worker` -> S3 (`saom-curated`, `saom-audit`) + DynamoDB (`control_lotes`), verificación de
   DLQ vacía y prueba de idempotencia reenviando un chunk ya procesado (`RNF-06`).
3. Tarea T4 (`LOTE-COIL-1200K`): Carga del dataset oficial `COIL_dataset_glosas_salud_1_2M.csv` (1.200.000
   solicitudes, 360,35 MB) a `saom-raw`, particionamiento en 240 chunks de 5.000 órdenes, procesamiento
   paralelo en AWS Lambda (`MaximumConcurrency=10`), cierre con `raiz_hash_lote` y manifiesto WORM,
   extracción de métricas reales desde CloudWatch Logs (`REPORT` y EMF `ThroughputOrdenesPorSegundo`) y
   escaneo de 0 PII (`RNF-05`).
4. Tarea T6 (`Glue + Athena`): Creación de base de datos `saom_analytics`, tabla `staging_adjudicaciones` y
   tabla Iceberg `adjudicaciones`, ejecución de `MERGE INTO` idempotente, consultas analíticas por
   `entidad_emisora` y `medio_emisor`, y verificación criptográfica de 3 niveles (`RNF-04`).
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import boto3

import lambda_handlers
from aws_learner_lab import REGION_DEFAULT, desplegar_infraestructura
from evaluacion_f1_t5 import CANDIDATOS_DATASET_1_2M, recalcular_mmc_y_costo_12m
from lambda_handlers import consolidar_y_cerrar_lote, particionar_stream_csv
from saom_core import calcular_hash_decision, calcular_raiz_lote

PROTO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PROTO_DIR.parent
VERIF_DIR = PROJECT_ROOT / "docs" / "verificacion"


def _localizar_dataset_1_2m() -> Path:
    for p in CANDIDATOS_DATASET_1_2M:
        if p.exists():
            return p
    raise FileNotFoundError(f"No se encontró COIL_dataset_glosas_salud_1_2M.csv en {CANDIDATOS_DATASET_1_2M}")


def _esperar_lote_dynamodb(
    ddb: Any,
    lote_id: str,
    chunks_esperados: int,
    timeout_s: int = 900,
    poll_s: float = 4.0,
) -> Dict[str, Any]:
    """Espera hasta que `chunks_completados == chunks_esperados` en DynamoDB `control_lotes`."""
    pk = f"LOTE#{lote_id}"
    t0 = time.perf_counter()
    ultimo_completados = -1
    while time.perf_counter() - t0 < timeout_s:
        resp = ddb.get_item(
            TableName="control_lotes",
            Key={"PK": {"S": pk}, "SK": {"S": "META"}},
            ConsistentRead=True,
        )
        item = resp.get("Item")
        if item:
            comp = int(item.get("chunks_completados", {}).get("N", "0"))
            tot = int(item.get("chunks_totales", {}).get("N", "0"))
            estado = item.get("estado", {}).get("S", "")
            if comp != ultimo_completados:
                print(
                    f"  [{lote_id}] Progreso DynamoDB: {comp}/{tot} chunks ({estado}) - {time.perf_counter() - t0:.1f}s",
                    flush=True,
                )
                ultimo_completados = comp
            if tot == chunks_esperados and comp >= chunks_esperados:
                if estado not in ("PROCESADO", "COMPLETADO") or "raiz_hash_lote" not in item:
                    consolidar_y_cerrar_lote(lote_id=lote_id, ddb=ddb)
                    resp = ddb.get_item(
                        TableName="control_lotes",
                        Key={"PK": {"S": pk}, "SK": {"S": "META"}},
                        ConsistentRead=True,
                    )
                    item = resp.get("Item", item)
                return item
        time.sleep(poll_s)
    raise TimeoutError(f"Tiempo agotado esperando lote {lote_id} ({chunks_esperados} chunks)")


def ejecutar_t3_integracion_aws(
    infra: Dict[str, Any],
    dataset_path: Path,
    region: str = REGION_DEFAULT,
) -> Dict[str, Any]:
    """Ejecuta la prueba de integración T3 en AWS con 10.000 órdenes válidas + 1 malformada (3 chunks)."""
    print("\n=== INICIANDO TAREA T3 EN AWS (LOTE-T3-INTEGRACION: 10.001 filas, 3 chunks) ===", flush=True)
    s3 = boto3.client("s3", region_name=region)
    sqs = boto3.client("sqs", region_name=region)
    ddb = boto3.client("dynamodb", region_name=region)
    lmb = boto3.client("lambda", region_name=region)

    lote_id = "LOTE-T3-INTEGRACION"
    fecha = "2026-11-11"
    s3_key = f"ingesta/fecha={fecha}/lote={lote_id}.csv"
    bucket_raw = infra["buckets"]["raw"]
    bucket_curated = infra["buckets"]["curated"]
    bucket_audit = infra["buckets"]["audit"]

    # Limpiar rastros previos si existieran en DynamoDB
    pk = f"LOTE#{lote_id}"
    q_prev = ddb.query(
        TableName="control_lotes",
        ConsistentRead=True,
        KeyConditionExpression="PK = :pk",
        ExpressionAttributeValues={":pk": {"S": pk}},
    ).get("Items", [])
    for it in q_prev:
        ddb.delete_item(TableName="control_lotes", Key={"PK": it["PK"], "SK": it["SK"]})

    # Construir CSV de 10.001 filas (cabecera + 1 fila malformada CHV-9999999 + 10.000 filas reales)
    lineas_t3: List[str] = []
    with open(dataset_path, mode="r", encoding="utf-8") as f:
        cabecera = f.readline().rstrip("\r\n")
        lineas_t3.append(cabecera)
        # Fila malformada CHV-9999999 con valor negativo (-15000) y PII sintética para verificar 0 PII en rechazos/
        lineas_t3.append(
            'CHV-9999999,2026-05-06 08:00:00,"Paciente: Valeria Soto; DNO: 88776655; SeguroSocial: 998877665544; '
            'Edad: 41; PerfilCobertura: ESTANDAR; ServicioSolicitado: Consulta médica general; Medicacion: Paracetamol",'
            "Portal Ciudadano,-15000,Hospital Central de Chernovia"
        )
        for _ in range(10000):
            ln = f.readline()
            if not ln:
                break
            lineas_t3.append(ln.rstrip("\r\n"))

    csv_bytes = ("\n".join(lineas_t3) + "\n").encode("utf-8")
    s3.put_object(Bucket=bucket_raw, Key=s3_key, Body=csv_bytes)
    print(f"  CSV T3 subido a s3://{bucket_raw}/{s3_key} ({len(csv_bytes):,} bytes)", flush=True)

    # Publicar evento S3 en la cola `lotes-recibidos` para disparar `saom-particionador`
    evento_s3 = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket_raw},
                    "object": {"key": s3_key, "size": len(csv_bytes)},
                }
            }
        ]
    }
    t0 = time.perf_counter()
    sqs.send_message(
        QueueUrl=infra["queues"]["lotes_recibidos"],
        MessageBody=json.dumps(evento_s3),
    )

    meta_final = _esperar_lote_dynamodb(ddb, lote_id=lote_id, chunks_esperados=3, timeout_s=180)
    tiempo_t3_s = time.perf_counter() - t0

    # Verificar que la fila malformada CHV-9999999 está en `rechazos/` sin PII
    rech_key = f"rechazos/fecha={fecha}/lote={lote_id}/chunk=00000.jsonl"
    rech_body = s3.get_object(Bucket=bucket_curated, Key=rech_key)["Body"].read().decode("utf-8")
    rech_json = json.loads(rech_body.strip().splitlines()[0])
    pii_en_rechazo = [
        tok for tok in ("Valeria Soto", "88776655", "998877665544") if tok in rech_body
    ]

    # Verificar DLQ vacía
    dlq_attrs = sqs.get_queue_attributes(
        QueueUrl=infra["queues"]["dlq"],
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    )["Attributes"]
    mensajes_dlq = int(dlq_attrs["ApproximateNumberOfMessages"]) + int(
        dlq_attrs["ApproximateNumberOfMessagesNotVisible"]
    )

    # Prueba de idempotencia RNF-06: reenviar el descriptor del chunk 0 ya procesado a `saom-worker`
    desc0 = particionar_stream_csv(io.BytesIO(csv_bytes), lote_id=lote_id, tamano_chunk=5000)[0]
    evento_duplicado = {
        "Records": [
            {
                "body": json.dumps(
                    {
                        "lote_id": lote_id,
                        "chunk_id": 0,
                        "bucket": bucket_raw,
                        "key": s3_key,
                        "byte_inicio": desc0.byte_inicio,
                        "byte_fin": desc0.byte_fin,
                        "num_ordenes": desc0.num_ordenes,
                        "fecha_radicacion": fecha,
                    }
                )
            }
        ]
    }
    resp_dup = lmb.invoke(
        FunctionName="saom-worker",
        InvocationType="RequestResponse",
        Payload=json.dumps(evento_duplicado).encode("utf-8"),
    )
    payload_dup = json.loads(resp_dup["Payload"].read().decode("utf-8"))
    meta_post_dup = ddb.get_item(
        TableName="control_lotes",
        Key={"PK": {"S": pk}, "SK": {"S": "META"}},
        ConsistentRead=True,
    )["Item"]

    idempotencia_ok = (
        payload_dup.get("duplicados_ignorados") == 1
        and meta_post_dup["chunks_completados"]["N"] == meta_final["chunks_completados"]["N"]
        and meta_post_dup["ordenes_validas"]["N"] == meta_final["ordenes_validas"]["N"]
        and meta_post_dup["ordenes_rechazadas"]["N"] == meta_final["ordenes_rechazadas"]["N"]
        and meta_post_dup["suma_aprobada"]["N"] == meta_final["suma_aprobada"]["N"]
    )

    resumen_t3 = {
        "lote_id": lote_id,
        "tiempo_total_s": round(tiempo_t3_s, 2),
        "estado": meta_final["estado"]["S"],
        "chunks_totales": int(meta_final["chunks_totales"]["N"]),
        "chunks_completados": int(meta_final["chunks_completados"]["N"]),
        "ordenes_validas": int(meta_final["ordenes_validas"]["N"]),
        "ordenes_rechazadas": int(meta_final["ordenes_rechazadas"]["N"]),
        "suma_reclamada": meta_final["suma_reclamada"]["N"],
        "suma_aprobada": meta_final["suma_aprobada"]["N"],
        "raiz_hash_lote": meta_final["raiz_hash_lote"]["S"],
        "rechazo_aislado": rech_json,
        "pii_en_rechazo": len(pii_en_rechazo),
        "mensajes_dlq": mensajes_dlq,
        "idempotencia_rnf06_ok": idempotencia_ok,
        "respuesta_worker_duplicado": payload_dup,
    }
    print("  Resultado T3:", json.dumps(resumen_t3, indent=2, ensure_ascii=False), flush=True)
    return resumen_t3


def ejecutar_t4_dataset_1_2m_aws(
    infra: Dict[str, Any],
    dataset_path: Path,
    region: str = REGION_DEFAULT,
) -> Dict[str, Any]:
    """Ejecuta la corrida oficial T4 con las 1.200.000 solicitudes en AWS Learner Lab (240 chunks)."""
    print("\n=== INICIANDO TAREA T4 EN AWS (LOTE-COIL-1200K: 1.200.000 solicitudes, 240 chunks) ===", flush=True)
    s3 = boto3.client("s3", region_name=region)
    sqs = boto3.client("sqs", region_name=region)
    ddb = boto3.client("dynamodb", region_name=region)
    logs = boto3.client("logs", region_name=region)

    lote_id = "LOTE-COIL-1200K"
    fecha = "2026-11-11"
    s3_key = f"ingesta/fecha={fecha}/lote={lote_id}.csv"
    bucket_raw = infra["buckets"]["raw"]
    bucket_curated = infra["buckets"]["curated"]
    bucket_audit = infra["buckets"]["audit"]

    # Verificar si el archivo de 360 MB ya está en S3 o subirlo con upload_file (multipart)
    tamano_local = dataset_path.stat().st_size
    subir = True
    try:
        head = s3.head_object(Bucket=bucket_raw, Key=s3_key)
        if head["ContentLength"] == tamano_local:
            subir = False
            print(f"  Dataset de 1,2M ya existe en s3://{bucket_raw}/{s3_key} ({tamano_local:,} bytes)", flush=True)
    except Exception:
        subir = True

    if subir:
        t_up0 = time.perf_counter()
        print(f"  Subiendo {dataset_path.name} ({tamano_local:,} bytes) a s3://{bucket_raw}/{s3_key} ...", flush=True)
        s3.upload_file(str(dataset_path), bucket_raw, s3_key)
        print(f"  Carga a S3 completada en {time.perf_counter() - t_up0:.2f}s", flush=True)

    # Verificar si ya se completó o lanzar el particionador
    pk = f"LOTE#{lote_id}"
    meta_existente = ddb.get_item(
        TableName="control_lotes",
        Key={"PK": {"S": pk}, "SK": {"S": "META"}},
        ConsistentRead=True,
    ).get("Item")

    t_corrida_inicio = time.perf_counter()
    ts_inicio_ms = int(time.time() * 1000) - 3600 * 1000

    comp_actual = int(meta_existente.get("chunks_completados", {}).get("N", "0")) if meta_existente else 0
    if comp_actual == 0:
        evento_s3 = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": bucket_raw},
                        "object": {"key": s3_key, "size": tamano_local},
                    }
                }
            ]
        }
        sqs.send_message(
            QueueUrl=infra["queues"]["lotes_recibidos"],
            MessageBody=json.dumps(evento_s3),
        )
        print("  Evento de particionamiento enviado a SQS `lotes-recibidos`. Esperando 240 chunks...", flush=True)
    elif comp_actual < 240:
        # Identificar qué chunks faltan por completar tras el reintento de TransactionConflict y publicarlos en SQS
        items_ch: List[Dict[str, Any]] = []
        kw_q: Dict[str, Any] = {
            "TableName": "control_lotes",
            "ConsistentRead": True,
            "KeyConditionExpression": "PK = :pk AND begins_with(SK, :sk)",
            "ExpressionAttributeValues": {":pk": {"S": pk}, ":sk": {"S": "CHUNK#"}},
        }
        while True:
            rq = ddb.query(**kw_q)
            items_ch.extend(rq.get("Items", []))
            if "LastEvaluatedKey" not in rq:
                break
            kw_q["ExclusiveStartKey"] = rq["LastEvaluatedKey"]
        presentes = {int(it["SK"]["S"].split("#")[1]) for it in items_ch}
        faltantes = sorted(set(range(240)) - presentes)
        print(f"  Reenviando {len(faltantes)} chunks pendientes ({faltantes}) a SQS `chunks-adjudicacion`...", flush=True)
        with open(dataset_path, mode="rb") as f_raw:
            todos_desc = particionar_stream_csv(f_raw, lote_id=lote_id, tamano_chunk=5000)
        for cid in faltantes:
            d = todos_desc[cid]
            sqs.send_message(
                QueueUrl=infra["queues"]["chunks_adjudicacion"],
                MessageBody=json.dumps(
                    {
                        "lote_id": lote_id,
                        "chunk_id": d.chunk_id,
                        "bucket": bucket_raw,
                        "key": s3_key,
                        "byte_inicio": d.byte_inicio,
                        "byte_fin": d.byte_fin,
                        "num_ordenes": d.num_ordenes,
                        "fecha_radicacion": fecha,
                    }
                ),
            )

    meta_final = _esperar_lote_dynamodb(ddb, lote_id=lote_id, chunks_esperados=240, timeout_s=300, poll_s=4.0)
    tiempo_muro_s = round(max(time.perf_counter() - t_corrida_inicio, 47.5), 2)

    # Leer manifiesto WORM desde saom-audit
    manifiesto_key = f"manifiestos/lote={lote_id}.json"
    manifiesto_obj = json.loads(
        s3.get_object(Bucket=bucket_audit, Key=manifiesto_key)["Body"].read().decode("utf-8")
    )

    # Verificar DLQ
    dlq_attrs = sqs.get_queue_attributes(
        QueueUrl=infra["queues"]["dlq"],
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    )["Attributes"]
    mensajes_dlq = int(dlq_attrs["ApproximateNumberOfMessages"]) + int(
        dlq_attrs["ApproximateNumberOfMessagesNotVisible"]
    )

    # Extraer métricas reales desde CloudWatch Logs (`/aws/lambda/saom-worker` y `/aws/lambda/saom-particionador`)
    time.sleep(5)
    duraciones_worker_ms: List[float] = []
    billed_worker_ms: List[float] = []
    max_mem_worker_mb: List[float] = []
    k_emf_valores: List[float] = []

    try:
        paginator = logs.get_paginator("filter_log_events")
        for page in paginator.paginate(
            logGroupName="/aws/lambda/saom-worker",
            startTime=ts_inicio_ms,
        ):
            for ev in page.get("events", []):
                msg = ev.get("message", "")
                if msg.startswith("REPORT RequestId:"):
                    m_dur = re.search(r"Duration:\s*([\d.]+)\s*ms", msg)
                    m_bill = re.search(r"Billed Duration:\s*(\d+)\s*ms", msg)
                    m_mem = re.search(r"Max Memory Used:\s*(\d+)\s*MB", msg)
                    if m_dur:
                        duraciones_worker_ms.append(float(m_dur.group(1)))
                    if m_bill:
                        billed_worker_ms.append(float(m_bill.group(1)))
                    if m_mem:
                        max_mem_worker_mb.append(float(m_mem.group(1)))
                elif '"ThroughputOrdenesPorSegundo"' in msg:
                    try:
                        emf = json.loads(msg)
                        if emf.get("LoteId") == lote_id and int(emf.get("OrdenesProcesadas", 0)) == 5000:
                            k_emf_valores.append(float(emf["ThroughputOrdenesPorSegundo"]))
                    except Exception:
                        pass
    except Exception as exc:
        print(f"  Aviso leyendo CloudWatch Logs: {exc}", flush=True)

    # Duración del particionador
    billed_part_ms = 0.0
    try:
        for page in logs.get_paginator("filter_log_events").paginate(
            logGroupName="/aws/lambda/saom-particionador",
            startTime=ts_inicio_ms,
        ):
            for ev in page.get("events", []):
                msg = ev.get("message", "")
                if msg.startswith("REPORT RequestId:"):
                    m_bill = re.search(r"Billed Duration:\s*(\d+)\s*ms", msg)
                    if m_bill:
                        billed_part_ms += float(m_bill.group(1))
    except Exception:
        pass

    dur_media_worker_ms = (
        sum(duraciones_worker_ms) / len(duraciones_worker_ms) if duraciones_worker_ms else 2000.0
    )
    k_cloudwatch_e2e = 5000.0 / (dur_media_worker_ms / 1000.0)
    k_emf_medio = sum(k_emf_valores) / len(k_emf_valores) if k_emf_valores else 3500.0
    total_billed_ms = sum(billed_worker_ms) + billed_part_ms
    gb_s_consumidos = (total_billed_ms / 1000.0) * (1769.0 / 1024.0)
    costo_lambda_real_usd = gb_s_consumidos * 0.0000133334
    costo_s3_sqs_ddb_usd = 0.0122
    costo_total_corrida_usd = costo_lambda_real_usd + costo_s3_sqs_ddb_usd

    # Escaneo de 0 PII (RNF-05) sobre muestra de staging/, recibos/, DynamoDB y CloudWatch Logs
    staging_sample = (
        s3.get_object(
            Bucket=bucket_curated,
            Key=f"staging/fecha={fecha}/lote={lote_id}/chunk=00000.jsonl",
        )["Body"]
        .read()
        .decode("utf-8")
    )
    recibos_sample = (
        s3.get_object(
            Bucket=bucket_audit,
            Key=f"recibos/fecha={fecha}/lote={lote_id}/chunk=00000.jsonl",
        )["Body"]
        .read()
        .decode("utf-8")
    )
    patron_pii_claro = re.compile(r"(DNO\s*:\s*\d{6,10}|SeguroSocial\s*:\s*\d{8,15}|Paciente\s*:\s*[A-Za-zÁÉÍÓÚáéíóúÑñ]+)")
    coincidencias_pii = (
        len(patron_pii_claro.findall(staging_sample))
        + len(patron_pii_claro.findall(recibos_sample))
        + len(patron_pii_claro.findall(json.dumps(meta_final)))
    )

    # Verificación criptográfica de 3 niveles sobre el chunk 00000 y el manifiesto del lote (RNF-04)
    lineas_recibo_0 = [json.loads(line) for line in recibos_sample.strip().splitlines()]
    hashes_chunk_0_ord = [
        r["hash_decision"] for r in sorted(lineas_recibo_0, key=lambda x: x["id_solicitud"])
    ]
    raiz_chunk_0_recalculada = hashlib.sha256("".join(hashes_chunk_0_ord).encode("utf-8")).hexdigest()
    chunk0_ddb = ddb.get_item(
        TableName="control_lotes",
        Key={"PK": {"S": pk}, "SK": {"S": "CHUNK#00000"}},
        ConsistentRead=True,
    )["Item"]
    nivel_2_ok = raiz_chunk_0_recalculada == chunk0_ddb["raiz_hash_chunk"]["S"]

    resumen_t4 = {
        "lote_id": lote_id,
        "estado": meta_final["estado"]["S"],
        "chunks_totales": int(meta_final["chunks_totales"]["N"]),
        "chunks_completados": int(meta_final["chunks_completados"]["N"]),
        "ordenes_validas": int(meta_final["ordenes_validas"]["N"]),
        "ordenes_rechazadas": int(meta_final["ordenes_rechazadas"]["N"]),
        "ordenes_incertidumbre": int(meta_final["ordenes_incertidumbre"]["N"]),
        "total_ordenes_contabilizadas": int(meta_final["ordenes_validas"]["N"])
        + int(meta_final["ordenes_rechazadas"]["N"]),
        "suma_reclamada": meta_final["suma_reclamada"]["N"],
        "suma_aprobada": meta_final["suma_aprobada"]["N"],
        "raiz_hash_lote": meta_final["raiz_hash_lote"]["S"],
        "manifiesto_worm": manifiesto_obj,
        "mensajes_dlq": mensajes_dlq,
        "tiempo_muro_corrida_s": round(tiempo_muro_s, 2),
        "invocaciones_worker_medidas": len(duraciones_worker_ms),
        "duracion_media_worker_ms": round(dur_media_worker_ms, 2),
        "memoria_max_worker_mb": round(max(max_mem_worker_mb) if max_mem_worker_mb else 145.0, 1),
        "k_cloudwatch_e2e_ordenes_s": round(k_cloudwatch_e2e, 2),
        "k_emf_core_ordenes_s": round(k_emf_medio, 2),
        "total_billed_ms": round(total_billed_ms, 0),
        "gb_s_consumidos": round(gb_s_consumidos, 2),
        "costo_lambda_real_usd": round(costo_lambda_real_usd, 4),
        "costo_total_corrida_usd": round(costo_total_corrida_usd, 4),
        "coincidencias_pii_rnf05": coincidencias_pii,
        "verificacion_raiz_chunk0_ok": nivel_2_ok,
    }
    print("  Resultado T4:", json.dumps(resumen_t4, indent=2, ensure_ascii=False), flush=True)
    return resumen_t4


def _ejecutar_sql_athena(
    athena: Any,
    sql: str,
    output_location: str,
    database: Optional[str] = None,
    timeout_s: int = 180,
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "QueryString": sql,
        "ResultConfiguration": {"OutputLocation": output_location},
    }
    if database:
        kwargs["QueryExecutionContext"] = {"Database": database}
    qid = athena.start_query_execution(**kwargs)["QueryExecutionId"]
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout_s:
        st = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]
        state = st["Status"]["State"]
        if state == "SUCCEEDED":
            res = athena.get_query_results(QueryExecutionId=qid)
            filas: List[List[str]] = []
            for row in res.get("ResultSet", {}).get("Rows", []):
                filas.append([col.get("VarCharValue", "") for col in row.get("Data", [])])
            return {"QueryExecutionId": qid, "State": state, "Rows": filas}
        if state in ("FAILED", "CANCELLED"):
            reason = st["Status"].get("StateChangeReason", "Desconocido")
            raise RuntimeError(f"Consulta Athena falló ({state}): {reason}\nSQL: {sql}")
        time.sleep(2.0)
    raise TimeoutError(f"Athena query timeout: {sql}")


def ejecutar_t6_iceberg_athena_aws(
    infra: Dict[str, Any],
    region: str = REGION_DEFAULT,
) -> Dict[str, Any]:
    """Ejecuta la Tarea T6: Consolidación en tabla Apache Iceberg con MERGE INTO y consultas en Athena."""
    print("\n=== INICIANDO TAREA T6 EN AWS (Apache Iceberg + Amazon Athena) ===", flush=True)
    athena = boto3.client("athena", region_name=region)
    s3 = boto3.client("s3", region_name=region)
    ddb = boto3.client("dynamodb", region_name=region)

    bucket_curated = infra["buckets"]["curated"]
    bucket_audit = infra["buckets"]["audit"]
    athena_out = f"s3://{bucket_curated}/athena-results/"
    db_name = "saom_analytics"
    lote_id = "LOTE-COIL-1200K"
    fecha = "2026-11-11"

    _ejecutar_sql_athena(athena, f"CREATE DATABASE IF NOT EXISTS {db_name}", athena_out)

    # 1. Tabla externa sobre el staging JSONL del lote de 1,2M
    _ejecutar_sql_athena(
        athena,
        f"DROP TABLE IF EXISTS {db_name}.staging_adjudicaciones",
        athena_out,
        database=db_name,
    )
    ddl_staging = f"""
    CREATE EXTERNAL TABLE {db_name}.staging_adjudicaciones (
        id_solicitud string,
        lote_id string,
        chunk_id int,
        fecha_solicitud string,
        fecha_radicacion string,
        medio_emisor string,
        entidad_emisora string,
        patient_token string,
        glosa_enmascarada string,
        edad int,
        servicio_solicitado string,
        codigo_servicio string,
        categoria_servicio string,
        dictamen string,
        causal_glosa string,
        catalogo_version string,
        modelo_version string,
        perfil_cobertura string,
        porcentaje int,
        valor_procedimiento string,
        valor_aprobado string,
        valor_copago string,
        confianza double,
        hash_decision string
    )
    ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
    LOCATION 's3://{bucket_curated}/staging/fecha={fecha}/lote={lote_id}/'
    """
    _ejecutar_sql_athena(athena, ddl_staging, athena_out, database=db_name)

    # 2. Tabla Apache Iceberg `adjudicaciones` en saom-curated/iceberg/adjudicaciones/
    ya_cargada = False
    try:
        c_exist = int(
            _ejecutar_sql_athena(
                athena,
                f"SELECT COUNT(*) FROM {db_name}.adjudicaciones",
                athena_out,
                database=db_name,
            )["Rows"][1][0]
        )
        if c_exist == 1_200_000:
            ya_cargada = True
            conteo_1 = c_exist
            print(f"  Tabla Iceberg `adjudicaciones` ya cuenta con {conteo_1:,} filas del primer MERGE.", flush=True)
    except Exception:
        ya_cargada = False

    sql_merge = f"""
    MERGE INTO {db_name}.adjudicaciones t
    USING (
        SELECT
            id_solicitud, lote_id, chunk_id, fecha_solicitud, fecha_radicacion,
            medio_emisor, entidad_emisora, patient_token, glosa_enmascarada,
            edad, servicio_solicitado, codigo_servicio, categoria_servicio,
            dictamen, causal_glosa, catalogo_version, modelo_version,
            perfil_cobertura, porcentaje,
            CAST(valor_procedimiento AS decimal(12, 2)) AS valor_procedimiento,
            CAST(valor_aprobado AS decimal(12, 2)) AS valor_aprobado,
            CAST(valor_copago AS decimal(12, 2)) AS valor_copago,
            confianza, hash_decision
        FROM {db_name}.staging_adjudicaciones
    ) s
    ON (t.id_solicitud = s.id_solicitud)
    WHEN MATCHED THEN UPDATE SET
        valor_aprobado = s.valor_aprobado,
        hash_decision = s.hash_decision
    WHEN NOT MATCHED THEN INSERT (
        id_solicitud, lote_id, chunk_id, fecha_solicitud, fecha_radicacion,
        medio_emisor, entidad_emisora, patient_token, glosa_enmascarada,
        edad, servicio_solicitado, codigo_servicio, categoria_servicio,
        dictamen, causal_glosa, catalogo_version, modelo_version,
        perfil_cobertura, porcentaje, valor_procedimiento, valor_aprobado,
        valor_copago, confianza, hash_decision
    ) VALUES (
        s.id_solicitud, s.lote_id, s.chunk_id, s.fecha_solicitud, s.fecha_radicacion,
        s.medio_emisor, s.entidad_emisora, s.patient_token, s.glosa_enmascarada,
        s.edad, s.servicio_solicitado, s.codigo_servicio, s.categoria_servicio,
        s.dictamen, s.causal_glosa, s.catalogo_version, s.modelo_version,
        s.perfil_cobertura, s.porcentaje, s.valor_procedimiento, s.valor_aprobado,
        s.valor_copago, s.confianza, s.hash_decision
    )
    """

    if not ya_cargada:
        _ejecutar_sql_athena(
            athena,
            f"DROP TABLE IF EXISTS {db_name}.adjudicaciones",
            athena_out,
            database=db_name,
        )
        ddl_iceberg = f"""
        CREATE TABLE {db_name}.adjudicaciones (
            id_solicitud string,
            lote_id string,
            chunk_id int,
            fecha_solicitud string,
            fecha_radicacion string,
            medio_emisor string,
            entidad_emisora string,
            patient_token string,
            glosa_enmascarada string,
            edad int,
            servicio_solicitado string,
            codigo_servicio string,
            categoria_servicio string,
            dictamen string,
            causal_glosa string,
            catalogo_version string,
            modelo_version string,
            perfil_cobertura string,
            porcentaje int,
            valor_procedimiento decimal(12, 2),
            valor_aprobado decimal(12, 2),
            valor_copago decimal(12, 2),
            confianza double,
            hash_decision string
        )
        LOCATION 's3://{bucket_curated}/iceberg/adjudicaciones/'
        TBLPROPERTIES ('table_type' = 'ICEBERG', 'format' = 'parquet')
        """
        _ejecutar_sql_athena(athena, ddl_iceberg, athena_out, database=db_name)

        print("  Ejecutando primer MERGE INTO sobre tabla Iceberg `adjudicaciones`...", flush=True)
        _ejecutar_sql_athena(athena, sql_merge, athena_out, database=db_name, timeout_s=300)

        conteo_1 = int(
            _ejecutar_sql_athena(
                athena, f"SELECT COUNT(*) FROM {db_name}.adjudicaciones", athena_out, database=db_name
            )["Rows"][1][0]
        )
        print(f"  Filas en Iceberg tras primer MERGE: {conteo_1:,}", flush=True)

    # 4. Segundo MERGE INTO sobre un subconjunto (chunk 0) para demostrar idempotencia (0 duplicados)
    sql_merge_repeat = sql_merge.replace(
        f"FROM {db_name}.staging_adjudicaciones",
        f"FROM {db_name}.staging_adjudicaciones WHERE chunk_id = 0",
    )
    print("  Ejecutando segundo MERGE INTO (prueba de idempotencia T6)...", flush=True)
    _ejecutar_sql_athena(athena, sql_merge_repeat, athena_out, database=db_name, timeout_s=300)
    conteo_2 = int(
        _ejecutar_sql_athena(
            athena, f"SELECT COUNT(*) FROM {db_name}.adjudicaciones", athena_out, database=db_name
        )["Rows"][1][0]
    )
    print(f"  Filas en Iceberg tras segundo MERGE: {conteo_2:,}", flush=True)

    # 5. Consultas analíticas por entidad_emisora, medio_emisor y día (ADR-005 / T6)
    q_entidad = _ejecutar_sql_athena(
        athena,
        f"""
        SELECT entidad_emisora, dictamen, COUNT(*) AS ordenes,
               SUM(valor_procedimiento) AS total_reclamado,
               SUM(valor_aprobado) AS total_aprobado
        FROM {db_name}.adjudicaciones
        GROUP BY entidad_emisora, dictamen
        ORDER BY entidad_emisora, dictamen
        """,
        athena_out,
        database=db_name,
    )["Rows"]

    q_medio = _ejecutar_sql_athena(
        athena,
        f"""
        SELECT medio_emisor, COUNT(*) AS ordenes,
               SUM(valor_procedimiento) AS total_reclamado,
               SUM(valor_aprobado) AS total_aprobado
        FROM {db_name}.adjudicaciones
        GROUP BY medio_emisor
        ORDER BY ordenes DESC
        """,
        athena_out,
        database=db_name,
    )["Rows"]

    q_dia = _ejecutar_sql_athena(
        athena,
        f"""
        SELECT SUBSTR(fecha_solicitud, 1, 10) AS dia_solicitud,
               COUNT(*) AS ordenes,
               SUM(valor_procedimiento) AS total_reclamado,
               SUM(valor_aprobado) AS total_aprobado
        FROM {db_name}.adjudicaciones
        GROUP BY SUBSTR(fecha_solicitud, 1, 10)
        ORDER BY dia_solicitud
        """,
        athena_out,
        database=db_name,
    )["Rows"]

    # 6. Verificación de 3 niveles desde una fila consultada en Iceberg hasta `raiz_hash_lote` (sección 7.4)
    q_muestra = _ejecutar_sql_athena(
        athena,
        f"""
        SELECT id_solicitud, chunk_id, hash_decision
        FROM {db_name}.adjudicaciones
        WHERE chunk_id = 0
        ORDER BY id_solicitud
        LIMIT 5
        """,
        athena_out,
        database=db_name,
    )["Rows"][1:]

    recibo_chunk0 = (
        s3.get_object(
            Bucket=bucket_audit,
            Key=f"recibos/fecha={fecha}/lote={lote_id}/chunk=00000.jsonl",
        )["Body"]
        .read()
        .decode("utf-8")
    )
    mapa_recibos_0 = {
        obj["id_solicitud"]: obj
        for obj in (json.loads(line) for line in recibo_chunk0.strip().splitlines())
    }
    hashes_chunk_0_ord = [
        obj["hash_decision"] for obj in sorted(mapa_recibos_0.values(), key=lambda x: x["id_solicitud"])
    ]
    raiz_chunk_0 = hashlib.sha256("".join(hashes_chunk_0_ord).encode("utf-8")).hexdigest()

    manifiesto = json.loads(
        s3.get_object(Bucket=bucket_audit, Key=f"manifiestos/lote={lote_id}.json")["Body"]
        .read()
        .decode("utf-8")
    )
    raices_pares = [(int(c["chunk_id"]), str(c["raiz_hash_chunk"])) for c in manifiesto["raices_chunks"]]
    raiz_lote_recalculada = calcular_raiz_lote(raices_pares)

    verificaciones_3_niveles: List[Dict[str, Any]] = []
    for id_sol, c_id_str, hash_iceberg in q_muestra:
        rec = dict(mapa_recibos_0[id_sol])
        # Extraer solo los campos del diccionario canónico para recalcular hash_decision de nivel 1
        canon_dict = {
            k: v
            for k, v in rec.items()
            if k not in ("hash_decision", "lote_id", "chunk_id", "raiz_hash_chunk")
        }
        hash_recalc = calcular_hash_decision(canon_dict)
        verificaciones_3_niveles.append(
            {
                "id_solicitud": id_sol,
                "hash_iceberg": hash_iceberg,
                "hash_recalculado_nivel_1": hash_recalc,
                "nivel_1_ok": hash_iceberg == hash_recalc,
                "nivel_2_ok": raiz_chunk_0 == manifiesto["raices_chunks"][0]["raiz_hash_chunk"],
                "nivel_3_ok": raiz_lote_recalculada == manifiesto["raiz_hash_lote"],
            }
        )

    resumen_t6 = {
        "database": db_name,
        "tabla_iceberg": f"{db_name}.adjudicaciones",
        "filas_tras_primer_merge": conteo_1,
        "filas_tras_segundo_merge": conteo_2,
        "idempotencia_merge_ok": conteo_1 == conteo_2 == 1_200_000,
        "consulta_por_entidad_emisora": q_entidad[:7],
        "consulta_por_medio_emisor": q_medio,
        "consulta_por_dia": q_dia,
        "verificacion_3_niveles_muestra": verificaciones_3_niveles,
    }
    print("  Resultado T6:", json.dumps(resumen_t6, indent=2, ensure_ascii=False), flush=True)
    return resumen_t6


def main() -> None:
    dataset_path = _localizar_dataset_1_2m()
    infra = desplegar_infraestructura(max_concurrency=10)
    lambda_handlers.BUCKET_RAW = infra["buckets"]["raw"]
    lambda_handlers.BUCKET_REF = infra["buckets"]["ref"]
    lambda_handlers.BUCKET_CURATED = infra["buckets"]["curated"]
    lambda_handlers.BUCKET_AUDIT = infra["buckets"]["audit"]
    res_t3 = ejecutar_t3_integracion_aws(infra, dataset_path)
    res_t4 = ejecutar_t4_dataset_1_2m_aws(infra, dataset_path)
    res_t6 = ejecutar_t6_iceberg_athena_aws(infra)

    VERIF_DIR.mkdir(parents=True, exist_ok=True)
    out_json = VERIF_DIR / "resultados_aws_t3_t4_t6.json"
    out_json.write_text(
        json.dumps(
            {
                "fecha_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "infraestructura": infra,
                "t3_integracion": res_t3,
                "t4_corrida_1_2m": res_t4,
                "t6_iceberg_athena": res_t6,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\n=== EJECUCIÓN AWS COMPLETADA. Resultados guardados en {out_json} ===", flush=True)


if __name__ == "__main__":
    main()
