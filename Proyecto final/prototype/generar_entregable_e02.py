"""Generador del Entregable 02: Diseño Técnico (Formato Word .docx editable y Markdown .md).

Alineado con `docs/design/03_arquitectura_tecnica.md`, ADR-001 a ADR-005, RF-01 a RF-05,
RNF-01 a RNF-06 y las resoluciones P-01 a P-17 de `docs/plan/04_plan_construccion.md`.
Incluye los diagramas simplificados de alta resolución en `docs/design/diagramas/`.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIAG_DIR = PROJECT_ROOT / "docs" / "design" / "diagramas"
E02_DIR = PROJECT_ROOT / "entregables" / "E02"
DOCX_PATH = E02_DIR / "Entregable_02_Diseno_Tecnico_Salud_COIL.docx"
MD_PATH = E02_DIR / "Entregable_02_Diseno_Tecnico_Salud_COIL.md"

COLOR_H1 = RGBColor(0x36, 0x5F, 0x91)
COLOR_H2 = RGBColor(0x4F, 0x81, 0xBD)
COLOR_TEXT = RGBColor(0x1E, 0x29, 0x3B)
HEX_HEADER_BG = "1E3A5F"
HEX_ROW_ALT = "F8FAFC"


def _set_cell_bg(cell: docx.table._Cell, hex_color: str) -> None:
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def _set_cell_margins(cell: docx.table._Cell, top: int = 80, bottom: int = 80, left: int = 120, right: int = 120) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        node = OxmlElement(f"w:{m}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def _agregar_tabla(
    doc: docx.Document,
    cabeceras: Sequence[str],
    filas: Sequence[Sequence[str]],
) -> None:
    tabla = doc.add_table(rows=1 + len(filas), cols=len(cabeceras))
    tabla.style = "Table Grid"
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Cabecera
    hdr_cells = tabla.rows[0].cells
    for idx, texto in enumerate(cabeceras):
        hdr_cells[idx].text = ""
        p = hdr_cells[idx].paragraphs[0]
        run = p.add_run(texto)
        run.bold = True
        run.font.name = "Calibri"
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        _set_cell_bg(hdr_cells[idx], HEX_HEADER_BG)
        _set_cell_margins(hdr_cells[idx])

    # Filas de datos
    for r_idx, fila in enumerate(filas):
        row_cells = tabla.rows[r_idx + 1].cells
        bg = HEX_ROW_ALT if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, valor in enumerate(fila):
            row_cells[c_idx].text = ""
            p = row_cells[c_idx].paragraphs[0]
            run = p.add_run(str(valor))
            run.font.name = "Calibri"
            run.font.size = Pt(9.5)
            if c_idx == 0:
                run.bold = True
            _set_cell_bg(row_cells[c_idx], bg)
            _set_cell_margins(row_cells[c_idx])

    doc.add_paragraph()


def _agregar_imagen(doc: docx.Document, ruta_img: Path, leyenda: str, ancho_pulgadas: float = 6.4) -> None:
    if ruta_img.exists():
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p_img.add_run()
        run.add_picture(str(ruta_img), width=Inches(ancho_pulgadas))

        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run(leyenda)
        r_cap.italic = True
        r_cap.font.name = "Calibri"
        r_cap.font.size = Pt(9.5)
        r_cap.font.color.rgb = RGBColor(0x47, 0x55, 0x69)


def construir_docx() -> Path:
    E02_DIR.mkdir(parents=True, exist_ok=True)
    doc = docx.Document()

    # Configurar márgenes de 1 pulgada (igual que E01 v2)
    for sec in doc.sections:
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)

    # Estilos base
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(11)

    for h_name, size_pt, color_rgb in (
        ("Heading 1", 15, COLOR_H1),
        ("Heading 2", 13, COLOR_H2),
        ("Heading 3", 11.5, COLOR_H2),
    ):
        st = doc.styles[h_name]
        st.font.name = "Calibri"
        st.font.size = Pt(size_pt)
        st.font.color.rgb = color_rgb

    # Encabezado / Portada Ejecutiva (mismo formato que E01 v2)
    h1 = doc.add_heading("ENTREGABLE 02: DISEÑO TÉCNICO Y ARQUITECTURA DISTRIBUIDA EN AWS", level=1)
    h1.alignment = WD_ALIGN_PARAGRAPH.LEFT

    for linea_meta in (
        "Licitación Pública — Proyecto COIL Interdisciplinario (Arquitectura de Big Data + Metodología de la Investigación)",
        "Sistema de Adjudicación de Órdenes Médicas (SAOM) · Sistema Público de Salud de Chernovia",
        "Integrantes: Naomi Chow, Daniel Lopez y María Fernanda Toro",
        "Versión: 1.0 (Alineada con el Dataset Oficial COIL de 1.200.000 solicitudes, ADR-001 a ADR-005 y Plan T1–T8)",
    ):
        p = doc.add_paragraph(linea_meta)
        p.runs[0].bold = "Integrantes:" in linea_meta or "Sistema de Adjudicación" in linea_meta

    _agregar_tabla(
        doc,
        ["Campo de Control", "Detalle del Entregable"],
        [
            ["Entregable del curso", "02 — Diseño Técnico (25 % de la calificación final)"],
            ["Contenido evaluado", "Arquitectura distribuida, flujo de datos, lógica de clasificación/liquidación y estrategia de costo (Diagrama + justificación)"],
            ["Metodología", "AI-DLC (Paso 3: Arquitectura y Diseño Técnico, conectado con Inception y Plan)"],
            ["Decisiones arquitectónicas", "ADR-001 (Híbrida por micro-lotes), ADR-002 (HMAC-SHA256 + '#' + SHA-256), ADR-003 (MVP Learner Lab 50 USD + M/M/c), ADR-004 (Lambda Arm64), ADR-005 (Almacenamiento Políglota)"],
        ],
    )

    # SECCIÓN 1
    doc.add_heading("1. Resumen Ejecutivo de la Solución Técnica", level=2)
    doc.add_paragraph(
        "El Sistema de Adjudicación de Órdenes Médicas (SAOM) para el Sistema Público de Salud de Chernovia es una "
        "arquitectura cloud-native, serverless y orientada a eventos en Amazon Web Services (región us-east-1) que "
        "materializa la ruta híbrida seleccionada en el ADR-001. Su objetivo es auditar, clasificar cobertura normativa, "
        "liquidar copagos y firmar criptográficamente un volumen licitado de 12 millones de órdenes médicas en menos de "
        "24 horas (y en una ventana operativa exigente de 3 horas como meta del equipo), garantizando cero exposición de "
        "datos personales identificables (PII) y un costo de nube inferior a 0,50 USD por millón de solicitudes."
    )
    doc.add_paragraph(
        "La decisión técnica central que hace viable este balance costo-rendimiento consiste en desacoplar la recepción "
        "de los archivos CSV respecto de su procesamiento mediante micro-lotes (chunks) de 5.000 solicitudes definidos por "
        "rangos exactos de bytes ([byte_inicio, byte_fin]). En lugar de invocar una función o una máquina de estados por "
        "cada orden individual (lo que multiplicaría por 5.000 las llamadas a SQS, S3, DynamoDB y Lambda), cada invocación "
        "del worker procesa en memoria un bloque de ~1,5 MB (5.000 filas), reduciendo el costo operativo en producción a "
        "3,02 USD por día para 12 millones de órdenes (0,25 USD por millón)."
    )

    _agregar_tabla(
        doc,
        ["Parámetro de Diseño", "Valor Verificado en el Dataset Oficial COIL", "Impacto Directo en la Arquitectura"],
        [
            ["Volumen del dataset oficial", "1.200.000 solicitudes (360,35 MB, 3 días hábiles, 10 IPS, 7 canales)", "Escala exacta 1:10 frente a los 12 M de la licitación; equivale a 240 chunks de 5.000 órdenes"],
            ["Esquema de entrada CSV", "6 columnas: id_solicitud, fecha_solicitud, glosa, medio_emisor, valor_procedimiento, entidad_emisora", "El particionador valida la cabecera en streaming O(1) y calcula desplazamientos de bytes por salto de línea"],
            ["Estructura de la glosa", "Plantilla semiestructurada (~213 caracteres) con Paciente, DNO, SeguroSocial, Edad, PerfilCobertura, ServicioSolicitado y Medicacion", "Permite extracción determinista con preservación exacta de spans [start_char, end_char] sin requerir GPU ni APIs externas por carácter"],
            ["Resolución del perfil", "Viene en la glosa (PRIORITARIO 100 %, ESTANDAR 50 %, COPAGO 25 %) y se cruza con COIL_catalogo_perfiles_cobertura.csv", "Se resuelve en memoria desde saom-ref, evitando 12 millones de lecturas diarias a DynamoDB (ahorro de 0,75 USD/día)"],
            ["Catálogo de cobertura", "COIL_catalogo_servicios_cubiertos.csv (COV-001 a COV-020) con rangos de valor y medicaciones de referencia", "Cargado en caché del contenedor Lambda; fija catalogo_version en cada recibo firmado"],
        ],
    )

    # SECCIÓN 2
    doc.add_heading("2. Arquitectura Distribuida Simplificada y Vistas C4", level=2)
    doc.add_heading("2.1. Diagrama Simplificado de Arquitectura en AWS (4 Etapas)", level=3)
    doc.add_paragraph(
        "Para facilitar la lectura ejecutiva y la defensa ante el comité evaluador, la arquitectura en AWS se organiza "
        "en cuatro etapas secuenciales claramente delimitadas: (1) Ingesta y Partición, (2) Coordinación y Cómputo "
        "Distribuido, (3) Almacenamiento Políglota y Evidencia WORM, y (4) Analítica SQL y Auditoría Criptográfica."
    )

    _agregar_imagen(
        doc,
        DIAG_DIR / "e02_arquitectura_simplificada.png",
        "Figura 1. Arquitectura distribuida simplificada en AWS (SAOM · Chernovia) organizada en 4 etapas.",
        ancho_pulgadas=6.5,
    )

    _agregar_tabla(
        doc,
        ["Etapa", "Componente / Servicio AWS", "Responsabilidad Técnica", "Requisitos / ADR"],
        [
            ["1. Ingesta y Partición", "Amazon S3 (saom-raw) + SQS (lotes-recibidos) + AWS Lambda Particionador", "Recibe el CSV original con cifrado SSE-KMS (única zona con PII), valida la cabecera de 6 columnas en streaming y calcula los 240 rangos de bytes [byte_inicio, byte_fin] de 5.000 filas", "RF-01, RNF-05, ADR-001"],
            ["2. Coordinación y Cómputo", "Amazon SQS (chunks-adjudicacion + DLQ) + AWS Lambda Workers Arm64 + Secrets/KMS", "SQS actúa como coordinador distribuyendo 1 chunk por invocación hasta N workers concurrentes; la DLQ aísla chunks tras 3 fallos técnicos de infraestructura", "RF-01 a RF-05, RNF-01, RNF-06, ADR-004"],
            ["3. Almacenamiento Políglota", "S3 (saom-ref, saom-curated, saom-audit WORM) + DynamoDB (control_lotes)", "Almacena catálogos COIL versionados, resultados analíticos (staging/ e Iceberg), rechazos sintácticos (rechazos/), recibos firmados inmutables y control idempotente por lote/chunk", "RF-04, RF-05, RNF-04, RNF-06, ADR-005"],
            ["4. Analítica y Auditoría", "Amazon Athena + AWS Glue Data Catalog + CloudWatch (Logs y EMF)", "Ejecuta MERGE INTO sobre la tabla Iceberg adjudicaciones, expone consultas SQL por IPS/canal/fecha, verifica integridad en 3 niveles y mide el throughput k sin exponer PII", "RNF-01, RNF-03, RNF-04, RNF-05"],
        ],
    )

    doc.add_heading("2.2. Vistas de Contexto y Contenedores (Modelo C4 Niveles 1 y 2)", level=3)
    doc.add_paragraph(
        "El diagrama de contexto (C4 Nivel 1) delimita las fronteras del sistema SAOM frente a los cuatro perfiles de "
        "usuario (Entidades Emisoras IPS, Auditores Médicos de segunda línea, Analistas Financieros del Pagador y Entes "
        "de Control) y los tres sistemas/insumos externos (Catálogo de Perfiles COIL, Catálogo de Servicios Cubiertos "
        "COV-001..COV-020 y Tesorería del Pagador)."
    )
    _agregar_imagen(
        doc,
        DIAG_DIR / "c4_1_contexto.png",
        "Figura 2. Vista de Contexto (C4 Nivel 1) del Sistema de Adjudicación de Órdenes Médicas (SAOM).",
        ancho_pulgadas=6.2,
    )
    _agregar_imagen(
        doc,
        DIAG_DIR / "c4_2_contenedores.png",
        "Figura 3. Vista de Contenedores (C4 Nivel 2) en AWS us-east-1.",
        ancho_pulgadas=6.3,
    )

    doc.add_heading("2.3. Justificación de las Decisiones Arquitectónicas (ADR-001 a ADR-005)", level=3)
    _agregar_tabla(
        doc,
        ["ADR", "Decisión Adoptada", "Alternativas Descartadas", "Justificación Técnica y Económica"],
        [
            ["ADR-001", "Arquitectura híbrida desacoplada por micro-lotes de 5.000 órdenes", "A) Batch monolítico nocturno; B) Serverless puro orden por orden (Step Functions + Comprehend)", "El procesamiento orden por orden dispara el costo a miles de dólares diarios por cobro por transición/carácter; el micro-lote de 5.000 filas mantiene latencia de minutos a 0,25 USD/millón"],
            ["ADR-002", "Pseudonimización HMAC-SHA256 con clave secreta, '#' de igual longitud y SHA-256 sobre JSON canónico", "Eliminación de longitud variable; SHA-256 sin clave sobre el DNO; texto claro en zona curada", "Un hash sin clave sobre un DNO de 8 dígitos es vulnerable a diccionario; reemplazar carácter por carácter con '#' preserva intactos los offsets [start_char, end_char]"],
            ["ADR-003", "Prototipo serverless en AWS Learner Lab (50 USD) con 1,2M órdenes reales y extrapolación M/M/c a 12M", "Clústeres EC2/EMR permanentes o corrida sintética de 12M en el laboratorio", "El Learner Lab restringe roles IAM y vCPU EC2; con Lambda Arm + S3 + SQS + DynamoDB on-demand el costo fijo es 0 USD/h y la corrida de 1,2M cuesta < 0,30 USD"],
            ["ADR-004", "Cómputo de workers en AWS Lambda Arm64 (portable a ECS Fargate Spot)", "EMR Serverless / AWS Glue PySpark para micro-lotes pequeños", "Lambda escala en segundos con SQS sin pagar arranque de clústeres Spark y ofrece 20 % mejor precio/rendimiento en arquitectura Graviton2 (Arm64)"],
            ["ADR-005", "Almacenamiento políglota: DynamoDB + Apache Iceberg en S3 + S3 WORM", "Base de datos relacional única (RDS/Aurora) o solo archivos sueltos en S3", "Separa la coordinación transaccional (DynamoDB TransactWriteItems), la analítica masiva SQL (Iceberg + Athena) y la custodia legal inmutable (S3 WORM)"],
        ],
    )

    # SECCIÓN 3
    doc.add_heading("3. Flujo de Datos Extremo a Extremo y Modelo de Almacenamiento", level=2)
    doc.add_heading("3.1. Secuencia Numerada del Flujo de Datos", level=3)
    _agregar_tabla(
        doc,
        ["Paso", "Origen → Destino", "Operación y Garantía de Datos"],
        [
            ["1", "Entidad Emisora → S3 saom-raw", "Carga del archivo CSV (ej. COIL_dataset_glosas_salud_1_2M.csv). En producción se realiza vía URL prefirmada (evitando el límite de 10 MB de API Gateway); en el prototipo se sube directo a saom-raw"],
            ["2–3", "S3 saom-raw → SQS lotes-recibidos → Lambda Particionador", "El evento ObjectCreated dispara al particionador, que lee el stream en bloques binarios O(1) y verifica las 6 columnas esperadas. Si la cabecera es inválida, marca el lote como RECHAZADO en DynamoDB y no emite chunks"],
            ["4", "Lambda Particionador → DynamoDB y SQS chunks-adjudicacion", "Registra chunks_totales = 240 y estado EN_PROCESO en control_lotes, y publica los 240 descriptores [byte_inicio, byte_fin] en lotes de 10 mensajes (send_message_batch)"],
            ["5–6", "SQS chunks-adjudicacion → Lambda Worker (× N)", "Cada invocación recibe un descriptor, reutiliza en memoria los catálogos de saom-ref y descarga únicamente su rango de bytes (GetObject Range=bytes=inicio-fin, ~1,5 MB)"],
            ["7", "Lambda Worker → S3 saom-curated", "Escribe las decisiones válidas en staging/fecha=.../lote=.../chunk=NNNNN.jsonl (o Parquet) y aísla cualquier fila malformada en rechazos/ con estado REJECTED_SYNTAX sin abortar las 4.999 órdenes restantes"],
            ["8", "Lambda Worker → S3 saom-audit (WORM)", "Escribe los recibos firmados en recibos/fecha=.../lote=.../chunk=NNNNN.jsonl incluyendo el JSON canónico, hash_decision y raiz_hash_chunk"],
            ["9", "Lambda Worker → DynamoDB control_lotes", "Ejecuta TransactWriteItems condicional: marca CHUNK#n como COMPLETADO solo si no lo estaba, y en la misma transacción suma chunks_completados, ordenes_validas y ordenes_rechazadas en META. Al completarse el último chunk, calcula raiz_hash_lote y escribe manifiestos/lote=<id>.json"],
            ["10–11", "Athena / Verificador → Analistas y Entes de Control", "Athena consolida hacia la tabla Iceberg adjudicaciones mediante MERGE INTO idempotente y permite consultas SQL y auditoría criptográfica en 3 niveles"],
        ],
    )

    doc.add_heading("3.2. Diseño de Almacenamiento en S3, DynamoDB e Iceberg", level=3)
    _agregar_tabla(
        doc,
        ["Capa / Tabla", "Clave / Prefijo", "Contenido y Regla de Integridad"],
        [
            ["S3 saom-raw", "entidad=<id>/fecha=<aaaa-mm-dd>/lote=<id>.csv", "Archivo CSV original con PII. Cifrado SSE-KMS y acceso restringido exclusivamente al particionador y workers"],
            ["S3 saom-ref", "catalogo/version=COIL-2026.1/*.csv", "COIL_catalogo_servicios_cubiertos.csv (20 servicios) y COIL_catalogo_perfiles_cobertura.csv (3 perfiles). Versionado activo"],
            ["S3 saom-curated", "staging/..., rechazos/..., warehouse/adjudicaciones/", "Salidas sin PII (con patient_token y glosa_enmascarada con '#'). Tabla analítica Apache Iceberg particionada por fecha_radicacion"],
            ["S3 saom-audit", "recibos/.../chunk=NNNNN.jsonl y manifiestos/lote=<id>.json", "Custodia inmutable WORM (S3 Object Lock en modo COMPLIANCE, o Versioning + política DenyDelete en Learner Lab)"],
            ["DynamoDB control_lotes", "PK = LOTE#<id>, SK = META | CHUNK#<00000>", "Diseño single-table on-demand. Garantiza idempotencia exacta ante entregas duplicadas de SQS (al menos una vez) mediante ConditionExpression"],
        ],
    )

    # SECCIÓN 4
    doc.add_heading("4. Lógica de Clasificación, Liquidación y Trazabilidad Criptográfica", level=2)
    doc.add_paragraph(
        "El núcleo del worker (implementado en prototype/saom_core.py y conectado a AWS mediante prototype/lambda_handlers.py) "
        "ejecuta cinco etapas deterministas en memoria por cada solicitud del chunk. La Figura 4 ilustra este pipeline "
        "y su correspondencia con los componentes de C4 Nivel 3 (Figura 5)."
    )

    _agregar_imagen(
        doc,
        DIAG_DIR / "e02_pipeline_worker.png",
        "Figura 4. Pipeline determinista de 5 etapas dentro del Worker de Adjudicación.",
        ancho_pulgadas=6.5,
    )
    _agregar_imagen(
        doc,
        DIAG_DIR / "c4_3_componentes.png",
        "Figura 5. Vista de Componentes (C4 Nivel 3) del Worker de Adjudicación.",
        ancho_pulgadas=6.4,
    )

    doc.add_heading("4.1. Reglas de Negocio y Decisiones Formalizadas (RF-01 a RF-05 y P-01 a P-17)", level=3)
    _agregar_tabla(
        doc,
        ["Etapa / Requisito", "Especificación Técnica Exacta", "Comportamiento ante Casos Borde (Resoluciones del Plan)"],
        [
            ["1. Validación Estructural (RF-01)", "Verifica 6 columnas no vacías y valor_procedimiento > 0.00 parseable con Decimal", "Si una fila falla (ej. CHV-9999999), se marca REJECTED_SYNTAX y se escribe en rechazos/ sin copiar campos libres con posible PII; las otras 4.999 filas continúan sin ir a la DLQ (P-02)"],
            ["2. Pseudonimización y Spans (RF-02, RNF-05)", "Calcula patient_token = HMAC-SHA256(clave_secreta, DNO || SeguroSocial) y reemplaza cada carácter de Paciente, DNO y SeguroSocial por '#'", "Al reemplazar carácter por carácter con '#', la longitud total de la glosa no cambia (ej. 235 caracteres en CHV-0000001, P-01) y los offsets [start_char, end_char] son idénticos en la glosa original y en la enmascarada"],
            ["3. Extracción Clínica y Confianza (RF-02, RNF-02)", "Parser determinista por expresiones regulares sobre la plantilla COIL: extrae Edad, PerfilCobertura, ServicioSolicitado y lista de Medicacion separada por '|'", "La confianza se calcula como campos_validos / 7 y se guarda como dato (P-04). Se agrega AUDIT_FLAG_CLINICAL_UNCERTAINTY si falta o es inválido Edad, ServicioSolicitado o Medicacion, o si falta PerfilCobertura"],
            ["4. Dictamen de Cobertura (RF-03)", "Cruza ServicioSolicitado contra COIL_catalogo_servicios_cubiertos.csv (COV-001 a COV-020). Si está cubierto emite CUBRE; si no, NO_CUBRE con GLOSA-EXCL-SERVICIO-NO-CUBIERTO", "Si el servicio cubre pero valor_procedimiento sale de [valor_min_referencia, valor_max_referencia] o la medicación no está en medicaciones_referencia, solo se agregan los flags AUDIT_FLAG_VALOR_FUERA_RANGO_REF y AUDIT_FLAG_MEDICACION_NO_REFERENCIA sin cambiar el dictamen (P-03)"],
            ["5. Liquidación Financiera (RF-04)", "Usa exclusivamente Decimal con 2 decimales y redondeo ROUND_HALF_UP (prohibido float). Si CUBRE: PRIORITARIO = 100 %, ESTANDAR = 50 %, COPAGO = 25 %. Si NO_CUBRE: 0 %", "Siempre se cumple valor_copago = valor_procedimiento - valor_aprobado (P-14). Si PerfilCobertura viene escrito pero no existe en el catálogo (ej. 'VIP'), liquida al 0 %, mantiene el dictamen del servicio y marca solo AUDIT_FLAG_PERFIL_DESCONOCIDO (P-17)"],
            ["6. Firma y Raíces Hash (RF-05, RNF-04)", "Serializa cada decisión en JSON canónico (llaves ordenadas, sin espacios, UTF-8) y calcula hash_decision = SHA-256", "Las raíces de chunk (raiz_hash_chunk) y de lote (raiz_hash_lote) se calculan como el SHA-256 de la concatenación ordenada por id_solicitud y por chunk_id respectivamente (P-09)"],
        ],
    )

    # SECCIÓN 5
    doc.add_heading("5. Dimensionamiento Matemático (M/M/c) y Estrategia de Costo", level=2)
    doc.add_heading("5.1. Modelo de Teoría de Colas (M/M/c) y Escalabilidad", level=3)
    doc.add_paragraph(
        "La cola chunks-adjudicacion consumida por N funciones Lambda concurrentes se modela como un sistema M/M/c "
        "(sección 8 de la arquitectura técnica, implementado en docs/design/modelo_capacidad_costo.py). Con tamaño de "
        "chunk de 5.000 órdenes, tasa de llegada λ = (órdenes/s) / 5.000, tasa de servicio por worker μ = k / 5.000 "
        "y un margen de seguridad del 25 % (N = ceil((λ / μ) × 1,25)), se obtienen los siguientes parámetros:"
    )

    _agregar_tabla(
        doc,
        ["Ventana (12M órdenes)", "λ (órdenes/s)", "k (órd/s/vCPU)", "N workers", "Utilización ρ", "P(espera)", "Wq (espera en cola)", "Tiempo servicio / chunk"],
        [
            ["24 h (Requisito enunciado)", "138,9", "25", "7", "0,79", "0,473", "65,5 s", "200,0 s"],
            ["24 h (Requisito enunciado)", "138,9", "100", "2", "0,69", "0,569", "46,6 s", "50,0 s"],
            ["24 h (Requisito enunciado)", "138,9", "400", "1", "0,35", "0,347", "6,6 s", "12,5 s"],
            ["3 h (Meta exigente equipo)", "1.111,1", "25", "56", "0,79", "0,064", "1,1 s", "200,0 s"],
            ["3 h (Meta exigente equipo)", "1.111,1", "100", "14", "0,79", "0,320", "5,5 s", "50,0 s"],
            ["3 h (Meta exigente equipo)", "1.111,1", "400", "4", "0,69", "0,420", "4,3 s", "12,5 s"],
        ],
    )

    doc.add_heading("5.2. Desglose de Costos Operativos en AWS (Producción 12M vs. Prototipo 1,2M)", level=3)
    doc.add_paragraph(
        "Con precios oficiales de lista de AWS en la región us-east-1 y resolución del perfil en memoria con los catálogos "
        "oficiales COIL, el costo total en producción para 12 millones de órdenes es de 3,02 USD con k = 100 (0,25 USD "
        "por millón de órdenes) y baja a 0,90 USD con k = 400. En el AWS Academy Learner Lab (presupuesto de 50 USD), "
        "ejecutar las 1.200.000 órdenes reales (240 chunks) cuesta entre 0,07 USD (k = 400, 5 min) y 0,28 USD (k = 100, "
        "20 min), cumpliendo con amplio margen la meta de <= 0,50 USD por millón (P-06)."
    )

    _agregar_tabla(
        doc,
        ["Rubro de Servicio AWS (us-east-1)", "Costo Producción (12M órdenes, k=100)", "Costo Prototipo Learner Lab (1,2M órdenes, k=100)", "Observación de Diseño (FinOps)"],
        [
            ["Cómputo AWS Lambda Arm64 (1.769 MB = 1 vCPU)", "2,8304 USD", "0,2830 USD", "0,0000133334 USD por GB-s; baja a 0,07 USD en el lab si k >= 400"],
            ["Operaciones PUT/GET en Amazon S3", "0,0439 USD", "0,0044 USD", "Lectura por rango de bytes y escritura de 1 objeto por chunk (no por orden)"],
            ["Amazon SQS (lotes, chunks y sondeo)", "0,0216 USD", "0,0022 USD", "240 mensajes en el prototipo (2.400 en 12M) enviados con send_message_batch"],
            ["Amazon DynamoDB on-demand (control_lotes)", "0,0060 USD", "0,0006 USD", "Solo ~4 WRU por chunk (TransactWriteItems); perfil resuelto en memoria"],
            ["Amazon Athena + Glue + Step Functions + API", "0,1184 USD", "0,0050 USD", "En el prototipo se consolida una sola vez al cerrar los 240 chunks (P-10)"],
            ["TOTAL OPERACIÓN NUBE", "3,02 USD (0,25 USD / M)", "0,30 USD (0,25 USD / M)", "Cumple meta <= 0,50 USD por millón y deja intacto el crédito de 50 USD"],
        ],
    )

    doc.add_heading("5.3. Sensibilidad Económica y Ahorro frente a la Línea Base Manual (RNF-03)", level=3)
    doc.add_paragraph(
        "Dado que el costo de infraestructura en la nube es de apenas 0,00000025 USD por orden, el costo total efectivo "
        "por solicitud está gobernado por la fracción f de órdenes marcadas con incertidumbre clínica que pasan a revisión "
        "médica humana de segunda línea (costo_efectivo = costo_nube + f × 0,80 USD). La meta de ahorro >= 70 % del RNF-03 "
        "se cumple siempre que f <= 30 %:"
    )

    _agregar_tabla(
        doc,
        ["Fracción en Revisión Manual (f)", "Costo Efectivo por Orden", "Costo para 12M de Órdenes", "Ahorro frente a Línea Base Manual (0,80 USD/orden)"],
        [
            ["2 %", "0,0160 USD", "192.003 USD", "98,0 %"],
            ["5 %", "0,0400 USD", "480.003 USD", "95,0 %"],
            ["10 %", "0,0800 USD", "960.003 USD", "90,0 %"],
            ["20 %", "0,1600 USD", "1.920.003 USD", "80,0 %"],
            ["30 % (Umbral máximo RNF-03)", "0,2400 USD", "2.880.003 USD", "70,0 %"],
        ],
    )

    # SECCIÓN 6
    doc.add_heading("6. Confiabilidad, Seguridad y Alcance en el Learner Lab vs. Producción", level=2)
    _agregar_tabla(
        doc,
        ["Dimensión", "Implementación en el Prototipo (Learner Lab · 50 USD)", "Diseño de Producción (Licitación · 12M)", "Sustento / Mitigación"],
        [
            ["Volumen procesado", "1.200.000 solicitudes reales (240 chunks de 5.000)", "12.000.000 solicitudes (2.400 chunks, factor exacto 10x)", "ADR-003 y extrapolación matemática M/M/c con el k real medido en T4"],
            ["Concurrencia de workers", "5 a 10 funciones Lambda Arm64 concurrentes", "Entre 1 y 56 workers según k y ventana (24 h o 3 h)", "Protege la cuota del laboratorio y el presupuesto de 50 USD"],
            ["Identidad y permisos IAM", "Rol compartido LabRole en todas las Lambdas", "Un rol IAM de mínimo privilegio por función", "El Learner Lab bloquea iam:CreateRole (sección 10 de arquitectura)"],
            ["Inmutabilidad en saom-audit", "Object Lock si LabRole lo permite; o S3 Versioning + DenyDelete + raíces SHA-256", "S3 Object Lock en modo COMPLIANCE", "Verificado mediante el script prototype/aws_learner_lab.py verify-r01 (T2)"],
            ["Consolidación analítica", "Una consolidación al cerrar los 240 chunks sin Step Functions", "EventBridge Scheduler + Step Functions cada 15 min", "Acordado en P-10 del plan de construcción"],
        ],
    )

    doc.save(DOCX_PATH)
    return DOCX_PATH


def construir_markdown() -> Path:
    contenido = """# Entregable 02: Diseño Técnico y Arquitectura Distribuida en AWS

