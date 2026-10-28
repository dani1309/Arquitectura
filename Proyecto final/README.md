# SAOM · Adjudicación masiva de órdenes médicas en AWS (Proyecto COIL)

Proyecto final de Arquitecturas de Nube y Big Data. El reto es procesar 12 M de órdenes médicas en AWS en menos de 24 h, emitir un dictamen `CUBRE` / `NO_CUBRE` por orden y liquidar al 100 / 50 / 25 % según `PerfilCobertura`, con trazabilidad verificable de cada decisión. El enunciado está en [docs/enunciado/TrabajoFinal.pdf](docs/enunciado/TrabajoFinal.pdf).

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
│   ├── design/                   # Paso 3 · Arquitectura (C4, flujo AWS, ADR-004..005, modelo de costo)
│   ├── plan/                     # Paso 4 · Plan de construcción (vacío)
│   ├── verificacion/             # Paso 6 · Evidencia de verificación (vacío)
│   └── bitacora/                 # Registro de sesiones y decisiones (vacío)
└── entregables/
    ├── E01/                      # Entregable_01_Propuesta_Arquitectura_Salud_COIL.docx
    ├── E02/
    ├── E03/
    └── E04/
```

El dataset `COIL_dataset_glosas_salud_1_2M.csv` (~360 MB) no se versiona: `.gitignore` lo excluye en cualquier ruta. Pendiente: el equipo confirmará de dónde se obtiene.

## Estado de los 6 pasos AI-DLC

| Paso | Estado | Dónde |
|------|--------|-------|
| 1. Problema | Documentado en E01, secciones 1 (Planteamiento del Problema) y 2 (Objetivos del Proyecto) | [E01](entregables/E01/Entregable_01_Propuesta_Arquitectura_Salud_COIL.docx) |
| 2. Requisitos | Documentado | [docs/inception/](docs/inception/) |
| 3. Arquitectura | Documentado | [docs/design/03_arquitectura_tecnica.md](docs/design/03_arquitectura_tecnica.md) |
| 4. Plan | Pendiente | [docs/plan/](docs/plan/) |
| 5. Implementación | Pendiente. El prototipo anterior se retiró a propósito en `a6bf93b` | — |
| 6. Verificación | Pendiente | [docs/verificacion/](docs/verificacion/) |

## Estado de los 4 entregables

Cada entregable vale el 25 % del curso. Las descripciones son las del enunciado. `docs/inception/` y `docs/design/` son el soporte técnico de E01 y E02.

| Entregable | Descripción (enunciado) | Producto | Dónde | Estado |
|------------|-------------------------|----------|-------|--------|
| E01 · Documento de propuesta | Problema, estado del arte, objetivos, metodología y análisis económico | Formato Word editable | [entregables/E01/](entregables/E01/) | Documento en el repo. Entrega: pendiente |
| E02 · Diseño técnico | Arquitectura distribuida, flujo de datos, lógica y estrategia de costo | Diagrama + justificación | [docs/design/](docs/design/) | Documento en el repo. Entrega: pendiente |
| E03 · Implementación | Prototipo funcional en AWS, pruebas, evidencia y alcance implementado | Código y resultados | [entregables/E03/](entregables/E03/) | Pendiente |
| E04 · Presentación final | Documento consolidado y defensa ejecutiva ante comité evaluador | Pitch + defensa oral | [entregables/E04/](entregables/E04/) | Pendiente |

Fechas de entrega: pendientes, el enunciado no las indica.
