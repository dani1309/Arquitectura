# -*- coding: utf-8 -*-
"""
Generador de la Presentación Ejecutiva Editable (.pptx) de 10 Diapositivas (Entregable 04).
Incluye:
- Diseño ejecutivo widescreen 16:9 (13.333 x 7.5 in)
- Tarjetas KPI, tablas comparativas estilizadas
- Diagramas simplificados de arquitectura en 300 DPI (e02_arquitectura_simplificada.png, e02_pipeline_worker.png)
- Capturas reales de AWS Console (DynamoDB META, Lambda CloudWatch Metrics, Amazon Athena Iceberg)
- Conciliación económica unificada (0,0158 USD/M vs. 0,1890 USD vs. 0,2483 USD vs. 0,25-0,31 USD/M)
- Extrapolación explícita Medido (1,2M en 47,50 s) vs. Proyectado (12M en 4,25 min drenaje / 7,92 min E2E)
- Notas del orador (Speaker Notes) integradas en cada diapositiva
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence, Tuple

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

PROTO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PROTO_DIR.parent
DIAG_DIR = PROJECT_ROOT / "docs" / "design" / "diagramas"
SCREEN_DIR = PROJECT_ROOT / "docs" / "verificacion" / "screenshots"
E04_DIR = PROJECT_ROOT / "entregables" / "E04"

# Paleta corporativa
NAVY_DARK = RGBColor(0x0F, 0x17, 0x2A)
NAVY_MED = RGBColor(0x1E, 0x29, 0x3B)
BLUE_ACCENT = RGBColor(0x02, 0x84, 0xC7)
CYAN_LIGHT = RGBColor(0xE0, 0xF2, 0xFE)
GREEN_OK = RGBColor(0x05, 0x96, 0x69)
GREEN_BG = RGBColor(0xEC, 0xFD, 0xF5)
AMBER_WARN = RGBColor(0xD9, 0x77, 0x06)
AMBER_BG = RGBColor(0xFF, 0xFB, 0xEB)
SLATE_TEXT = RGBColor(0x33, 0x41, 0x55)
SLATE_MUTED = RGBColor(0x64, 0x74, 0x8B)
BG_LIGHT = RGBColor(0xF8, 0xFA, 0xFC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BORDER_GRAY = RGBColor(0xCB, 0xD5, 0xE1)


def _add_header_and_footer(
    slide,
    slide_num: int,
    title: str,
    subtitle: str,
    speaker: str,
    time_window: str,
) -> None:
    # Fondo general claro
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5)
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG_LIGHT
    bg.line.fill.background()

    # Barra superior Navy
    header = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.08)
    )
    header.fill.solid()
    header.fill.fore_color.rgb = NAVY_DARK
    header.line.fill.background()

    # Franja acento azul
    stripe = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(1.08), Inches(13.333), Inches(0.05)
    )
    stripe.fill.solid()
    stripe.fill.fore_color.rgb = BLUE_ACCENT
    stripe.line.fill.background()

    # Título y subtítulo
    tb = slide.shapes.add_textbox(Inches(0.45), Inches(0.10), Inches(9.6), Inches(0.92))
    tf = tb.text_frame
    tf.word_wrap = True
    p0 = tf.paragraphs[0]
    r0 = p0.add_run()
    r0.text = title
    r0.font.name = "Calibri"
    r0.font.size = Pt(22)
    r0.font.bold = True
    r0.font.color.rgb = WHITE

    p1 = tf.add_paragraph()
    r1 = p1.add_run()
    r1.text = subtitle
    r1.font.name = "Calibri"
    r1.font.size = Pt(11.5)
    r1.font.color.rgb = RGBColor(0x93, 0xC5, 0xFD)

    # Badge de expositor y tiempo arriba a la derecha
    badge = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(10.15), Inches(0.18), Inches(2.85), Inches(0.72)
    )
    badge.fill.solid()
    badge.fill.fore_color.rgb = NAVY_MED
    badge.line.color.rgb = BLUE_ACCENT
    badge.line.width = Pt(1.2)
    btf = badge.text_frame
    btf.word_wrap = True
    bp0 = btf.paragraphs[0]
    bp0.alignment = PP_ALIGN.CENTER
    br0 = bp0.add_run()
    br0.text = f"Expositor(a): {speaker}"
    br0.font.name = "Calibri"
    br0.font.size = Pt(11)
    br0.font.bold = True
    br0.font.color.rgb = WHITE

    bp1 = btf.add_paragraph()
    bp1.alignment = PP_ALIGN.CENTER
    br1 = bp1.add_run()
    br1.text = f"Tiempo: {time_window}  |  Diapositiva {slide_num}/10"
    br1.font.name = "Calibri"
    br1.font.size = Pt(9.5)
    br1.font.color.rgb = RGBColor(0x7D, 0xD3, 0xFC)

    # Pie de página
    footer = slide.shapes.add_textbox(Inches(0.45), Inches(7.12), Inches(12.4), Inches(0.30))
    ftf = footer.text_frame
    fp = ftf.paragraphs[0]
    fr = fp.add_run()
    fr.text = (
        f"SAOM · Sistema de Salud de Chernovia (Proyecto COIL)  |  "
        f"Naomi Chow · Daniel Lopez · María Fernanda Toro  |  Cuenta AWS: 329771219583 (us-east-1)"
    )
    fr.font.name = "Calibri"
    fr.font.size = Pt(9.5)
    fr.font.color.rgb = SLATE_MUTED


def _add_kpi_card(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    kpi_value: str,
    kpi_title: str,
    kpi_desc: str,
    accent: RGBColor = BLUE_ACCENT,
    bg_color: RGBColor = WHITE,
) -> None:
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = accent
    card.line.width = Pt(1.5)

    tf = card.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.15)
    tf.margin_right = Inches(0.15)
    tf.margin_top = Inches(0.10)

    p0 = tf.paragraphs[0]
    r0 = p0.add_run()
    r0.text = kpi_value
    r0.font.name = "Calibri"
    r0.font.size = Pt(22)
    r0.font.bold = True
    r0.font.color.rgb = accent

    p1 = tf.add_paragraph()
    r1 = p1.add_run()
    r1.text = kpi_title
    r1.font.name = "Calibri"
    r1.font.size = Pt(11.5)
    r1.font.bold = True
    r1.font.color.rgb = NAVY_DARK

    p2 = tf.add_paragraph()
    r2 = p2.add_run()
    r2.text = kpi_desc
    r2.font.name = "Calibri"
    r2.font.size = Pt(9.8)
    r2.font.color.rgb = SLATE_TEXT


def _add_bullet_card(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    heading: str,
    bullets: Sequence[str],
    accent: RGBColor = NAVY_DARK,
) -> None:
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    card.fill.solid()
    card.fill.fore_color.rgb = WHITE
    card.line.color.rgb = BORDER_GRAY
    card.line.width = Pt(1.0)

    tf = card.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.18)
    tf.margin_right = Inches(0.18)
    tf.margin_top = Inches(0.12)

    p0 = tf.paragraphs[0]
    r0 = p0.add_run()
    r0.text = heading
    r0.font.name = "Calibri"
    r0.font.size = Pt(13.5)
    r0.font.bold = True
    r0.font.color.rgb = accent

    for b in bullets:
        p = tf.add_paragraph()
        p.space_before = Pt(4)
        r = p.add_run()
        r.text = f"• {b}"
        r.font.name = "Calibri"
        r.font.size = Pt(10.8)
        r.font.color.rgb = SLATE_TEXT


def _add_styled_table(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    col_widths: Sequence[float] | None = None,
    font_size: float = 10.0,
) -> None:
    shape = slide.shapes.add_table(
        len(rows) + 1, len(headers), Inches(left), Inches(top), Inches(width), Inches(height)
    )
    table = shape.table
    if col_widths and len(col_widths) == len(headers):
        for idx, w in enumerate(col_widths):
            table.columns[idx].width = Inches(w)

    for c_idx, h_text in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY_DARK
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = h_text
        r.font.name = "Calibri"
        r.font.size = Pt(font_size)
        r.font.bold = True
        r.font.color.rgb = WHITE

    for r_idx, row_vals in enumerate(rows, start=1):
        bg = WHITE if r_idx % 2 == 1 else RGBColor(0xF1, 0xF5, 0xF9)
        for c_idx, val in enumerate(row_vals):
            cell = table.cell(r_idx, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            r = p.add_run()
            r.text = val
            r.font.name = "Calibri"
            r.font.size = Pt(font_size - 0.5)
            if c_idx == 0 or "CUMPLIDO" in val or "0,0158" in val or "4,25 min" in val or "0,9886" in val:
                r.font.bold = True
            r.font.color.rgb = NAVY_DARK if c_idx == 0 else SLATE_TEXT


def _set_notes(slide, text: str) -> None:
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = text


def build_presentation() -> Path:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # DIAPOSITIVA 1: Portada y Contexto de la Licitación en Chernovia
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s1,
        1,
        "SAOM · Adjudicación Masiva de Órdenes Médicas en AWS",
        "Licitación Pública del Ministerio de Salud de Chernovia (Proyecto COIL · Metodología AI-DLC)",
        "Naomi Chow",
        "0:00 – 0:50",
    )
    _add_kpi_card(
        s1, 0.45, 1.35, 3.95, 1.45,
        "12.000.000 / día",
        "Escala de la Licitación (Chernovia)",
        "SLA oficial < 24 h (138,89 órd/s). Meta interna de ingeniería del equipo: ventana nocturna de 3 h (1.111,11 órd/s).",
        BLUE_ACCENT,
    )
    _add_kpi_card(
        s1, 4.68, 1.35, 3.95, 1.45,
        "100% · 50% · 25% · 0%",
        "Reglas de Liquidación Financiera",
        "Cruce contra catálogo vigente (COV-001..020) y liquidación según PerfilCobertura (PRIORITARIO, ESTANDAR, COPAGO).",
        GREEN_OK,
    )
    _add_kpi_card(
        s1, 8.90, 1.35, 3.98, 1.45,
        "0 PII + SHA-256",
        "Privacidad Clínica y No Repudio",
        "Pseudonimización HMAC-SHA256, enmascaramiento '#' con preservación de spans y cadena SHA-256 de 3 niveles.",
        NAVY_DARK,
    )
    _add_bullet_card(
        s1, 0.45, 3.00, 6.10, 3.90,
        "El Reto Operativo y Clínico del Fondo Público de Chernovia",
        [
            "Cada orden llega con 6 columnas estructuradas más una glosa clínica libre en español (~213 caracteres) con 7 campos semánticos.",
            "El sistema debe extraer con posición exacta [start_char, end_char]: Edad, PerfilCobertura, ServicioSolicitado y Medicacion.",
            "Cualquier error de punto flotante o reprocesamiento por reintento distorsiona miles de millones del presupuesto público.",
            "Exigencia de auditoría: reconstruir criptográficamente por qué se aprobó o rechazó cada orden individual.",
        ],
        NAVY_DARK,
    )
    _add_bullet_card(
        s1, 6.78, 3.00, 6.10, 3.90,
        "Equipo de Arquitectura COIL y Resumen de Logros en AWS",
        [
            "Equipo: Naomi Chow · Daniel Lopez · María Fernanda Toro.",
            "Prototipo ejecutado en vivo sobre AWS Academy Learner Lab (cuenta 329771219583, us-east-1) con el dataset oficial de 1.200.000 órdenes.",
            "Corrida completa de 1,2M (240 chunks) completada en 47,50 s de reloj (1.061,60 ms/chunk = 4.710,44 órd/s/vCPU) y 0 mensajes en DLQ.",
            "Macro-F1 = 0,9886 sobre 600 glosas etiquetadas y costo real medido de 0,0189 USD (0,0158 USD por millón de órdenes).",
        ],
        BLUE_ACCENT,
    )
    _set_notes(
        s1,
        "Naomi Chow (0:00-0:50): Buenas tardes. Somos Naomi Chow, Daniel Lopez y María Fernanda Toro, y presentamos el Sistema de Adjudicación de Órdenes Médicas (SAOM) para el Sistema Público de Salud de Chernovia. El reto exige procesar hasta 12 millones de consultas médicas en menos de 24 horas (con meta interna de 3 horas), extraer paciente, edad, servicio y medicación con spans exactos, cruzar contra el catálogo COV-001..020, liquidar al 100%, 50%, 25% o 0% y dejar evidencia auditable con cero PII.",
    )

    # =========================================================================
    # DIAPOSITIVA 2: Estado del Arte y Por Qué Fallan las Arquitecturas Típicas
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s2,
        2,
        "Estado del Arte: Por Qué Fracasan las Arquitecturas Convencionales",
        "Análisis comparativo sobre 52 referencias académicas e industriales (Entregable 01 v2)",
        "Naomi Chow",
        "0:50 – 2:10",
    )
    _add_styled_table(
        s2, 0.45, 1.35, 12.43, 3.35,
        [
            "Alternativa Evaluada",
            "Patrón Técnico",
            "Costo Diario (12M órd.)",
            "Costo Unitario (USD/M)",
            "Viabilidad en Licitación y Learner Lab (50 USD)",
        ],
        [
            [
                "A. Auditoría Manual",
                "Revisión humana tradicional (~3 min/orden)",
                "9.600.000 USD / día",
                "800.000 USD / M",
                "INVIABLE: Cuello de botella operativo y financiero.",
            ],
            [
                "B. Serverless Orden por Orden + Comprehend Medical",
                "Step Functions Standard (10 trans./ord) + API NLP por carácter (mín. 300 chars = 3 u./glosa = 36M u./día)",
                "244.500 USD / día (escalonado)\n381.000 USD / día (Tier 1)",
                "20.375 USD / M\n(31.750 USD / M Tier 1)",
                "INVIABLE: Cobro mínimo de 300 chars multiplica la factura y Comprehend Medical solo soporta inglés.",
            ],
            [
                "C. Clúster Big Data Pesado (EMR Spark)",
                "24 nodos c6g.4xlarge (384 vCPU) + coordinación YARN/HDFS",
                "~220,00 USD / día",
                "~18,33 USD / M",
                "INVIABLE EN LAB: Excede cuotas de instancias/IAM y agota los 50 USD del Learner Lab en horas.",
            ],
            [
                "D. SAOM (Micro-Lotes Serverless en Lambda Arm64)",
                "S3 Range GET (5.000 órd/chunk) + SQS + Lambda Graviton2 (1.769 MB) + DynamoDB + Iceberg",
                "0,1890 USD (lineal 12M)\n0,2483 USD (con operación)",
                "0,0158 USD / M (medido)\n0,0207 USD / M (prod.)",
                "ÓPTIMA (ADR-001..005): Ahorro > 99,99 %, corrida 1,2M en vivo por solo 0,0189 USD.",
            ],
        ],
        col_widths=[2.55, 3.25, 2.25, 1.85, 2.53],
        font_size=10.0,
    )
    _add_bullet_card(
        s2, 0.45, 4.90, 12.43, 2.05,
        "Hallazgos Clave del Estado del Arte Verificados en E01 v2",
        [
            "Facturación escalonada oficial de Amazon Comprehend Medical [24]: para 12M de glosas (36M de unidades de 100 caracteres por el mínimo de 300 chars), los primeros 10M cuestan 105.000 USD (0,0105 USD/u) y los 26M restantes 136.500 USD (0,00525 USD/u) = 241.500 USD + 3.000 USD de Step Functions = 244.500 USD/día.",
            "Empaquetar de 1 en 1 a 5.000 órdenes por chunk reduce en 5.000 veces las llamadas a S3, SQS y DynamoDB, haciendo viable el procesamiento en AWS Lambda.",
        ],
        BLUE_ACCENT,
    )
    _set_notes(
        s2,
        "Naomi Chow (0:50-2:10): En el Entregable 01 contrastamos 52 referencias y demostramos por qué las arquitecturas típicas fracasan. Primero, orquestar orden por orden con Step Functions e invocar Comprehend Medical cobra un mínimo de 300 caracteres (3 unidades) por cada glosa de 213 caracteres: 36 millones de unidades diarias cuestan 244.500 USD/día aplicando los tramos oficiales de descuento de AWS (o 381.000 USD a tarifa plana Tier 1), y además solo opera en inglés. Segundo, un clúster EMR cuesta ~220 USD/día y choca con los permisos y los 50 USD del Learner Lab. Nuestra arquitectura por micro-lotes de 5.000 órdenes en Lambda Arm64 cuesta apenas 0,0158 USD por millón.",
    )

    # =========================================================================
    # DIAPOSITIVA 3: Metodología AI-DLC y Requisitos Verificables (RF + RNF)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s3,
        3,
        "Metodología AI-DLC en 6 Pasos y Requisitos Verificables",
        "Trazabilidad completa desde el problema hasta la verificación empírica en AWS",
        "Naomi Chow",
        "2:10 – 3:20",
    )
    _add_styled_table(
        s3, 0.45, 1.35, 12.43, 3.65,
        [
            "Código",
            "Requisito / Dimensión",
            "Exigencia del Enunciado",
            "Meta Interna del Equipo",
            "Resultado Verificado (36/36 Tests + AWS)",
        ],
        [
            [
                "RF-01..05",
                "Ingesta, Extracción, Cobertura, Liquidación y Firma",
                "Clasificar CUBRE/NO_CUBRE y liquidar 100/50/25/0 % con auditoría",
                "100 % de escenarios BDD en Gherkin sin usar float (Decimal exacto)",
                "CUMPLIDO: 25/25 tests BDD en local + corrida de 1.200.000 órdenes en AWS.",
            ],
            [
                "RNF-01",
                "Volumen y Ventana Batch (Throughput)",
                "12M en < 24 h (138,89 órd/s)",
                "12M en <= 3 h (1.111,11 órd/s); 1,2M en <= 2,4 h",
                "CUMPLIDO: 1,2M medido en 47,50 s; 12M proyectado en 4,25 min (drenaje) / 7,92 min (E2E).",
            ],
            [
                "RNF-02",
                "Calidad de Extracción Clínica (F1)",
                "Extraer paciente, edad, servicio y medicación",
                "Macro-F1 >= 0,92 con coincidencia exacta de span [start, end]",
                "CUMPLIDO: Macro-F1 = 0,9886 sobre 600 glosas (1,0000 limpias / 0,9765 perturbadas).",
            ],
            [
                "RNF-03",
                "Eficiencia Financiera (FinOps)",
                "Costo operativo razonable",
                "<= 0,50 USD/millón en lab y ahorro >= 70 % vs. manual",
                "CUMPLIDO: 0,0158 USD/millón medido (0,0189 USD para 1,2M; ahorro del 99,99 %).",
            ],
            [
                "RNF-04 / 05",
                "No Repudio Criptográfico y Privacidad PII",
                "Registro trazable de cada decisión",
                "Cadena SHA-256 de 3 niveles y 0 PII en claro en S3/DDB/Logs",
                "CUMPLIDO: 100 % verificado en 3 niveles desde Iceberg y 0 coincidencias de PII.",
            ],
            [
                "RNF-06",
                "Tolerancia a Fallos e Idempotencia",
                "Escalabilidad y resiliencia",
                "Idempotencia ante reenvíos SQS y aislamiento de filas corruptas",
                "CUMPLIDO: CHV-9999999 aislada en rechazos/, duplicados_ignorados=1 y doble MERGE exacto.",
            ],
        ],
        col_widths=[1.30, 2.35, 2.35, 2.75, 3.68],
        font_size=9.5,
    )
    _add_bullet_card(
        s3, 0.45, 5.18, 12.43, 1.75,
        "Ciclo AI-DLC Completado con Gobernanza del Equipo",
        [
            "Paso 1 (Problema · E01 v2) → Paso 2 (Requisitos BDD/RNF + ADR-001..003) → Paso 3 (Arquitectura C4/E02 + ADR-004..005) → Paso 4 (Plan T0..T8 y resolución P-01..P-17) → Paso 5 (Código funcional y despliegue AWS) → Paso 6 (Verificación real en AWS Learner Lab).",
            "Separación transparente entre requisitos del pliego licitatorio y metas de ingeniería propias del equipo.",
        ],
        NAVY_DARK,
    )
    _set_notes(
        s3,
        "Naomi Chow (2:10-3:20): Trabajamos bajo la metodología AI-DLC en 6 pasos trazables. En esta matriz distinguimos los requisitos del enunciado (< 24 horas y costo razonable) de nuestras metas internas de ingeniería: ventana de 3 horas, Macro-F1 >= 0,92 con spans exactos, <= 0,50 USD por millón y cero PII en claro. Todos los requisitos fueron superados. Le doy paso a Daniel para presentar la arquitectura y la corrida en AWS.",
    )

    # =========================================================================
    # DIAPOSITIVA 4: Arquitectura Híbrida Serverless por Micro-Lotes (E02)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s4,
        4,
        "Arquitectura Híbrida Serverless por Micro-Lotes en AWS (8 Pasos)",
        "Desacoplamiento por colas SQS y lectura directa por rangos de bytes (S3 Range GET)",
        "Daniel Lopez",
        "3:20 – 4:40",
    )
    arch_img = DIAG_DIR / "e02_arquitectura_simplificada.png"
    if arch_img.exists():
        s4.shapes.add_picture(str(arch_img), Inches(0.45), Inches(1.28), width=Inches(8.25))

    _add_bullet_card(
        s4, 8.85, 1.28, 4.03, 5.65,
        "Decisiones Clave (ADR-001 a ADR-005)",
        [
            "1–3. Ingesta y Particionamiento en Streaming (4 MB RAM): saom-particionador lee el CSV en S3 sin cargarlo completo en memoria y calcula los desplazamientos exactos [byte_inicio, byte_fin] de cada bloque de 5.000 órdenes.",
            "4–5. Procesamiento Paralelo sin Estado: Hasta 10 workers saom-worker (Lambda Arm64, 1.769 MB = 1 vCPU) descargan solo su rango de bytes (HTTP Range) y adjudican en memoria.",
            "6. Persistencia Políglota: Resultados pseudonimizados en saom-curated, recibos SHA-256 en saom-audit (con política DenyDeleteAuditReceipts) y control en DynamoDB.",
            "7–8. Consolidación ACID: MERGE INTO en Apache Iceberg (saom_analytics.adjudicaciones) consultado con Amazon Athena.",
        ],
        BLUE_ACCENT,
    )
    _set_notes(
        s4,
        "Daniel Lopez (3:20-4:40): Gracias, Naomi. En nuestro diagrama de arquitectura simplificada vemos los 8 pasos del flujo en AWS. El CSV llega a saom-raw y activa saom-particionador, que recorre los 360 MB en streaming con 4 MB de RAM y publica en SQS 240 descriptores livianos con los rangos de bytes [byte_inicio, byte_fin] de cada bloque de 5.000 órdenes. Luego, hasta 10 workers Lambda Arm64 con 1.769 MB (1 vCPU completa) descargan únicamente su rango de bytes desde S3 y adjudican en paralelo.",
    )

    # =========================================================================
    # DIAPOSITIVA 5: Idempotencia Atómica en DynamoDB y Lección Aprendida en AWS
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s5,
        5,
        "Idempotencia Atómica en DynamoDB y Hallazgo Real en Concurrencia",
        "Verificación en vivo de T3 (LOTE-T3-INTEGRACION) y manejo de TransactionConflict en META",
        "Daniel Lopez",
        "4:40 – 5:45",
    )
    ddb_img = SCREEN_DIR / "aws_dynamodb_lote_coil_1200k_meta.png"
    if ddb_img.exists():
        s5.shapes.add_picture(str(ddb_img), Inches(0.45), Inches(1.30), width=Inches(7.45))

    _add_bullet_card(
        s5, 8.05, 1.30, 4.83, 2.75,
        "Prueba T3 en AWS (10.001 filas · 4,83 s)",
        [
            "3 chunks (5.000 + 5.000 + 1 órdenes) con la fila corrupta CHV-9999999 inyectada.",
            "CHV-9999999 aislada en s3://.../rechazos/ con 0 PII sin abortar las 10.000 órdenes válidas.",
            "Al reenviar intencionalmente el chunk 0 ya procesado, DynamoDB rechazó la duplicación (duplicados_ignorados = 1) y los saldos financieros de META quedaron intactos.",
        ],
        GREEN_OK,
    )
    _add_bullet_card(
        s5, 8.05, 4.20, 4.83, 2.75,
        "Hallazgo Real en los 240 Chunks: TransactionConflict",
        [
            "Cada worker ejecuta TransactWriteItems sobre CHUNK#<id> (con ConditionExpression estado <> COMPLETADO) y suma contadores en el item único META.",
            "En la corrida paralela de 240 chunks, cuando 2 workers actualizaban META en el mismo milisegundo ocurría TransactionConflict.",
            "Solución en lambda_handlers.py: inspeccionar CancellationReasons y aplicar exponential backoff + jitter cuando el motivo es TransactionConflict, logrando 240/240 chunks exactos.",
        ],
        NAVY_DARK,
    )
    _set_notes(
        s5,
        "Daniel Lopez (4:40-5:45): Aquí vemos la captura real de nuestra tabla DynamoDB control_lotes en la cuenta 329771219583 mostrando el item META de LOTE-COIL-1200K con 240 de 240 chunks completados. En T3 verificamos que una fila corrupta (CHV-9999999) se aísla en rechazos/ con cero PII y que reenviar un chunk ya procesado es ignorado por ConditionExpression. Además, al correr los 240 chunks en paralelo detectamos contención transitoria TransactionConflict sobre el item caliente META y lo resolvimos con reintentos exponential backoff + jitter distinguiendo conflictos de duplicados.",
    )

    # =========================================================================
    # DIAPOSITIVA 6: Resultados Reales en AWS Learner Lab (1.200.000 Solicitudes)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s6,
        6,
        "Ejecución Real en AWS Learner Lab: 1.200.000 Solicitudes (T4)",
        "Métricas medidas directamente en Amazon CloudWatch y consola AWS Lambda (saom-worker)",
        "Daniel Lopez",
        "5:45 – 6:50",
    )
    _add_kpi_card(
        s6, 0.45, 1.28, 3.00, 1.35,
        "47,50 s",
        "Tiempo de Reloj Medido (1,2M)",
        "240/240 chunks completados con 10 workers concurrentes y DLQ = 0.",
        GREEN_OK,
    )
    _add_kpi_card(
        s6, 3.60, 1.28, 3.00, 1.35,
        "4.710,44 órd/s",
        "Throughput Real E2E / vCPU",
        "Duración media CloudWatch: 1.061,60 ms por chunk de 5.000 órdenes.",
        BLUE_ACCENT,
    )
    _add_kpi_card(
        s6, 6.75, 1.28, 3.00, 1.35,
        "153,0 MB",
        "Memoria RAM Pico (de 1.769 MB)",
        "Solo 8,6 % de la memoria aprovisionada gracias al diseño en streaming.",
        NAVY_DARK,
    )
    _add_kpi_card(
        s6, 9.90, 1.28, 2.98, 1.35,
        "0,0189 USD",
        "Costo Total Real de 1,2M",
        "Equivalente a 0,0158 USD por millón (505,37 GB-s = 0,0067 USD en Lambda).",
        GREEN_OK,
    )

    cw_img = SCREEN_DIR / "aws_lambda_saom_worker_metrics.png"
    if cw_img.exists():
        s6.shapes.add_picture(str(cw_img), Inches(0.45), Inches(2.78), width=Inches(7.55))

    _add_bullet_card(
        s6, 8.15, 2.78, 4.73, 4.15,
        "Resumen de la Corrida Oficial LOTE-COIL-1200K",
        [
            "Órdenes válidas: 1.200.000 | Rechazadas: 0 | DLQ: 0.",
            "Valor total reclamado: 1.583.859.890.309,00.",
            "Valor total aprobado: 57.328.903.464,00.",
            "Throughput del núcleo en memoria (EMF): 14.279,66 órdenes/s/vCPU; throughput E2E incluyendo red S3 y DynamoDB: 4.710,44 órdenes/s/vCPU (supera 11,8 veces la hipótesis P-07 k >= 400).",
            "Raíz criptográfica del lote (raiz_hash_lote): 78dbff2ea6b365f3...869e sellada en saom-audit.",
        ],
        BLUE_ACCENT,
    )
    _set_notes(
        s6,
        "Daniel Lopez (5:45-6:50): En esta diapositiva vemos las gráficas reales de CloudWatch de saom-worker tras procesar las 1.200.000 solicitudes oficiales. Los 240 chunks terminaron en 47,50 segundos de reloj con cero errores (100% success rate) y concurrencia máxima en 10. Cada chunk tardó 1.061,60 ms en promedio, es decir un throughput real extremo a extremo de 4.710,44 órdenes/s/vCPU y 153 MB de RAM. Toda la corrida costó 0,0189 dólares (0,0158 USD por millón). Continúa María Fernanda.",
    )

    # =========================================================================
    # DIAPOSITIVA 7: Pipeline Interno del Worker: Privacidad PII y Decimal
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s7,
        7,
        "Pipeline Interno del Worker: Privacidad PII y Liquidación Decimal",
        "Enmascaramiento con preservación exacta de longitud y desplazamientos [start_char, end_char]",
        "María Fernanda Toro",
        "6:50 – 7:55",
    )
    pipe_img = DIAG_DIR / "e02_pipeline_worker.png"
    if pipe_img.exists():
        s7.shapes.add_picture(str(pipe_img), Inches(0.45), Inches(1.30), width=Inches(7.85))

    _add_bullet_card(
        s7, 8.45, 1.30, 4.43, 5.60,
        "Garantías del Núcleo Funcional (saom_core.py)",
        [
            "Etapa 2 (HMAC-SHA256 + '#'): Paciente, DNO y SeguroSocial se derivan en patient_token con clave versionada (hmac-2026-v1) y se sustituyen por '#' * len(valor).",
            "Invarianza de Spans (ADR-002): Al mantener intacto el número de caracteres de la glosa, los índices [start_char, end_char] de Edad, PerfilCobertura, ServicioSolicitado y Medicacion son idénticos en la glosa original y en la enmascarada.",
            "Etapa 4 y 5 (Liquidación Decimal Exacta): Cruce O(1) contra los 20 servicios (COV-001..020), cálculo con decimal.Decimal + ROUND_HALF_UP y valor_copago = valor_procedimiento - valor_aprobado (P-14).",
            "Verificado con 0 coincidencias de PII en S3, DynamoDB y CloudWatch Logs.",
        ],
        NAVY_DARK,
    )
    _set_notes(
        s7,
        "María Fernanda Toro (6:50-7:55): Gracias, Daniel. Dentro de cada worker, saom_core.py ejecuta 6 etapas deterministas. Antes de extraer entidades, el nombre del paciente, el DNO y el Seguro Social se convierten en un patient_token con HMAC-SHA256 y se reemplazan en la glosa carácter por carácter con el símbolo '#'. Como la longitud de la cadena no cambia, los desplazamientos [start_char, end_char] de las entidades clínicas son idénticos en la glosa original y en la enmascarada, garantizando cero PII en claro. Además, toda la liquidación usa Decimal con ROUND_HALF_UP, prohibiendo float.",
    )

    # =========================================================================
    # DIAPOSITIVA 8: Calidad de Extracción Clínica (Macro-F1 = 0,9886)
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s8,
        8,
        "Evaluación de Calidad Clínica (T5a / T5): Macro-F1 = 0,9886",
        "Protocolo de etiquetado manual sobre 600 glosas fuera de git (300 limpias + 300 perturbadas)",
        "María Fernanda Toro",
        "7:55 – 8:45",
    )
    _add_styled_table(
        s8, 0.45, 1.35, 7.65, 3.35,
        [
            "Entidad Clínica (RNF-02)",
            "F1 Limpias (300)",
            "F1 Perturbadas (300)",
            "TP Global",
            "FP Global",
            "FN Global",
            "Precision",
            "Recall",
            "F1 Global (600)",
        ],
        [
            ["Edad", "1,0000", "0,9768", "574", "0", "13", "1,0000", "0,9779", "0,9888"],
            ["PerfilCobertura", "1,0000", "0,9768", "574", "0", "13", "1,0000", "0,9779", "0,9888"],
            ["ServicioSolicitado", "1,0000", "0,9787", "576", "0", "12", "1,0000", "0,9796", "0,9897"],
            ["Medicacion", "1,0000", "0,9737", "1.359", "0", "35", "1,0000", "0,9749", "0,9873"],
            ["PROMEDIO MACRO", "1,0000", "0,9765", "—", "—", "—", "1,0000", "0,9776", "0,9886 (>= 0,92)"],
        ],
        col_widths=[1.75, 0.85, 0.95, 0.70, 0.65, 0.65, 0.68, 0.65, 0.77],
        font_size=9.5,
    )
    _add_bullet_card(
        s8, 8.25, 1.35, 4.63, 3.35,
        "Diseño de la Muestra de 600 Glosas (P-05, P-15)",
        [
            "Distribuida entre los 3 integrantes (200 glosas c/u: Naomi Chow, Daniel Lopez y María Fernanda Toro) y almacenada fuera de git.",
            "300 glosas limpias estratificadas del dataset oficial (F1 = 1,0000).",
            "300 glosas sometidas a 6 familias de perturbación documental (espacios irregulares, orden permutado, perfil fuera de catálogo, campo omitido, ruido OCR en etiqueta y separadores vacíos): F1 = 0,9765.",
            "Criterio estricto: True Positive exige coincidencia exacta simultánea de valor + start_char + end_char.",
        ],
        BLUE_ACCENT,
    )
    _add_bullet_card(
        s8, 0.45, 4.88, 12.43, 2.05,
        "Control de Incertidumbre Clínica y Fracción de Revisión Manual f <= 0,30 (RNF-03, P-04)",
        [
            "Cero falsos positivos silenciosos (Precision = 1,0000): cuando el ruido OCR corrompe una etiqueta obligatoria o falta un campo clínico, el parser no inventa valores; activa AUDIT_FLAG_CLINICAL_UNCERTAINTY y liquida preventivamente a 0,00.",
            "Fracción de revisión humana f = 0,0000 en el dataset oficial (1,2M) y f = 0,1667 en la muestra de estrés con 50 % de glosas perturbadas (ambos muy por debajo del tope f <= 0,30).",
        ],
        GREEN_OK,
    )
    _set_notes(
        s8,
        "María Fernanda Toro (7:55-8:45): Para evaluar RNF-02 (F1 >= 0,92) sin sesgo, construimos fuera de git una muestra de 600 glosas (200 por integrante): 300 limpias del dataset oficial y 300 con 6 tipos de perturbación (permutación de campos, omisiones y ruido OCR). Bajo coincidencia exacta de span y valor obtuvimos F1 = 1,0000 en limpias, 0,9765 en perturbadas y un Macro-F1 global de 0,9886, con Precision = 1,0000 y fracción de revisión manual dentro del umbral f <= 0,30.",
    )

    # =========================================================================
    # DIAPOSITIVA 9: No Repudio SHA-256 de 3 Niveles y Analítica en Athena (T6)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s9,
        9,
        "No Repudio SHA-256 de 3 Niveles y Consolidación en Apache Iceberg (T6)",
        "Consultas analíticas en vivo desde Amazon Athena sobre las 1.200.000 órdenes adjudicadas",
        "María Fernanda Toro",
        "8:45 – 9:30",
    )
    ath_img = SCREEN_DIR / "aws_athena_iceberg_1200k.png"
    if ath_img.exists():
        s9.shapes.add_picture(str(ath_img), Inches(0.45), Inches(1.30), width=Inches(7.35))

    _add_styled_table(
        s9, 7.95, 1.30, 4.93, 2.35,
        ["Día Solicitud", "Órdenes", "Total Reclamado", "Total Aprobado"],
        [
            ["2026-05-04", "402.000", "529.215.196.182,00", "19.155.939.616,75"],
            ["2026-05-05", "396.000", "522.711.751.027,00", "18.950.939.658,50"],
            ["2026-05-06", "402.000", "531.932.943.100,00", "19.222.024.188,75"],
            ["TOTAL OFICIAL", "1.200.000", "1.583.859.890.309,00", "57.328.903.464,00"],
        ],
        col_widths=[1.05, 0.90, 1.50, 1.48],
        font_size=9.0,
    )
    _add_bullet_card(
        s9, 7.95, 3.80, 4.93, 3.10,
        "Cadena Criptográfica de 3 Niveles Verificada (100 % OK)",
        [
            "Nivel 1 (Orden): hash_decision = SHA-256 del JSON canónico (verificado desde filas de Iceberg CHV-0000001..0000005).",
            "Nivel 2 (Chunk): raiz_hash_chunk = SHA-256 de los 5.000 hashes ordenados (chunk 0: 6e8de620c632b638...).",
            "Nivel 3 (Lote WORM): raiz_hash_lote = 78dbff2ea6b365f3...869e sellado en saom-audit con Versioning + DenyDeleteAuditReceipts.",
            "Idempotencia Iceberg: Doble MERGE INTO en Athena mantuvo exactamente 1.200.000 filas (0 duplicados).",
        ],
        NAVY_DARK,
    )
    _set_notes(
        s9,
        "María Fernanda Toro (8:45-9:30): En esta captura de Amazon Athena vemos la consulta sobre nuestra tabla Apache Iceberg saom_analytics.adjudicaciones devolviendo exactamente 1.200.000 órdenes tras ejecutar MERGE INTO dos veces seguidas, demostrando idempotencia analítica. Además, desde las filas de Iceberg verificamos los 3 niveles criptográficos SHA-256: desde hash_decision de cada orden, pasando por raiz_hash_chunk hasta raiz_hash_lote en el manifiesto WORM.",
    )

    # =========================================================================
    # DIAPOSITIVA 10: Extrapolación a 12M (Medido vs. Proyectado) y Conciliación FinOps
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s10,
        10,
        "Extrapolación a 12 Millones (Medido vs. Proyectado) y Conciliación FinOps",
        "Derivación exacta de los 4,25 min / 7,92 min y unificación de las cifras económicas del proyecto",
        "Equipo COIL",
        "9:30 – 10:00",
    )
    _add_styled_table(
        s10, 0.45, 1.30, 12.43, 2.55,
        [
            "Métrica de Rendimiento (c = 10 workers Lambda Arm64)",
            "Naturaleza",
            "Escala 1,2M (240 chunks)",
            "Escala 12M (2.400 chunks)",
            "Fórmula / Origen Exacto",
        ],
        [
            [
                "Duración media por chunk (T_chunk) y Throughput (k)",
                "Medido en CloudWatch",
                "1,0616 s/chunk (4.710,44 órd/s/vCPU)",
                "1,0616 s/chunk (4.710,44 órd/s/vCPU)",
                "Promedio de REPORT Duration en CloudWatch Logs de saom-worker (1.769 MB = 1 vCPU).",
            ],
            [
                "Tiempo de drenaje puro de cómputo en workers",
                "Medido (1,2M) → Proyectado M/M/c (12M)",
                "25,48 segundos (0,42 min)",
                "254,78 segundos = 4,25 min",
                "De dónde salen los 4,25 min: (2.400 chunks × 1,0616 s) / 10 workers = 254,78 s = 4,25 min.",
            ],
            [
                "Tiempo de reloj extremo a extremo (incl. colas/particionador)",
                "Medido (1,2M) → Proyectado lineal (12M)",
                "47,50 segundos (0,79 min)",
                "475,00 segundos = 7,92 min",
                "Escalamiento 10 × 47,50 s (incluye particionador streaming, SQS y backoff en DynamoDB). Cumple <= 3 h.",
            ],
        ],
        col_widths=[3.15, 2.15, 2.10, 2.10, 2.93],
        font_size=9.5,
    )

    _add_styled_table(
        s10, 0.45, 4.02, 12.43, 2.90,
        [
            "Escenario Económico Unificado",
            "Naturaleza",
            "Volumen Lote",
            "Costo Total del Lote",
            "Costo Unitario (USD / Millón)",
            "Explicación Coherente y Conciliación de Cifras",
        ],
        [
            [
                "1. Estimado Previo de Diseño (E01/E02 con k=400)",
                "Estimado pre-ejecución",
                "1.200.000",
                "~0,3000 USD",
                "0,25 – 0,31 USD / M",
                "Estimación inicial en ADR-003 y RNF-03 antes de medir k en AWS (asumía conservadoramente 12,5 s/chunk).",
            ],
            [
                "2. Corrida Real en AWS Learner Lab (LOTE-COIL-1200K)",
                "Medido en AWS",
                "1.200.000",
                "0,0189 USD",
                "0,0158 USD / M",
                "Gasto real facturado en AWS (0,0067 USD Lambda + 0,0122 USD S3/SQS/DDB/CW): 0,0189 / 1,2 = 0,0158 USD/M.",
            ],
            [
                "3. Escalamiento Lineal Directo 10× (12M)",
                "Proyectado lineal puro",
                "12.000.000",
                "0,1890 USD",
                "0,0158 USD / M",
                "Multiplicación directa 10 × 0,0189 USD de los mismos servicios ejecutados en el prototipo.",
            ],
            [
                "4. Producción Completa 12M con Operación",
                "Proyectado producción",
                "12.000.000",
                "0,2483 USD (~0,25 USD)",
                "0,0207 USD / M",
                "0,2483 USD (~0,25 USD) es el costo del LOTE COMPLETO de 12M (añade retención S3 y compactación Iceberg), igual a 0,0207 USD/M.",
            ],
        ],
        col_widths=[2.85, 1.65, 1.25, 1.55, 1.75, 3.38],
        font_size=9.2,
    )
    _set_notes(
        s10,
        "Cierre (9:30-10:00): En esta diapositiva final dejamos totalmente claras las dos preguntas clave de evaluación. Primero, sobre los tiempos: en AWS medimos 1,0616 s por chunk en CloudWatch y 47,50 s de reloj para 1,2M. Al proyectar a 12 millones (2.400 chunks con 10 workers), los 4,25 minutos (254,78 s) salen del tiempo de drenaje puro de cómputo (2.400 × 1,0616 / 10), mientras que si escalamos por 10 el tiempo de reloj completo con colas y particionador obtenemos 7,92 minutos, ambos muy por debajo de las 3 horas. Segundo, sobre los costos: 0,25-0,31 USD/M era el estimado teórico previo cuando asumíamos k=400; el costo real medido en AWS fue de 0,0158 USD por millón (0,0189 USD en 1,2M y 0,1890 USD escalado a 12M), y 0,2483 USD (~0,25 USD) es el costo del lote completo de 12 millones en producción incluyendo retención S3 y compactación Iceberg, lo que equivale a 0,0207 USD por millón. Muchas gracias.",
    )

    out_path = E04_DIR / "Entregable_04_Presentacion_Ejecutiva_Salud_COIL.pptx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    return out_path


if __name__ == "__main__":
    pptx_file = build_presentation()
    print(f"Presentación PowerPoint generada: {pptx_file} ({pptx_file.stat().st_size:,} bytes)")
