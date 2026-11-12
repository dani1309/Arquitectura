"""Generador automatizado de los Entregables E03 (Tarea T8) y E04 (Tarea T7: Documento Consolidado + Pitch).

Produce en `entregables/E03/` y `entregables/E04/` tanto las versiones Markdown (`.md`) como los
documentos Word (`.docx`) con formato corporativo e imágenes embebidas a 300 DPI, integrando los
resultados reales obtenidos en AWS Academy Learner Lab (`docs/verificacion/resultados_aws_t3_t4_t6.json`).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

PROTO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PROTO_DIR.parent
DIAG_DIR = PROJECT_ROOT / "docs" / "design" / "diagramas"
VERIF_DIR = PROJECT_ROOT / "docs" / "verificacion"
E03_DIR = PROJECT_ROOT / "entregables" / "E03"
E04_DIR = PROJECT_ROOT / "entregables" / "E04"


def _set_cell_background(cell: docx.table._Cell, fill_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tc_pr.append(shd)


def _add_formatted_runs(paragraph: docx.text.paragraph.Paragraph, text: str) -> None:
    tokens = re.split(r"(\*\*.*?\*\*|`.*?`)", text)
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            run = paragraph.add_run(tok[2:-2])
            run.bold = True
        elif tok.startswith("`") and tok.endswith("`"):
            run = paragraph.add_run(tok[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
        else:
            paragraph.add_run(tok)


def render_markdown_to_docx(
    md_text: str,
    docx_path: Path,
    title: str,
    subtitle: str,
) -> None:
    doc = docx.Document()
    for section in doc.sections:
        section.top_margin = Inches(0.85)
        section.bottom_margin = Inches(0.85)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run(title)
    r_title.bold = True
    r_title.font.size = Pt(18)
    r_title.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run(subtitle)
    r_sub.italic = True
    r_sub.font.size = Pt(11.5)
    r_sub.font.color.rgb = RGBColor(0x02, 0x84, 0xC7)

    p_team = doc.add_paragraph()
    p_team.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_team = p_team.add_run(
        "Equipo de Arquitectura COIL: Naomi Chow · Daniel Lopez · María Fernanda Toro"
    )
    r_team.bold = True
    r_team.font.size = Pt(10.5)
    r_team.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

    doc.add_paragraph()

    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if not line or line.strip() == "---":
            i += 1
            continue

        # Ignorar H1 principal porque ya se puso en portada
        if line.startswith("# "):
            i += 1
            continue

        if line.startswith("## "):
            h = doc.add_heading(line[3:].strip(), level=1)
            for r in h.runs:
                r.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
            i += 1
            continue

        if line.startswith("### "):
            h = doc.add_heading(line[4:].strip(), level=2)
            for r in h.runs:
                r.font.color.rgb = RGBColor(0x02, 0x84, 0xC7)
            i += 1
            continue

        # Imagen Markdown ![alt](path)
        m_img = re.match(r"^!\[(.*?)\]\((.*?)\)$", line.strip())
        if m_img:
            caption, rel_path = m_img.group(1), m_img.group(2)
            # Buscar en DIAG_DIR o resolver relativo a docs/ o absoluto
            img_file = (DIAG_DIR / Path(rel_path).name).resolve()
            if not img_file.exists():
                candidate = (PROJECT_ROOT / "docs" / "verificacion" / "screenshots" / Path(rel_path).name).resolve()
                if candidate.exists():
                    img_file = candidate
            if not img_file.exists():
                candidate2 = (Path(rel_path)).resolve()
                if candidate2.exists():
                    img_file = candidate2

            if img_file.exists():
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.add_run().add_picture(str(img_file), width=Inches(6.3))
                p_cap = doc.add_paragraph()
                p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r_cap = p_cap.add_run(caption)
                r_cap.italic = True
                r_cap.font.size = Pt(9.0)
                r_cap.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
            i += 1
            continue

        # Bloque de código ```
        if line.strip().startswith("```"):
            code_lines: List[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i].rstrip("\r"))
                i += 1
            i += 1
            p_code = doc.add_paragraph()
            r_code = p_code.add_run("\n".join(code_lines))
            r_code.font.name = "Consolas"
            r_code.font.size = Pt(8.5)
            r_code.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
            continue

        # Tabla Markdown
        if line.strip().startswith("|"):
            table_lines: List[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            rows_parsed: List[List[str]] = []
            for tl in table_lines:
                if re.match(r"^\|\s*[:\-]+", tl):
                    continue
                cells = [c.strip() for c in tl.strip("|").split("|")]
                rows_parsed.append(cells)
            if rows_parsed:
                n_cols = max(len(r) for r in rows_parsed)
                table = doc.add_table(rows=len(rows_parsed), cols=n_cols)
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                table.style = "Table Grid"
                for r_idx, row_vals in enumerate(rows_parsed):
                    for c_idx in range(n_cols):
                        val = row_vals[c_idx] if c_idx < len(row_vals) else ""
                        cell = table.cell(r_idx, c_idx)
                        cell.text = ""
                        p_cell = cell.paragraphs[0]
                        _add_formatted_runs(p_cell, val)
                        for run in p_cell.runs:
                            run.font.size = Pt(9.0)
                            if r_idx == 0:
                                run.bold = True
                                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                        if r_idx == 0:
                            _set_cell_background(cell, "0F172A")
                        elif r_idx % 2 == 1:
                            _set_cell_background(cell, "F8FAFC")
                doc.add_paragraph()
            continue

        # Viñetas o listas numeradas
        if line.lstrip().startswith("- ") or re.match(r"^\d+\.\s+", line.lstrip()):
            clean = re.sub(r"^(\-\s+|\d+\.\s+)", "", line.lstrip())
            p_list = doc.add_paragraph(
                style="List Bullet" if line.lstrip().startswith("- ") else "List Number"
            )
            _add_formatted_runs(p_list, clean)
            i += 1
            continue

        # Párrafo normal
        p = doc.add_paragraph()
        _add_formatted_runs(p, line.strip())
        i += 1

    docx_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(docx_path))


def construir_e03_markdown() -> str:
    return r"""# Entregable 03: Prototipo Funcional en AWS, Pruebas, Evidencia y Alcance Implementado

| Campo | Detalle |
| :--- | :--- |
| **Proyecto** | Sistema de Adjudicación de Órdenes Médicas (SAOM) — Sistema de Salud de Chernovia (Dataset Oficial COIL) |
| **Curso y Metodología** | Arquitecturas de Nube y Big Data · Metodología AI-DLC (Pasos 4, 5 y 6: Plan, Implementación y Verificación) |
| **Equipo de Arquitectura** | **Naomi Chow · Daniel Lopez · María Fernanda Toro** |
| **Cuenta AWS ejecutada** | `329771219583` (`us-east-1`, rol `arn:aws:iam::329771219583:role/LabRole`, usuario `daniel_lopez`) |
| **Paquete desplegado** | `prototype/dist/saom_lambda_bundle.zip` (`17.737 bytes`, SHA-256 `2fc3dc25d1d0f38b7f5d790135a2bdfa7725827040f5be560bb893c538ff45b6`) |

---

## 1. Matriz de Cumplimiento de la Rúbrica del Entregable 03

De acuerdo con la sección 5 del [Plan de Construcción](../../docs/plan/04_plan_construccion.md), la tabla siguiente relaciona cada criterio de evaluación del E03 con el artefacto verificable generado en el repositorio y ejecutado en vivo sobre **AWS Academy Learner Lab**:

| Criterio de la Rúbrica (E03) | Evidencia Verificable Generada | Archivo / Ubicación en el Repositorio | Estado |
| :--- | :--- | :--- | :--- |
| **1. Prototipo funcional en AWS** | Corrida completa en vivo del lote oficial `LOTE-COIL-1200K` (`1.200.000` solicitudes en `240` chunks de 5.000 órdenes) en `47,50 s`, con `240/240` chunks en estado `PROCESADO`, `DLQ = 0`, `raiz_hash_lote = 78dbff2ea6b365f3399315b1377111bc3ec23939ce539a101378b3f8b648869e` y manifiesto WORM en `saom-audit-329771219583`. | [`docs/verificacion/T3_T4_T6_ejecucion_real_aws.md`](../../docs/verificacion/T3_T4_T6_ejecucion_real_aws.md) y [`resultados_aws_t3_t4_t6.json`](../../docs/verificacion/resultados_aws_t3_t4_t6.json) | **CUMPLIDO (100 %)** |
| **2. Uso pertinente de AWS** | Inventario real de 4 buckets S3, 3 colas SQS, tabla DynamoDB `control_lotes`, 2 funciones AWS Lambda `arm64` (`1.769 MB`) con `LabRole`, Glue Data Catalog y tabla Apache Iceberg consultada por Amazon Athena, más sonda de permisos `R-01`. | [`docs/verificacion/R01_verificacion_learner_lab.md`](../../docs/verificacion/R01_verificacion_learner_lab.md) y [`prototype/aws_learner_lab.py`](../../prototype/aws_learner_lab.py) | **CUMPLIDO (100 %)** |
| **3. Evidencia de pruebas** | **36 pruebas automatizadas (`pytest`)** que cubren el 100 % de los escenarios BDD (`RF-01..05`), integración multi-chunk (`T3`), muestreo y F1 (`T5a/T5`), más prueba en vivo en AWS (`LOTE-T3-INTEGRACION`), reenvío duplicado (`RNF-06`), escaneo de `0` PII (`RNF-05`) y verificación criptográfica de 3 niveles (`RNF-04`). | [`prototype/test_bdd_rf01_rf05.py`](../../prototype/test_bdd_rf01_rf05.py), [`prototype/test_lambda_t3.py`](../../prototype/test_lambda_t3.py) y [`prototype/test_evaluacion_f1_t5.py`](../../prototype/test_evaluacion_f1_t5.py) | **CUMPLIDO (36/36 PASS)** |
| **4. Resultados cuantitativos** | Throughput real en AWS CloudWatch **$k_{\text{AWS-E2E}} = 4.710,44\text{ órd/s/vCPU}$** (`1.061,60 ms/chunk`), **Macro-F1 = `0,9886`** sobre 600 glosas (`1,0000` en limpias y `0,9765` en perturbadas), fracción de revisión $f = 0,0000$ en plantilla oficial ($0,1667$ bajo estrés $\le 0,30$), costo real **`0,0189 USD`** para 1,2M (**`0,0158 USD/M`** $\le 0,50\text{ USD/M}$) y recálculo $M/M/c$ hacia 12M. | [`docs/verificacion/T5_informe_metricas_f1_mmc_costo.md`](../../docs/verificacion/T5_informe_metricas_f1_mmc_costo.md) y [`T5a_protocolo_etiquetado_y_spans.md`](../../docs/verificacion/T5a_protocolo_etiquetado_y_spans.md) | **CUMPLIDO (100 %)** |
| **5. Código fuente ejecutable** | Núcleo funcional sin dependencias externas (`saom_core.py`), adaptadores AWS Lambda con reintento ante `TransactionConflict` (`lambda_handlers.py`), CLI de aprovisionamiento (`aws_learner_lab.py`) y orquestador de pruebas en vivo (`ejecutar_pruebas_aws_t3_t4_t6.py`). | Carpeta [`prototype/`](../../prototype/) | **CUMPLIDO (100 %)** |
| **6. Alcance implementado** | Tabla comparativa final entre el prototipo ejecutado en AWS Learner Lab y la arquitectura de producción para 12M de órdenes, detallando los ajustes derivados de `R-01`. | Sección 2 de este documento | **CUMPLIDO (100 %)** |

