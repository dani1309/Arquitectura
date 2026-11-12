# Bitácora de Decisiones y Sesiones Colaborativas COIL

Registro trazable de las decisiones arquitectónicas y de las sesiones de coordinación colaborativa internacional (COIL) del equipo conformado por **Naomi Chow, Daniel Lopez y María Fernanda Toro**. La tabla de la sección 1 relaciona cada decisión con su commit en `git log`, su ADR o el informe de verificación correspondiente; la sección 2 documenta las sesiones de trabajo binacional/colaborativo siguiendo la estructura definida en la sección 4.2 del Entregable 01.

---

## 1. Decisiones Registradas

| Fecha | Decisión | ADR, Commit o Evidencia | Autor |
| :--- | :--- | :--- | :--- |
| 2026-10-21 | Arquitectura híbrida con ingesta continua a S3 y SQS y procesamiento por chunks de 5.000 órdenes | [ADR-001](../design/adr/ADR-001-patron-arquitectonico.md), agregado en `413b2e2` | Equipo de Arquitectura Proyecto COIL |
| 2026-10-21 | Pseudonimización con `HMAC-SHA256` y clave secreta, enmascaramiento con `#` que conserva la longitud y `hash_decision` sobre JSON canónico | [ADR-002](../design/adr/ADR-002-estrategia-trazabilidad-y-pii.md), agregado en `413b2e2` | Equipo de Arquitectura Proyecto COIL |
| 2026-10-21 | Prototipo serverless en el Learner Lab con el dataset de 1,2 M y extrapolación M/M/c a 12 M | [ADR-003](../design/adr/ADR-003-dimensionamiento-prototipo-vs-produccion.md), agregado en `413b2e2` | Equipo de Arquitectura Proyecto COIL |
| 2026-10-21 | Crédito del Learner Lab corregido de 100 USD a 50 USD en los RNF | `a24f8e7` | naochow |
| 2026-10-21 en el ADR, 2026-10-22 en git | Workers de adjudicación en AWS Lambda Arm con imagen de contenedor portable a ECS Fargate Spot | [ADR-004](../design/adr/ADR-004-motor-computo-workers.md), agregado en `148cf96` | Equipo |
| 2026-10-21 en el ADR, 2026-10-22 en git | Almacenamiento políglota con DynamoDB para control, Iceberg con Athena para analítica y bucket S3 WORM para evidencia | [ADR-005](../design/adr/ADR-005-almacenamiento-analitico-y-control.md), agregado en `148cf96` | Equipo |
| 2026-10-27 | Alinear requisitos, ADR-001 a ADR-005 y diseño al dataset oficial COIL de 1,2 M e incorporar los catálogos en `data/ref/` | `41218ad` | dani1309 |
| 2026-10-27 | Retirar el código del prototipo y `data/`, y conservar solo Inception y Diseño (entregables 1 y 2) | `a6bf93b` | dani1309 |
| 2026-10-28 | Mover `design/` a `Proyecto final/docs/design/` | `8a52800` | naochow |
| 2026-10-28 | Restaurar los catálogos COIL y el diccionario desde `41218ad`, sin restaurar el código del prototipo | `6773fcf` | naochow |
| 2026-10-28 | No versionar el dataset de 1,2 M ni los cursores locales de AI-DLC | `62cdc54` | naochow |
| 2026-10-28 | Crear carpetas para plan, verificación, bitácora y entregables E01 a E04 | `5b69fbc` | naochow |
| 2026-10-28 | Agregar el README con la estructura y el estado de pasos y entregables | `13e3570` | naochow |
| 2026-10-28 | Versionar el enunciado y el Entregable 01 | `bd9feac` | naochow |
| 2026-10-28 | Alinear los entregables y el paso 1 del README con el enunciado | `f18c57d` | naochow |
| 2026-10-28 | Ignorar `desktop.ini` de Windows | `e89eaf5` | naochow |
| 2026-10-28 | Integrar la reorganización en `main` | `b83909c`, merge del PR #1 | naochow |
| 2026-11-09 | Resolver `P-01` a `P-17` del plan. Los flags de valor y medicación no cambian el dictamen, el extractor es un parser determinista con confianza como dato, `valor_copago` es siempre la diferencia con `valor_aprobado`, el perfil inválido liquida 0 % con flag propio, la meta del laboratorio es 0,50 USD o menos por millón, el SLA de la corrida de 1,2 M es 2,4 h, el F1 se mide sobre 300 glosas etiquetadas más 300 perturbadas fuera de git, el prototipo consolida una vez al final sin Step Functions, las raíces usan concatenación ordenada de hashes con SHA-256 y T4b se descarta | [Plan de construcción, sección 7](../plan/04_plan_construccion.md) | Equipo |
| 2026-11-09 | `T0` queda cumplida. `COIL_dataset_glosas_salud_1_2M.csv`, fuera de git, tiene 1.200.000 filas más la cabecera de 6 columnas de RF-01, y su SHA-256 es `2c7631da66ffd2dc20c1f3aa17acc875b319601f0152c54ba7a36bc0716049c1` | [Plan de construcción, T0](../plan/04_plan_construccion.md) | naochow |
| 2026-11-10 | `T1` cumplida: se recupera el núcleo del prototipo (`prototype/saom_core.py`) y se completan los 27 tests BDD de `RF-01` a `RF-05`, además de generar la versión 2 corregida del Entregable 01 (`Entregable_01_Propuesta_Arquitectura_Salud_COIL_v2.docx`) | `0a85454` | naochow |
| 2026-11-11 | `T2` (empaquetado), `T3` (handlers Lambda y 6 tests locales), `T5a`/`T5` (muestra de 600 glosas fuera de git y evaluación F1 = 0,9886), verificación de citas `[10]`, `[16]` y precios oficiales AWS `[24]` en el E01 v2, y generación del Entregable 02 con diagramas simplificados | `b2a3f44` | dani1309 / Equipo |
| 2026-11-11 | `T2`, `T3`, `T4` y `T6` verificadas en vivo en AWS Academy Learner Lab (cuenta `329771219583`, `us-east-1`, `LabRole`): corrida completa de las `1.200.000` solicitudes (`240/240` chunks) en `47,50 s` con $k_{\text{AWS-E2E}} = 4.710,44\text{ órd/s/vCPU}$, costo real `0,0189 USD` (`0,0158 USD/M`), `0` PII y consolidación `MERGE INTO` sobre `1.200.000` filas en Apache Iceberg + Amazon Athena; incorporación de reintento con *exponential backoff* ante `TransactionConflict` en `META` | [T3_T4_T6_ejecucion_real_aws.md](../verificacion/T3_T4_T6_ejecucion_real_aws.md) y [R01_verificacion_learner_lab.md](../verificacion/R01_verificacion_learner_lab.md) | dani1309 / Equipo |