| Campo de Control | Detalle del Entregable |
| :--- | :--- |
| **Proyecto** | Sistema de Adjudicación de Órdenes Médicas (**SAOM**) · Sistema Público de Salud de Chernovia (Proyecto COIL) |
| **Entregable** | **02 — Diseño Técnico** (25 % de la calificación del curso) |
| **Equipo** | Naomi Chow, Daniel Lopez y María Fernanda Toro |
| **Versión** | 1.0 (Alineada con el Dataset Oficial COIL de 1,2 M, ADR-001 a ADR-005 y resoluciones P-01 a P-17) |
| **Artefactos relacionados** | [`03_arquitectura_tecnica.md`](../../docs/design/03_arquitectura_tecnica.md), [`modelo_capacidad_costo.py`](../../docs/design/modelo_capacidad_costo.py), [`saom_core.py`](../../prototype/saom_core.py), [`lambda_handlers.py`](../../prototype/lambda_handlers.py) |

---

## 1. Resumen Ejecutivo de la Solución Técnica

El **Sistema de Adjudicación de Órdenes Médicas (SAOM)** es una arquitectura **cloud-native, serverless y orientada a eventos** en Amazon Web Services (`us-east-1`) que materializa la ruta híbrida del **ADR-001**. Su propósito es validar, pseudonimizar datos sensibles, extraer entidades clínicas con posiciones de caracteres (`spans`), dictaminar cobertura normativa (`COV-001` a `COV-020`), liquidar montos aprobados y copagos (`100 %`, `50 %`, `25 %` o `0 %`) y firmar criptográficamente cada decisión para un volumen objetivo de **12 millones de órdenes médicas en menos de 24 horas** (y en una ventana exigente de **3 horas** como meta del equipo).