---

## 2. Uso Pertinente de AWS y Alcance Implementado frente al Diseño (`T2` y `T8`)

### 2.1. Resultados de la Verificación Temprana del Entorno (`R-01`)

Antes de desplegar los recursos, el comando `python prototype/aws_learner_lab.py verify-r01` sondeó programáticamente las capacidades y restricciones reales del **AWS Academy Learner Lab** en la cuenta `329771219583` (`us-east-1`):

| Prueba `R-01` | Servicio AWS | Resultado en Cuenta `329771219583` | Decisión Arquitectónica Aplicada |
| :--- | :--- | :--- | :--- |
| **Rol IAM `LabRole`** | AWS IAM | **OK** (`arn:aws:iam::329771219583:role/LabRole`) | Todas las funciones Lambda operan bajo `LabRole` sin crear roles IAM adicionales (`ADR-003`). |
| **S3 Object Lock (WORM)** | Amazon S3 | **ALTERNATIVA ACTIVA** (`AccessDenied` en `ObjectLockEnabledForBucket`) | Se activó la contingencia prevista en `ADR-003` y `ADR-005`: **S3 Versioning + Bucket Policy `DenyDeleteAuditReceipts` (`s3:DeleteObject`, `s3:DeleteObjectVersion`) + cadena criptográfica SHA-256 de 3 niveles**. |
| **Concurrencia AWS Lambda** | AWS Lambda | **OK** (`ConcurrentExecutions = 1000`) | Se fijó `MaximumConcurrency = 10` en el Event Source Mapping de SQS (`saom-worker`) para proteger las cuotas académicas y evitar estrangulamiento (`RNF-06`). |
| **AWS Glue Data Catalog** | AWS Glue / Athena | **OK** (`glue:GetDatabases` habilitado) | Permitió ejecutar íntegramente la **Tarea T6** creando la base de datos `saom_analytics` y la tabla **Apache Iceberg (`Parquet`)** `adjudicaciones`. |
| **Secrets Manager / KMS** | Secrets Manager | **OK** (`list_secrets` permitido) | Clave secreta HMAC provista en variable de entorno cifrada con KMS (`SAOM_HMAC_SECRET_FALLBACK`) con soporte transparente para Secrets Manager (`key_version = hmac-2026-v1`). |
| **Consulta de Costos** | Cost Explorer | **OK** (`ce:GetCostAndUsage` activa) | Costo medido simultáneamente mediante `Billed Duration` (`GB-s` en CloudWatch Logs) y panel de presupuesto del laboratorio. |

### 2.2. Tabla Final de Alcance Implementado vs. Diseño de Producción

| Componente / Capacidad | Estado en el Prototipo AWS (`1,2M`) | Diseño de Producción (`12M`) | Justificación Técnica del Alcance |
| :--- | :--- | :--- | :--- |
| **Ingesta por lotes en S3 (`saom-raw`) y notificación a SQS (`lotes-recibidos`)** | **Implementado y ejecutado en AWS** (`s3://saom-raw-329771219583`) | Idéntico | Desacopla la recepción del archivo CSV de `360,35 MB` del procesamiento posterior (`ADR-001`). |
| **Particionador por rangos de bytes (`saom-particionador`)** | **Implementado y ejecutado en AWS** (`arm64`, streaming en bloques de `4 MB`, $O(1)$ en memoria) | Idéntico | Valida la cabecera de 6 columnas y genera `240` descriptores `[byte_inicio, byte_fin]` de `5.000` órdenes sin cargar el CSV completo en RAM. |
| **Cola de trabajo (`chunks-adjudicacion`) + DLQ (`chunks-adjudicacion-dlq`)** | **Implementado y ejecutado en AWS** (`VisibilityTimeout = 1800 s`, `maxReceiveCount = 3`) | Idéntico | Amortigua los picos de carga y aísla fallos de infraestructura tras 3 intentos (`RNF-06`). |
| **Workers de adjudicación (`saom-worker`) en AWS Lambda Graviton2 (`arm64`, `1.769 MB`)** | **Implementado y ejecutado en AWS** con `MaximumConcurrency = 10` | Mismo código e imagen con `MaximumConcurrency = 10..56` (o ECS Fargate Spot) | En el Learner Lab 10 workers procesaron las `1.200.000` órdenes en `47,50 s`. Con el $k$ real medido (`4.710,44 órd/s/vCPU`), 10 workers procesan 12M de órdenes en `~4,2 minutos`. |
| **Núcleo `saom_core.py` (pseudonimización `HMAC-SHA256`, `#`, spans, catálogo `COV-001..020`, `Decimal`, `SHA-256`)** | **Implementado al 100 % y verificado con 36 tests + corrida de 1,2M** | Idéntico | Cero uso de `float`, cero PII en claro y correspondencia exacta de `[start_char, end_char]` entre glosa original y enmascarada. |
| **Control transaccional e idempotencia en DynamoDB (`control_lotes`)** | **Implementado y ejecutado en AWS** (`TransactWriteItems` con reintento *backoff* ante `TransactionConflict`) | Idéntico | Garantiza que cada chunk sume sus montos exactamente una vez en `META`, incluso ante reentregas de SQS o contención concurrente. |
| **Evidencia inmutable WORM (`saom-audit`) y manifiesto de lote** | **Implementado en AWS** con `S3 Versioning` + `DenyDeleteAuditReceipts` + árbol plano SHA-256 de 3 niveles | S3 Object Lock en modo `COMPLIANCE` + misma cadena SHA-256 | `LabRole` restringe `PutObjectLockConfiguration`, por lo que se activó la alternativa de `ADR-003` y `ADR-005`. |
| **Consolidación analítica en Apache Iceberg (`MERGE INTO`) y consultas en Amazon Athena (`T6`)** | **Implementado y ejecutado en AWS** (`saom_analytics.adjudicaciones`, `1.200.000` filas) | Idéntico | Consolidación idempotente verificada con doble `MERGE INTO` (`1.200.000` filas, `0` duplicados) y consultas por día, medio y entidad. |
| **API Gateway + Lambda de Radicación (`radicacion_api_handler`)** | **Handler implementado y probado en suite T3**; en la corrida se cargó directo a `saom-raw` | API Gateway HTTP + WAF + API Keys por entidad | La carga directa por S3/CLI mide exactamente el mismo pipeline de particionamiento y adjudicación sin exponer endpoints públicos en el laboratorio. |

---

## 3. Evidencia de Pruebas Automatizadas y Prueba de Integración en AWS (`T1` y `T3`)

### 3.1. Suite Local de 36 Pruebas Automatizadas (`pytest`)

La ejecución de `python -m pytest prototype/ -v` valida **36 pruebas automatizadas en `0,67 s` (`36 passed, 0 failed`)**:
- **[`prototype/test_bdd_rf01_rf05.py`](../../prototype/test_bdd_rf01_rf05.py) (27 tests)**: Cubre todos los escenarios Gherkin de `RF-01` a `RF-05`, las resoluciones `P-01` a `P-17`, la prohibición de `float` en `RF-04`, la igualdad de spans `[start_char, end_char]` antes y después de enmascarar con `#`, la sensibilidad del `hash_decision` ante el cambio de un centavo o un carácter, y el escaneo de `0` PII.
- **[`prototype/test_lambda_t3.py`](../../prototype/test_lambda_t3.py) (6 tests)**: Valida el flujo completo multi-chunk en los handlers Lambda, el rechazo inmediato de archivos con cabecera inválida (`estado = RECHAZADO`), el aislamiento de `CHV-9999999` en `rechazos/`, la idempotencia ante mensajes duplicados de SQS y la generación del paquete ZIP.
- **[`prototype/test_evaluacion_f1_t5.py`](../../prototype/test_evaluacion_f1_t5.py) (3 tests)**: Verifica la estructura de la muestra de 600 glosas (`300` limpias + `300` perturbadas), la ausencia de PII en la planilla de etiquetado, el cumplimiento de `Macro-F1 >= 0,92` y el dimensionamiento $M/M/c$.

### 3.2. Prueba de Integración e Idempotencia en Vivo en AWS (`LOTE-T3-INTEGRACION`)