*Notas sobre las fechas*: ADR-001, ADR-002 y ADR-003 indican una actualización el 2026-10-27, que coincide con el commit `41218ad`. ADR-004 y ADR-005 también dicen "Actualizado 2026-10-27". `aidlc/spaces/default/memory/project.md` registra otras fechas para ADR-002, ADR-004 y ADR-005, y esa diferencia queda cerrada sin impacto como pregunta `P-11` en el [plan de construcción](../plan/04_plan_construccion.md).

---

## 2. Registro de Sesiones COIL entre Integrantes y Sedes

### Sesión 2026-10-21 — Fase Inception y Decisiones Arquitectónicas Base (ADR-001 a ADR-005)

| Campo | Valor |
| :--- | :--- |
| **Fecha y hora** | 2026-10-21 · 18:00–19:30 COT (UTC-5) |
| **Modalidad** | Síncrona (videollamada + trabajo colaborativo en repositorio GitHub) |
| **Participantes** | Naomi Chow, Daniel Lopez y María Fernanda Toro |
| **Agenda** | 1. Análisis de los requisitos del enunciado de licitación (12M de órdenes en < 24 h, clasificación de cobertura y cálculo 100 % / 50 % / 25 %).<br>2. Evaluación de alternativas arquitectónicas (Batch puro en EMR/Glue vs. Serverless orden por orden vs. Híbrido con micro-lotes de 5.000 órdenes).<br>3. Estrategia de privacidad (`HMAC-SHA256` + `#`), trazabilidad criptográfica y ajuste al presupuesto de 50 USD del Learner Lab. |
| **Acuerdos técnicos** | - Adoptar el patrón híbrido de ingesta desacoplada en S3 + SQS y procesamiento paralelo por chunks de 5.000 órdenes en AWS Lambda `arm64` (`1.769 MB` = 1 vCPU).<br>- Prohibir el uso de `float` en la liquidación financiera (`Decimal` con `ROUND_HALF_UP`).<br>- Enmascarar `Paciente`, `DNO` y `SeguroSocial` carácter por carácter con `#` antes de calcular los desplazamientos `[start_char, end_char]`. |
| **Decisiones con enlace a ADR o commit** | [ADR-001](../design/adr/ADR-001-patron-arquitectonico.md), [ADR-002](../design/adr/ADR-002-estrategia-trazabilidad-y-pii.md), [ADR-003](../design/adr/ADR-003-dimensionamiento-prototipo-vs-produccion.md), [ADR-004](../design/adr/ADR-004-motor-computo-workers.md) y [ADR-005](../design/adr/ADR-005-almacenamiento-analitico-y-control.md) (`413b2e2`, `a24f8e7`, `148cf96`). |
| **Discrepancias y cómo se resolvieron** | Existía la propuesta inicial de utilizar un clúster Apache Spark en Amazon EMR con Spark NLP. Al contrastar las restricciones del AWS Academy Learner Lab (crédito de 50 USD, límite de vCPU y bloqueo de roles IAM personalizados), se acordó por unanimidad migrar el motor de ejecución a **AWS Lambda Graviton2 (`arm64`) por chunks de 5.000 órdenes**, reduciendo el costo operativo proyectado de ~220 USD/día a **3,02 USD/día** para 12M de órdenes. |
| **Tareas asignadas** | - **Naomi Chow**: Redacción y ajuste de `RNF-01..06` y presupuesto de 50 USD.<br>- **Daniel Lopez**: Alineación con el diccionario de datos y catálogos COIL (`data/ref/`).<br>- **María Fernanda Toro**: Revisión de escenarios BDD (`RF-01..05`) y matriz de trazabilidad. |
| **Entregables revisados en forma cruzada** | `docs/inception/01_requisitos_funcionales_bdd.md`, `docs/inception/02_requisitos_no_funcionales.md` y `ADR-001` a `ADR-005`. |
| **Lecciones de la colaboración** | Documentar cada decisión en un ADR corto con contexto, alternativas descartadas y consecuencias evita retrabajos cuando el equipo trabaja de manera asíncrona sobre distintas ramas de git. |
| **Pendientes para la próxima sesión** | Auditar el documento del Entregable 01 frente a los ADR definitivos y estructurar el repositorio por pasos de AI-DLC. |

