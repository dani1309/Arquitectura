"""Actualiza `Entregable_01_Propuesta_Arquitectura_Salud_COIL_v2.docx` con la verificación de:
1. Fuente `[10]` (ADRES Colombia): separa el contexto de giro directo/auditoría [10] de la meta de 3h (1.111 órd/s) del equipo.
2. Fuente `[16]` (Khan, SparkRules): retira la atribución de '12 millones de órdenes' a [16] en la Tabla 4 (sección 3.5) y precisa su alcance.
3. Precios oficiales de Amazon Comprehend Medical `[24]`: incorpora la URL oficial de precios de AWS (`https://aws.amazon.com/comprehend/medical/pricing/`) y detalla tanto el costo escalonado por tramos AWS (`244.500 USD/día`: `241.500 USD` Comprehend Medical + `3.000 USD` Step Functions para 36M unidades) como el cálculo plano en Tier 1 (`381.000 USD/día`).
4. Cita en el cuerpo las 11 referencias `[7], [9], [18], [27], [31], [36], [38], [40], [42], [46], [50]` que estaban en la bibliografía sin cita en el texto.
"""
from __future__ import annotations

import re
from pathlib import Path
import docx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCX_V2_PATH = PROJECT_ROOT / "entregables" / "E01" / "Entregable_01_Propuesta_Arquitectura_Salud_COIL_v2.docx"