En la cuenta de AWS `329771219583` se ejecutó el lote `LOTE-T3-INTEGRACION` (`10.001` filas = `10.000` válidas + `1` fila malformada `CHV-9999999` con `valor_procedimiento = -15000`, distribuido en `3` chunks):
- **Tiempo total de ejecución en AWS**: **`4,83 segundos`** (`estado = PROCESADO`, `chunks_completados = 3 / 3`).
- **Aislamiento de fila malformada sin abortar el chunk**: `ordenes_validas = 10.000`, `ordenes_rechazadas = 1`. El objeto `s3://saom-curated-329771219583/rechazos/fecha=2026-11-11/lote=LOTE-T3-INTEGRACION/chunk=00000.jsonl` registró `{"id_solicitud": "CHV-9999999", "estado": "REJECTED_SYNTAX", "motivo": "valor_procedimiento inválido"}` con **`0` datos PII en claro**.
- **Prueba de idempotencia en vivo (`RNF-06`)**: Al reenviar el descriptor del `chunk_id = 0` ya completado a la función `saom-worker` en AWS, DynamoDB rechazó la sobrescritura mediante `ConditionExpression`, devolviendo `{"chunks_procesados": 0, "duplicados_ignorados": 1}` y manteniendo inalterados los contadores de `META` (`chunks_completados = 3`, `ordenes_validas = 10.000`, `suma_aprobada = 475070357.5`).

---

## 4. Corrida Real del Dataset Oficial de 1.200.000 Solicitudes en AWS (`T4` · `LOTE-COIL-1200K`)

Se cargó el archivo oficial `COIL_dataset_glosas_salud_1_2M.csv` (`360.354.593 bytes`, SHA-256 `2c7631da66ffd2dc20c1f3aa17acc875b319601f0152c54ba7a36bc0716049c1`) en `s3://saom-raw-329771219583/ingesta/fecha=2026-11-11/lote=LOTE-COIL-1200K.csv` y se procesaron sus **240 chunks de 5.000 órdenes** en AWS Lambda (`arm64`, `1.769 MB`, `MaximumConcurrency = 10`):

| Indicador de la Corrida Oficial (`LOTE-COIL-1200K`) | Valor Real Medido en AWS | Cumplimiento de Requisitos |
| :--- | :--- | :--- |
| **Chunks completados / Chunks totales** | **`240 / 240`** (`estado = PROCESADO`) | 100 % completado sin pérdidas (`RNF-06`) |
| **Órdenes válidas + Órdenes rechazadas** | **`1.200.000` + `0` = `1.200.000`** | Conservación exacta de órdenes (`RF-01`) |
| **Suma total reclamada (`Decimal`)** | **`1.583.859.890.309,00`** | Aritmética decimal exacta (`RF-04`) |
| **Suma total aprobada (`Decimal`)** | **`57.328.903.464,00`** | Aritmética decimal exacta (`RF-04`) |
| **Raíz criptográfica del lote (`raiz_hash_lote`)** | `78dbff2ea6b365f3399315b1377111bc3ec23939ce539a101378b3f8b648869e` | Manifiesto WORM en `saom-audit` (`RF-05`, `RNF-04`) |
| **Mensajes en DLQ (`chunks-adjudicacion-dlq`)** | **`0` mensajes** | Cero fallos no recuperados (`RNF-06`) |
| **Tiempo de reloj (muro) de la corrida (10 workers)** | **`47,50 segundos`** (`0,79 minutos`) | Cumple SLA prototipo $\le 2,4\text{ h}$ (`RNF-01`, `P-16`) |
| **Duración media E2E por chunk en CloudWatch (`REPORT`)** | **`1.061,60 ms`** (`1,06 s` por bloque de 5.000 órdenes) | Incluye S3 Range GET + CPU + S3 PUT + DynamoDB |
| **Throughput real E2E en CloudWatch ($k_{\text{AWS-E2E}}$)** | **`4.710,44 órdenes/s/vCPU`** | Supera **11,8x** la hipótesis $k \ge 400$ (`P-07`) |
| **Throughput del núcleo en memoria ($k_{\text{EMF-Core}}$)** | **`14.279,66 órdenes/s/vCPU`** | Métrica EMF `ThroughputOrdenesPorSegundo` |
| **Memoria máxima consumida (`Max Memory Used`)** | **`153,0 MB`** (de `1.769 MB` = 8,6 % de uso) | Amplio margen de seguridad en memoria |
| **Cómputo total facturado (`Billed Duration`)** | `292.540 ms` = **`505,37 GB-s`** (`0,0067 USD` en Lambda Arm64) | Medido directamente de los registros `REPORT` |
| **Costo total real de la corrida de 1,2M en AWS** | **`0,0189 USD`** (**`0,0158 USD por millón`**) | Cumple `RNF-03` ($\le 0,50\text{ USD/M}$; `< 0,04 %` del crédito de 50 USD) |
| **Escaneo de PII en S3, DynamoDB y CloudWatch (`RNF-05`)** | **`0` coincidencias** | Cumple `RNF-05` y `ADR-002` |

### 4.1. Evidencia Visual en AWS Console: DynamoDB (`control_lotes`)

La siguiente captura de pantalla de la consola oficial de Amazon DynamoDB en la cuenta `329771219583` demuestra la consulta directa sobre `PK = LOTE#LOTE-COIL-1200K` y `SK = META`, evidenciando el estado `PROCESADO`, los `240` chunks completados y la versión del catálogo:

![Evidencia en Amazon DynamoDB: Item Resumen META de LOTE-COIL-1200K](../../docs/verificacion/screenshots/aws_dynamodb_lote_coil_1200k_meta.png)

### 4.2. Evidencia Visual en AWS Console: CloudWatch Metrics de AWS Lambda (`saom-worker`)

La siguiente captura de las métricas de Amazon CloudWatch para la función `saom-worker` en la cuenta `329771219583` muestra el pico de invocaciones concurrentes (10 ejecuciones simultáneas), la tasa de éxito del **100 % (0 errores)** y la duración promedio en torno a `1.061 ms`:

![Métricas en CloudWatch de la función Lambda saom-worker](../../docs/verificacion/screenshots/aws_lambda_saom_worker_metrics.png)

---

## 5. Calidad de Extracción `F1-Score` (`T5a`/`T5`) y Extrapolación $M/M/c$ hacia 12 Millones

### 5.1. Resultados de Precision, Recall y F1 sobre la Muestra de 600 Glosas (`RNF-02`)

Siguiendo el protocolo de [`docs/verificacion/T5a_protocolo_etiquetado_y_spans.md`](../../docs/verificacion/T5a_protocolo_etiquetado_y_spans.md), se evaluó `extraer_y_pseudonimizar_glosa()` bajo criterio estricto de coincidencia exacta de span (`[start_char, end_char]`) + valor sobre **600 glosas** (`300` limpias del dataset oficial + `300` perturbadas en 6 categorías de ruido/permutación/OCR, almacenadas fuera de git):