---

### Sesión 2026-10-28 — Estructuración del Repositorio AI-DLC y Auditoría Cruzada del E01

| Campo | Valor |
| :--- | :--- |
| **Fecha y hora** | 2026-10-28 · 17:00–18:30 COT (UTC-5) |
| **Modalidad** | Asíncrona coordinada mediante Pull Request (`PR #1`, merge `b83909c`) y sesión corta de cierre |
| **Participantes** | Naomi Chow, Daniel Lopez y María Fernanda Toro |
| **Agenda** | 1. Reorganización de carpetas (`docs/inception`, `docs/design`, `docs/plan`, `docs/verificacion`, `docs/bitacora`, `entregables/E01..E04`).<br>2. Configuración de `.gitignore` para impedir que el dataset de 1,2M (`360 MB`) o datos con PII sintética suban a GitHub.<br>3. Contraste punto por punto entre el E01 original y la arquitectura técnica real. |
| **Acuerdos técnicos** | - Mantener `COIL_dataset_glosas_salud_1_2M.csv` estrictamente fuera de git (`P-15`).<br>- Registrar todas las divergencias del E01 original en [`docs/plan/correcciones_E01.md`](../plan/correcciones_E01.md) para producir una versión `v2` consistente con los ADR y los catálogos de Chernovia. |
| **Decisiones con enlace a ADR o commit** | Commits `8a52800`, `6773fcf`, `62cdc54`, `5b69fbc`, `13e3570`, `bd9feac`, `f18c57d` y `b83909c`. |
| **Discrepancias y cómo se resolvieron** | El E01 original presentaba metas propias del equipo (`F1 >= 0,92`, ahorro `>= 70 %` y ventana batch de `3 horas` a `1.111 órdenes/s`) como si fueran exigencias literales del enunciado. Se resolvió separar explícitamente en tablas y texto las metas del enunciado (< 24 h, costo razonable, trazabilidad) de las metas internas de ingeniería del equipo. |
| **Tareas asignadas** | - **Naomi Chow**: Elaboración de `docs/plan/correcciones_E01.md` y `docs/plan/04_plan_construccion.md`.<br>- **Daniel Lopez**: Verificación de integridad del dataset oficial de 1,2M (`T0`).<br>- **María Fernanda Toro**: Especificación de casos borde para las preguntas `P-01` a `P-17`. |
| **Entregables revisados en forma cruzada** | `README.md`, `docs/plan/04_plan_construccion.md` y `docs/plan/correcciones_E01.md`. |
| **Lecciones de la colaboración** | La revisión cruzada entre quien redacta el estado del arte y quien diseña los contratos de código detectó a tiempo discrepancias de unidades y citas bibliográficas. |
| **Pendientes para la próxima sesión** | Cerrar las 17 preguntas abiertas (`P-01` a `P-17`), implementar el núcleo `saom_core.py` y su suite BDD (`T1`). |

