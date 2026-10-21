# Project-Level Rules

> Project-specific specialisation and corrections. Loaded after `org.md` and
> `team.md` as strict-additive guidance; contradictions with broader policy
> are rejected. Populated by practices-discovery and the self-learning loop.
>
> Use sparingly: most teams don't need a project layer. Reach for it
> only when this specific project needs stable, durable guidance beyond the
> team practice (for example, package-specific release checks or an additional
> regression suite for a legacy component).

## Way of Working

<!-- Project-specific specialisation. Example: -->
<!-- This monorepo requires package-scoped branch names and a package owner -->
<!-- review in addition to the team's normal merge policy. -->

## Walking Skeleton

<!-- Project-specific specialisation. Example: -->
<!-- The walking skeleton must exercise the legacy service adapter as well -->
<!-- as the new service boundary. -->

## Testing Posture

<!-- Project-specific specialisation. -->

## Guard Policy

<!-- Project-specific. Mode: strict, relaxed, or off. Strict here holds for every intent, whatever one person asks in chat; relaxed or off here applies to every intent whose policy came from its scope, unless the person sets another; changing this line changes it. A section under the retired Change Control heading, written by an earlier release, is still read. -->

## Deployment

<!-- Project-specific specialisation. -->

## Code Style

<!-- Project-specific specialisation. -->

## Tech Stack

- Cloud: AWS (AWS Academy Learner Lab compatible)
- Ingesta & Almacenamiento: Amazon S3 (Data Lake con prefijos raw/processed/adjudicated), Amazon SQS / EventBridge
- Cómputo Distribuido & Batch: PySpark / AWS Glue / ECS Fargate / Python multithreaded workers
- NLP & Extracción Clínica: Modelos NER optimizados (spaCy / HuggingFace Transformers en ONNX / quantizados en CPU)
- Formato de Datos & Particionamiento: Apache Parquet / Columnar con compresión Snappy
- Trazabilidad & Criptografía: HMAC-SHA256 para anonimización de DNO, SHA-256 para firma inmutable de adjudicación

## Decided

- DECIDED: ADR-001 Arquitectura Híbrida Desacoplada (Ingesta continua a S3/SQS + Procesamiento por lotes/micro-batch) (Stage Inception, 2026-10-21)
- DECIDED: ADR-002 Anonimización obligatoria de PII (DNO/NSS) con HMAC-SHA256 y persistencia de spans de texto clínicos para trazabilidad inmutable (Stage Inception, 2026-10-21)
- DECIDED: ADR-003 Prototipo MVP en AWS Learner Lab validado con dataset sintético de 100k-1M registros y modelo formal de extrapolación hacia 12M órdenes (Stage Inception, 2026-10-21)
- DECIDED: Unidad de medida unificada a "Orden médica / Cuenta médica" auditada (Stage Inception, 2026-10-21)
- DECIDED: Liquidación escalonada según Perfil de Usuario categorizado en A (100%), B (50%), C (25%) y Excluido/No asegurado (0%) (Stage Inception, 2026-10-21)
- DECIDED: F1-score >= 0.92 y reducción de costos >= 70% fijados como metas técnicas del equipo evaluadas contra ground-truth sintético (Stage Inception, 2026-10-21)

## Scope Overrides

- Inception abarca especificación BDD, matriz de RNF cuantificable y primeros 3 ADRs.

## Forbidden

- NEVER almacenar DNO, NSS o nombres de pacientes en texto claro en logs de CloudWatch o tablas analíticas no restringidas (affirmed 2026-10-21)
- NEVER aprovisionar clústeres no controlados o instancias costosas que superen el saldo de $100 USD del AWS Learner Lab (affirmed 2026-10-21)
- NEVER emitir una adjudicación financiera sin registrar la versión de catálogo y la regla normativa que la sustenta (affirmed 2026-10-21)

## Mandated

- ALWAYS registrar los caracteres de inicio y fin (spans) de la glosa médica que fundamentan la extracción clínica (affirmed 2026-10-21)
- ALWAYS calcular el hash SHA-256 de la decisión para garantizar inmutabilidad y verificabilidad (affirmed 2026-10-21)
- ALWAYS documentar las pruebas de aceptación en formato BDD (Given/When/Then) (affirmed 2026-10-21)

## Corrections

<!-- Project-specific corrections from human feedback. -->
<!-- Format: NEVER/ALWAYS [behavior] (learned [date]) -->