| Entidad Clínica (`RNF-02`) | F1 en Subconjunto Limpio (`300`) | F1 en Subconjunto Perturbado (`300`) | TP Global | FP Global | FN Global | Precision Global | Recall Global | **F1-Score Global (`600`)** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Edad` | `1,0000` | `0,9768` | 574 | 0 | 13 | 1,0000 | 0,9779 | **0,9888** |
| `PerfilCobertura` | `1,0000` | `0,9768` | 574 | 0 | 13 | 1,0000 | 0,9779 | **0,9888** |
| `ServicioSolicitado` | `1,0000` | `0,9787` | 576 | 0 | 12 | 1,0000 | 0,9796 | **0,9897** |
| `Medicacion` | `1,0000` | `0,9737` | 1.359 | 0 | 35 | 1,0000 | 0,9749 | **0,9873** |
| **Promedio Macro** | **1,0000** | **0,9765** | — | — | — | **1,0000** | **0,9776** | **0,9886** ($\ge 0,92$) |

### 5.2. Diferenciación entre Rendimiento Medido (`1,2M`) y Proyectado (`12M`) — Derivación de los `4,25 min` y `7,92 min`

Para distinguir con rigor qué se midió empíricamente en la cuenta `329771219583` y qué se proyecta hacia los `12.000.000` de órdenes (`2.400` chunks de `5.000` órdenes), se desglosan las dos métricas temporales:

1. **Rendimiento Medido en AWS (`1.200.000` órdenes · `240` chunks · `c = 10` workers)**:
   - **Duración media E2E por chunk en CloudWatch (`REPORT Duration`)**: $T_{\text{chunk}} = 1.061,60\text{ ms} = 1,0616\text{ s}$, lo que determina un throughput unitario real por worker ($1\text{ vCPU}$) de:
     $$k_{\text{AWS-E2E}} = \frac{5.000\text{ órdenes}}{1,0616\text{ s}} = 4.710,44\text{ órdenes/s/vCPU}$$
   - **Tiempo de drenaje puro de cómputo en los 10 workers (`240` chunks)**: $\frac{240 \times 1,0616\text{ s}}{10} = 25,48\text{ s}$.
   - **Tiempo de reloj extremo a extremo medido (`wall-clock`)**: **`47,50 s` (`0,79 min`)**, que suma los `25,48 s` de drenaje puro más `3,40 s` de particionamiento en streaming y `18,62 s` de *cold starts*, *polling* de SQS y *exponential backoff* en los 6 chunks con `TransactionConflict` en DynamoDB.
2. **Rendimiento Proyectado para `12.000.000` de Órdenes (`2.400` chunks · `c = 10` workers)**:
   - **De dónde salen los `4,25 minutos` (Tiempo de drenaje puro de cómputo en workers)**:
     $$T_{\text{drenaje, 12M}} = \frac{N_{\text{chunks}} \times T_{\text{chunk}}}{c} = \frac{2.400\text{ chunks} \times 1,0616\text{ s/chunk}}{10\text{ workers}} = \frac{2.547,84\text{ s}}{10} = 254,78\text{ s} = \mathbf{4,25\text{ minutos}}$$
     *(Equivalente a dividir $12.000.000\text{ órdenes}$ entre la capacidad agregada de los 10 workers: $10 \times 4.710,44 = 47.104,4\text{ órdenes/s}$).*
   - **Tiempo de reloj extremo a extremo proyectado incluyendo sobrecarga de coordinación (`7,92 minutos`)**:
     $$T_{\text{reloj, 12M}} = 10 \times T_{\text{reloj, 1.2M}} = 10 \times 47,50\text{ s} = 475,0\text{ s} = \mathbf{7,92\text{ minutos}}$$
   - Tanto el tiempo de drenaje puro (**`4,25 min`**) como el tiempo de reloj extremo a extremo (**`7,92 min`**) procesan los 12 millones de órdenes en **menos de 8 minutos**, cumpliendo con amplísimo margen la meta interna del equipo ($\le 3\text{ h} = 180\text{ min}$) y el SLA de la licitación ($< 24\text{ h}$).

| Escenario (12.000.000 de órdenes · 2.400 chunks) | $\lambda$ (órd/s) | $k$ (órd/s/vCPU) | $N$ workers ($M/M/c$) | Utilización $\rho$ | $W_q$ en cola | Drenaje puro (`c=10`) | Reloj E2E proyectado (`c=10`) | Costo Lote Completo (12M) | Costo Unitario por Millón |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Hipótesis Conservadora `P-07` — Ventana 24 h** | 138,89 | 400,00 | **1** | 0,3472 | 6,649 s | 50,00 min | ~55,00 min | 0,8806 USD | 0,0734 USD/M |
| **Hipótesis Conservadora `P-07` — Ventana 3 h** | 1.111,11 | 400,00 | **4** (`c=10` con 2,5x) | 0,6944 | 4,296 s | 50,00 min | ~55,00 min | 0,8806 USD | 0,0734 USD/M |
| **Con $k$ Medido en AWS — Ventana 24 h** | 138,89 | **4.710,44** | **1** | 0,0295 | 0,032 s | **4,25 min** | **7,92 min** | **0,2483 USD** (`0,1890` lineal) | **0,0207 USD/M** (`0,0158` lineal) |
| **Con $k$ Medido en AWS — Ventana 3 h** | 1.111,11 | **4.710,44** | **1** (`c=10` configurado) | 0,2359 | 0,328 s | **4,25 min** | **7,92 min** | **0,2483 USD** (`0,1890` lineal) | **0,0207 USD/M** (`0,0158` lineal) |

### 5.3. Conciliación y Unificación de las Cifras Económicas (`0,0158 USD/M`, `0,2483 USD` y `0,25–0,31 USD/M`)

Para evitar cualquier confusión entre el **costo unitario por millón de órdenes (`USD/M`)** y el **costo del lote completo (`1,2M` vs. `12M`)**, la tabla siguiente concilia los cuatro valores económicos del proyecto:

| Escenario Económico | Tipo de Cifra | Volumen del Lote | Cómputo Lambda Arm64 | S3 + SQS + DynamoDB + Operación | **Costo Total del Lote** | **Costo Unitario (`USD/M`)** | Explicación Coherente |
| :--- | :---: | :---: | ---: | ---: | ---: | ---: | :--- |
| **1. Estimado Previo de Diseño (E01/E02 con $k=400$)** | Estimado pre-ejecución | `1.200.000` (`240` chunks) | `0,0691 USD` (`~5.184 GB-s`) | `0,2309 USD` (con holgura operativa inicial) | **`~0,3000 USD`** | **`0,25 – 0,31 USD/M`** | Estimación teórica inicial en `ADR-003` y `RNF-03` (`P-06`) antes de medir $k$ en AWS, asumiendo `12,50 s/chunk` ($k=400$). |
| **2. Corrida Real en AWS Learner Lab (`LOTE-COIL-1200K`)** | **Medido en AWS** | `1.200.000` (`240` chunks) | **`0,0067 USD`** (`505,37 GB-s` reales) | **`0,0122 USD`** (`S3` `0,0025` + `DDB` `0,0012` + `SQS` `0,0002` + `CW/Athena` `0,0083`) | **`0,0189 USD`** | **`0,0158 USD/M`** | **Costo real medido**: $\frac{0,0189\text{ USD}}{1,2\text{ M}} = \mathbf{0,0158\text{ USD/M}}$ (16x menor que el estimado previo gracias a $k=4.710,44$). |
| **3. Escalamiento Lineal Directo `10×` (`12M`)** | Proyectado lineal puro | `12.000.000` (`2.400` chunks) | **`0,0674 USD`** (`5.053,7 GB-s`) | **`0,1216 USD`** (`10 ×` solicitudes S3, SQS, DynamoDB y CloudWatch) | **`0,1890 USD`** | **`0,0158 USD/M`** | Multiplicación directa $10 \times 0,0189\text{ USD}$ de exactamente los mismos servicios del prototipo. |
| **4. Producción Completa `12M` con Operación** | **Proyectado producción** | `12.000.000` (`2.400` chunks) | **`0,0587 USD`** (`2.400` chunks $\times 1,0616\text{ s}$) | **`0,1896 USD`** (añade retención S3 30 días, compactación Iceberg/Athena y API Gateway) | **`0,2483 USD`** (`~0,25 USD/lote`) | **`0,0207 USD/M`** | **`0,2483 USD` (`~0,25 USD`) es el costo del lote completo de 12 millones**, equivalente a **`0,0207 USD por millón`** ($\frac{0,2483}{12}$). |

---

## 6. Consolidación en Apache Iceberg y Consultas en Amazon Athena (`T6`)

En Amazon Athena (`saom_analytics.adjudicaciones`) se ejecutó la sentencia `MERGE INTO` desde `staging_adjudicaciones` hacia la tabla **Apache Iceberg (`Parquet`)**:
- **Primer `MERGE INTO`**: **`1.200.000` filas** consolidadas.
- **Segundo `MERGE INTO` sobre `chunk_id = 0` (prueba de idempotencia)**: **`1.200.000` filas** (`0` duplicados).
- **Verificación criptográfica de 3 niveles desde filas de Iceberg (`CHV-0000001` a `CHV-0000005`)**: coincidencia del **100 %** en Nivel 1 (`hash_decision`), Nivel 2 (`raiz_hash_chunk = 6e8de620c632b6382346f841988f2739595340e778a7b098daeacee40f26a757`) y Nivel 3 (`raiz_hash_lote = 78dbff2ea6b365f3399315b1377111bc3ec23939ce539a101378b3f8b648869e`).

### 6.1. Evidencia Visual en AWS Console: Amazon Athena (Consulta SQL a Apache Iceberg)

La siguiente captura en el editor de consultas de Amazon Athena muestra la ejecución exitosa de `SELECT COUNT(*) AS total_ordenes_iceberg FROM adjudicaciones;` sobre la base de datos `saom_analytics`, certificando la consolidación de exactamente **`1.200.000` registros**:

![Evidencia en Amazon Athena: Consulta SELECT COUNT a la tabla Iceberg adjudicaciones](../../docs/verificacion/screenshots/aws_athena_iceberg_1200k.png)
"""


def construir_e04_consolidado_markdown() -> str:
    return r"""# Entregable 04: Documento Consolidado Final de Arquitectura, Prototipo AWS y Verificación

| Campo | Detalle |
| :--- | :--- |
| **Proyecto** | Sistema de Adjudicación de Órdenes Médicas (SAOM) — Sistema de Salud de Chernovia (Licitación COIL) |
| **Metodología** | AI-DLC (6 Pasos: Problema/Estado del Arte, Requisitos BDD/RNF, Arquitectura C4/ADR, Plan, Implementación y Verificación) |
| **Equipo de Arquitectura** | **Naomi Chow · Daniel Lopez · María Fernanda Toro** |
| **Estado del Ciclo AI-DLC** | **Pasos 1 a 6 Completados y Verificados en AWS Academy Learner Lab (`329771219583`, `us-east-1`)** |

---

## 1. Resumen Ejecutivo y Contexto del Problema (Paso 1 AI-DLC · E01 v2)

El Ministerio de Salud de la República Federal de **Chernovia** requiere adjudicar lotes masivos de hasta **12.000.000 de órdenes médicas en menos de 24 horas** (con una meta interna de ingeniería del equipo de **3 horas** en ventana nocturna a `1.111,11 órdenes/s`), determinando para cada orden si el servicio solicitado está cubierto (`CUBRE` / `NO_CUBRE`), liquidando el monto aprobado al **100 %, 50 %, 25 % o 0 %** según el perfil de cobertura del afiliado (`PRIORITARIO`, `ESTANDAR`, `COPAGO`) y emitiendo evidencia criptográfica inmutable sin exponer información personal identificable (PII).

La revisión sistemática de la literatura (52 fuentes indexadas `[1]` a `[52]` en el [Entregable 01 v2](../E01/Entregable_01_Propuesta_Arquitectura_Salud_COIL_v2.docx)) demostró que:
1. **Inviabilidad de la orquestación serverless orden por orden con APIs cognitivas por carácter**: Procesar 12 millones de glosas (~213 caracteres promedio, facturadas al mínimo de 300 caracteres = 3 unidades de 100 caracteres por solicitud = 36 millones de unidades) en **Amazon Comprehend Medical** más **AWS Step Functions Standard** (`10` transiciones/orden) cuesta **`244.500 USD/día`** aplicando la tarifa escalonada oficial de AWS (`10M u. × 0,0105 USD + 26M u. × 0,00525 USD = 241.500 USD` + `3.000 USD` de Step Functions) o **`381.000 USD/día`** a tarifa plana Tier 1, además de que Comprehend Medical opera únicamente en idioma inglés.
2. **Inviabilidad de clústeres pesados en el entorno de validación académica**: Un clúster Apache Spark sobre Amazon EMR (`24 × c6g.4xlarge`, ~220 USD/día) excede los límites de instancias, vCPU, permisos IAM y presupuesto (`50 USD`) del **AWS Academy Learner Lab**.
3. **Solución adoptada (`ADR-001` a `ADR-005`)**: Una **arquitectura híbrida serverless por micro-lotes (chunks de 5.000 órdenes)** sobre **AWS Lambda Graviton2 (`arm64`, `1.769 MB`)**, que elimina el cobro por carácter y por transición individual, logrando un costo real medido en AWS de **`0,0189 USD`** para el dataset oficial de `1.200.000` solicitudes (**`0,0158 USD por millón`**, o **`0,2483 USD`** proyectados para 12 millones de órdenes), lo que representa un **ahorro superior al 99,9 %** frente a la línea base de auditoría manual (`0,80 USD/orden`).

---

## 2. Requisitos Funcionales (BDD) y No Funcionales Verificados (Paso 2 AI-DLC)

### 2.1. Requisitos del Enunciado vs. Metas de Ingeniería del Equipo

| Dimensión | Requisito del Enunciado | Meta Propia del Equipo (`RNF`) | Resultado Real Medido en AWS (`T4`/`T5`/`T6`) |
| :--- | :--- | :--- | :--- |
| **Volumen y ventana (SLA)** | 12M de órdenes en `< 24 h` (`138,89 órd/s`) | 12M en `<= 3 h` (`1.111,11 órd/s`); 1,2M en `<= 2,4 h` | **1,2M procesadas en `47,50 s`** (`4,25 min` proyectados para 12M con 10 workers) |
| **Calidad de extracción** | Extraer paciente, edad, servicio y medicación | `Macro-F1 >= 0,92` en 4 entidades con spans exactos (`RNF-02`) | **`Macro-F1 = 0,9886`** (`1,0000` en 300 limpias y `0,9765` en 300 perturbadas) |
| **Costo de operación** | Costo razonable | `<= 0,50 USD/millón` en laboratorio y ahorro `>= 70 %` (`RNF-03`) | **`0,0158 USD/millón`** (`0,0189 USD` para 1,2M; ahorro del **99,99 %**) |
| **Trazabilidad y privacidad** | Registro trazable de cada decisión | Cadena SHA-256 de 3 niveles (`RNF-04`) y `0` PII en claro (`RNF-05`) | **`100 %` verificado en 3 niveles** desde Iceberg hasta `raiz_hash_lote`; **`0` PII** |
| **Tolerancia a fallos** | Escalabilidad y resiliencia | Idempotencia exacta en DynamoDB e Iceberg y aislamiento de filas malformadas (`RNF-06`) | **`1.200.000` órdenes exactas** tras doble `MERGE INTO` y `duplicados_ignorados = 1` en reenvío |

---

## 3. Diseño Técnico Simplificado y Decisiones Arquitectónicas (Paso 3 AI-DLC · E02)

### 3.1. Vista General del Flujo en AWS (8 Pasos numerados)

![Arquitectura Simplificada en AWS (E02)](../../docs/design/diagramas/e02_arquitectura_simplificada.png)

### 3.2. Pipeline Interno Determinista de un Worker (`saom_core.py`)

![Pipeline Interno del Worker Adjudicador](../../docs/design/diagramas/e02_pipeline_worker.png)

### 3.3. Síntesis de los 5 Architecture Decision Records (`ADR-001` a `ADR-005`)

| ADR | Decisión | Justificación y Verificación Empírica |
| :--- | :--- | :--- |
| **[ADR-001](../../docs/design/adr/ADR-001-patron-arquitectonico.md)** | Ingesta desacoplada en S3 + SQS y procesamiento paralelo por chunks de 5.000 órdenes (`Range=bytes=inicio-fin`). | Reduce en **5.000x** las llamadas de coordinación frente al patrón orden por orden; verificado con 240 chunks en AWS. |
| **[ADR-002](../../docs/design/adr/ADR-002-estrategia-trazabilidad-y-pii.md)** | Pseudonimización `HMAC-SHA256`, enmascaramiento con `#` preservando longitud y cadena SHA-256 de 3 niveles. | Conserva intactos los desplazamientos `[start_char, end_char]` y logra `0` coincidencias de PII en S3, DynamoDB y CloudWatch. |
| **[ADR-003](../../docs/design/adr/ADR-003-dimensionamiento-prototipo-vs-produccion.md)** | Prototipo con las 1.200.000 órdenes oficiales en el Learner Lab (`LabRole`) y extrapolación $M/M/c$ hacia 12M. | Ejecutado consumiendo solo `0,0189 USD` del crédito académico de `50 USD`. |
| **[ADR-004](../../docs/design/adr/ADR-004-motor-computo-workers.md)** | Workers sin estado en AWS Lambda Graviton2 (`arm64`, `1.769 MB` = 1 vCPU) portables a ECS Fargate Spot. | Duración media real en CloudWatch de `1.061,60 ms` por chunk (`4.710,44 órdenes/s/vCPU`) y `153 MB` de RAM pico. |
| **[ADR-005](../../docs/design/adr/ADR-005-almacenamiento-analitico-y-control.md)** | Persistencia políglota: DynamoDB (`control_lotes`), Apache Iceberg en S3 (`adjudicaciones`) y bucket WORM (`saom-audit`). | Verificado con `TransactWriteItems` (con *backoff* ante `TransactionConflict`), doble `MERGE INTO` en Athena (`1.200.000` filas) y manifiesto WORM. |

