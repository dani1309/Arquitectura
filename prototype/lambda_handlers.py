"""Adaptadores AWS Lambda para el despliegue en AWS Academy Learner Lab (`LabRole`).

Incluye los tres handlers serverless definidos en `design/03_arquitectura_tecnica.md`:
1. `radicacion_api_handler`: Registra el lote en DynamoDB `control_lotes` y genera URL prefirmada hacia `saom-raw`.
2. `particionador_handler`: Lee la cabecera CSV en `saom-raw`, calcula rangos de bytes de 5.000 órdenes y publica en SQS `chunks-adjudicacion`.
3. `worker_adjudicador_handler`: Consume un chunk desde SQS, ejecuta `procesar_rango_bytes_csv()`, escribe recibos firmados en `saom-audit`, resultados en `saom-curated` y actualiza `control_lotes` de forma idempotente con `TransactWriteItems`.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:  # Permite importar el módulo en entornos locales sin boto3 instalado
    boto3 = None  # type: ignore
    ClientError = Exception  # type: ignore

from saom_core import (
    CatalogoCOIL,
    DescriptorChunk,
    procesar_rango_bytes_csv,
)

BUCKET_RAW = os.environ.get("SAOM_BUCKET_RAW", "saom-raw")
BUCKET_REF = os.environ.get("SAOM_BUCKET_REF", "saom-ref")
BUCKET_CURATED = os.environ.get("SAOM_BUCKET_CURATED", "saom-curated")
BUCKET_AUDIT = os.environ.get("SAOM_BUCKET_AUDIT", "saom-audit")
QUEUE_CHUNKS_URL = os.environ.get("SAOM_QUEUE_CHUNKS_URL", "")
DDB_TABLE_CONTROL = os.environ.get("SAOM_DDB_CONTROL", "control_lotes")
SECRET_HMAC_ID = os.environ.get("SAOM_SECRET_HMAC_ID", "saom/hmac-key")
CHUNK_SIZE = int(os.environ.get("SAOM_CHUNK_SIZE", "5000"))

# Caché en memoria del contenedor Lambda (se conserva entre invocaciones tibias)
_CATALOGO_CACHE: CatalogoCOIL | None = None
_HMAC_KEY_CACHE: bytes | None = None


def _obtener_catalogo() -> CatalogoCOIL:
    global _CATALOGO_CACHE
    if _CATALOGO_CACHE is not None:
        return _CATALOGO_CACHE

    ref_dir = Path(__file__).resolve().parent.parent / "data" / "ref"
    servicios_local = ref_dir / "COIL_catalogo_servicios_cubiertos.csv"
    perfiles_local = ref_dir / "COIL_catalogo_perfiles_cobertura.csv"

    if not servicios_local.exists() and boto3 is not None:
        s3 = boto3.client("s3")
        tmp_dir = Path("/tmp/saom_ref")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        servicios_local = tmp_dir / "COIL_catalogo_servicios_cubiertos.csv"
        perfiles_local = tmp_dir / "COIL_catalogo_perfiles_cobertura.csv"
        s3.download_file(
            BUCKET_REF,
            "catalogo/version=COIL-2026.1/COIL_catalogo_servicios_cubiertos.csv",
            str(servicios_local),
        )
        s3.download_file(
            BUCKET_REF,
            "catalogo/version=COIL-2026.1/COIL_catalogo_perfiles_cobertura.csv",
            str(perfiles_local),
        )

    _CATALOGO_CACHE = CatalogoCOIL(servicios_local, perfiles_local, version="COIL-2026.1")
    return _CATALOGO_CACHE


def _obtener_clave_hmac() -> bytes:
    global _HMAC_KEY_CACHE
    if _HMAC_KEY_CACHE is not None:
        return _HMAC_KEY_CACHE

    env_key = os.environ.get("SAOM_HMAC_SECRET_FALLBACK")
    if env_key:
        _HMAC_KEY_CACHE = env_key.encode("utf-8")
        return _HMAC_KEY_CACHE

    if boto3 is not None:
        sm = boto3.client("secretsmanager")
        resp = sm.get_secret_value(SecretId=SECRET_HMAC_ID)
        _HMAC_KEY_CACHE = resp["SecretString"].encode("utf-8")
        return _HMAC_KEY_CACHE

    _HMAC_KEY_CACHE = b"coil-chernovia-default-key-2026"
    return _HMAC_KEY_CACHE


def radicacion_api_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Paso 1 del flujo en AWS: Registra el lote en DynamoDB y devuelve URL prefirmada S3."""
    body = json.loads(event.get("body") or "{}")
    entidad_emisora = body.get("entidad_emisora", "IPS-GENERICA")
    lote_id = body.get("lote_id", f"LOTE-{int(time.time())}")
    fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    s3_key = f"entidad={entidad_emisora}/fecha={fecha_hoy}/lote={lote_id}.csv"

    ddb = boto3.client("dynamodb")
    s3 = boto3.client("s3")

    ddb.put_item(
        TableName=DDB_TABLE_CONTROL,
        Item={
            "PK": {"S": f"LOTE#{lote_id}"},
            "SK": {"S": "META"},
            "entidad_emisora": {"S": entidad_emisora},
            "estado": {"S": "RADICADO"},
            "s3_key": {"S": s3_key},
            "catalogo_version": {"S": "COIL-2026.1"},
            "chunks_totales": {"N": "0"},
            "chunks_completados": {"N": "0"},
            "ordenes_validas": {"N": "0"},
            "ordenes_rechazadas": {"N": "0"},
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


def particionador_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Pasos 4 y 5 del flujo en AWS: Divide el CSV de S3 en descriptores de 5.000 filas."""
    s3 = boto3.client("s3")
    sqs = boto3.client("sqs")
    ddb = boto3.client("dynamodb")

    total_chunks_emitidos = 0
    for sqs_record in event.get("Records", []):
        s3_event = json.loads(sqs_record["body"])
        for rec in s3_event.get("Records", []):
            bucket = rec["s3"]["bucket"]["name"]
            key = urllib.parse.unquote_plus(rec["s3"]["object"]["key"])
            lote_id = key.split("lote=")[-1].replace(".csv", "")

            obj = s3.get_object(Bucket=bucket, Key=key)
            stream = obj["Body"]

            lines_iter = stream.iter_lines(keepends=True)
            header = next(lines_iter, b"")
            offset = len(header)

            chunk_id = 0
            byte_inicio = offset
            conteo = 0
            descriptores: List[Dict[str, Any]] = []

            for linea in lines_iter:
                offset += len(linea)
                conteo += 1
                if conteo == CHUNK_SIZE:
                    descriptores.append(
                        {
                            "lote_id": lote_id,
                            "chunk_id": chunk_id,
                            "bucket": bucket,
                            "key": key,
                            "byte_inicio": byte_inicio,
                            "byte_fin": offset - 1,
                            "num_ordenes": conteo,
                        }
                    )
                    chunk_id += 1
                    byte_inicio = offset
                    conteo = 0

            if conteo > 0:
                descriptores.append(
                    {
                        "lote_id": lote_id,
                        "chunk_id": chunk_id,
                        "bucket": bucket,
                        "key": key,
                        "byte_inicio": byte_inicio,
                        "byte_fin": offset - 1,
                        "num_ordenes": conteo,
                    }
                )

            ddb.update_item(
                TableName=DDB_TABLE_CONTROL,
                Key={"PK": {"S": f"LOTE#{lote_id}"}, "SK": {"S": "META"}},
                UpdateExpression="SET estado = :e, chunks_totales = :ct",
                ExpressionAttributeValues={
                    ":e": {"S": "EN_PROCESO"},
                    ":ct": {"N": str(len(descriptores))},
                },
            )

            for desc in descriptores:
                sqs.send_message(QueueUrl=QUEUE_CHUNKS_URL, MessageBody=json.dumps(desc))
                total_chunks_emitidos += 1

    return {"chunks_emitidos": total_chunks_emitidos}


def worker_adjudicador_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Pasos 6 a 9 del flujo en AWS: Adjudica un chunk de 5.000 órdenes de manera idempotente."""
    s3 = boto3.client("s3")
    ddb = boto3.client("dynamodb")
    catalogo = _obtener_catalogo()
    clave_hmac = _obtener_clave_hmac()

    procesados = 0
    for record in event.get("Records", []):
        payload = json.loads(record["body"])
        lote_id = payload["lote_id"]
        chunk_id = int(payload["chunk_id"])
        bucket = payload["bucket"]
        key = payload["key"]
        byte_inicio = int(payload["byte_inicio"])
        byte_fin = int(payload["byte_fin"])
        num_ordenes = int(payload.get("num_ordenes", CHUNK_SIZE))

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
        resultado = procesar_rango_bytes_csv(
            bloque_bytes=bloque_bytes,
            descriptor=descriptor,
            catalogo=catalogo,
            clave_hmac=clave_hmac,
            retener_decisiones=True,
        )

        fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        staging_key = f"staging/fecha={fecha_hoy}/lote={lote_id}/chunk={chunk_id:05d}.jsonl"
        recibos_key = f"recibos/fecha={fecha_hoy}/lote={lote_id}/chunk={chunk_id:05d}.jsonl"

        lineas_staging = []
        lineas_recibos = []
        for d in resultado.decisiones:
            canon = d.to_canonical_dict()
            canon["hash_decision"] = d.hash_decision
            lineas_recibos.append(json.dumps(canon, ensure_ascii=False))
            lineas_staging.append(
                json.dumps(
                    {
                        **canon,
                        "lote_id": d.lote_id,
                        "chunk_id": d.chunk_id,
                        "fecha_solicitud": d.fecha_solicitud,
                        "medio_emisor": d.medio_emisor,
                        "entidad_emisora": d.entidad_emisora,
                        "edad": d.edad,
                        "servicio_solicitado": d.servicio_solicitado,
                        "codigo_servicio": d.codigo_servicio,
                        "categoria_servicio": d.categoria_servicio,
                        "glosa_enmascarada": d.glosa_enmascarada,
                        "flags": d.flags,
                    },
                    ensure_ascii=False,
                )
            )

        s3.put_object(
            Bucket=BUCKET_CURATED,
            Key=staging_key,
            Body=("\n".join(lineas_staging) + "\n").encode("utf-8"),
        )
        s3.put_object(
            Bucket=BUCKET_AUDIT,
            Key=recibos_key,
            Body=("\n".join(lineas_recibos) + "\n").encode("utf-8"),
        )

        if resultado.rechazos:
            rechazos_key = f"rechazos/fecha={fecha_hoy}/lote={lote_id}/chunk={chunk_id:05d}.jsonl"
            body_rech = "\n".join(
                json.dumps(
                    {
                        "id_solicitud": r.id_solicitud,
                        "linea_num": r.linea_num,
                        "estado": r.estado,
                        "motivo": r.motivo,
                    },
                    ensure_ascii=False,
                )
                for r in resultado.rechazos
            )
            s3.put_object(Bucket=BUCKET_CURATED, Key=rechazos_key, Body=body_rech.encode("utf-8"))

        # Idempotencia condicional en DynamoDB (sección 7.2)
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
                                "n_ordenes": {"N": str(resultado.ordenes_validas)},
                                "raiz_hash_chunk": {"S": resultado.raiz_hash_chunk},
                                "clave_resultado": {"S": staging_key},
                            },
                            "ConditionExpression": "attribute_not_exists(SK) OR estado <> :comp",
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
                                "ordenes_rechazadas :or"
                            ),
                            "ExpressionAttributeValues": {
                                ":uno": {"N": "1"},
                                ":ov": {"N": str(resultado.ordenes_validas)},
                                ":or": {"N": str(resultado.ordenes_rechazadas)},
                            },
                        }
                    },
                ]
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "TransactionCanceledException":
                raise
        procesados += 1

    return {"chunks_procesados": procesados}