---

### Sesión 2026-11-09 / 2026-11-10 — Resolución de Reglas Pendientes (`P-01..P-17`), Núcleo `T1` y E01 v2

| Campo | Valor |
| :--- | :--- |
| **Fecha y hora** | 2026-11-09 y 2026-11-10 · 19:00–21:00 COT (UTC-5) |
| **Modalidad** | Síncrona y asíncrona en repositorio (`0a85454`) |
| **Participantes** | Naomi Chow, Daniel Lopez y María Fernanda Toro |
| **Agenda** | 1. Cierre formal de las 17 preguntas de diseño (`P-01` a `P-17`).<br>2. Verificación del SHA-256 del dataset de 1.200.000 filas (`T0`).<br>3. Implementación de `prototype/saom_core.py` y ejecución de los 27 tests BDD (`T1`).<br>4. Generación de `Entregable_01_Propuesta_Arquitectura_Salud_COIL_v2.docx`. |
| **Acuerdos técnicos** | - `P-03`: Los flags `AUDIT_FLAG_VALOR_FUERA_RANGO_REF` y `AUDIT_FLAG_MEDICACION_NO_REFERENCIA` son informativos para auditoría y no cambian el dictamen `CUBRE`/`NO_CUBRE`.<br>- `P-04` y `P-17`: La confianza se registra como `campos_validos / 7`; si `PerfilCobertura` falta se marca `AUDIT_FLAG_CLINICAL_UNCERTAINTY`, pero si viene escrito con un valor fuera del catálogo se liquida al `0 %` con `AUDIT_FLAG_PERFIL_DESCONOCIDO`.<br>- `P-05` y `P-15`: Medir `F1` sobre una muestra estratificada de **300 glosas limpias + 300 glosas perturbadas** almacenada fuera de git, repartida a razón de 200 glosas por integrante.<br>- `P-09` y `P-10`: Consolidar el manifiesto del lote al completarse el chunk #240 sin Step Functions, usando la concatenación ordenada de hashes SHA-256. |
| **Decisiones con enlace a ADR o commit** | Commit `0a85454`, [sección 7 del plan de construcción](../plan/04_plan_construccion.md) y [`prototype/saom_core.py`](../../prototype/saom_core.py). |
| **Discrepancias y cómo se resolvieron** | Se discutió cómo evaluar el `F1` de un parser determinista si el dataset oficial completo sigue una plantilla fija (donde `F1 = 1,0000`). Se acordó construir un subconjunto adicional de **300 glosas con 6 tipos de perturbación** (espacios irregulares, orden permutado de campos, minúsculas/perfiles desconocidos, campos omitidos, ruido OCR en etiquetas y separadores vacíos) para someter a prueba real la robustez del extractor. |
| **Tareas asignadas** | - **Naomi Chow** (`T0`, `T1`, `E01 v2`): Núcleo `saom_core.py`, 27 tests BDD y documento E01 v2.<br>- **Daniel Lopez** (`T2`, `T3`, `T4`, `T6`): Adaptadores Lambda, despliegue y corrida de 1,2M en AWS Learner Lab.<br>- **María Fernanda Toro** (`T5a`, `T5`, `E02`, `E03`, `E04`): Protocolo y muestra de 600 glosas, evaluación F1 + M/M/c y consolidación de entregables. |
| **Entregables revisados en forma cruzada** | `prototype/saom_core.py`, `prototype/test_bdd_rf01_rf05.py` y `entregables/E01/Entregable_01_Propuesta_Arquitectura_Salud_COIL_v2.docx`. |
| **Lecciones de la colaboración** | Traducir cada regla de negocio ambigua (`P-01..P-17`) en un test automatizado `pytest` antes de pasar a la nube eliminó por completo los errores lógicos durante el despliegue en AWS. |
| **Pendientes para la próxima sesión** | Desplegar en AWS Learner Lab, correr el lote de 1,2M (`T4`), ejecutar las consultas en Athena (`T6`) y cerrar `E02`, `E03` y `E04`. |

---

### Sesión 2026-11-11 — Despliegue en AWS Learner Lab (`T2/T3/T4/T6`), Evaluación F1 (`T5a/T5`) y Cierre de `E02`, `E03` y `E04`