La decisión arquitectónica que optimiza simultáneamente el rendimiento y el costo es **procesar por micro-lotes (chunks) de 5.000 solicitudes definidos por rangos exactos de bytes (`[byte_inicio, byte_fin]`)** en lugar de orquestar orden por orden. Esto reduce las operaciones de S3, SQS, DynamoDB y Lambda en un factor de $5.000\\times$, logrando un costo de nube de **3,02 USD por cada 12 millones de órdenes** (**0,25 USD por millón**) y de **0,07 a 0,28 USD** para la corrida completa de **1.200.000 solicitudes** en el AWS Academy Learner Lab.

---

## 2. Arquitectura Distribuida Simplificada y Vistas C4

### 2.1. Diagrama Simplificado de Arquitectura en AWS (4 Etapas)

![Arquitectura Simplificada E02](../../docs/design/diagramas/e02_arquitectura_simplificada.png)

| Etapa | Componentes AWS | Responsabilidad en el Flujo | Requisitos / ADR |
| :--- | :--- | :--- | :--- |
| **1. Ingesta y Partición** | `S3 saom-raw` + `SQS lotes-recibidos` + `Lambda Particionador` | Custodia el CSV original con PII (SSE-KMS), valida la cabecera de 6 columnas en streaming $\\mathcal{O}(1)$ y emite 240 descriptores de rangos de bytes de 5.000 filas | RF-01, RNF-05, ADR-001 |
| **2. Coordinación y Cómputo** | `SQS chunks-adjudicacion` (+ `DLQ`) + `Lambda Workers Arm64` + `Secrets/KMS` | Reparte los chunks entre $N$ workers en paralelo; cada worker lee solo su rango de bytes (`~1,5 MB`), ejecuta las 5 etapas del núcleo y emite métricas EMF ($k$) | RF-01..05, RNF-01, RNF-06, ADR-004 |
| **3. Almacenamiento Políglota** | `S3 saom-ref`, `S3 saom-curated`, `S3 saom-audit (WORM)` y `DynamoDB control_lotes` | Mantiene catálogos COIL versionados, `staging/`, `rechazos/`, recibos firmados inmutables, manifiesto del lote y control idempotente con `TransactWriteItems` | RF-04, RF-05, RNF-04, RNF-06, ADR-005 |
| **4. Analítica y Auditoría** | `Athena + Glue Data Catalog` + `Verificador 3 Niveles` | Consolida `staging/` en la tabla Iceberg `adjudicaciones` mediante `MERGE INTO`, habilita consultas SQL para giros y verifica los hashes SHA-256 en 3 niveles | RNF-01, RNF-03, RNF-04 |

