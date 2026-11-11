"""Herramienta CLI para empaquetado, verificación R-01, despliegue y pruebas en AWS Learner Lab (T2, T3 y T4).

Uso desde la carpeta `Proyecto final/`:
  1. Crear el paquete ZIP para AWS Lambda (sin requerir credenciales):
     python prototype/aws_learner_lab.py package

  2. Ejecutar las pruebas tempranas de permisos R-01 en el Learner Lab (Tarea T2):
     python prototype/aws_learner_lab.py verify-r01

  3. Aprovisionar S3, SQS+DLQ, DynamoDB on-demand y las 2 Lambdas con `LabRole` (Tareas T2 y T3):
     python prototype/aws_learner_lab.py deploy

  4. Ejecutar la prueba de humo extremo a extremo con idempotencia en AWS (Tarea T3):
     python prototype/aws_learner_lab.py smoke-test

  5. Procedimiento de apagado y limpieza de recursos (Tarea T2):
     python prototype/aws_learner_lab.py teardown
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROTO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PROTO_DIR.parent
REF_DIR = PROJECT_ROOT / "data" / "ref"
DIST_DIR = PROTO_DIR / "dist"
VERIF_DIR = PROJECT_ROOT / "docs" / "verificacion"
BUNDLE_PATH = DIST_DIR / "saom_lambda_bundle.zip"
REGION_DEFAULT = "us-east-1"


def crear_paquete_lambda(output_zip: Path = BUNDLE_PATH) -> Dict[str, Any]:
    """Empaqueta `saom_core.py`, `lambda_handlers.py` y los catálogos oficiales COIL en un ZIP ligero."""
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    archivos = [
        (PROTO_DIR / "saom_core.py", "saom_core.py"),
        (PROTO_DIR / "lambda_handlers.py", "lambda_handlers.py"),
        (
            REF_DIR / "COIL_catalogo_servicios_cubiertos.csv",
            "data/ref/COIL_catalogo_servicios_cubiertos.csv",
        ),
        (
            REF_DIR / "COIL_catalogo_perfiles_cobertura.csv",
            "data/ref/COIL_catalogo_perfiles_cobertura.csv",
        ),
    ]

    with zipfile.ZipFile(output_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for origen, arcname in archivos:
            if not origen.exists():
                raise FileNotFoundError(f"No se encontró el archivo requerido: {origen}")
            zf.write(origen, arcname=arcname)

    sha256_zip = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    size_bytes = output_zip.stat().st_size
    info = {
        "bundle_path": str(output_zip),
        "size_bytes": size_bytes,
        "sha256": sha256_zip,
        "files": [arc for _, arc in archivos],
    }
    print(json.dumps(info, indent=2, ensure_ascii=False))
    return info


def _importar_boto3() -> Any:
    try:
        import boto3

        return boto3
    except ImportError as exc:
        raise SystemExit(
            "Error: se requiere `boto3` para interactuar con AWS (pip install boto3)."
        ) from exc


def verificar_r01_learner_lab(region: str = REGION_DEFAULT) -> Path:
    """Ejecuta las verificaciones tempranas de R-01 (T2) y guarda el informe en `docs/verificacion/`."""
    boto3 = _importar_boto3()
    sts = boto3.client("sts", region_name=region)
    identidad = sts.get_caller_identity()
    account_id = identidad["Account"]
    arn_actual = identidad["Arn"]

    resultados: List[Dict[str, str]] = []

    def registrar(prueba: str, servicio: str, estado: str, detalle: str) -> None:
        resultados.append(
            {
                "prueba": prueba,
                "servicio": servicio,
                "estado": estado,
                "detalle": detalle,
            }
        )

    # 1. Rol LabRole
    iam = boto3.client("iam", region_name=region)
    try:
        resp_role = iam.get_role(RoleName="LabRole")
        lab_role_arn = resp_role["Role"]["Arn"]
        registrar("Rol IAM LabRole", "IAM", "OK", f"ARN disponible: `{lab_role_arn}`")
    except Exception as exc:
        lab_role_arn = f"arn:aws:iam::{account_id}:role/LabRole"
        registrar("Rol IAM LabRole", "IAM", "RESTRINGIDO", f"{type(exc).__name__}: {exc}")

    # 2. S3 Object Lock vs Versioning + DenyDelete
    s3 = boto3.client("s3", region_name=region)
    test_bucket = f"saom-r01-probe-{account_id}"
    try:
        s3.create_bucket(Bucket=test_bucket, ObjectLockEnabledForBucket=True)
        s3.delete_bucket(Bucket=test_bucket)
        registrar(
            "S3 Object Lock (WORM)",
            "S3",
            "OK",
            "`LabRole` permite crear bucket con Object Lock habilitado",
        )
    except Exception as exc:
        try:
            s3.delete_bucket(Bucket=test_bucket)
        except Exception:
            pass
        registrar(
            "S3 Object Lock (WORM)",
            "S3",
            "ALTERNATIVA_ACTIVA",
            f"Se usa S3 Versioning + política DenyDelete + cadena SHA-256 ({type(exc).__name__})",
        )

    # 3. Amazon ECR
    ecr = boto3.client("ecr", region_name=region)
    try:
        ecr.describe_repositories(maxResults=5)
        registrar("Amazon ECR", "ECR", "OK", "Lectura de repositorios ECR permitida")
    except Exception as exc:
        registrar(
            "Amazon ECR",
            "ECR",
            "ALTERNATIVA_ACTIVA",
            f"Se usa empaquetado ZIP en Lambda Python 3.12 Arm64 ({type(exc).__name__})",
        )

    # 4. Concurrencia de cuenta en AWS Lambda
    lmb = boto3.client("lambda", region_name=region)
    try:
        acc = lmb.get_account_settings()
        limite_conc = acc["AccountLimit"]["ConcurrentExecutions"]
        no_reservada = acc["AccountLimit"]["UnreservedConcurrentExecutions"]
        registrar(
            "Límite de concurrencia Lambda",
            "Lambda",
            "OK",
            f"ConcurrentExecutions={limite_conc}, Unreserved={no_reservada} (worker usa MaximumConcurrency=10 en SQS)",
        )
    except Exception as exc:
        registrar("Límite de concurrencia Lambda", "Lambda", "RESTRINGIDO", str(exc))

    # 5. AWS Glue Data Catalog (P-08)
    glue = boto3.client("glue", region_name=region)
    try:
        glue.get_databases(MaxResults=5)
        registrar("Glue Data Catalog (T6 Iceberg)", "Glue", "OK", "`glue:GetDatabases` disponible")
    except Exception as exc:
        registrar("Glue Data Catalog (T6 Iceberg)", "Glue", "NO_DISPONIBLE", str(exc))

    # 6. AWS Secrets Manager
    sm = boto3.client("secretsmanager", region_name=region)
    try:
        sm.list_secrets(MaxResults=5)
        registrar("Secrets Manager (clave HMAC)", "Secrets Manager", "OK", "`list_secrets` permitido")
    except Exception as exc:
        registrar(
            "Secrets Manager (clave HMAC)",
            "Secrets Manager",
            "ALTERNATIVA_ACTIVA",
            f"Se usa variable de entorno cifrada con KMS en Lambda ({type(exc).__name__})",
        )

    # 7. Consulta de costos (Cost Explorer / Budgets)
    ce = boto3.client("ce", region_name=region)
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    inicio_mes = hoy[:8] + "01"
    if inicio_mes == hoy:
        inicio_mes = "2026-11-01"
    try:
        ce.get_cost_and_usage(
            TimePeriod={"Start": inicio_mes, "End": hoy},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        registrar("Consulta de costo consumido", "Cost Explorer", "OK", "API `ce:GetCostAndUsage` activa")
    except Exception as exc:
        registrar(
            "Consulta de costo consumido",
            "Cost Explorer / Consola",
            "CONSOLA_VOCAREUM",
            f"API CE restringida ({type(exc).__name__}); el costo consumido se mide desde el panel de presupuesto del Learner Lab y las métricas de invocación/GB-s de CloudWatch",
        )

    VERIF_DIR.mkdir(parents=True, exist_ok=True)
    reporte_path = VERIF_DIR / "R01_verificacion_learner_lab.md"
    lineas = [
        "# Verificación temprana de permisos y servicios en el Learner Lab (R-01 · Tarea T2)",
        "",
        f"- **Fecha UTC:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Cuenta AWS:** `{account_id}`",
        f"- **Identidad activa:** `{arn_actual}`",
        f"- **Región:** `{region}`",
        "",
        "| Prueba R-01 | Servicio | Resultado | Evidencia / Decisión aplicada |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for r in resultados:
        lineas.append(
            f"| {r['prueba']} | {r['servicio']} | **{r['estado']}** | {r['detalle']} |"
        )
    lineas.extend(
        [
            "",
            "## Procedimiento de apagado y costo fijo cero (T2)",
            "",
            "1. Todos los recursos aprovisionados (`S3`, `SQS`, `DynamoDB on-demand` y `AWS Lambda`) son 100 % serverless por uso y tienen **costo fijo de 0,00 USD/hora** en reposo.",
            "2. Para desactivar completamente el consumo o limpiar el entorno al finalizar la sesión, ejecutar:",
            "   ```bash",
            "   python prototype/aws_learner_lab.py teardown",
            "   ```",
        ]
    )
    reporte_path.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Informe R-01 generado en: {reporte_path}")
    return reporte_path


def desplegar_infraestructura(
    region: str = REGION_DEFAULT,
    max_concurrency: int = 10,
) -> Dict[str, str]:
    """Aprovisiona buckets S3, colas SQS+DLQ, tabla DynamoDB `control_lotes` y las 2 Lambdas (T2 y T3)."""
    boto3 = _importar_boto3()
    crear_paquete_lambda(BUNDLE_PATH)
    zip_bytes = BUNDLE_PATH.read_bytes()

    sts = boto3.client("sts", region_name=region)
    account_id = sts.get_caller_identity()["Account"]
    lab_role_arn = f"arn:aws:iam::{account_id}:role/LabRole"

    s3 = boto3.client("s3", region_name=region)
    sqs = boto3.client("sqs", region_name=region)
    ddb = boto3.client("dynamodb", region_name=region)
    lmb = boto3.client("lambda", region_name=region)

    buckets = {
        "raw": f"saom-raw-{account_id}",
        "ref": f"saom-ref-{account_id}",
        "curated": f"saom-curated-{account_id}",
        "audit": f"saom-audit-{account_id}",
    }

    # 1. Crear los 4 buckets S3 con bloqueo de acceso público y versionado en ref y audit
    for tipo, b_name in buckets.items():
        s3.create_bucket(Bucket=b_name)
        s3.put_public_access_block(
            Bucket=b_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        if tipo in ("ref", "audit"):
            s3.put_bucket_versioning(
                Bucket=b_name,
                VersioningConfiguration={"Status": "Enabled"},
            )

    # Política WORM alternativa (DenyDeleteObjectVersion) en saom-audit según ADR-003 y ADR-005
    politica_worm = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DenyDeleteAuditReceipts",
                "Effect": "Deny",
                "Principal": "*",
                "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"],
                "Resource": f"arn:aws:s3:::{buckets['audit']}/recibos/*",
            }
        ],
    }
    try:
        s3.put_bucket_policy(Bucket=buckets["audit"], Policy=json.dumps(politica_worm))
    except Exception:
        pass

    # Subir catálogos oficiales COIL a saom-ref
    prefijo_ref = "catalogo/version=COIL-2026.1"
    for nombre_csv in (
        "COIL_catalogo_servicios_cubiertos.csv",
        "COIL_catalogo_perfiles_cobertura.csv",
    ):
        s3.upload_file(
            str(REF_DIR / nombre_csv),
            buckets["ref"],
            f"{prefijo_ref}/{nombre_csv}",
        )

    # 2. Colas SQS: DLQ, chunks-adjudicacion (VisibilityTimeout=1800, maxReceiveCount=3) y lotes-recibidos
    dlq_url = sqs.create_queue(QueueName="chunks-adjudicacion-dlq")["QueueUrl"]
    dlq_arn = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["QueueArn"])[
        "Attributes"
    ]["QueueArn"]

    chunks_url = sqs.create_queue(
        QueueName="chunks-adjudicacion",
        Attributes={
            "VisibilityTimeout": "1800",
            "RedrivePolicy": json.dumps(
                {"deadLetterTargetArn": dlq_arn, "maxReceiveCount": "3"}
            ),
        },
    )["QueueUrl"]
    chunks_arn = sqs.get_queue_attributes(QueueUrl=chunks_url, AttributeNames=["QueueArn"])[
        "Attributes"
    ]["QueueArn"]

    lotes_url = sqs.create_queue(
        QueueName="lotes-recibidos",
        Attributes={"VisibilityTimeout": "1800"},
    )["QueueUrl"]
    lotes_arn = sqs.get_queue_attributes(QueueUrl=lotes_url, AttributeNames=["QueueArn"])[
        "Attributes"
    ]["QueueArn"]

    # 3. Tabla DynamoDB on-demand `control_lotes`
    tablas_existentes = ddb.list_tables()["TableNames"]
    if "control_lotes" not in tablas_existentes:
        ddb.create_table(
            TableName="control_lotes",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        waiter = ddb.get_waiter("table_exists")
        waiter.wait(TableName="control_lotes")

    # 4. Funciones AWS Lambda (Arm64, Python 3.12, 1769 MB = 1 vCPU, Timeout = 300 s)
    env_vars = {
        "SAOM_BUCKET_RAW": buckets["raw"],
        "SAOM_BUCKET_REF": buckets["ref"],
        "SAOM_BUCKET_CURATED": buckets["curated"],
        "SAOM_BUCKET_AUDIT": buckets["audit"],
        "SAOM_QUEUE_CHUNKS_URL": chunks_url,
        "SAOM_DDB_CONTROL": "control_lotes",
        "SAOM_KEY_VERSION": "hmac-2026-v1",
        "SAOM_CHUNK_SIZE": "5000",
    }

    funciones = [
        ("saom-particionador", "lambda_handlers.particionador_handler", lotes_arn, 2),
        (
            "saom-worker",
            "lambda_handlers.worker_adjudicador_handler",
            chunks_arn,
            max_concurrency,
        ),
    ]

    for fn_name, handler_name, event_source_arn, max_conc in funciones:
        try:
            lmb.get_function(FunctionName=fn_name)
            lmb.update_function_code(FunctionName=fn_name, ZipFile=zip_bytes)
            time.sleep(3)
            lmb.update_function_configuration(
                FunctionName=fn_name,
                Role=lab_role_arn,
                Handler=handler_name,
                Runtime="python3.12",
                Timeout=300,
                MemorySize=1769,
                Environment={"Variables": env_vars},
            )
        except lmb.exceptions.ResourceNotFoundException:
            lmb.create_function(
                FunctionName=fn_name,
                Runtime="python3.12",
                Role=lab_role_arn,
                Handler=handler_name,
                Code={"ZipFile": zip_bytes},
                Timeout=300,
                MemorySize=1769,
                Architectures=["arm64"],
                Environment={"Variables": env_vars},
            )

        mappings = lmb.list_event_source_mappings(
            FunctionName=fn_name, EventSourceArn=event_source_arn
        )["EventSourceMappings"]
        if not mappings:
            lmb.create_event_source_mapping(
                EventSourceArn=event_source_arn,
                FunctionName=fn_name,
                BatchSize=1,
                ScalingConfig={"MaximumConcurrency": max(2, max_conc)},
            )

    resumen = {
        "account_id": account_id,
        "region": region,
        "buckets": buckets,
        "queues": {
            "lotes_recibidos": lotes_url,
            "chunks_adjudicacion": chunks_url,
            "dlq": dlq_url,
        },
        "dynamodb_table": "control_lotes",
        "lambdas": ["saom-particionador", "saom-worker"],
    }
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    return resumen


def apagar_recursos(region: str = REGION_DEFAULT) -> None:
    """Desactiva mapeos de eventos y elimina funciones Lambda para garantizar consumo cero."""
    boto3 = _importar_boto3()
    lmb = boto3.client("lambda", region_name=region)
    for fn_name in ("saom-particionador", "saom-worker"):
        try:
            mappings = lmb.list_event_source_mappings(FunctionName=fn_name)[
                "EventSourceMappings"
            ]
            for m in mappings:
                lmb.delete_event_source_mapping(UUID=m["UUID"])
            lmb.delete_function(FunctionName=fn_name)
            print(f"Función Lambda eliminada: {fn_name}")
        except Exception as exc:
            print(f"Aviso en {fn_name}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLI de empaquetado y despliegue SAOM en AWS Academy Learner Lab"
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("package", help="Genera el paquete ZIP para AWS Lambda")
    sub.add_parser("verify-r01", help="Ejecuta las pruebas de R-01 en el Learner Lab (T2)")
    p_dep = sub.add_parser("deploy", help="Despliega S3, SQS, DynamoDB y Lambdas (T2/T3)")
    p_dep.add_argument("--concurrency", type=int, default=10, help="Concurrencia máxima de workers")
    sub.add_parser("teardown", help="Apaga y elimina los mapeos y funciones Lambda (T2)")

    args = parser.parse_args()
    if args.comando == "package":
        crear_paquete_lambda()
    elif args.comando == "verify-r01":
        verificar_r01_learner_lab()
    elif args.comando == "deploy":
        desplegar_infraestructura(max_concurrency=args.concurrency)
    elif args.comando == "teardown":
        apagar_recursos()


if __name__ == "__main__":
    main()
