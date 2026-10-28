# SAOM · Adjudicación masiva de órdenes médicas en AWS (Proyecto COIL)

Proyecto final de Arquitecturas de Nube y Big Data. El reto es procesar 12 M de órdenes médicas en AWS en menos de 24 h, emitir un dictamen `CUBRE` / `NO_CUBRE` por orden y liquidar al 100 / 50 / 25 % según `PerfilCobertura`, con trazabilidad verificable de cada decisión.

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
│   ├── inception/                # Paso 2 · Requisitos (RF BDD, RNF, ADR-001..003)
│   ├── design/                   # Paso 3 · Arquitectura (C4, flujo AWS, ADR-004..005, modelo de costo)
│   ├── plan/                     # Paso 4 · Plan de construcción (vacío)
│   ├── verificacion/             # Paso 6 · Evidencia de verificación (vacío)
│   └── bitacora/                 # Registro de sesiones y decisiones (vacío)
└── entregables/
    ├── E01/
    ├── E02/
    ├── E03/
    └── E04/
```

El dataset `COIL_dataset_glosas_salud_1_2M.csv` (~360 MB) no se versiona: `.gitignore` lo excluye en cualquier ruta. Pendiente: definir dónde se guarda localmente y cómo se obtiene.

## Estado de los 6 pasos AI-DLC

| Paso | Estado | Dónde |
|------|--------|-------|
| 1. Problema | Pendiente: no hay un documento dedicado. El contexto aparece resumido en [docs/inception/README.md](docs/inception/README.md) | — |
| 2. Requisitos | Documentado | [docs/inception/](docs/inception/) |
| 3. Arquitectura | Documentado | [docs/design/03_arquitectura_tecnica.md](docs/design/03_arquitectura_tecnica.md) |
| 4. Plan | Pendiente | [docs/plan/](docs/plan/) |
| 5. Implementación | Pendiente. El prototipo anterior se retiró a propósito en `a6bf93b` | — |
| 6. Verificación | Pendiente | [docs/verificacion/](docs/verificacion/) |

## Estado de los 4 entregables

| Entregable | Contenido | Estado |
|------------|-----------|--------|
| E01 | Inception: requisitos funcionales y no funcionales, ADR-001..003 | Contenido en [docs/inception/](docs/inception/). Pendiente: confirmar si ya se entregó y qué se archiva en `entregables/E01/` |
| E02 | Diseño técnico: diagrama y justificación, ADR-004..005 | Contenido en [docs/design/](docs/design/). Pendiente: confirmar si ya se entregó y qué se archiva en `entregables/E02/` |
| E03 | Prototipo en AWS Academy Learner Lab con el dataset de 1,2 M (según [ADR-003](docs/inception/adrs/ADR-003-estrategia-mvp-lab-aws.md)) | Pendiente |
| E04 | Pendiente: no está definido en el repositorio | Pendiente |

Pendiente general: el enunciado (`docs/enunciado/TrabajoFinal.pdf`) no está en el repositorio. Hay que agregarlo para confirmar el alcance y las fechas de cada entregable.