### 2.2. Vistas C4 de Contexto (Nivel 1) y Contenedores (Nivel 2)

![C4 Nivel 1 Contexto](../../docs/design/diagramas/c4_1_contexto.png)

![C4 Nivel 2 Contenedores](../../docs/design/diagramas/c4_2_contenedores.png)

### 2.3. Justificación de las Decisiones Arquitectónicas (ADR-001 a ADR-005)

| ADR | Decisión | Alternativas Descartadas | Justificación Técnica y Económica |
| :--- | :--- | :--- | :--- |
| **[ADR-001](../../docs/inception/adrs/ADR-001-estrategia-procesamiento.md)** | Ruta híbrida con ingesta continua y micro-lotes de 5.000 órdenes | Batch monolítico nocturno; Serverless orden por orden (Step Functions + Comprehend Medical) | Procesar orden por orden multiplica por 5.000 las transiciones y llamadas de red; el micro-lote por rango de bytes mantiene baja latencia a 0,25 USD/millón |
| **[ADR-002](../../docs/inception/adrs/ADR-002-anonimizacion-pii-y-trazabilidad.md)** | `HMAC-SHA256` con clave secreta, enmascaramiento `#` de igual longitud y `SHA-256` sobre JSON canónico | Supresión de longitud variable; SHA-256 sin clave sobre el DNO | Evita ataques de diccionario sobre identificadores cortos y conserva intactos los desplazamientos `[start_char, end_char]` entre la glosa original y la enmascarada |
| **[ADR-003](../../docs/inception/adrs/ADR-003-estrategia-mvp-lab-aws.md)** | Prototipo serverless en Learner Lab (50 USD) con 1,2 M de órdenes reales y extrapolación $M/M/c$ a 12 M | Clústeres EMR permanentes o corrida de 12 M en el laboratorio | Respeta `LabRole` y el límite de 50 USD con costo fijo de 0,00 USD/hora en reposo |
| **[ADR-004](../../docs/design/adrs/ADR-004-computo-workers-lambda.md)** | Cómputo de workers en AWS Lambda Arm64 (portable a ECS Fargate Spot) | EMR / Glue PySpark para bloques de 1,5 MB | Escalado casi instantáneo por cola SQS y 20 % de ahorro en Graviton2 (Arm64) |
| **[ADR-005](../../docs/design/adrs/ADR-005-almacenamiento-poliglota.md)** | Almacenamiento políglota: DynamoDB + Apache Iceberg en S3 + S3 WORM | Base relacional única o archivos CSV/JSON sueltos sin catálogo | Asigna cada carga al servicio óptimo: transacciones condicionales en DynamoDB, SQL analítico en Iceberg/Athena e inmutabilidad probatoria en S3 WORM |