---

## 4. Resultados de la Ejecución Real en AWS (`T2`, `T3`, `T4`, `T5` y `T6` · E03)

### 4.1. Corrida Completa del Dataset Oficial (`LOTE-COIL-1200K` · 1.200.000 Solicitudes)

- **Identificador del lote**: `LOTE-COIL-1200K` (`s3://saom-raw-329771219583/ingesta/fecha=2026-11-11/lote=LOTE-COIL-1200K.csv`, `360.354.593 bytes`).
- **Progreso y tiempo total**: **`240 / 240` chunks completados en `47,50 segundos`** con 10 workers concurrentes (`ordenes_validas = 1.200.000`, `ordenes_rechazadas = 0`, `DLQ = 0`).
- **Liquidación financiera exacta (`Decimal`)**:
  - Valor total reclamado: **`1.583.859.890.309,00`**
  - Valor total aprobado por el fondo público: **`57.328.903.464,00`**
- **Raíz criptográfica del lote (`raiz_hash_lote`)**: `78dbff2ea6b365f3399315b1377111bc3ec23939ce539a101378b3f8b648869e`.

#### Evidencia en AWS Console: Control de Lotes y Chunks en DynamoDB (`META`)
![Evidencia en Amazon DynamoDB: Item Resumen META de LOTE-COIL-1200K](../../docs/verificacion/screenshots/aws_dynamodb_lote_coil_1200k_meta.png)

#### Evidencia en AWS Console: Métricas de Cómputo CloudWatch en AWS Lambda (`saom-worker`)
![Métricas en CloudWatch de la función Lambda saom-worker](../../docs/verificacion/screenshots/aws_lambda_saom_worker_metrics.png)

### 4.2. Consolidación en Apache Iceberg y Consultas Analíticas en Amazon Athena (`T6`)

La tabla Iceberg `saom_analytics.adjudicaciones` consolidó las **`1.200.000` órdenes** y demostró idempotencia exacta tras repetir `MERGE INTO` (`1.200.000` filas). El desglose por fecha y por canal emisor obtenido en Athena es el siguiente:

| Día de Solicitud | Órdenes Adjudicadas | Total Reclamado | Total Aprobado |
| :--- | ---: | ---: | ---: |
| `2026-05-04` | 402.000 | 529.215.196.182,00 | 19.155.939.616,75 |
| `2026-05-05` | 396.000 | 522.711.751.027,00 | 18.950.939.658,50 |
| `2026-05-06` | 402.000 | 531.932.943.100,00 | 19.222.024.188,75 |
| **Total Oficial** | **1.200.000** | **1.583.859.890.309,00** | **57.328.903.464,00** |

#### Evidencia en AWS Console: Consulta SQL SELECT COUNT en Amazon Athena
![Evidencia en Amazon Athena: Consulta SELECT COUNT a la tabla Iceberg adjudicaciones](../../docs/verificacion/screenshots/aws_athena_iceberg_1200k.png)

### 4.3. Justificación de la Extrapolación a 12 Millones: Rendimiento Medido (`1,2M`) vs. Proyectado (`12M`)

Para distinguir con absoluta precisión qué se midió en vivo en AWS (`1.200.000` órdenes = `240` chunks) y cómo se proyecta el comportamiento para el lote completo de la licitación (`12.000.000` de órdenes = `2.400` chunks de `5.000` órdenes con `c = 10` workers), se presenta la derivación paso a paso:

| Métrica | Naturaleza | Escala | Valor | Derivación / Origen |
| :--- | :---: | :---: | ---: | :--- |
| **Duración media por chunk ($T_{\text{chunk}}$)** | **Medido (CloudWatch)** | 1 chunk (`5.000` órd.) | **`1.061,60 ms`** (`1,0616 s`) | Promedio de `REPORT Duration` en `saom-worker` (`1.769 MB` = `1 vCPU`). |
| **Throughput unitario E2E ($k_{\text{AWS-E2E}}$)** | **Medido (CloudWatch)** | 1 worker (`1 vCPU`) | **`4.710,44 órd/s/vCPU`** | $k_{\text{AWS-E2E}} = \frac{5.000\text{ órd.}}{1,0616\text{ s}} = 4.710,44\text{ órd/s/vCPU}$. |
| **Tiempo de drenaje puro de cómputo (`1,2M`)** | **Medido (CloudWatch)** | `1,2M` (`240` chunks, `c=10`) | **`25,48 s`** (`0,42 min`) | $\frac{240\text{ chunks} \times 1,0616\text{ s}}{10\text{ workers}} = 25,48\text{ s}$ de trabajo efectivo en workers. |
| **Tiempo de reloj extremo a extremo (`1,2M`)** | **Medido (Reloj E2E)** | `1,2M` (`240` chunks, `c=10`) | **`47,50 s`** (`0,79 min`) | Incluye los `25,48 s` de drenaje + `3,40 s` del particionador + `18,62 s` de *cold starts*, colas SQS y *backoff* en 6 chunks con `TransactionConflict`. |
| **Tiempo de drenaje puro de cómputo (`12M`)** | **Proyectado ($M/M/c$)** | `12M` (`2.400` chunks, `c=10`) | **`254,78 s` (`4,25 min`)** | $\frac{2.400\text{ chunks} \times 1,0616\text{ s}}{10\text{ workers}} = \frac{12.000.000\text{ órd.}}{47.104,4\text{ órd/s}} = 254,78\text{ s} = \mathbf{4,25\text{ min}}$. |
| **Tiempo de reloj extremo a extremo (`12M`)** | **Proyectado (Lineal E2E)** | `12M` (`2.400` chunks, `c=10`) | **`475,00 s` (`7,92 min`)** | $10 \times 47,50\text{ s} = 475,0\text{ s} = \mathbf{7,92\text{ min}}$ (incluyendo particionador, SQS y reintentos DynamoDB). |

