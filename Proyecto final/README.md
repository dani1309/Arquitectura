# SAOM · Adjudicación masiva de órdenes médicas en AWS (Proyecto COIL)

Proyecto final de Arquitecturas de Nube y Big Data. El reto es procesar 12 M de órdenes médicas en AWS en menos de 24 h, emitir un dictamen `CUBRE` / `NO_CUBRE` por orden y liquidar al 100 / 50 / 25 % según `PerfilCobertura`, con trazabilidad verificable de cada decisión. El enunciado está en [docs/enunciado/TrabajoFinal.pdf](docs/enunciado/TrabajoFinal.pdf).

El equipo está conformado por Naomi Chow, Daniel Lopez y María Fernanda Toro.

El trabajo sigue AI-DLC en 6 pasos. La configuración del método está en [AGENTS.md](AGENTS.md) y [aidlc/](aidlc/).

## Estructura

```
Proyecto final/
├── README.md                     # Este archivo
├── AGENTS.md                     # Convenciones AI-DLC
├── aidlc.settings.json
├── aidlc/                        # Memoria y reglas AI-DLC (org, team, project, fases)
├── data/
│   └── ref/                      # Catálogos oficiales COIL (versionados)
│       ├── COIL_catalogo_perfiles_cobertura.csv
│       ├── COIL_catalogo_servicios_cubiertos.csv
│       └── COIL_diccionario_datos.md
├── docs/
│   ├── enunciado/                # TrabajoFinal.pdf
│   ├── inception/                # Paso 2 · Requisitos (RF BDD, RNF, ADR-001..003)
│   ├── design/                   # Paso 3 · Arquitectura (C4, flujo AWS, diagramas E02, ADR-004..005, modelo de costo)
│   ├── plan/                     # Paso 4 · Plan de construcción y correcciones E01
│   │   ├── 04_plan_construccion.md
│   │   └── correcciones_E01.md
│   ├── verificacion/             # Paso 6 · Evidencia de verificación en AWS y métricas F1 / M/M/c
│   │   ├── R01_verificacion_learner_lab.md
│   │   ├── T3_T4_T6_ejecucion_real_aws.md
│   │   ├── T5_informe_metricas_f1_mmc_costo.md
│   │   ├── T5a_protocolo_etiquetado_y_spans.md
│   │   └── resultados_aws_t3_t4_t6.json
│   └── bitacora/                 # Registro de sesiones COIL y decisiones (D-01 a D-27)
│       └── bitacora_decisiones.md
├── prototype/                    # Paso 5 · Núcleo funcional Python, handlers AWS Lambda, CLI y 36 tests
│   ├── saom_core.py
│   ├── lambda_handlers.py
│   ├── aws_learner_lab.py
│   ├── ejecutar_pruebas_aws_t3_t4_t6.py
│   ├── evaluacion_f1_t5.py
│   ├── test_bdd_rf01_rf05.py
│   ├── test_lambda_t3.py
│   └── test_evaluacion_f1_t5.py
└── entregables/
    ├── E01/                      # Entregable_01_Propuesta_Arquitectura_Salud_COIL_v2.docx (52 citas verificadas)
    ├── E02/                      # Entregable_02_Diseno_Tecnico_Salud_COIL.docx + .md
    ├── E03/                      # Entregable_03_Prototipo_Evidencia_Salud_COIL.docx + .md
    └── E04/                      # Consolidado (.docx), Presentación Ejecutiva (.pptx), Guion Pitch (.docx) y Guía Demo (.docx)
```

El dataset `COIL_dataset_glosas_salud_1_2M.csv` (~360 MB) y la muestra de 600 glosas de `T5a` no se versionan: `.gitignore` los excluye en cualquier ruta. Cada integrante los mantiene fuera de git y su SHA-256 está en la [bitácora](docs/bitacora/bitacora_decisiones.md).

## Estado de los 6 pasos AI-DLC

| Paso | Estado | Dónde |
|------|--------|-------|
| 1. Problema | **Completado** (E01 v2 con 52 referencias citadas y precios oficiales verificados) | [E01 v2](entregables/E01/Entregable_01_Propuesta_Arquitectura_Salud_COIL_v2.docx) |
| 2. Requisitos | **Completado** (`RF-01..05` en Gherkin + `RNF-01..06` + `ADR-001..003`) | [docs/inception/](docs/inception/) |
| 3. Arquitectura | **Completado** (C4 Niveles 1–3, diagramas simplificados E02, `ADR-004..005`, modelo $M/M/c$) | [docs/design/03_arquitectura_tecnica.md](docs/design/03_arquitectura_tecnica.md) y [E02](entregables/E02/Entregable_02_Diseno_Tecnico_Salud_COIL.docx) |
| 4. Plan | **Completado** (`T0..T8` asignadas y cerradas, contradicciones `P-01..P-17` resueltas) | [docs/plan/04_plan_construccion.md](docs/plan/04_plan_construccion.md) |
| 5. Implementación | **Completado** (Núcleo `saom_core.py`, handlers Lambda `arm64`, despliegue `LabRole` en cuenta `329771219583`) | [prototype/](prototype/) |
| 6. Verificación | **Completado** (`36/36` tests en `pytest`, corrida real de `1.200.000` órdenes en `47,50 s`, `Macro-F1 = 0,9886`, Iceberg + Athena `1.200.000` filas, `0,0189 USD`) | [docs/verificacion/](docs/verificacion/) |

## Estado de los 4 entregables

Cada entregable vale el 25 % del curso. Las descripciones son las del enunciado. `docs/inception/`, `docs/design/`, `prototype/` y `docs/verificacion/` respaldan los cuatro paquetes en `entregables/`.

| Entregable | Descripción (enunciado) | Producto | Dónde | Estado |
|------------|-------------------------|----------|-------|--------|
| E01 · Documento de propuesta | Problema, estado del arte, objetivos, metodología y análisis económico | Formato Word editable (`.docx`) | [entregables/E01/](entregables/E01/) | **Completado** (`v2` con citas `[1]..[52]` y precios AWS verificados) |
| E02 · Diseño técnico | Arquitectura distribuida, flujo de datos, lógica y estrategia de costo | Diagramas simplificados + justificación (`.docx` y `.md`) | [entregables/E02/](entregables/E02/) y [docs/design/](docs/design/) | **Completado** |
| E03 · Implementación | Prototipo funcional en AWS, pruebas, evidencia y alcance implementado | Código, corrida real 1,2M en AWS y resultados (`.docx` y `.md`) | [entregables/E03/](entregables/E03/), [prototype/](prototype/) y [docs/verificacion/](docs/verificacion/) | **Completado** |
| E04 · Presentación final | Documento consolidado y defensa ejecutiva ante comité evaluador | Presentación 6 diapositivas (`.pptx`), Documento Consolidado, Guion Video 3–4 min y Guía Demo (`.docx` y `.md`) | [entregables/E04/](entregables/E04/) | **Completado** |