---

## 3. Lógica de Clasificación, Liquidación y Trazabilidad del Worker

![Pipeline Interno del Worker](../../docs/design/diagramas/e02_pipeline_worker.png)

![C4 Nivel 3 Componentes](../../docs/design/diagramas/c4_3_componentes.png)

| Etapa Interna | Regla Implementada en `saom_core.py` | Resolución de Casos Borde (P-01 a P-17) |
| :--- | :--- | :--- |
| **1. Validación CSV (`RF-01`)** | Verifica las 6 columnas obligatorias y `valor_procedimiento > 0.00` con `Decimal` | Filas malformadas (ej. `CHV-9999999`) se aíslan como `REJECTED_SYNTAX` en `rechazos/` sin exponer PII y sin abortar el resto del chunk (`P-02`) |
| **2. Pseudonimización (`RF-02`, `RNF-05`)** | Calcula `patient_token = HMAC-SHA256(K, DNO‖SeguroSocial)` y reemplaza `Paciente`, `DNO` y `SeguroSocial` con `#` carácter por carácter | Mantiene exactamente la misma longitud (235 caracteres en `CHV-0000001`, `P-01`), garantizando que `glosa[ini:fin] == glosa_enmascarada[ini:fin]` para toda entidad clínica |
| **3. Extracción con Spans (`RF-02`, `RNF-02`)** | Extrae `Edad`, `PerfilCobertura`, `ServicioSolicitado` y `Medicacion` (separada por `|`) con sus posiciones `[start_char, end_char]` | La confianza se calcula como `campos_validos / 7` y se almacena como dato (`P-04`). Se marca `AUDIT_FLAG_CLINICAL_UNCERTAINTY` si falta o es inválido `Edad`, `ServicioSolicitado` o `Medicacion`, o si falta `PerfilCobertura` |
| **4. Cobertura Normativa (`RF-03`)** | Cruza `ServicioSolicitado` contra `COIL_catalogo_servicios_cubiertos.csv` (`COV-001` a `COV-020`) para emitir `CUBRE` o `NO_CUBRE` | Si el valor sale del rango de referencia o una medicación no está en `medicaciones_referencia`, se agregan `AUDIT_FLAG_VALOR_FUERA_RANGO_REF` y `AUDIT_FLAG_MEDICACION_NO_REFERENCIA` sin cambiar el dictamen (`P-03`) |
| **5. Liquidación Decimal (`RF-04`)** | Aplica `PRIORITARIO = 100 %`, `ESTANDAR = 50 %`, `COPAGO = 25 %` cuando `CUBRE`, o `0 %` cuando `NO_CUBRE`, usando `Decimal` y `ROUND_HALF_UP` | Siempre `valor_copago = valor_procedimiento - valor_aprobado` (`P-14`). Un perfil escrito fuera del catálogo liquida al `0 %`, conserva el dictamen del servicio y lleva solo `AUDIT_FLAG_PERFIL_DESCONOCIDO` (`P-17`) |
| **6. Firma y Raíces (`RF-05`, `RNF-04`)** | Serializa la decisión en JSON canónico y calcula `hash_decision` (`SHA-256`) | `raiz_hash_chunk` y `raiz_hash_lote` son el `SHA-256` de la concatenación ordenada de hashes por `id_solicitud` y por `chunk_id` respectivamente (`P-09`) |