### 4.4. Unificación y Conciliación de las Cifras Económicas (`0,0158 USD/M`, `0,1890 USD`, `0,2483 USD` y `0,25–0,31 USD/M`)

Para evitar cualquier confusión entre el **costo unitario por millón (`USD/M`)** y el **costo total por lote (`1,2M` vs. `12M`)**, la tabla siguiente concilia en un único cuadro las cifras económicas de todas las etapas del proyecto:

| Escenario Económico | Naturaleza | Tamaño del Lote | Cómputo Lambda Arm64 | S3 + SQS + DynamoDB + Operación | **Costo Total del Lote** | **Costo Unitario (`USD/M`)** | Explicación Coherente |
| :--- | :---: | :---: | ---: | ---: | ---: | ---: | :--- |
| **1. Estimado Teórico Previo (Diseño E01/E02 con $k=400$)** | Estimado pre-ejecución | `1.200.000` (`240` chunks) | `0,0691 USD` (`~5.184 GB-s`) | `0,2309 USD` (con holgura operativa inicial) | **`~0,3000 USD`** | **`0,25 – 0,31 USD/M`** | Estimación inicial en `ADR-003` y `RNF-03` (`P-06`) antes de medir $k$ en AWS, asumiendo `12,50 s/chunk` ($k=400$). |
| **2. Corrida Real en AWS Learner Lab (`LOTE-COIL-1200K`)** | **Medido en AWS** | `1.200.000` (`240` chunks) | **`0,0067 USD`** (`505,37 GB-s` reales) | **`0,0122 USD`** (`S3` `0,0025` + `DDB` `0,0012` + `SQS` `0,0002` + `CW/Athena` `0,0083`) | **`0,0189 USD`** | **`0,0158 USD/M`** | **Costo real medido**: $\frac{0,0189\text{ USD}}{1,2\text{ M}} = \mathbf{0,0158\text{ USD/M}}$ (16x menor que el estimado previo gracias a $k=4.710,44$). |
| **3. Escalamiento Lineal Directo `10×` (`12M`)** | Proyectado lineal puro | `12.000.000` (`2.400` chunks) | **`0,0674 USD`** (`5.053,7 GB-s`) | **`0,1216 USD`** (`10 ×` solicitudes S3, SQS, DynamoDB y CloudWatch) | **`0,1890 USD`** | **`0,0158 USD/M`** | Multiplicación directa $10 \times 0,0189\text{ USD}$ de exactamente los mismos servicios ejecutados en el prototipo. |
| **4. Producción Completa `12M` con Operación** | **Proyectado producción** | `12.000.000` (`2.400` chunks) | **`0,0587 USD`** (`2.400` chunks $\times 1,0616\text{ s}$) | **`0,1896 USD`** (añade retención S3 30 días, compactación diaria Iceberg/Athena y API Gateway) | **`0,2483 USD`** (`~0,25 USD/lote`) | **`0,0207 USD/M`** | **`0,2483 USD` (`~0,25 USD`) es el costo del lote diario completo de 12 millones**, equivalente a **`0,0207 USD por millón`** ($\frac{0,2483}{12}$). |

---

## 5. Conclusiones e Índice Maestro de Entregables

1. **Trazabilidad extremo a extremo bajo AI-DLC**: Cada requisito (`RF-01..05`, `RNF-01..06`) está vinculado a una decisión arquitectónica (`ADR-001..005`), a una función de código en `prototype/`, a un test automatizado en `pytest` (`36 passed`) y a una métrica real medida en AWS (`T3_T4_T6_ejecucion_real_aws.md`).
2. **Índice de documentos finales del repositorio**:
   - **Entregable 01 (v2 corregida)**: [`entregables/E01/Entregable_01_Propuesta_Arquitectura_Salud_COIL_v2.docx`](../E01/Entregable_01_Propuesta_Arquitectura_Salud_COIL_v2.docx)
   - **Entregable 02 (Diseño Técnico Simplificado)**: [`entregables/E02/Entregable_02_Diseno_Tecnico_Salud_COIL.docx`](../E02/Entregable_02_Diseno_Tecnico_Salud_COIL.docx)
   - **Entregable 03 (Prototipo en AWS y Evidencias)**: [`entregables/E03/Entregable_03_Prototipo_Evidencia_Salud_COIL.docx`](../E03/Entregable_03_Prototipo_Evidencia_Salud_COIL.docx)
   - **Entregable 04 (Documento Consolidado + Presentación `.pptx` + Guion Video 3–4 min + Guía Demo)**:
     - [`entregables/E04/Entregable_04_Documento_Consolidado_Salud_COIL.docx`](Entregable_04_Documento_Consolidado_Salud_COIL.docx)
     - [`entregables/E04/Entregable_04_Presentacion_Ejecutiva_Salud_COIL.pptx`](Entregable_04_Presentacion_Ejecutiva_Salud_COIL.pptx)
     - [`entregables/E04/Entregable_04_Guion_Pitch_Sustentacion_COIL.docx`](Entregable_04_Guion_Pitch_Sustentacion_COIL.docx)
     - [`entregables/E04/Entregable_04_Guia_Demostracion_Comite.docx`](Entregable_04_Guia_Demostracion_Comite.docx)
   - **Bitácora COIL**: [`docs/bitacora/bitacora_decisiones.md`](../../docs/bitacora/bitacora_decisiones.md)
"""


def construir_e04_pitch_markdown() -> str:
    return r"""# Entregable 04: Estructura de Diapositivas y Guion de Video (3 a 4 Minutos)

| Campo | Detalle |
| :--- | :--- |
| **Duración objetivo del video** | **3 minutos 30 segundos** (rango permitido: **3:00 a 4:00 minutos**; ~35 s por diapositiva) |
| **Presentación Editable** | [`Entregable_04_Presentacion_Ejecutiva_Salud_COIL.pptx`](Entregable_04_Presentacion_Ejecutiva_Salud_COIL.pptx) (`6` diapositivas ejecutivas 16:9 con diagramas, capturas AWS y notas de orador) |
| **Expositores (70 s c/u)** | **Naomi Chow** (`0:00 – 1:10`) · **Daniel Lopez** (`1:10 – 2:20`) · **María Fernanda Toro** (`2:20 – 3:30`) |
| **Evidencia en vivo incluida** | Cuenta AWS `329771219583` (`us-east-1`), corrida real de `1.200.000` órdenes en `47,50 s`, CloudWatch, DynamoDB `META` y Amazon Athena (Iceberg) |

---

## 1. Mapa de las 6 Diapositivas y Distribución del Tiempo (3:30 min)

| Diapositiva | Título | Expositor(a) | Tiempo | Mensaje Clave / Visual |
| :---: | :--- | :--- | :---: | :--- |
| **1** | Reto de Chernovia y Por Qué Fallan Otras Arquitecturas | **Naomi Chow** | `0:00 – 0:35` | `12M` órdenes en `< 24 h` (meta `3 h`), liquidación `100/50/25/0 %`. Comprehend Medical (`244.500 USD/día` escalonado, solo inglés) y EMR (`~220 USD/día`) son inviables frente a SAOM (**`0,0158 USD/M`**). |
| **2** | Metodología AI-DLC y Requisitos Verificados (`RF` + `RNF`) | **Naomi Chow** | `0:35 – 1:10` | 6 pasos AI-DLC y tabla de cumplimiento: `36/36` tests, `Macro-F1 = 0,9886 >= 0,92`, `0` PII en claro, `<= 0,50 USD/M` e idempotencia exacta. |
| **3** | Arquitectura Serverless por Micro-Lotes e Idempotencia (`ADR-001..005`) | **Daniel Lopez** | `1:10 – 1:45` | Diagrama `e02_arquitectura_simplificada.png`: S3 Raw → SQS → Particionador streaming (`4 MB` RAM, bloques de `5.000` órd.) → Lambda `arm64` (`1.769 MB`) + `TransactWriteItems` con *backoff* ante `TransactionConflict`. |
| **4** | Ejecución Real en AWS Learner Lab (`1.200.000` Órdenes en `47,50 s`) | **Daniel Lopez** | `1:45 – 2:20` | Capturas reales de **CloudWatch (`saom-worker`)** y **DynamoDB (`META`)**: `240/240` chunks, `4.710,44 órd/s/vCPU`, `1.061,60 ms/chunk`, `153 MB` RAM, `0` DLQ y **`0,0189 USD`** totales. |
| **5** | Privacidad PII, `Macro-F1 = 0,9886`, SHA-256 y Apache Iceberg (`T5` + `T6`) | **María Fernanda Toro** | `2:20 – 2:55` | `HMAC-SHA256` + `#` conservando spans `[start_char, end_char]`, `Decimal` sin `float`, `Macro-F1 = 0,9886` (600 glosas), cadena SHA-256 de 3 niveles y captura de **Amazon Athena** (`1.200.000` filas). |
| **6** | Extrapolación a 12M (`4,25` / `7,92 min`), Conciliación FinOps y Cierre | **María Fernanda Toro** | `2:55 – 3:30` | Medido vs. Proyectado (`4,25 min` drenaje puro vs. `7,92 min` E2E) y unificación de costos (`0,25–0,31 USD/M` estimado previo vs. **`0,0158 USD/M`** medido vs. **`0,2483 USD`** lote 12M con operación). |

---

## 2. Guion Detallado Cronometrado para Video (~515 Palabras · 3:30 min a Ritmo Normal)

> **Consejo de grabación:** A un ritmo natural de **145 palabras por minuto**, cada bloque de ~170 palabras dura exactamente **70 segundos**, dejando 20–30 segundos de holgura por debajo del límite de 4 minutos para transiciones entre integrantes o mostrar brevemente la consola de AWS.

