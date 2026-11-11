"""Generador de diagramas limpios y simplificados para el Entregable 02 (Diseño Técnico) y C4 actualizados.

No requiere Graphviz externo; utiliza `matplotlib` a 300 DPI con control exacto de coordenadas
para evitar cruces de líneas o textos superpuestos y reflejar fielmente las reglas COIL vigentes.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

SALIDA = Path(__file__).resolve().parent

# Paleta ejecutiva AWS / C4
COLOR_FONDO = "#FFFFFF"
COLOR_CLUSTER_BG = "#F8FAFC"
COLOR_CLUSTER_BORDE = "#CBD5E1"
COLOR_NAVY = "#1E293B"
COLOR_TEXTO_SUB = "#475569"

# Colores por categoría de servicio AWS
COLOR_S3 = "#2E7D32"         # Verde almacenamiento S3
COLOR_SQS = "#C2185B"        # Rosa/Magenta mensajería SQS
COLOR_LAMBDA = "#E65100"     # Naranja cómputo Lambda
COLOR_DDB = "#1565C0"        # Azul base de datos DynamoDB
COLOR_ATHENA = "#6A1B9A"     # Morado analítica Athena / Iceberg
COLOR_CW = "#00838F"         # Cian observabilidad / Seguridad
COLOR_ACTOR = "#334155"      # Gris oscuro actores externos
COLOR_C4_PERSON = "#08427B"
COLOR_C4_SYSTEM = "#1168BD"
COLOR_C4_CONTAINER = "#438DD5"
COLOR_C4_COMPONENT = "#E0F2FE"
COLOR_C4_EXT = "#64748B"


def _caja(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    titulo: str,
    subtitulo: str = "",
    detalle: str = "",
    color_borde: str = COLOR_NAVY,
    color_fondo: str = "#FFFFFF",
    color_franja: Optional[str] = None,
    color_texto: str = "#0F172A",
    fontsize_titulo: float = 10.0,
    fontsize_sub: float = 8.2,
    fontsize_det: float = 7.8,
) -> None:
    """Dibuja una tarjeta de arquitectura con franja superior opcional y texto centrado."""
    rect = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        linewidth=1.6,
        edgecolor=color_borde,
        facecolor=color_fondo,
        zorder=3,
    )
    ax.add_patch(rect)

    if color_franja:
        franja_h = min(0.28, h * 0.22)
        franja = FancyBboxPatch(
            (x, y + h - franja_h),
            w,
            franja_h,
            boxstyle="round,pad=0.02,rounding_size=0.10",
            linewidth=0,
            facecolor=color_franja,
            zorder=4,
        )
        ax.add_patch(franja)
        ax.text(
            x + w / 2,
            y + h - franja_h / 2,
            subtitulo,
            ha="center",
            va="center",
            fontsize=fontsize_sub,
            fontweight="bold",
            color="#FFFFFF",
            zorder=5,
        )
        y_centro = y + (h - franja_h) / 2
        if detalle:
            ax.text(
                x + w / 2,
                y_centro + (h - franja_h) * 0.18,
                titulo,
                ha="center",
                va="center",
                fontsize=fontsize_titulo,
                fontweight="bold",
                color=color_texto,
                zorder=5,
            )
            ax.text(
                x + w / 2,
                y_centro - (h - franja_h) * 0.20,
                detalle,
                ha="center",
                va="center",
                fontsize=fontsize_det,
                color=COLOR_TEXTO_SUB,
                zorder=5,
            )
        else:
            ax.text(
                x + w / 2,
                y_centro,
                titulo,
                ha="center",
                va="center",
                fontsize=fontsize_titulo,
                fontweight="bold",
                color=color_texto,
                zorder=5,
            )
    else:
        if subtitulo and detalle:
            ax.text(
                x + w / 2,
                y + h * 0.72,
                titulo,
                ha="center",
                va="center",
                fontsize=fontsize_titulo,
                fontweight="bold",
                color=color_texto,
                zorder=5,
            )
            ax.text(
                x + w / 2,
                y + h * 0.50,
                subtitulo,
                ha="center",
                va="center",
                fontsize=fontsize_sub,
                style="italic",
                color=color_texto if color_texto == "#FFFFFF" else COLOR_TEXTO_SUB,
                zorder=5,
            )
            ax.text(
                x + w / 2,
                y + h * 0.24,
                detalle,
                ha="center",
                va="center",
                fontsize=fontsize_det,
                color=color_texto if color_texto == "#FFFFFF" else COLOR_TEXTO_SUB,
                zorder=5,
            )
        elif subtitulo:
            ax.text(
                x + w / 2,
                y + h * 0.62,
                titulo,
                ha="center",
                va="center",
                fontsize=fontsize_titulo,
                fontweight="bold",
                color=color_texto,
                zorder=5,
            )
            ax.text(
                x + w / 2,
                y + h * 0.30,
                subtitulo,
                ha="center",
                va="center",
                fontsize=fontsize_sub,
                color=color_texto if color_texto == "#FFFFFF" else COLOR_TEXTO_SUB,
                zorder=5,
            )
        else:
            ax.text(
                x + w / 2,
                y + h / 2,
                titulo,
                ha="center",
                va="center",
                fontsize=fontsize_titulo,
                fontweight="bold",
                color=color_texto,
                zorder=5,
            )


def _cluster(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    titulo: str,
    color_borde: str = COLOR_CLUSTER_BORDE,
    color_fondo: str = COLOR_CLUSTER_BG,
    linestyle: str = "--",
) -> None:
    rect = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.03,rounding_size=0.18",
        linewidth=1.4,
        linestyle=linestyle,
        edgecolor=color_borde,
        facecolor=color_fondo,
        zorder=1,
    )
    ax.add_patch(rect)
    ax.text(
        x + 0.20,
        y + h - 0.24,
        titulo,
        ha="left",
        va="top",
        fontsize=9.5,
        fontweight="bold",
        color=COLOR_NAVY,
        zorder=2,
    )


def _flecha(
    ax: plt.Axes,
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    etiqueta: str = "",
    color: str = "#334155",
    linestyle: str = "-",
    rad: float = 0.0,
    label_offset: Tuple[float, float] = (0.0, 0.16),
    fontsize: float = 8.0,
) -> None:
    conn = f"arc3,rad={rad}"
    arr = FancyArrowPatch(
        p1,
        p2,
        connectionstyle=conn,
        arrowstyle="-|>,head_length=6,head_width=3.8",
        linewidth=1.5,
        linestyle=linestyle,
        color=color,
        zorder=6,
    )
    ax.add_patch(arr)
    if etiqueta:
        mx = (p1[0] + p2[0]) / 2 + label_offset[0]
        my = (p1[1] + p2[1]) / 2 + label_offset[1]
        ax.text(
            mx,
            my,
            etiqueta,
            ha="center",
            va="center",
            fontsize=fontsize,
            fontweight="bold",
            color=color,
            bbox=dict(
                boxstyle="round,pad=0.15",
                facecolor="#FFFFFF",
                edgecolor="none",
                alpha=0.92,
            ),
            zorder=7,
        )


def generar_arquitectura_simplificada_e02() -> Path:
    """Genera el diagrama principal simplificado del E02 (Flujo en AWS en 4 etapas claras sin cruces)."""
    fig, ax = plt.subplots(figsize=(17.5, 9.2), dpi=300)
    ax.set_xlim(0, 17.5)
    ax.set_ylim(0, 9.2)
    ax.axis("off")
    fig.patch.set_facecolor(COLOR_FONDO)

    # Título principal
    ax.text(
        8.75,
        8.85,
        "Arquitectura Distribuida en AWS · SAOM Chernovia (Proyecto COIL)",
        ha="center",
        va="center",
        fontsize=14.5,
        fontweight="bold",
        color=COLOR_NAVY,
    )
    ax.text(
        8.75,
        8.50,
        "Ingesta continua y adjudicación por micro-lotes de 5.000 órdenes (Región us-east-1 · Presupuesto Learner Lab 50 USD)",
        ha="center",
        va="center",
        fontsize=10.0,
        color=COLOR_TEXTO_SUB,
    )

    # Contenedor regional AWS
    _cluster(
        ax,
        2.05,
        0.45,
        13.25,
        7.75,
        "AWS Cloud · Región us-east-1 (Servicios Serverless Multi-AZ · Rol LabRole)",
        color_borde="#94A3B8",
        color_fondo="#F8FAFC",
    )

    # 4 Columnas / Etapas dentro de AWS con amplios corredores entre ellas
    _cluster(ax, 2.30, 0.75, 2.75, 6.95, "1. Ingesta y Partición", color_fondo="#FFFFFF")
    _cluster(ax, 5.75, 0.75, 3.15, 6.95, "2. Coordinación y Cómputo", color_fondo="#FFFFFF")
    _cluster(ax, 9.60, 0.75, 2.75, 6.95, "3. Almacenamiento Políglota", color_fondo="#FFFFFF")
    _cluster(ax, 12.95, 0.75, 2.10, 6.95, "4. Analítica y Auditoría", color_fondo="#FFFFFF")

    # Actores externos (Izquierda y Derecha)
    _caja(
        ax,
        0.15,
        5.55,
        1.55,
        1.45,
        "Entidades\nEmisoras (IPS)",
        "10 instituciones",
        "7 canales de envío\n(CSV 1,2M / 12M)",
        color_borde=COLOR_ACTOR,
        color_franja=COLOR_ACTOR,
        fontsize_titulo=9.5,
    )

    _caja(
        ax,
        15.65,
        3.55,
        1.70,
        1.65,
        "Analistas y\nEntes de Control",
        "Pagador / Auditoría",
        "Consultas SQL y\nverificación en\n3 niveles SHA-256",
        color_borde=COLOR_ACTOR,
        color_franja=COLOR_ACTOR,
        fontsize_titulo=9.5,
    )

    # Columna 1: Ingesta y Partición
    _caja(
        ax,
        2.50,
        5.55,
        2.35,
        1.40,
        "saom-raw",
        "Amazon S3 (SSE-KMS)",
        "CSV original con PII\n(360 MB · 1,2M filas)",
        color_borde=COLOR_S3,
        color_franja=COLOR_S3,
    )
    _caja(
        ax,
        2.50,
        3.35,
        2.35,
        1.30,
        "lotes-recibidos",
        "Amazon SQS",
        "Cola de eventos\nObjectCreated",
        color_borde=COLOR_SQS,
        color_franja=COLOR_SQS,
    )
    _caja(
        ax,
        2.50,
        1.10,
        2.35,
        1.35,
        "Particionador CSV",
        "AWS Lambda (Python)",
        "Valida cabecera y emite\nrangos de 5.000 filas",
        color_borde=COLOR_LAMBDA,
        color_franja=COLOR_LAMBDA,
    )

    # Columna 2: Coordinación, Cómputo y Observabilidad
    _caja(
        ax,
        5.95,
        5.65,
        1.75,
        1.30,
        "chunks-\nadjudicacion",
        "Amazon SQS",
        "240 descriptores\n[inicio, fin]",
        color_borde=COLOR_SQS,
        color_franja=COLOR_SQS,
        fontsize_titulo=9.2,
    )
    _caja(
        ax,
        7.85,
        5.65,
        0.90,
        1.30,
        "DLQ",
        "SQS DLQ",
        "Aísla tras\n3 fallos",
        color_borde=COLOR_SQS,
        color_franja=COLOR_SQS,
        fontsize_titulo=9.0,
        fontsize_sub=7.5,
        fontsize_det=7.2,
    )
    _caja(
        ax,
        5.95,
        3.15,
        2.80,
        1.75,
        "Workers Adjudicación\n(× N en paralelo)",
        "AWS Lambda Arm64 (1 vCPU)",
        "1. Valida CSV   2. HMAC + '#'\n3. Extrae spans   4. Cubre/Liquida\n5. Firma JSON canónico SHA-256",
        color_borde=COLOR_LAMBDA,
        color_franja=COLOR_LAMBDA,
    )
    _caja(
        ax,
        5.95,
        1.10,
        1.32,
        1.30,
        "Clave HMAC",
        "Secrets / KMS",
        "Tokenización\npatient_token",
        color_borde=COLOR_CW,
        color_franja=COLOR_CW,
        fontsize_titulo=9.0,
        fontsize_det=7.4,
    )
    _caja(
        ax,
        7.43,
        1.10,
        1.32,
        1.30,
        "CloudWatch",
        "Logs + EMF",
        "Mide k (órd/s)\nCero PII",
        color_borde=COLOR_CW,
        color_franja=COLOR_CW,
        fontsize_titulo=9.0,
        fontsize_det=7.4,
    )

    # Columna 3: Almacenamiento Políglota
    _caja(
        ax,
        9.80,
        5.85,
        2.35,
        1.20,
        "saom-ref",
        "Amazon S3 (Versionado)",
        "Catálogos COIL (COV-001..020)\ny perfiles (100%, 50%, 25%)",
        color_borde=COLOR_S3,
        color_franja=COLOR_S3,
        fontsize_titulo=9.5,
    )
    _caja(
        ax,
        9.80,
        4.20,
        2.35,
        1.25,
        "saom-curated",
        "Amazon S3 + Iceberg",
        "staging/, rechazos/ y tabla\nanalítica adjudicaciones",
        color_borde=COLOR_S3,
        color_franja=COLOR_S3,
        fontsize_titulo=9.5,
    )
    _caja(
        ax,
        9.80,
        2.55,
        2.35,
        1.25,
        "saom-audit (WORM)",
        "S3 Object Lock / Versioning",
        "recibos/ firmados y\nmanifiestos/ con raíz hash",
        color_borde=COLOR_S3,
        color_franja=COLOR_S3,
        fontsize_titulo=9.5,
    )
    _caja(
        ax,
        9.80,
        0.95,
        2.35,
        1.20,
        "control_lotes",
        "DynamoDB On-Demand",
        "Estado META/CHUNK# e\nidempotencia TransactWrite",
        color_borde=COLOR_DDB,
        color_franja=COLOR_DDB,
        fontsize_titulo=9.5,
    )

    # Columna 4: Consolidación y Consulta
    _caja(
        ax,
        13.12,
        4.10,
        1.76,
        1.50,
        "Athena +\nGlue Catalog",
        "Motor Analítico SQL",
        "MERGE INTO Iceberg\nConsultas por IPS,\ncanal y fecha",
        color_borde=COLOR_ATHENA,
        color_franja=COLOR_ATHENA,
        fontsize_titulo=9.2,
    )
    _caja(
        ax,
        13.12,
        2.25,
        1.76,
        1.40,
        "Verificador\n3 Niveles",
        "Auditoría Criptográfica",
        "Compara fila Iceberg,\nrecibo WORM y\nraíz del manifiesto",
        color_borde=COLOR_CW,
        color_franja=COLOR_CW,
        fontsize_titulo=9.2,
    )

    # Flechas limpias y sin superposiciones
    _flecha(ax, (1.70, 6.25), (2.50, 6.25), "1. CSV", label_offset=(0.0, 0.22))
    _flecha(ax, (3.67, 5.55), (3.67, 4.65), "2. Evento S3", label_offset=(0.58, 0.0))
    _flecha(ax, (3.67, 3.35), (3.67, 2.45), "3. Invoca", label_offset=(0.50, 0.0))
    _flecha(
        ax,
        (4.85, 1.85),
        (5.95, 6.10),
        "4. 240 chunks",
        rad=-0.08,
        label_offset=(-0.08, 0.35),
    )

    # DLQ al lado derecho de chunks-adjudicacion
    _flecha(
        ax,
        (7.70, 6.30),
        (7.85, 6.30),
        "",
        color=COLOR_SQS,
        linestyle=":",
    )
    ax.text(7.77, 6.52, "3 fallos", ha="center", va="center", fontsize=7.2, fontweight="bold", color=COLOR_SQS)

    # SQS a Workers
    _flecha(ax, (6.82, 5.65), (6.82, 4.90), "5. 1 chunk", label_offset=(-0.52, 0.0))

    # Lectura de Range bytes (saom-raw -> Workers)
    _flecha(
        ax,
        (4.85, 5.95),
        (5.95, 4.55),
        "6a. Range bytes",
        color="#475569",
        linestyle="--",
        rad=-0.10,
        label_offset=(0.0, 0.28),
    )

    # Catálogos saom-ref -> Workers
    _flecha(
        ax,
        (9.80, 6.35),
        (8.75, 4.65),
        "6b. Catálogos",
        color="#475569",
        linestyle="--",
        rad=0.10,
        label_offset=(-0.10, 0.32),
    )

    # Clave HMAC y CloudWatch EMF (vertical directo hacia abajo/arriba en Columna 2)
    _flecha(
        ax,
        (6.61, 2.40),
        (6.61, 3.15),
        "Clave",
        color=COLOR_CW,
        linestyle="--",
        label_offset=(-0.38, 0.0),
    )
    _flecha(
        ax,
        (8.09, 3.15),
        (8.09, 2.40),
        "EMF (k)",
        color=COLOR_CW,
        linestyle="--",
        label_offset=(0.45, 0.0),
    )

    # Salidas de Workers a Columna 3 (Almacenamiento Políglota)
    _flecha(ax, (8.75, 4.30), (9.80, 4.75), "7. Staging", label_offset=(0.0, 0.24))
    _flecha(ax, (8.75, 3.75), (9.80, 3.20), "8. WORM", label_offset=(0.0, 0.22))
    _flecha(
        ax,
        (8.75, 3.35),
        (9.80, 1.65),
        "9. Transact",
        rad=0.08,
        label_offset=(-0.05, -0.32),
    )

    # Columna 3 a Columna 4
    _flecha(ax, (12.15, 4.82), (13.12, 4.82), "10. MERGE", label_offset=(0.0, 0.22))
    _flecha(ax, (12.15, 2.95), (13.12, 2.95), "Recibos", color="#475569", linestyle="--", label_offset=(0.0, 0.22))

    # Columna 4 a Analistas / Entes de control
    _flecha(ax, (15.65, 4.65), (14.88, 4.82), "11. SQL", label_offset=(0.0, 0.22))
    _flecha(ax, (15.65, 3.95), (14.88, 2.95), "Audita", color="#475569", linestyle="--", label_offset=(0.12, -0.25))

    out_path = SALIDA / "e02_arquitectura_simplificada.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor=COLOR_FONDO)
    fig.savefig(SALIDA / "aws_flujo.png", bbox_inches="tight", facecolor=COLOR_FONDO)
    plt.close(fig)
    return out_path


def generar_pipeline_worker_e02() -> Path:
    """Genera el diagrama de las 5 etapas internas del Worker de Adjudicación (`saom_core.py`)."""
    fig, ax = plt.subplots(figsize=(15.5, 5.2), dpi=300)
    ax.set_xlim(0, 15.5)
    ax.set_ylim(0, 5.2)
    ax.axis("off")
    fig.patch.set_facecolor(COLOR_FONDO)

    ax.text(
        7.75,
        4.85,
        "Lógica Interna del Worker de Adjudicación (Procesamiento Determinista por Solicitud)",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=COLOR_NAVY,
    )
    ax.text(
        7.75,
        4.48,
        "Ejecutado en memoria sobre cada bloque de 5.000 solicitudes leído por rango de bytes desde saom-raw",
        ha="center",
        va="center",
        fontsize=9.5,
        color=COLOR_TEXTO_SUB,
    )

    etapas = [
        (
            0.35,
            "Etapa 1 · RF-01",
            "Lectura y Validación\nEstructural CSV",
            "• Verifica 6 columnas\n• Valor > 0.00 (Decimal)\n• Si falla: aísla fila como\n  REJECTED_SYNTAX en\n  rechazos/ sin abortar chunk",
            "#1E40AF",
        ),
        (
            3.35,
            "Etapa 2 · RF-02 / RNF-05",
            "Pseudonimización\nIn-Situ y Token HMAC",
            "• patient_token =\n  HMAC-SHA256(K, DNO||SS)\n• Reemplaza Paciente, DNO y\n  SS con '#' conservando la\n  longitud exacta (235 chars)",
            "#0F766E",
        ),
        (
            6.35,
            "Etapa 3 · RF-02 / RNF-02",
            "Extracción Clínica\ncon Spans Exactos",
            "• Extrae Edad, PerfilCobertura,\n  Servicio y Medicacion (|)\n• Registra [start_char, end_char]\n• Confianza = válidos / 7\n• Flag CLINICAL_UNCERTAINTY",
            "#6D28D9",
        ),
        (
            9.35,
            "Etapa 4 · RF-03 / RF-04",
            "Dictamen de Cobertura y\nLiquidación Decimal",
            "• Cruza COV-001..COV-020:\n  CUBRE vs NO_CUBRE\n• PRIORITARIO 100%, ESTANDAR\n  50%, COPAGO 25%, NO_CUBRE 0%\n• Decimal ROUND_HALF_UP",
            "#B45309",
        ),
        (
            12.35,
            "Etapa 5 · RF-05 / RNF-04",
            "Firma Criptográfica\ny Escritura Idempotente",
            "• JSON canónico ordenado\n• hash_decision = SHA-256\n• raiz_hash_chunk y lote\n• S3 determinista + DynamoDB\n  TransactWriteItems",
            "#BE123C",
        ),
    ]

    for idx, (x, sub, tit, det, col) in enumerate(etapas):
        _caja(
            ax,
            x,
            1.15,
            2.75,
            2.95,
            tit,
            sub,
            det,
            color_borde=col,
            color_franja=col,
            fontsize_titulo=9.6,
            fontsize_sub=8.2,
            fontsize_det=7.8,
        )
        if idx < len(etapas) - 1:
            _flecha(ax, (x + 2.75, 2.62), (etapas[idx + 1][0], 2.62), color=COLOR_NAVY)

    # Cinta inferior de garantías arquitectónicas
    _caja(
        ax,
        0.35,
        0.20,
        14.75,
        0.68,
        "Garantías transversales:   [RNF-05] Cero PII fuera de saom-raw     |     [RNF-04] Cero uso de float (100% Decimal)     |     [RNF-06] Idempotencia exacta ante reintentos de SQS",
        color_borde="#CBD5E1",
        color_fondo="#F1F5F9",
        color_texto=COLOR_NAVY,
        fontsize_titulo=8.8,
    )

    out_path = SALIDA / "e02_pipeline_worker.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor=COLOR_FONDO)
    plt.close(fig)
    return out_path


def actualizar_diagramas_c4() -> None:
    """Actualiza `c4_1_contexto.png`, `c4_2_contenedores.png` y `c4_3_componentes.png` con los datos COIL."""
    # C4 Nivel 1: Contexto
    fig, ax = plt.subplots(figsize=(14, 8), dpi=300)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis("off")
    fig.patch.set_facecolor(COLOR_FONDO)

    ax.text(
        7.0,
        7.65,
        "C4 Nivel 1 · Diagrama de Contexto del Sistema (SAOM · Sistema de Salud de Chernovia)",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=COLOR_NAVY,
    )

    actores = [
        (0.6, "Entidad Emisora (IPS)", "[Person · 10 instituciones]", "Radica lotes CSV por 7 canales\ny consulta estado del lote"),
        (3.9, "Auditor Médico", "[Person · Segunda línea]", "Revisa órdenes marcadas con\nAUDIT_FLAG_CLINICAL_UNCERTAINTY"),
        (7.2, "Analista del Pagador", "[Person · Finanzas]", "Consulta montos aprobados por\nentidad, canal y fecha [SQL]"),
        (10.5, "Ente de Control", "[Person · Auditoría externa]", "Verifica en 3 niveles hashes\nSHA-256 y recibos WORM"),
    ]
    for x, t, s, d in actores:
        _caja(ax, x, 5.55, 2.9, 1.55, t, s, d, color_borde=COLOR_C4_PERSON, color_fondo=COLOR_C4_PERSON, color_texto="#FFFFFF")

    _caja(
        ax,
        4.2,
        2.85,
        5.6,
        1.75,
        "SAOM · Sistema de Adjudicación de Órdenes Médicas",
        "[Software System · AWS Cloud]",
        "Valida lotes CSV, pseudonimiza PII (#), extrae entidades con spans,\ndictamina cobertura (COV-001..020), liquida (100/50/25/0%) y firma en WORM",
        color_borde=COLOR_C4_SYSTEM,
        color_fondo=COLOR_C4_SYSTEM,
        color_texto="#FFFFFF",
        fontsize_titulo=10.5,
    )

    externos = [
        (0.9, "Catálogo de Perfiles COIL", "[External System · CSV Oficial]", "PRIORITARIO (100%), ESTANDAR (50%),\nCOPAGO (25%), NO_CUBRE (0%)"),
        (5.2, "Catálogo de Servicios COIL", "[External System · COV-001..COV-020]", "20 servicios, rangos de valor y\nmedicaciones de referencia"),
        (9.5, "Tesorería del Pagador", "[External System · Giros]", "Recibe liquidaciones consolidadas\npara desembolso a las IPS"),
    ]
    for x, t, s, d in externos:
        _caja(ax, x, 0.45, 3.6, 1.45, t, s, d, color_borde=COLOR_C4_EXT, color_fondo=COLOR_C4_EXT, color_texto="#FFFFFF")

    _flecha(ax, (2.05, 5.55), (5.2, 4.60), "Radica CSV [HTTPS]", label_offset=(-0.4, 0.1))
    _flecha(ax, (5.35, 5.55), (6.3, 4.60), "Revisa flags", label_offset=(-0.3, 0.1))
    _flecha(ax, (8.65, 5.55), (7.7, 4.60), "Consulta [SQL]", label_offset=(0.3, 0.1))
    _flecha(ax, (11.95, 5.55), (8.8, 4.60), "Verifica SHA-256", label_offset=(0.4, 0.1))

    _flecha(ax, (5.5, 2.85), (2.7, 1.90), "Importa perfiles", label_offset=(-0.4, 0.05))
    _flecha(ax, (7.0, 2.85), (7.0, 1.90), "Importa COV-001..020", label_offset=(0.65, 0.0))
    _flecha(ax, (8.5, 2.85), (11.3, 1.90), "Entrega liquidación", label_offset=(0.4, 0.05))

    fig.savefig(SALIDA / "c4_1_contexto.png", bbox_inches="tight", facecolor=COLOR_FONDO)
    plt.close(fig)

    # C4 Nivel 2: Contenedores
    fig, ax = plt.subplots(figsize=(15, 8.5), dpi=300)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8.5)
    ax.axis("off")
    fig.patch.set_facecolor(COLOR_FONDO)

    ax.text(
        7.5,
        8.15,
        "C4 Nivel 2 · Diagrama de Contenedores (SAOM · AWS us-east-1)",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=COLOR_NAVY,
    )
    _cluster(ax, 0.4, 0.5, 14.2, 7.3, "Sistema SAOM · Chernovia [AWS us-east-1]", color_fondo="#F8FAFC")

    contenedores = [
        (0.8, 5.5, "Zona Raw (saom-raw)", "[Container: Amazon S3 · SSE-KMS]", "Almacena el CSV original con PII\n(COIL 1,2M / 12M órdenes)"),
        (4.3, 5.5, "Cola lotes-recibidos", "[Container: Amazon SQS]", "Recibe eventos ObjectCreated\ny desacopla la ingesta"),
        (7.8, 5.5, "Particionador CSV", "[Container: AWS Lambda Python]", "Valida cabecera de 6 columnas y\ngenera rangos de 5.000 filas"),
        (11.3, 5.5, "Cola chunks-adjudicacion", "[Container: Amazon SQS + DLQ]", "Reparte descriptores de bytes a\nworkers (maxReceiveCount=3)"),
        (4.3, 3.2, "Workers de Adjudicación", "[Container: AWS Lambda Arm64]", "Ejecuta validación, HMAC+#, spans,\ncobertura COV, Decimal y SHA-256"),
        (0.8, 3.2, "Referencias (saom-ref)", "[Container: Amazon S3 Versionado]", "Catálogos oficiales COIL:\nservicios y perfiles en caché"),
        (7.8, 3.2, "Control (control_lotes)", "[Container: DynamoDB On-Demand]", "Estado META y CHUNK# con\nidempotencia TransactWriteItems"),
        (11.3, 3.2, "Observabilidad", "[Container: CloudWatch EMF]", "Throughput k, rechazos y alarmas\nde DLQ sin datos personales"),
        (2.5, 0.9, "Zona Curated (saom-curated)", "[Container: S3 + Apache Iceberg]", "staging/, rechazos/ y tabla\nanalítica adjudicaciones"),
        (6.5, 0.9, "Zona Audit (saom-audit)", "[Container: S3 WORM / Versioning]", "Recibos firmados JSONL y\nmanifiesto del lote con raíz hash"),
        (10.5, 0.9, "Consolidador Analítico", "[Container: Athena + Glue Catalog]", "MERGE INTO adjudicaciones y\nconsultas SQL para el pagador"),
    ]
    for x, y, t, s, d in contenedores:
        _caja(ax, x, y, 3.0, 1.55, t, s, d, color_borde=COLOR_C4_SYSTEM, color_fondo=COLOR_C4_CONTAINER, color_texto="#FFFFFF", fontsize_titulo=9.5)

    _flecha(ax, (3.8, 6.27), (4.3, 6.27), "1. Evento")
    _flecha(ax, (7.3, 6.27), (7.8, 6.27), "2. Invoca")
    _flecha(ax, (10.8, 6.27), (11.3, 6.27), "3. Chunks")
    _flecha(ax, (12.8, 5.5), (7.3, 4.35), "4. Consume chunk", rad=-0.12, label_offset=(0.0, 0.25))
    _flecha(ax, (3.8, 3.97), (4.3, 3.97), "Catálogos")
    _flecha(ax, (7.3, 3.97), (7.8, 3.97), "5. TransactWrite")
    _flecha(ax, (9.3, 4.75), (11.3, 4.25), "Métricas EMF", linestyle="--")
    _flecha(ax, (5.2, 3.2), (4.0, 2.45), "6. Staging/Rechazos", label_offset=(-0.45, 0.0))
    _flecha(ax, (6.3, 3.2), (8.0, 2.45), "7. Recibos/Manifiesto", label_offset=(0.45, 0.0))
    _flecha(ax, (5.5, 1.67), (10.5, 1.67), "8. MERGE / SQL", rad=-0.18, label_offset=(0.0, -0.35))

    fig.savefig(SALIDA / "c4_2_contenedores.png", bbox_inches="tight", facecolor=COLOR_FONDO)
    plt.close(fig)

    # C4 Nivel 3: Componentes del Worker
    fig, ax = plt.subplots(figsize=(15.5, 6.5), dpi=300)
    ax.set_xlim(0, 15.5)
    ax.set_ylim(0, 6.5)
    ax.axis("off")
    fig.patch.set_facecolor(COLOR_FONDO)

    ax.text(
        7.75,
        6.15,
        "C4 Nivel 3 · Diagrama de Componentes del Worker de Adjudicación (saom_core.py + lambda_handlers.py)",
        ha="center",
        va="center",
        fontsize=12.5,
        fontweight="bold",
        color=COLOR_NAVY,
    )
    _cluster(ax, 0.4, 0.5, 14.7, 5.3, "Contenedor: Worker de Adjudicación [AWS Lambda Python 3.12 Arm64]", color_fondo="#F8FAFC")

    comps = [
        (0.7, 3.4, "1. LectorValidador", "[Component: csv + Decimal]", "Lee Range bytes de S3 y valida 6\ncolumnas; aísla REJECTED_SYNTAX"),
        (4.3, 3.4, "2. Pseudonimizador", "[Component: hmac + hashlib]", "Calcula patient_token HMAC-SHA256\ny enmascara PII con '#' (igual largo)"),
        (7.9, 3.4, "3. ExtractorClinico", "[Component: Parser determinista]", "Extrae Edad, Perfil, Servicio y\nMedicacion con spans [ini, fin]"),
        (11.5, 3.4, "4. ResolutorPerfil", "[Component: CatalogoCOIL]", "Cruza PRIORITARIO (100%), ESTANDAR\n(50%), COPAGO (25%) en memoria"),
        (0.7, 1.0, "5. MotorCobertura", "[Component: COV-001..COV-020]", "Dictamina CUBRE / NO_CUBRE y\nevalúa rango de valor y medicación"),
        (4.3, 1.0, "6. LiquidadorFinanciero", "[Component: Decimal ROUND_HALF_UP]", "Calcula valor_aprobado y\nvalor_copago sin usar float"),
        (7.9, 1.0, "7. GeneradorRecibo", "[Component: JSON canónico + SHA-256]", "Calcula hash_decision, raiz_hash_chunk\ny raiz_hash_lote"),
        (11.5, 1.0, "8. EscritorIdempotente", "[Component: boto3 S3 + DynamoDB]", "Escribe en curated/audit y ejecuta\nTransactWriteItems condicional"),
    ]
    for x, y, t, s, d in comps:
        _caja(ax, x, y, 3.1, 1.65, t, s, d, color_borde="#0284C7", color_fondo=COLOR_C4_COMPONENT, color_texto="#0F172A", fontsize_titulo=9.5)

    _flecha(ax, (3.8, 4.22), (4.3, 4.22))
    _flecha(ax, (7.4, 4.22), (7.9, 4.22))
    _flecha(ax, (11.0, 4.22), (11.5, 4.22))
    _flecha(ax, (13.05, 3.4), (2.25, 2.65), "Orden con perfil y spans", rad=-0.08, label_offset=(0.0, 0.18))
    _flecha(ax, (3.8, 1.82), (4.3, 1.82))
    _flecha(ax, (7.4, 1.82), (7.9, 1.82))
    _flecha(ax, (11.0, 1.82), (11.5, 1.82))

    fig.savefig(SALIDA / "c4_3_componentes.png", bbox_inches="tight", facecolor=COLOR_FONDO)
    plt.close(fig)


if __name__ == "__main__":
    p1 = generar_arquitectura_simplificada_e02()
    p2 = generar_pipeline_worker_e02()
    actualizar_diagramas_c4()
    print("Diagramas generados exitosamente:", p1, p2)