| Campo | Valor |
| :--- | :--- |
| **Fecha y hora** | 2026-11-11 · 17:30–19:30 COT (UTC-5) |
| **Modalidad** | Síncrona (sesión de despliegue en vivo sobre AWS Academy Learner Lab + cierre documental) |
| **Participantes** | Naomi Chow, Daniel Lopez y María Fernanda Toro |
| **Agenda** | 1. Verificación de citas `[10]`, `[16]` y precios oficiales por tramos de Amazon Comprehend Medical `[24]` en el E01 v2.<br>2. Generación del Entregable 02 con diagramas de arquitectura simplificados a 300 DPI.<br>3. Ejecución de `T5a` y `T5` (600 glosas etiquetadas y evaluación `Macro-F1 = 0,9886`).<br>4. Ejecución en vivo en AWS Learner Lab (cuenta `329771219583`) de `T2` (`R-01`), `T3` (`10.001` filas), `T4` (`1.200.000` filas en `240` chunks) y `T6` (Apache Iceberg + Amazon Athena).<br>5. Empaquetado final de `E03` y `E04` (documento consolidado + guion de sustentación). |
| **Acuerdos técnicos** | - Activar en `saom-audit-329771219583` la contingencia prevista en `R-01`: `S3 Versioning` + política `DenyDeleteAuditReceipts` + cadena SHA-256 de 3 niveles, dado que `LabRole` restringe `s3:PutObjectLockConfiguration`.<br>- Incorporar reintento con *exponential backoff* y *jitter* en `worker_adjudicador_handler` ante colisiones `TransactionConflict` sobre el registro `META` de DynamoDB cuando 10 workers finalizan chunks en el mismo milisegundo.<br>- Conservar la tabla Apache Iceberg `saom_analytics.adjudicaciones` (`1.200.000` filas) y los reportes de verificación en `docs/verificacion/`. |
| **Decisiones con enlace a ADR o commit** | Commit `b2a3f44`, [`R01_verificacion_learner_lab.md`](../verificacion/R01_verificacion_learner_lab.md), [`T3_T4_T6_ejecucion_real_aws.md`](../verificacion/T3_T4_T6_ejecucion_real_aws.md) y [`T5_informe_metricas_f1_mmc_costo.md`](../verificacion/T5_informe_metricas_f1_mmc_costo.md). |
| **Discrepancias y cómo se resolvieron** | Durante la primera corrida de los 240 chunks en AWS (`LOTE-COIL-1200K`), 234 chunks finalizaron en `45,9 s`, pero 6 chunks (`[43, 69, 140, 175, 216, 238]`) experimentaron `TransactionConflict` en DynamoDB porque varios workers intentaron hacer `ADD` sobre la misma clave `META` en el mismo milisegundo, y el bloque `except` trataba cualquier `TransactionCanceledException` como duplicado. Se resolvió inspeccionando `CancellationReasons` en `lambda_handlers.py` para distinguir `ConditionalCheckFailed` (duplicado real) de `TransactionConflict` (contención transitoria en `META`, que ahora se reintenta hasta 8 veces con *backoff* exponencial), logrando **`240/240` chunks (`1.200.000` órdenes) procesados en `47,50 s`**. |
| **Tareas asignadas** | - **Naomi Chow**: Revisión final de trazabilidad documental (`E01 v2`, `E02`, `E04`) y apertura del pitch (Problema, Estado del Arte y Cumplimiento de SLA/Costos).<br>- **Daniel Lopez**: Ejecución y monitoreo de `T2`, `T3`, `T4` y `T6` en AWS Learner Lab y sección de Arquitectura Serverless, Idempotencia y Demo en AWS del pitch.<br>- **María Fernanda Toro**: Consolidación de resultados de `T5a`/`T5` (`F1 = 0,9886`), paquete de evidencias `E03` y sección de Extracción Clínica, Privacidad PII y Trazabilidad SHA-256 del pitch. |
| **Entregables revisados en forma cruzada** | `entregables/E01/Entregable_01_Propuesta_Arquitectura_Salud_COIL_v2.docx`, `entregables/E02/Entregable_02_Diseno_Tecnico_Salud_COIL.docx`, `entregables/E03/Entregable_03_Prototipo_Evidencia_Salud_COIL.docx` y `entregables/E04/Entregable_04_Documento_Consolidado_Salud_COIL.docx`. |
| **Lecciones de la colaboración** | La prueba con carga real de 1,2M de registros en AWS permitió descubrir y corregir un fenómeno de contención distribuida (`TransactionConflict` sobre llave caliente en DynamoDB) que no se manifiesta en pruebas unitarias secuenciales. |
| **Pendientes para la próxima sesión** | Sustentación final (Pitch E04) ante el jurado evaluador. |