### Bloque 1 — Naomi Chow (`0:00` a `1:10` · ~170 palabras)

- **[Diapositiva 1 · `0:00–0:35`]**:
  > *"Hola, somos Naomi Chow, Daniel Lopez y María Fernanda Toro, y presentamos SAOM, el Sistema de Adjudicación de Órdenes Médicas para el Ministerio de Salud de Chernovia. El reto exige procesar hasta 12 millones de órdenes diarias en menos de 24 horas —con una meta interna de nuestro equipo de 3 horas—, extraer cuatro entidades clínicas de cada glosa, liquidar al 100, 50, 25 o 0 por ciento y dejar auditoría verificable sin exponer PII. Al evaluar 52 fuentes técnicas demostramos que orquestar orden por orden con Step Functions y Comprehend Medical cuesta 244.500 dólares al día por su mínimo de 300 caracteres y solo opera en inglés, mientras que un clúster EMR de 220 dólares diarios excede los 50 dólares del Learner Lab. Por eso diseñamos una arquitectura por micro-lotes de 5.000 órdenes en AWS Lambda Arm64."*
- **[Diapositiva 2 · `0:35–1:10`]**:
  > *"Aplicamos la metodología AI-DLC en seis pasos trazables, separando los requisitos del enunciado de nuestras metas de ingeniería: `Macro-F1 >= 0,92`, costo `<= 0,50 USD por millón`, cero datos personales en claro e idempotencia exacta, todo verificado con 36 pruebas automatizadas y ejecución real en AWS. Le doy paso a Daniel para mostrar la arquitectura y los resultados en la nube."*

---

### Bloque 2 — Daniel Lopez (`1:10` a `2:20` · ~170 palabras)

- **[Diapositiva 3 · `1:10–1:45`]**:
  > *"Gracias, Naomi. Como muestra nuestro diagrama de 8 pasos, cuando el CSV llega a `saom-raw`, la función `saom-particionador` lo recorre en streaming con solo 4 MB de RAM y publica en SQS descriptores livianos con los rangos exactos de bytes de cada bloque de 5.000 órdenes, reduciendo 5.000 veces la coordinación. Hasta 10 workers Lambda `arm64` leen solo su rango con `S3 Range GET` y consolidan atómicamente en DynamoDB `control_lotes`. En la prueba `T3` aislamos una fila corrupta en `rechazos/` sin PII e ignoramos reenvíos duplicados; y al correr los 240 chunks en paralelo resolvimos la contención `TransactionConflict` sobre el ítem `META` mediante exponential backoff con jitter."*
- **[Diapositiva 4 · `1:45–2:20`]**:
  > *"Con esto ejecutamos en nuestra cuenta de AWS (`329771219583`) el dataset oficial completo de 1.200.000 órdenes (`LOTE-COIL-1200K`). Como muestran las capturas reales de CloudWatch y DynamoDB, los 240 chunks finalizaron en **47,50 segundos** de reloj con cero errores y cero mensajes en la DLQ, a una media de `1.061,60 ms` por chunk —es decir, **4.710,44 órdenes por segundo por vCPU**— consumiendo apenas `153 MB` de RAM y **0,0189 dólares totales**. Continúa María Fernanda."*

---

### Bloque 3 — María Fernanda Toro (`2:20` a `3:30` · ~175 palabras)

- **[Diapositiva 5 · `2:20–2:55`]**:
  > *"Gracias, Daniel. En cada worker, `saom_core.py` pseudonimiza paciente, DNO y Seguro Social con `HMAC-SHA256` y los enmascara con `#` conservando la longitud exacta de la glosa, de modo que los spans `[start_char, end_char]` no se desplazan y logramos cero PII en S3, DynamoDB y CloudWatch. Sobre 600 glosas evaluadas fuera de git —300 limpias y 300 con ruido OCR y permutaciones— obtuvimos un **Macro-F1 de `0,9886`**, usando `Decimal` exacto sin `float`. Además, como ven en la captura de Amazon Athena, consolidamos las 1.200.000 filas en Apache Iceberg con doble `MERGE INTO` sin duplicados y verificamos la cadena SHA-256 de tres niveles hasta `raiz_hash_lote`."*
- **[Diapositiva 6 · `2:55–3:30`]**:
  > *"Para cerrar, diferenciamos lo medido de lo proyectado a 12 millones (`2.400` chunks con 10 workers): el drenaje puro de cómputo es `2.400 × 1,0616 / 10 = 4,25 minutos`, y el tiempo de reloj extremo a extremo escalando colas y particionador es `7,92 minutos`, ambos muy por debajo de 3 horas. En costos, frente al estimado teórico previo de `0,25 a 0,31 USD/M`, el gasto real medido en AWS fue **`0,0158 USD por millón`**, proyectando **`0,1890 USD` lineal** o **`0,2483 USD` por el lote diario completo de 12 millones** con retención S3 y compactación Iceberg (`0,0207 USD/M`). Muchas gracias."*

---

## 3. Banco de Defensa Técnica (Para Sesión de Preguntas o Anexos)

| Posible Pregunta del Jurado | Respuesta Técnica Concreta con Datos del Proyecto |
| :--- | :--- |
| **1. ¿Por qué usaron un parser determinista en lugar de un LLM o Comprehend Medical?** | Porque las glosas de Chernovia siguen una plantilla semiestructurada de 7 campos (`ADR-004`). Un parser determinista logra `F1 = 1,0000` en la plantilla oficial (`0,9886` incluyendo ruido OCR/permutación), procesa a `4.710 órdenes/s/vCPU` con `0,0158 USD/millón` y ofrece explicabilidad determinista (`regla_ids` + spans), mientras que Comprehend Medical cuesta `244.500 USD/día` y solo soporta inglés. Si una glosa llega truncada o alterada por OCR en un campo obligatorio, el sistema activa `AUDIT_FLAG_CLINICAL_UNCERTAINTY` y la deriva a revisión humana de segunda línea. |
| **2. ¿Cómo garantizan que el enmascaramiento de PII no desplace los spans `[start_char, end_char]`?** | En `extraer_y_pseudonimizar_glosa()` (`prototype/saom_core.py`), los valores de `Paciente`, `DNO` y `SeguroSocial` se sustituyen carácter por carácter por `'#' * len(valor)`. Como la longitud en caracteres antes y después de cada `;` permanece invariante, cualquier índice `glosa[start_char:end_char]` apunta exactamente a la misma subcadena clínica, lo cual está verificado en `test_t1_spans_iguales_en_glosa_original_y_enmascarada`. |
| **3. ¿Qué ocurrió en DynamoDB cuando corrieron los 240 chunks en paralelo en AWS?** | Los 10 workers concurrentes intentaban actualizar atómicamente su registro `CHUNK#` y sumar al contador único `META` del lote mediante `TransactWriteItems`. En 6 de los 240 chunks coincidieron dos escrituras en el mismo milisegundo sobre `META`, generando `TransactionConflict`. Inspeccionamos `CancellationReasons` para distinguir `ConditionalCheckFailed` (chunk duplicado ya procesado, que se ignora) de `TransactionConflict` (contención transitoria en `META`, que se reintenta con *exponential backoff* + *jitter*), logrando `240/240` chunks exactos en `47,50 s`. |
| **4. ¿Cómo resolvieron la restricción de S3 Object Lock en el Learner Lab?** | La sonda `verify-r01` detectó que `LabRole` deniega `s3:PutObjectLockConfiguration` al crear el bucket. Se activó automáticamente la contingencia definida en `ADR-003` y `ADR-005`: **S3 Versioning + Bucket Policy `DenyDeleteAuditReceipts`** (que bloquea `s3:DeleteObject` y `s3:DeleteObjectVersion` sobre `recibos/*`) combinada con la verificación criptográfica SHA-256 de tres niveles (`hash_decision` → `raiz_hash_chunk` → `raiz_hash_lote`). |
| **5. ¿Cómo se concilian las cifras de `0,0158 USD/M`, `0,2483 USD` y `0,25–0,31 USD/M`?** | Corresponden a tres escenarios claramente diferenciados: **1)** `0,25 a 0,31 USD por millón` fue la **estimación teórica previa de diseño** (`E01/E02`) antes de ejecutar en AWS, cuando asumíamos conservadoramente $k=400\text{ órd/s/vCPU}$ (`12,5 s/chunk`). **2)** **`0,0158 USD por millón`** es el **costo unitario real medido en AWS** en la corrida de 1,2M (`0,0189 USD / 1,2M`), que al escalar linealmente por 10 da **`0,1890 USD` para un lote de 12M**. **3)** **`0,2483 USD`** (aprox. `0,25 USD` por lote diario) no es un costo por millón, sino el **costo del lote completo de 12 millones en producción** incluyendo retención mensual en S3 y compactación diaria de Iceberg/Athena, lo que equivale a **`0,0207 USD por millón`** (`0,2483 / 12`). |
| **6. ¿De dónde salen los `4,25 minutos` para 12 millones y qué diferencia hay entre el tiempo medido y el proyectado?** | En la corrida real de 1,2M (`240` chunks con 10 workers), medimos dos tiempos: **a)** la duración media de un chunk en un worker Lambda según CloudWatch (`1,0616 s`, equivalente a $k = 4.710,44\text{ órd/s/vCPU}$ y `25,48 s` de drenaje puro para 240 chunks) y **b)** el tiempo total de reloj extremo a extremo (`47,50 s`, que añade particionador, colas SQS y *backoff* en DynamoDB). Al proyectar a 12 millones (`2.400` chunks con 10 workers): el **tiempo de drenaje puro de cómputo en workers** es $\frac{2.400 \times 1,0616\text{ s}}{10} = 254,78\text{ s} = \mathbf{4,25\text{ minutos}}$, mientras que el **tiempo de reloj extremo a extremo proyectado** (incluyendo sobrecarga de colas y coordinación) es $10 \times 47,50\text{ s} = 475,0\text{ s} = \mathbf{7,92\text{ minutos}}$. Ambos están muy por debajo de la meta de 3 horas (`180 min`). |
"""


def construir_e04_guia_demo_markdown() -> str:
    return r"""# Entregable 04: Guía Operativa de Demostración en Vivo ante el Comité Evaluador