---

## 4. Dimensionamiento Matemático ($M/M/c$) y Estrategia de Costo

### 4.1. Dimensionamiento por Teoría de Colas ($M/M/c$)

| Ventana (12M órdenes) | $\\lambda$ (órdenes/s) | $k$ (órd/s/vCPU) | $N$ workers | Utilización $\\rho$ | $P(\\text{espera})$ | $W_q$ | Tiempo servicio / chunk |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **24 h** (Requisito enunciado) | 138,9 | 25 | 7 | 0,79 | 0,473 | 65,5 s | 200,0 s |
| **24 h** (Requisito enunciado) | 138,9 | 100 | 2 | 0,69 | 0,569 | 46,6 s | 50,0 s |
| **24 h** (Requisito enunciado) | 138,9 | 400 | 1 | 0,35 | 0,347 | 6,6 s | 12,5 s |
| **3 h** (Meta exigente equipo) | 1.111,1 | 25 | 56 | 0,79 | 0,064 | 1,1 s | 200,0 s |
| **3 h** (Meta exigente equipo) | 1.111,1 | 100 | 14 | 0,79 | 0,320 | 5,5 s | 50,0 s |
| **3 h** (Meta exigente equipo) | 1.111,1 | 400 | 4 | 0,69 | 0,420 | 4,3 s | 12,5 s |