def actualizar_docx_v2(path: Path = DOCX_V2_PATH) -> None:
    doc = docx.Document(str(path))

    # 1. P18: Verificar y separar cita [10] (ADRES) de la meta de 3 horas (1.111 órd/s) del equipo
    doc.paragraphs[18].text = (
        "Rendimiento en ventana batch (3 horas): Para conciliar los lotes antes de los cierres contables, "
        "reintentos e integración con los sistemas financieros de giro directo y auditoría automatizada de "
        "cuentas médicas [10], [18], [38], el equipo define como meta propia de diseño acotar la ventana "
        "nocturna de procesamiento por lotes (batch) a 3 horas operativas (frente al máximo de 24 horas del "
        "enunciado), lo que exige sostener un caudal efectivo de 1.111 órdenes/segundo "
        "((12.000.000 / 10.800 s) ≈ 1.111,11 órdenes/s)."
    )

    # 2. P13, P44, P45, P46, P81, P86, P92, P93: Vincular entradas bibliográficas sin cita y precisar [16]
    doc.paragraphs[13].text = (
        "La modernización de los sistemas públicos de aseguramiento y pago en salud enfrenta un cuello de "
        "botella crítico cuando el volumen transaccional exige conciliar millones de prestaciones diarias "
        "contra marcos normativos complejos y evidencia clínica no estructurada [1]. Entidades gubernamentales "
        "como la Administradora de los Recursos del Sistema General de Seguridad Social en Salud (ADRES) en "
        "Colombia, el Fondo Nacional de Salud (Fonasa) en Chile, el Departamento de Informática del Sistema "
        "Único de Salud (DATASUS) en Brasil [7], la NHS Business Services Authority (NHSBSA) en el Reino Unido "
        "[31] y los Centers for Medicare & Medicaid Services (CMS) en los Estados Unidos operan bajo la presión "
        "simultánea de acelerar el flujo de caja hacia clínicas y hospitales mientras contienen el fraude, el "
        "desperdicio y el abuso (Fraud, Waste, and Abuse - FWA) [2]. Tan solo en el programa Medicare de los "
        "Estados Unidos, con un gasto anual superior a los 903.000 millones de dólares, las pérdidas por fraude "
        "e improcedencias se estiman en un 10 % del presupuesto, habiendo recuperado el gobierno federal más de "
        "1.800 millones de dólares anuales mediante litigios, analítica bayesiana y auditorías retrospectivas [8], [9]."
    )

    doc.paragraphs[44].text = (
        "Determinar qué paradigma de cómputo distribuido en AWS (Batch con Apache Spark en EMR Graviton2 [27] o "
        "Glue frente a Serverless dirigido por eventos con Step Functions [46] y a la ruta híbrida por chunks) "
        "maximiza la relación rendimiento-costo para procesar 12 millones de órdenes médicas en ventanas fijas "
        "menores a 24 horas (139 órdenes/s continuo del enunciado o 1.111 órdenes/s en ventana batch de 3 horas, "
        "meta del equipo) [11]."
    )

    doc.paragraphs[45].text = (
        "Caracterizar la arquitectura operativa y las limitaciones económicas de los grandes pagadores públicos "
        "(CMS [40], NHSBSA [31], DATASUS [7], Fonasa [6], ADRES [18], [38]) y clearinghouses privados "
        "(Optum/Change Healthcare, Cognizant TriZetto) [3]."
    )

    doc.paragraphs[46].text = (
        "Identificar las técnicas de procesamiento distribuido de lenguaje natural (NLP) [22], [36] y evaluación "
        "de reglas de negocio (algoritmos ReteOO/Phreak y motores distribuidos) [16], [42] que alcanzan un "
        "F1-score ≥ 0,92 (meta del equipo) y preservan la trazabilidad determinista sin incurrir en costos "
        "prohibitivos de inferencia [50]."
    )

    doc.paragraphs[81].text = (
        "Evaluación distribuida de reglas: Motores como SparkRules y variantes distribuidas del algoritmo "
        "ReteOO/Phreak de Drools [42] evalúan tablas de decisión DMN 1.3 y reglas DRL directamente sobre "
        "DataFrames de Spark, emitiendo códigos de razón auditables (adverse action / reason codes) a "
        "velocidades de 15.000 reglas/s por motor con latencias < 10 ms [16], [33]."
    )

    doc.paragraphs[82].text = (
        "Persistencia ACID y Time Travel: Apache Iceberg sobre Amazon S3 proporciona transacciones ACID "
        "completas, aislamiento de instantáneas (snapshot isolation), vistas materializadas sobre anotaciones "
        "clínicas y viaje en el tiempo, cumpliendo los estándares HIPAA, GDPR y SOX sin bloqueo de proveedor "
        "(vendor lock-in) [14], [26], [45]."
    )

    doc.paragraphs[86].text = (
        "Los estudios empíricos de Kocaman, Ul Haq & Talby [22], [25], [36] y Seastedt et al. [35] confirman que "
        "la combinación de arquitecturas BiLSTM-CNN-Char y modelos BioBERT/BioELECTRA con adaptadores LoRA "
        "(Low-Rank Adaptation, que actualizan < 1 % de los parámetros totales —~ 3 millones frente a > 110 "
        "millones— acelerando la inferencia entre 2× y 3× [48]) supera el umbral de F1-score ≥ 0,92 (meta del "
        "equipo) en entidades de texto clínico libre. La tabla siguiente es un antecedente, porque esas "
        "entidades no existen en la glosa COIL. El extractor del proyecto es un parser determinista sobre la "
        "plantilla fija, y RNF-02 mide el F1 sobre Edad, PerfilCobertura, ServicioSolicitado y Medicacion."
    )

    doc.paragraphs[92].text = (
        "Brecha de Explicabilidad y Trazabilidad Contable en Inteligencia Artificial: Dictaminar que una orden "
        "médica No cubre o que se liquida parcialmente al 50 % o 25 % basándose en la salida opaca de una red "
        "neuronal o de un LLM generativo resulta jurídicamente indefendible ante recursos administrativos de "
        "clínicas y hospitales o auditorías de contralorías fiscales [14], [50]. El mercado comercial carece de "
        "soluciones integradas que combinen la extracción de alta sensibilidad (F1-score ≥ 0,92 como meta del "
        "equipo, conservando los índices exactos de caracteres char_begin y char_end) con reglas deterministas "
        "sobre catálogos versionados (catalogo_version), capaces de registrar regla_ids, spans y un hash_decision "
        "verificable sobre JSON canónico y de persistir todo el linaje sobre tablas versionadas [13]."
    )

    # 3. P73 y P90: Precios oficiales de Amazon Comprehend Medical [24] (escalonado por tramos vs tarifa plana Tier 1)
    doc.paragraphs[73].text = (
        "Inviabilidad de APIs Cognitivas por Caracteres: Según la tabla oficial de precios de AWS, Amazon "
        "Comprehend Medical factura en unidades de 100 caracteres (con un mínimo facturable de 300 caracteres o "
        "3 unidades por solicitud), cobrando en el tramo base (Tier 1, primeros 10M de unidades/mes) 0,01 USD "
        "por unidad en DetectEntitiesV2, 0,0025 USD en InferSNOMEDCT, 0,0014 USD en DetectPHI, 0,0005 USD en "
        "InferICD10CM y 0,0005 USD en InferRxNorm, y reduciendo en el tramo 2 (10M a 100M de unidades/mes) a "
        "0,005 USD en DetectEntitiesV2 y 0,00025 USD en InferRxNorm [24]. Con glosas COIL de unos 213 caracteres "
        "(facturadas al mínimo de 3 unidades por llamada = 36 millones de unidades para 12 millones de órdenes), "
        "el escenario orden por orden de la opción A de la sección 5.1 genera una factura diaria prohibitiva de "
        "244.500 USD aplicando los tramos oficiales de volumen (241.500 USD de Comprehend Medical + 3.000 USD de "
        "Step Functions) o de 381.000 USD a tarifa plana de Tier 1 [24], además de una limitación técnica "
        "excluyente: solo procesa textos en inglés, siendo incapaz de analizar glosas en español o portugués de "
        "forma nativa [52]."
    )

    doc.paragraphs[90].text = (
        "Brecha de Escala Económica en el Procesamiento de Texto Clínico: Existe una desconexión severa entre "
        "los motores transaccionales tradicionales (TriZetto Facets, QNXT, mainframes COBOL [40]) —que carecen "
        "de capacidades nativas para interpretar texto libre— y las APIs gestionadas de NLP en la nube (Amazon "
        "Comprehend Medical), cuyo esquema de tarificación por bloques de 100 caracteres (con mínimo de 300 "
        "caracteres por documento) fue concebido para cargas departamentales y resulta financieramente inviable "
        "a escala nacional [3], [24]. Procesar 12 millones de órdenes médicas diarias en una API comercial por "
        "caracteres, con glosas de unos 213 caracteres (36M de unidades), demandaría 244.500 USD por día con "
        "tarifa escalonada oficial (o 381.000 USD por día a tarifa plana Tier 1, opción A de la sección 5.1), "
        "mientras que el diseño elegido, con extracción en workers AWS Lambda por chunks de 5.000 órdenes y sin "
        "cobro por carácter, cuesta 3,02 USD diarios (0,25 USD por millón de órdenes). Como antecedente, Spark "
        "NLP mejora en un +13 % la precisión clínica (F1-score = 0,936 ≥ 0,92, meta del equipo) [22]."
    )

    # 4. Tabla 4 Fila 8 (Khan - SparkRules [16]): retirar atribución de 12 millones de órdenes a [16]
    t4_row8 = doc.tables[4].rows[8].cells
    t4_row8[2].text = (
        "Lotes masivos (batches) de registros distribuidos horizontalmente en particiones de clústeres Apache Spark [16]."
    )
    t4_row8[3].text = (
        "Paralelización de particiones en memoria sin estado compartido, aplicable para evaluar la meta del equipo (> 1.111 órdenes/s) [16]."
    )

    # 5. Tabla 8 Fila 1 (Opción A: Serverless + Comprehend Medical [24])
    t8_row1 = doc.tables[8].rows[1].cells
    t8_row1[1].text = (
        "AWS Step Functions Standard (10 pasos/orden = 120M transiciones a 25 USD/M) + AWS Lambda + Amazon "
        "Comprehend Medical (DetectEntitiesV2 + InferRxNorm, glosa de ~213 caracteres facturada al mínimo de "
        "300 caracteres = 3 unidades/glosa = 36M unidades) [24], [29], [46]."
    )
    t8_row1[3].text = (
        "244.500 USD/día con tramos oficiales AWS (3.000 USD Step Functions + 241.500 USD Comprehend Medical: "
        "10M u. × 0,0105 USD + 26M u. × 0,00525 USD) o 381.000 USD/día a tarifa plana Tier 1 [24]."
    )

    # 6. Referencia [24] (P145): URL oficial de precios de AWS Comprehend Medical
    doc.paragraphs[145].text = (
        '[24] Amazon Web Services (AWS), "Amazon Comprehend Medical Pricing (DetectEntitiesV2, InferRxNorm, '
        'InferICD10CM, InferSNOMEDCT, DetectPHI)," AWS Official Pricing Documentation, 2025–2026. [En línea]. '
        "Disponible en: https://aws.amazon.com/comprehend/medical/pricing/"
    )

    doc.save(str(path))
    print("Actualizado exitosamente:", path)


if __name__ == "__main__":
    actualizar_docx_v2()