| Campo | Detalle |
| :--- | :--- |
| **Objetivo** | Comprobar en tiempo real (o mediante evidencia certificada si la sesión del Learner Lab está cerrada) los resultados en **Amazon DynamoDB**, **Amazon Athena (Apache Iceberg)** y **Amazon CloudWatch / AWS Lambda** |
| **Cuenta AWS** | `329771219583` (`us-east-1`, rol `LabRole`, usuario `daniel_lopez`) |
| **Tiempo estimado de demo** | **2 a 3 minutos** durante la sesión de preguntas del comité |

---

## 1. Preparación Previa (10 Minutos antes de la Sustentación)

1. Iniciar sesión en **AWS Academy Learner Lab** y pulsar **Start Lab** (esperar a que el círculo de `AWS` pase a verde).
2. Dejar abiertas **3 pestañas en el navegador** en la región **`us-east-1` (N. Virginia)**:
   - **Pestaña 1 — Amazon DynamoDB**: `DynamoDB` → `Explore items` → tabla **`control_lotes`**.
   - **Pestaña 2 — Amazon Athena**: `Athena` → `Query editor` → `Database: saom_analytics`.
   - **Pestaña 3 — AWS Lambda / CloudWatch**: `Lambda` → `Functions` → **`saom-worker`** → pestaña **`Monitor`**.
3. Si se desea ejecutar un comando desde la terminal local, actualizar las credenciales temporales en `C:\Users\danie\.aws\credentials` copiando el bloque de `AWS Details` → `AWS CLI: Show`.

---

## 2. Paso 1 de la Demo (45 s) — Comprobación del Lote `LOTE-COIL-1200K` en Amazon DynamoDB

En la **Pestaña 1 (`DynamoDB` → `control_lotes` → `Explore items`)**:
1. Seleccionar **Query**.
2. En **Partition key (`PK`)**, ingresar:
   ```text
   LOTE#LOTE-COIL-1200K
   ```
3. En **Sort key (`SK`)**, seleccionar `Equal to` e ingresar:
   ```text
   META
   ```
4. Pulsar **Run** y mostrar al comité la fila devuelta:
   - `estado = PROCESADO`
   - `chunks_completados = 240` y `chunks_totales = 240`
   - `ordenes_validas = 1200000` y `ordenes_rechazadas = 0`
   - `suma_reclamada = 1583859890309.00` y `suma_aprobada = 57328903464.00`
   - `raiz_hash_lote = 78dbff2ea6b365f3399315b1377111bc3ec23939ce539a101378b3f8b648869e`

![Respaldo visual de DynamoDB META](../../docs/verificacion/screenshots/aws_dynamodb_lote_coil_1200k_meta.png)

---

## 3. Paso 2 de la Demo (60 s) — Consultas Analíticas en Vivo en Amazon Athena (`Apache Iceberg`)

En la **Pestaña 2 (`Amazon Athena` → `Database: saom_analytics`)**, pegar y ejecutar cualquiera de las tres consultas siguientes según lo solicite el jurado:

### Consulta A — Verificar las `1.200.000` órdenes consolidadas sin duplicados (`RNF-06`)
```sql
SELECT
    COUNT(*) AS total_filas_iceberg,
    COUNT(DISTINCT id_solicitud) AS solicitudes_unicas,
    SUM(valor_procedimiento) AS total_reclamado,
    SUM(valor_aprobado) AS total_aprobado
FROM saom_analytics.adjudicaciones;
```
- **Resultado esperado (`~1,7 s`)**: `total_filas_iceberg = 1200000`, `solicitudes_unicas = 1200000`, `total_reclamado = 1583859890309.00`, `total_aprobado = 57328903464.00`.

### Consulta B — Liquidación agregada por Día de Solicitud y Medio Emisor (`ADR-005`)
```sql
SELECT
    SUBSTR(fecha_solicitud, 1, 10) AS dia_solicitud,
    COUNT(*) AS ordenes,
    SUM(valor_procedimiento) AS suma_reclamada,
    SUM(valor_aprobado) AS suma_aprobada
FROM saom_analytics.adjudicaciones
GROUP BY SUBSTR(fecha_solicitud, 1, 10)
ORDER BY dia_solicitud;
```
- **Resultado esperado**: `2026-05-04` (`402.000` órd., `19.155.939.616,75` aprobados), `2026-05-05` (`396.000` órd., `18.950.939.658,50` aprobados), `2026-05-06` (`402.000` órd., `19.222.024.188,75` aprobados).

### Consulta C — Inspeccionar una orden individual con `patient_token` (0 PII) y `hash_decision` (`RNF-04`, `RNF-05`)
```sql
SELECT
    id_solicitud,
    patient_token,
    perfil_cobertura,
    servicio_codigo,
    dictamen,
    porcentaje_aplicado,
    valor_procedimiento,
    valor_aprobado,
    hash_decision
FROM saom_analytics.adjudicaciones
WHERE id_solicitud IN ('CHV-0000001', 'CHV-0000002', 'CHV-0000003', 'CHV-0000004', 'CHV-0000005')
ORDER BY id_solicitud;
```

![Respaldo visual de Amazon Athena](../../docs/verificacion/screenshots/aws_athena_iceberg_1200k.png)

---

## 4. Paso 3 de la Demo (45 s) — Telemetría y Rendimiento en CloudWatch / AWS Lambda

En la **Pestaña 3 (`AWS Lambda` → `saom-worker` → `Monitor`)**:
1. Mostrar las gráficas de **Invocations** (`261` invocaciones totales entre `T3`, `T4` y pruebas de reenvío), **Duration** (`Average ~1.061 ms`, `Minimum 431 ms`, `Maximum 1.484 ms`), **Error count and success rate** (`0 errors`, `100 % success rate`) y **Total concurrent executions** (pico exacto en `10` workers según `MaximumConcurrency = 10`).
2. Si el jurado desea ver los logs detallados o las métricas EMF (`ThroughputOrdenesPorSegundo`), abrir **View CloudWatch logs** → `/aws/lambda/saom-worker` y mostrar las líneas `REPORT` con `Memory Size: 1769 MB` y `Max Memory Used: 153 MB`.

![Respaldo visual de CloudWatch Metrics en AWS Lambda](../../docs/verificacion/screenshots/aws_lambda_saom_worker_metrics.png)
"""


def main() -> None:
    E03_DIR.mkdir(parents=True, exist_ok=True)
    E04_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Generar E03 (.md y .docx)
    md_e03 = construir_e03_markdown()
    e03_md_path = E03_DIR / "Entregable_03_Prototipo_Evidencia_Salud_COIL.md"
    e03_docx_path = E03_DIR / "Entregable_03_Prototipo_Evidencia_Salud_COIL.docx"
    e03_md_path.write_text(md_e03, encoding="utf-8")
    render_markdown_to_docx(
        md_text=md_e03,
        docx_path=e03_docx_path,
        title="Entregable 03: Prototipo Funcional en AWS, Pruebas y Evidencia",
        subtitle="Sistema de Adjudicación de Órdenes Médicas (SAOM) — Ejecución Real 1,2M en AWS Learner Lab",
    )

    # 2. Generar E04 Documento Consolidado (.md y .docx)
    md_e04_doc = construir_e04_consolidado_markdown()
    e04_doc_md_path = E04_DIR / "Entregable_04_Documento_Consolidado_Salud_COIL.md"
    e04_doc_docx_path = E04_DIR / "Entregable_04_Documento_Consolidado_Salud_COIL.docx"
    e04_doc_md_path.write_text(md_e04_doc, encoding="utf-8")
    render_markdown_to_docx(
        md_text=md_e04_doc,
        docx_path=e04_doc_docx_path,
        title="Entregable 04: Documento Consolidado Final de Arquitectura y Verificación",
        subtitle="Ciclo Completo AI-DLC (Pasos 1 a 6) — Sistema de Salud de Chernovia (COIL)",
    )

    # 3. Generar E04 Guion y Estructura del Pitch (.md y .docx)
    md_e04_pitch = construir_e04_pitch_markdown()
    e04_pitch_md_path = E04_DIR / "Entregable_04_Guion_Pitch_Sustentacion_COIL.md"
    e04_pitch_docx_path = E04_DIR / "Entregable_04_Guion_Pitch_Sustentacion_COIL.docx"
    e04_pitch_md_path.write_text(md_e04_pitch, encoding="utf-8")
    render_markdown_to_docx(
        md_text=md_e04_pitch,
        docx_path=e04_pitch_docx_path,
        title="Entregable 04: Guion de Sustentación (Pitch) y Defensa Técnica",
        subtitle="Presentación Ejecutiva y Demostración en AWS — Equipo de Arquitectura COIL",
    )

    # 4. Generar E04 Guía Operativa de Demostración ante el Comité (.md y .docx)
    md_e04_demo = construir_e04_guia_demo_markdown()
    e04_demo_md_path = E04_DIR / "Entregable_04_Guia_Demostracion_Comite.md"
    e04_demo_docx_path = E04_DIR / "Entregable_04_Guia_Demostracion_Comite.docx"
    e04_demo_md_path.write_text(md_e04_demo, encoding="utf-8")
    render_markdown_to_docx(
        md_text=md_e04_demo,
        docx_path=e04_demo_docx_path,
        title="Entregable 04: Guía Operativa de Demostración en Vivo (AWS Console)",
        subtitle="Consultas SQL en Amazon Athena, Estado en DynamoDB y Métricas en CloudWatch",
    )

    print("Entregables E03 y E04 generados exitosamente:")
    for p in (
        e03_md_path,
        e03_docx_path,
        e04_doc_md_path,
        e04_doc_docx_path,
        e04_pitch_md_path,
        e04_pitch_docx_path,
        e04_demo_md_path,
        e04_demo_docx_path,
    ):
        print(f" - {p} ({p.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