### 4.2. Costo Operativo en Producción (12 M) y en el Learner Lab (1,2 M)

| Rubro AWS (`us-east-1`) | Producción (12 M órdenes, $k=100$) | Prototipo Learner Lab (1,2 M órdenes, $k=100$) | Nota FinOps |
| :--- | ---: | ---: | :--- |
| **Cómputo Lambda Arm64 (1.769 MB = 1 vCPU)** | 2,8304 USD | 0,2830 USD | Baja a **0,07 USD** en el laboratorio si $k \\ge 400$ |
| **Operaciones S3 (PUT/GET por rango)** | 0,0439 USD | 0,0044 USD | 1 lectura y 2 escrituras por chunk de 5.000 órdenes |
| **Amazon SQS (lotes, chunks y sondeo)** | 0,0216 USD | 0,0022 USD | Publicación agrupada con `send_message_batch` |
| **Amazon DynamoDB on-demand (`control_lotes`)** | 0,0060 USD | 0,0006 USD | `TransactWriteItems` por chunk; perfil resuelto en memoria |
| **Athena + Glue + Consolidación** | 0,1184 USD | 0,0050 USD | En el prototipo se consolida una vez al cerrar los 240 chunks (`P-10`) |
| **TOTAL NUBE** | **3,02 USD (0,25 USD / M)** | **0,30 USD (0,25 USD / M)** | Cumple holgadamente la meta $\\le 0,50\\text{ USD/millón}$ (`RNF-03`) |

