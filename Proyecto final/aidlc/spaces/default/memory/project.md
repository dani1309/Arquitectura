<!-- AI-DLC keeps this copy in step with aidlc/spaces/default/memory/project.md. Edit that file; this copy is replaced. -->
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

<!-- Project-specific specialisation. -->

## Walking Skeleton

<!-- Project-specific specialisation. -->

## Testing Posture

<!-- Project-specific specialisation. -->

## Guard Policy

<!-- Project-specific. Mode: strict, relaxed, or off. -->

## Deployment

<!-- Project-specific specialisation. -->

## Code Style

<!-- Project-specific specialisation. -->

## Tech Stack

- Cloud: AWS (AWS Academy Learner Lab compatible, presupuesto $50 USD, rol `LabRole`)
- Ingesta & Almacenamiento: Amazon S3 (`saom-raw`, `saom-ref`, `saom-curated`, `saom-audit`), Amazon SQS (`lotes-recibidos`, `chunks-adjudicacion` + DLQ)
- Cómputo Distribuido: AWS Lambda (arquitectura Arm, imagen de contenedor) procesando chunks de 5.000 solicitudes
- Analítica & Control: Apache Iceberg en S3 + AWS Glue Data Catalog + Amazon Athena (`MERGE INTO` cada 15 min) + Amazon DynamoDB on-demand (`control_lotes`)
- NLP & Extracción Clínica: Extractor de entidades sobre la glosa COIL (`Edad`, `PerfilCobertura`, `ServicioSolicitado`, `Medicacion`) con preservación de spans `[start_char, end_char]`
- Trazabilidad & Criptografía: `HMAC-SHA256` con clave secreta para `patient_token`, enmascaramiento de longitud fija (`#`) y `SHA-256` sobre JSON canónico para `hash_decision`, `raiz_hash_chunk` y `raiz_hash_lote`

## Decided

- DECIDED: ADR-001 Arquitectura Híbrida Desacoplada (Ingesta continua a S3/SQS + Procesamiento por chunks de 5.000 órdenes) (Stage Inception, 2026-10-21)
- DECIDED: ADR-002 Pseudonimización obligatoria de PII (`DNO` y `SeguroSocial`) con `HMAC-SHA256(clave_secreta, ...)`, enmascaramiento `#` preservando longitud y firma `SHA-256` sobre JSON canónico (Stage Inception, 2026-10-27)
- DECIDED: ADR-003 Prototipo en AWS Learner Lab ($50 USD) validado con el dataset oficial `COIL_dataset_glosas_salud_1_2M.csv` (1.200.000 órdenes, escala 1:10) y extrapolación M/M/c hacia 12M órdenes (Stage Inception, 2026-10-27)
- DECIDED: ADR-004 Cómputo de workers en AWS Lambda (Arm, imagen de contenedor portable a ECS Fargate Spot) (Stage Construction, 2026-10-27)
- DECIDED: ADR-005 Almacenamiento políglota: DynamoDB (`control_lotes`), Apache Iceberg en S3 + Athena (`adjudicaciones`) y S3 WORM (`saom-audit`) (Stage Construction, 2026-10-27)
- DECIDED: Esquema y reglas alineados al Dataset Oficial COIL del Sistema de Salud de Chernovia (`PRIORITARIO` 100%, `ESTANDAR` 50%, `COPAGO` 25%, `NO_CUBRE` 0%, catálogo `COV-001` a `COV-020`) (Stage Construction, 2026-10-27)

## Scope Overrides

- Inception y Diseño Técnico cubren especificación BDD, matriz RNF, modelo matemático M/M/c y ADRs 001 a 005 alineados al dataset oficial COIL de 1,2M de solicitudes.

## Forbidden

- NEVER almacenar `Paciente`, `DNO` o `SeguroSocial` en texto claro en `saom-curated`, `saom-audit`, DynamoDB o logs de CloudWatch (affirmed 2026-10-27)
- NEVER aprovisionar recursos con costo fijo por hora que pongan en riesgo el límite de $50 USD del AWS Learner Lab (affirmed 2026-10-27)
- NEVER usar `float` para el cálculo de `valor_aprobado`; usar siempre `Decimal` con dos decimales y `ROUND_HALF_UP` (affirmed 2026-10-27)
- NEVER emitir una adjudicación financiera sin registrar `catalogo_version`, `modelo_version`, `regla_ids`, `spans` y `hash_decision` (affirmed 2026-10-27)

## Mandated

- ALWAYS reemplazar carácter por carácter con `#` los valores de `Paciente`, `DNO` y `SeguroSocial` para mantener intactos los desplazamientos `[start_char, end_char]` (affirmed 2026-10-27)
- ALWAYS calcular `hash_decision` con `SHA-256` sobre JSON canónico (llaves ordenadas, sin espacios, UTF-8) (affirmed 2026-10-27)
- ALWAYS aislar filas malformadas como `REJECTED_SYNTAX` en `rechazos/` sin enviar el chunk sano a la DLQ (affirmed 2026-10-27)

## Corrections

<!-- Project-specific corrections from human feedback. -->
