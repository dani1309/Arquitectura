# -*- coding: utf-8 -*-
"""
Generador de la Presentación Ejecutiva Editable (.pptx) de 6 Diapositivas (Entregable 04)
adaptada al formato de video de 3 a 4 minutos (duración objetivo: 3:30 min).

Incluye:
- Diseño ejecutivo widescreen 16:9 (13.333 x 7.5 in)
- 6 diapositivas de alto impacto (~35 s/diapositiva; 70 s por integrante)
- Diagrama simplificado de arquitectura en 300 DPI (e02_arquitectura_simplificada.png)
- Capturas reales de AWS Console (DynamoDB META, Lambda CloudWatch Metrics, Amazon Athena Iceberg)
- Conciliación económica unificada (0,0158 USD/M vs. 0,1890 USD vs. 0,2483 USD vs. 0,25-0,31 USD/M)
- Extrapolación explícita Medido (1,2M en 47,50 s) vs. Proyectado (12M en 4,25 min drenaje / 7,92 min E2E)
- Notas del orador (Speaker Notes) cronometradas para la grabación del video
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

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
GREEN_OK = RGBColor(0x05, 0x96, 0x69)
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
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5)
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG_LIGHT
    bg.line.fill.background()

    header = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.08)
    )
    header.fill.solid()
    header.fill.fore_color.rgb = NAVY_DARK
    header.line.fill.background()

    stripe = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(1.08), Inches(13.333), Inches(0.05)
    )
    stripe.fill.solid()
    stripe.fill.fore_color.rgb = BLUE_ACCENT
    stripe.line.fill.background()

    tb = slide.shapes.add_textbox(Inches(0.45), Inches(0.10), Inches(9.55), Inches(0.92))
    tf = tb.text_frame
    tf.word_wrap = True
    p0 = tf.paragraphs[0]
    r0 = p0.add_run()
    r0.text = title
    r0.font.name = "Calibri"
    r0.font.size = Pt(21.5)
    r0.font.bold = True
    r0.font.color.rgb = WHITE

    p1 = tf.add_paragraph()
    r1 = p1.add_run()
    r1.text = subtitle
    r1.font.name = "Calibri"
    r1.font.size = Pt(11.5)
    r1.font.color.rgb = RGBColor(0x93, 0xC5, 0xFD)

    badge = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(10.10), Inches(0.18), Inches(2.90), Inches(0.72)
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
    br1.text = f"Video: {time_window}  |  Slide {slide_num}/6"
    br1.font.name = "Calibri"
    br1.font.size = Pt(9.5)
    br1.font.color.rgb = RGBColor(0x7D, 0xD3, 0xFC)

    footer = slide.shapes.add_textbox(Inches(0.45), Inches(7.12), Inches(12.4), Inches(0.30))
    ftf = footer.text_frame
    fp = ftf.paragraphs[0]
    fr = fp.add_run()
    fr.text = (
        "SAOM · Sistema de Salud de Chernovia (Proyecto COIL)  |  "
        "Naomi Chow · Daniel Lopez · María Fernanda Toro  |  Cuenta AWS: 329771219583 (us-east-1)"
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
    tf.margin_left = Inches(0.14)
    tf.margin_right = Inches(0.14)
    tf.margin_top = Inches(0.08)

    p0 = tf.paragraphs[0]
    r0 = p0.add_run()
    r0.text = kpi_value
    r0.font.name = "Calibri"
    r0.font.size = Pt(21)
    r0.font.bold = True
    r0.font.color.rgb = accent

    p1 = tf.add_paragraph()
    r1 = p1.add_run()
    r1.text = kpi_title
    r1.font.name = "Calibri"
    r1.font.size = Pt(11)
    r1.font.bold = True
    r1.font.color.rgb = NAVY_DARK

    p2 = tf.add_paragraph()
    r2 = p2.add_run()
    r2.text = kpi_desc
    r2.font.name = "Calibri"
    r2.font.size = Pt(9.5)
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
    tf.margin_left = Inches(0.16)
    tf.margin_right = Inches(0.16)
    tf.margin_top = Inches(0.10)

    p0 = tf.paragraphs[0]
    r0 = p0.add_run()
    r0.text = heading
    r0.font.name = "Calibri"
    r0.font.size = Pt(13)
    r0.font.bold = True
    r0.font.color.rgb = accent

    for b in bullets:
        p = tf.add_paragraph()
        p.space_before = Pt(3.5)
        r = p.add_run()
        r.text = f"• {b}"
        r.font.name = "Calibri"
        r.font.size = Pt(10.3)
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
    font_size: float = 9.8,
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
            if (
                c_idx == 0
                or "CUMPLIDO" in val
                or "0,0158" in val
                or "4,25 min" in val
                or "0,9886" in val
                or "ÓPTIMA" in val
            ):
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
    # SLIDE 1 (0:00 - 0:35 · Naomi Chow): Reto Chernovia + Estado del Arte
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s1,
        1,
        "SAOM · Adjudicación Masiva de Órdenes Médicas en AWS (Proyecto COIL)",
        "Reto de Chernovia (12M órd/día) y Por Qué Fallan las Arquitecturas Convencionales (52 fuentes, E01 v2)",
        "Naomi Chow",
        "0:00 – 0:35",
    )
    _add_kpi_card(
        s1, 0.45, 1.28, 3.95, 1.32,
        "12.000.000 / día",
        "Escala Oficial (SLA < 24 h)",
        "Meta interna del equipo: 3 h (1.111 órd/s). Extracción clínica + liquidación 100/50/25/0 %.",
        BLUE_ACCENT,
    )
    _add_kpi_card(
        s1, 4.68, 1.28, 3.95, 1.32,
        "244.500 USD/día",
        "Step Functions + Comprehend Medical",
        "Inviable: mínimo 300 chars (36M u./día, tarifa escalonada AWS) y solo procesa inglés.",
        NAVY_DARK,
    )
    _add_kpi_card(
        s1, 8.90, 1.28, 3.98, 1.32,
        "0,0158 USD / M",
        "Nuestra Solución SAOM (Medido AWS)",
        "Micro-lotes de 5.000 órdenes en Lambda Arm64: ahorro > 99,99 % vs. manual y EMR (~220 USD/día).",
        GREEN_OK,
    )
    _add_styled_table(
        s1, 0.45, 2.78, 12.43, 4.10,
        [
            "Alternativa Evaluada (E01 v2)",
            "Patrón Técnico",
            "Costo Diario (12M órd.)",
            "Costo Unitario (USD/M)",
            "Veredicto Técnico y Financiero",
        ],
        [
            [
                "A. Auditoría Manual",
                "Revisión humana (~3 min/orden)",
                "9.600.000 USD / día",
                "800.000 USD / M",
                "INVIABLE: Cuello de botella operativo.",
            ],
            [
                "B. Orden por Orden + Comprehend Medical",
                "Step Functions + API NLP (mín. 300 chars = 3 u./glosa)",
                "244.500 USD / día (escalonado)\n381.000 USD / día (Tier 1)",
                "20.375 USD / M\n(31.750 USD / M)",
                "INVIABLE: Costo prohibitivo y limitado a idioma inglés.",
            ],
            [
                "C. Clúster Big Data Pesado (EMR Spark)",
                "24 nodos c6g.4xlarge (384 vCPU)",
                "~220,00 USD / día",
                "~18,33 USD / M",
                "INVIABLE EN LAB: Excede cuotas y crédito de 50 USD del Learner Lab.",
            ],
            [
                "D. SAOM (Micro-Lotes Lambda Arm64)",
                "S3 Range GET (5.000 órd/chunk) + SQS + DynamoDB + Iceberg",
                "0,1890 USD (lineal 12M)\n0,2483 USD (con operación)",
                "0,0158 USD / M (medido)\n0,0207 USD / M (prod.)",
                "ÓPTIMA (ADR-001..005): Validada en vivo con 1,2M en AWS por 0,0189 USD.",
            ],
        ],
        col_widths=[2.65, 3.30, 2.25, 1.85, 2.38],
        font_size=9.8,
    )
    _set_notes(
        s1,
        "Naomi Chow (0:00-0:35): Hola, somos Naomi Chow, Daniel Lopez y María Fernanda Toro, y presentamos SAOM, el Sistema de Adjudicación de Órdenes Médicas para el Ministerio de Salud de Chernovia. El reto exige procesar hasta 12 millones de órdenes diarias en menos de 24 horas —con una meta interna de nuestro equipo de 3 horas—, extraer cuatro entidades clínicas de cada glosa, liquidar al 100, 50, 25 o 0 por ciento y dejar auditoría verificable sin exponer PII. Al evaluar 52 fuentes técnicas demostramos que orquestar orden por orden con Step Functions y Comprehend Medical cuesta 244.500 dólares al día por su mínimo de 300 caracteres y solo opera en inglés, mientras que un clúster EMR de 220 dólares diarios excede los 50 dólares del Learner Lab. Por eso diseñamos una arquitectura por micro-lotes de 5.000 órdenes en AWS Lambda Arm64.",
    )

    # =========================================================================
    # SLIDE 2 (0:35 - 1:10 · Naomi Chow): Metodología AI-DLC y Requisitos
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s2,
        2,
        "Metodología AI-DLC en 6 Pasos y Requisitos Verificados",
        "Separación rigurosa entre exigencias del enunciado y metas de ingeniería del equipo",
        "Naomi Chow",
        "0:35 – 1:10",
    )
    _add_styled_table(
        s2, 0.45, 1.28, 12.43, 4.10,
        [
            "Código",
            "Dimensión",
            "Requisito del Enunciado",
            "Meta Interna del Equipo",
            "Resultado Verificado (36/36 Tests + AWS)",
        ],
        [
            [
                "RF-01..05",
                "Ingesta, Extracción, Cobertura, Liquidación y Firma",
                "CUBRE / NO_CUBRE y liquidación 100/50/25/0 %",
                "100 % BDD Gherkin con Decimal exacto (sin float)",
                "CUMPLIDO: 25/25 tests BDD + 1.200.000 órdenes en AWS.",
            ],
            [
                "RNF-01",
                "Volumen y Ventana Batch",
                "12M en < 24 h (138,89 órd/s)",
                "12M en <= 3 h (1.111 órd/s); 1,2M <= 2,4 h",
                "CUMPLIDO: 1,2M en 47,50 s; 12M en 4,25 min drenaje / 7,92 min E2E.",
            ],
            [
                "RNF-02",
                "Calidad Clínica (F1)",
                "Extraer paciente, edad, servicio y medicación",
                "Macro-F1 >= 0,92 con spans exactos",
                "CUMPLIDO: Macro-F1 = 0,9886 (1,0000 limpias / 0,9765 perturbadas).",
            ],
            [
                "RNF-03",
                "Eficiencia Financiera",
                "Costo razonable",
                "<= 0,50 USD/M en lab y ahorro >= 70 %",
                "CUMPLIDO: 0,0158 USD/M medido (0,0189 USD en 1,2M; ahorro 99,99 %).",
            ],
            [
                "RNF-04/05",
                "Trazabilidad y PII",
                "Registro trazable de decisiones",
                "Cadena SHA-256 de 3 niveles y 0 PII en claro",
                "CUMPLIDO: 100 % verificado desde Iceberg y 0 coincidencias PII.",
            ],
            [
                "RNF-06",
                "Tolerancia a Fallos",
                "Escalabilidad y resiliencia",
                "Idempotencia DynamoDB/Iceberg y aislamiento de errores",
                "CUMPLIDO: CHV-9999999 en rechazos/, duplicados_ignorados=1, 0 DLQ.",
            ],
        ],
        col_widths=[1.25, 2.25, 2.30, 2.85, 3.78],
        font_size=9.5,
    )
    _add_bullet_card(
        s2, 0.45, 5.55, 12.43, 1.38,
        "Gobernanza AI-DLC (Pasos 1 a 6 Completados y Auditables en Git)",
        [
            "Paso 1 (E01 v2, 52 citas) → Paso 2 (BDD + ADR-001..003) → Paso 3 (C4/E02 + ADR-004..005) → Paso 4 (Plan T0..T8) → Paso 5 (saom_core.py + Lambda Arm64) → Paso 6 (Corrida real 1,2M en AWS Learner Lab).",
            "36 pruebas automatizadas en pytest (BDD, integración multi-chunk T3 y evaluación F1 sobre 600 glosas) ejecutadas con 100 % de éxito.",
        ],
        NAVY_DARK,
    )
    _set_notes(
        s2,
        "Naomi Chow (0:35-1:10): Aplicamos la metodología AI-DLC en seis pasos trazables, separando los requisitos del enunciado de nuestras metas de ingeniería: Macro-F1 >= 0,92, costo <= 0,50 USD por millón, cero datos personales en claro e idempotencia exacta, todo verificado con 36 pruebas automatizadas y ejecución real en AWS. Le doy paso a Daniel para mostrar la arquitectura y los resultados en la nube.",
    )

    # =========================================================================
    # SLIDE 3 (1:10 - 1:45 · Daniel Lopez): Arquitectura e Idempotencia
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s3,
        3,
        "Arquitectura Híbrida Serverless por Micro-Lotes e Idempotencia (8 Pasos)",
        "Particionamiento streaming (4 MB RAM), S3 Range GET e idempotencia atómica en DynamoDB",
        "Daniel Lopez",
        "1:10 – 1:45",
    )
    arch_img = DIAG_DIR / "e02_arquitectura_simplificada.png"
    if arch_img.exists():
        s3.shapes.add_picture(str(arch_img), Inches(0.45), Inches(1.26), width=Inches(8.15))

    _add_bullet_card(
        s3, 8.75, 1.26, 4.13, 5.65,
        "Flujo Serverless y Lección Real en AWS",
        [
            "Streaming (4 MB RAM): saom-particionador lee el CSV de 360 MB en S3 y publica en SQS 240 descriptores [byte_inicio, byte_fin] de 5.000 órdenes, reduciendo 5.000x la coordinación.",
            "Workers sin Estado: Hasta 10 Lambdas Arm64 (1.769 MB = 1 vCPU) descargan solo su rango de bytes (Range GET) y adjudican en paralelo.",
            "Prueba T3 (10.001 filas en 4,83 s): Fila corrupta CHV-9999999 aislada en rechazos/ con 0 PII; reenvío de chunk 0 ignorado (duplicados_ignorados = 1).",
            "Hallazgo TransactionConflict: Al correr 240 chunks en paralelo sobre el ítem caliente META, distinguimos ConditionalCheckFailed de TransactionConflict y aplicamos exponential backoff + jitter (240/240 exactos).",
        ],
        BLUE_ACCENT,
    )
    _set_notes(
        s3,
        "Daniel Lopez (1:10-1:45): Gracias, Naomi. Como muestra nuestro diagrama de 8 pasos, cuando el CSV llega a saom-raw, la función saom-particionador lo recorre en streaming con solo 4 MB de RAM y publica en SQS descriptores livianos con los rangos exactos de bytes de cada bloque de 5.000 órdenes, reduciendo 5.000 veces la coordinación. Hasta 10 workers Lambda arm64 leen solo su rango con S3 Range GET y consolidan atómicamente en DynamoDB control_lotes. En la prueba T3 aislamos una fila corrupta en rechazos/ sin PII e ignoramos reenvíos duplicados; y al correr los 240 chunks en paralelo resolvimos la contención TransactionConflict sobre el ítem META mediante exponential backoff con jitter.",
    )

    # =========================================================================
    # SLIDE 4 (1:45 - 2:20 · Daniel Lopez): Corrida Real 1.2M en AWS
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s4,
        4,
        "Ejecución Real en AWS Learner Lab: 1.200.000 Órdenes en 47,50 s (T4)",
        "Evidencia en vivo en CloudWatch Metrics (saom-worker) y Amazon DynamoDB (control_lotes)",
        "Daniel Lopez",
        "1:45 – 2:20",
    )
    _add_kpi_card(
        s4, 0.45, 1.24, 3.00, 1.20,
        "47,50 s (240/240)",
        "Reloj Real 1,2M en AWS",
        "10 workers concurrentes, 0 errores y 0 mensajes en DLQ.",
        GREEN_OK,
    )
    _add_kpi_card(
        s4, 3.60, 1.24, 3.00, 1.20,
        "4.710,44 órd/s",
        "Throughput E2E / vCPU",
        "1.061,60 ms/chunk en CloudWatch (11,8x sobre k >= 400).",
        BLUE_ACCENT,
    )
    _add_kpi_card(
        s4, 6.75, 1.24, 3.00, 1.20,
        "153,0 MB RAM",
        "Memoria Pico (de 1.769 MB)",
        "Solo 8,6 % de RAM usada; 505,37 GB-s facturados.",
        NAVY_DARK,
    )
    _add_kpi_card(
        s4, 9.90, 1.24, 2.98, 1.20,
        "0,0189 USD",
        "Costo Total Real (1,2M)",
        "Equivalente a 0,0158 USD/M (0,0067 USD en Lambda Arm64).",
        GREEN_OK,
    )

    cw_img = SCREEN_DIR / "aws_lambda_saom_worker_metrics.png"
    if cw_img.exists():
        s4.shapes.add_picture(str(cw_img), Inches(0.45), Inches(2.58), width=Inches(6.15))

    ddb_img = SCREEN_DIR / "aws_dynamodb_lote_coil_1200k_meta.png"
    if ddb_img.exists():
        s4.shapes.add_picture(str(ddb_img), Inches(6.73), Inches(2.58), width=Inches(6.15))

    # Etiquetas de pie de captura
    cap1 = s4.shapes.add_textbox(Inches(0.45), Inches(6.55), Inches(6.15), Inches(0.38))
    c1p = cap1.text_frame.paragraphs[0]
    c1p.alignment = PP_ALIGN.CENTER
    c1r = c1p.add_run()
    c1r.text = "CloudWatch Metrics (saom-worker): 10 concurrentes, ~1.061 ms/chunk, 100 % éxito (0 errores)"
    c1r.font.name = "Calibri"
    c1r.font.size = Pt(9.8)
    c1r.font.bold = True
    c1r.font.color.rgb = NAVY_DARK

    cap2 = s4.shapes.add_textbox(Inches(6.73), Inches(6.55), Inches(6.15), Inches(0.38))
    c2p = cap2.text_frame.paragraphs[0]
    c2p.alignment = PP_ALIGN.CENTER
    c2r = c2p.add_run()
    c2r.text = "DynamoDB (control_lotes): PK=LOTE#LOTE-COIL-1200K, SK=META → 240/240 chunks PROCESADO"
    c2r.font.name = "Calibri"
    c2r.font.size = Pt(9.8)
    c2r.font.bold = True
    c2r.font.color.rgb = NAVY_DARK

    _set_notes(
        s4,
        "Daniel Lopez (1:45-2:20): Con esto ejecutamos en nuestra cuenta de AWS (329771219583) el dataset oficial completo de 1.200.000 órdenes (LOTE-COIL-1200K). Como muestran las capturas reales de CloudWatch y DynamoDB, los 240 chunks finalizaron en 47,50 segundos de reloj con cero errores y cero mensajes en la DLQ, a una media de 1.061,60 ms por chunk —es decir, 4.710,44 órdenes por segundo por vCPU— consumiendo apenas 153 MB de RAM y 0,0189 dólares totales. Continúa María Fernanda.",
    )

    # =========================================================================
    # SLIDE 5 (2:20 - 2:55 · María Fernanda Toro): PII, F1=0,9886, SHA-256 e Iceberg
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s5,
        5,
        "Privacidad PII, Macro-F1 = 0,9886, SHA-256 y Apache Iceberg (T5 + T6)",
        "Invarianza de spans con '#', exactitud financiera Decimal y consolidación SQL en Amazon Athena",
        "María Fernanda Toro",
        "2:20 – 2:55",
    )
    ath_img = SCREEN_DIR / "aws_athena_iceberg_1200k.png"
    if ath_img.exists():
        s5.shapes.add_picture(str(ath_img), Inches(0.45), Inches(1.28), width=Inches(7.15))

    _add_styled_table(
        s5, 0.45, 5.05, 7.15, 1.85,
        ["Entidad Clínica (600 glosas)", "F1 Limpias (300)", "F1 Perturbadas (300)", "F1 Global"],
        [
            ["Edad / PerfilCobertura", "1,0000", "0,9768", "0,9888"],
            ["ServicioSolicitado / Medicación", "1,0000", "0,9787 / 0,9737", "0,9897 / 0,9873"],
            ["PROMEDIO MACRO-F1 (Meta >= 0,92)", "1,0000", "0,9765", "0,9886 (Precision 1,0000)"],
        ],
        col_widths=[2.65, 1.40, 1.60, 1.50],
        font_size=9.2,
    )

    _add_bullet_card(
        s5, 7.78, 1.28, 5.10, 5.62,
        "Garantías Clínicas, Criptográficas y Analíticas",
        [
            "Cero PII (ADR-002): Paciente, DNO y SeguroSocial se pseudonimizan con HMAC-SHA256 y se enmascaran con '#' * len(valor). La longitud no cambia y los spans [start_char, end_char] permanecen idénticos (0 PII en S3/DDB/Logs).",
            "Aritmética Decimal Exacta: Liquidación con Decimal + ROUND_HALF_UP (sin float). Reclamado: 1.583.859.890.309,00 | Aprobado: 57.328.903.464,00.",
            "Cadena SHA-256 de 3 Niveles: hash_decision → raiz_hash_chunk → raiz_hash_lote (78dbff2e...869e) en saom-audit con política DenyDeleteAuditReceipts.",
            "Idempotencia Iceberg (Athena): Doble MERGE INTO mantuvo exactamente 1.200.000 filas (0 duplicados) y verificación 100 % OK desde Iceberg.",
        ],
        NAVY_DARK,
    )
    _set_notes(
        s5,
        "María Fernanda Toro (2:20-2:55): Gracias, Daniel. En cada worker, saom_core.py pseudonimiza paciente, DNO y Seguro Social con HMAC-SHA256 y los enmascara con '#' conservando la longitud exacta de la glosa, de modo que los spans [start_char, end_char] no se desplazan y logramos cero PII en S3, DynamoDB y CloudWatch. Sobre 600 glosas evaluadas fuera de git —300 limpias y 300 con ruido OCR y permutaciones— obtuvimos un Macro-F1 de 0,9886, usando Decimal exacto sin float. Además, como ven en la captura de Amazon Athena, consolidamos las 1.200.000 filas en Apache Iceberg con doble MERGE INTO sin duplicados y verificamos la cadena SHA-256 de tres niveles hasta raiz_hash_lote.",
    )

    # =========================================================================
    # SLIDE 6 (2:55 - 3:30 · María Fernanda Toro): Extrapolación 12M y FinOps
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    _add_header_and_footer(
        s6,
        6,
        "Extrapolación a 12M (Medido vs. Proyectado) y Conciliación FinOps",
        "Derivación exacta de los 4,25 min / 7,92 min y unificación de todas las cifras económicas",
        "María Fernanda Toro",
        "2:55 – 3:30",
    )
    _add_styled_table(
        s6, 0.45, 1.28, 12.43, 2.55,
        [
            "Métrica de Rendimiento (c = 10 workers Lambda Arm64)",
            "Naturaleza",
            "Escala 1,2M (240 chunks)",
            "Escala 12M (2.400 chunks)",
            "Fórmula / Origen Exacto",
        ],
        [
            [
                "Duración media por chunk y Throughput (k)",
                "Medido en CloudWatch",
                "1,0616 s/chunk (4.710,44 órd/s/vCPU)",
                "1,0616 s/chunk (4.710,44 órd/s/vCPU)",
                "Promedio REPORT Duration de saom-worker (1.769 MB = 1 vCPU).",
            ],
            [
                "Tiempo de drenaje puro de cómputo en workers",
                "Medido (1,2M) → Proyectado M/M/c (12M)",
                "25,48 segundos (0,42 min)",
                "254,78 segundos = 4,25 min",
                "Origen de 4,25 min: (2.400 chunks × 1,0616 s) / 10 workers = 254,78 s.",
            ],
            [
                "Tiempo de reloj extremo a extremo (incl. colas/particionador)",
                "Medido (1,2M) → Proyectado lineal (12M)",
                "47,50 segundos (0,79 min)",
                "475,00 segundos = 7,92 min",
                "Escalamiento 10 × 47,50 s (incluye SQS, particionador y backoff). Meta <= 3 h.",
            ],
        ],
        col_widths=[3.15, 2.15, 2.10, 2.10, 2.93],
        font_size=9.5,
    )

    _add_styled_table(
        s6, 0.45, 4.00, 12.43, 2.92,
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
                "Estimación inicial en ADR-003 y RNF-03 antes de medir k en AWS (asumía 12,5 s/chunk).",
            ],
            [
                "2. Corrida Real en AWS Learner Lab (LOTE-COIL-1200K)",
                "Medido en AWS",
                "1.200.000",
                "0,0189 USD",
                "0,0158 USD / M",
                "Gasto real facturado en AWS (0,0067 Lambda + 0,0122 S3/SQS/DDB/CW): 0,0189 / 1,2 = 0,0158 USD/M.",
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
                "0,2483 USD (~0,25 USD) es el costo del LOTE COMPLETO de 12M (retención S3 + Iceberg), igual a 0,0207 USD/M.",
            ],
        ],
        col_widths=[2.85, 1.65, 1.25, 1.55, 1.75, 3.38],
        font_size=9.2,
    )
    _set_notes(
        s6,
        "María Fernanda Toro (2:55-3:30): Para cerrar, diferenciamos lo medido de lo proyectado a 12 millones (2.400 chunks con 10 workers): el drenaje puro de cómputo es 2.400 × 1,0616 / 10 = 4,25 minutos, y el tiempo de reloj extremo a extremo escalando colas y particionador es 7,92 minutos, ambos muy por debajo de 3 horas. En costos, frente al estimado teórico previo de 0,25 a 0,31 USD/M, el gasto real medido en AWS fue 0,0158 USD por millón, proyectando 0,1890 USD lineal o 0,2483 USD por el lote diario completo de 12 millones con retención S3 y compactación Iceberg (0,0207 USD/M). Muchas gracias.",
    )

    out_path = E04_DIR / "Entregable_04_Presentacion_Ejecutiva_Salud_COIL.pptx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    return out_path


if __name__ == "__main__":
    pptx_file = build_presentation()
    print(f"Presentación PowerPoint generada: {pptx_file} ({pptx_file.stat().st_size:,} bytes)")