### 4.3. Sensibilidad del Ahorro frente a la Revisión Manual (`RNF-03`)

Frente a la línea base de auditoría médica manual ($0,80\\text{ USD/orden}$), el costo efectivo por solicitud es $\\text{costo\\_nube} + f \\times 0,80\\text{ USD}$, cumpliendo la meta de **ahorro $\\ge 70\\%$** siempre que la fracción enviada a revisión humana sea **$f \\le 30\\%$**:

| Fracción en Revisión Manual ($f$) | Costo Efectivo por Orden | Ahorro frente a Línea Base Manual (0,80 USD/orden) |
| ---: | ---: | ---: |
| 2 % | 0,0160 USD | **98,0 %** |
| 5 % | 0,0400 USD | **95,0 %** |
| 10 % | 0,0800 USD | **90,0 %** |
| 20 % | 0,1600 USD | **80,0 %** |
| **30 % (Umbral máximo RNF-03)** | **0,2400 USD** | **70,0 %** |
"""
    E02_DIR.mkdir(parents=True, exist_ok=True)
    MD_PATH.write_text(contenido, encoding="utf-8")
    return MD_PATH


if __name__ == "__main__":
    p_md = construir_markdown()
    p_docx = construir_docx()
    print("Entregable 02 generado exitosamente:")
    print(" - Markdown:", p_md)
    print(" - Word (.docx):", p_docx)
