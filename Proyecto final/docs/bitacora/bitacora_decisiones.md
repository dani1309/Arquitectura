# Bitácora de decisiones

Registro de las decisiones del proyecto. La tabla de la sección 1 solo contiene lo que se puede comprobar en `git log` y en los ADR. La fecha de un ADR es la que figura en el propio ADR, y la de un commit es su fecha de autor en git. En las filas de un ADR el autor es lo que indica su campo "Decisores", o "Equipo" si el ADR no lo indica. En las demás filas el autor es el usuario de GitHub que hizo el commit. La plantilla de la sección 2 sirve para registrar las sesiones COIL entre sedes desde ahora.

## 1. Decisiones registradas

| Fecha | Decisión | ADR o commit | Autor |
| :--- | :--- | :--- | :--- |
| 2026-10-21 | Arquitectura híbrida con ingesta continua a S3 y SQS y procesamiento por chunks de 5.000 órdenes | ADR-001, agregado en 413b2e2 | Equipo de Arquitectura Proyecto COIL |
| 2026-10-21 | Pseudonimización con `HMAC-SHA256` y clave secreta, enmascaramiento con `#` que conserva la longitud y `hash_decision` sobre JSON canónico | ADR-002, agregado en 413b2e2 | Equipo de Arquitectura Proyecto COIL |
| 2026-10-21 | Prototipo serverless en el Learner Lab con el dataset de 1,2 M y extrapolación M/M/c a 12 M | ADR-003, agregado en 413b2e2 | Equipo de Arquitectura Proyecto COIL |
| 2026-10-21 | Crédito del Learner Lab corregido de 100 USD a 50 USD en los RNF | a24f8e7 | naochow |
| 2026-10-21 en el ADR, 2026-10-22 en git | Workers de adjudicación en AWS Lambda Arm con imagen de contenedor portable a ECS Fargate Spot | ADR-004, agregado en 148cf96 | Equipo |
| 2026-10-21 en el ADR, 2026-10-22 en git | Almacenamiento políglota con DynamoDB para control, Iceberg con Athena para analítica y bucket S3 WORM para evidencia | ADR-005, agregado en 148cf96 | Equipo |
| 2026-10-27 | Alinear requisitos, ADR-001 a ADR-005 y diseño al dataset oficial COIL de 1,2 M e incorporar los catálogos en `data/ref/` | 41218ad | dani1309 |
| 2026-10-27 | Retirar el código del prototipo y `data/`, y conservar solo Inception y Diseño (entregables 1 y 2) | a6bf93b | dani1309 |
| 2026-10-28 | Mover `design/` a `Proyecto final/docs/design/` | 8a52800 | naochow |
| 2026-10-28 | Restaurar los catálogos COIL y el diccionario desde 41218ad, sin restaurar el código del prototipo | 6773fcf | naochow |
| 2026-10-28 | No versionar el dataset de 1,2 M ni los cursores locales de AI-DLC | 62cdc54 | naochow |
| 2026-10-28 | Crear carpetas para plan, verificación, bitácora y entregables E01 a E04 | 5b69fbc | naochow |
| 2026-10-28 | Agregar el README con la estructura y el estado de pasos y entregables | 13e3570 | naochow |
| 2026-10-28 | Versionar el enunciado y el Entregable 01 | bd9feac | naochow |
| 2026-10-28 | Alinear los entregables y el paso 1 del README con el enunciado | f18c57d | naochow |
| 2026-10-28 | Ignorar `desktop.ini` de Windows | e89eaf5 | naochow |
| 2026-10-28 | Integrar la reorganización en `main` | b83909c, merge del PR #1 | naochow |
| 2026-11-09 | Resolver P-01 a P-17 del plan. Los flags de valor y medicación no cambian el dictamen, el extractor es un parser determinista con confianza como dato, `valor_copago` es siempre la diferencia con `valor_aprobado`, el perfil inválido liquida 0 % con flag propio, la meta del laboratorio es 0,50 USD o menos por millón, el SLA de la corrida de 1,2 M es 2,4 h, el F1 se mide sobre 300 glosas etiquetadas más 300 perturbadas fuera de git, el prototipo consolida una vez al final sin Step Functions, las raíces usan concatenación ordenada de hashes con SHA-256 y T4b se descarta | [Plan de construcción, sección 7](../plan/04_plan_construccion.md) | Equipo |
| 2026-11-09 | T0 queda cumplida. `data/raw/COIL_dataset_glosas_salud_1_2M.csv`, fuera de git, tiene 1.200.000 filas más la cabecera de 6 columnas de RF-01, y su SHA-256 es `2c7631da66ffd2dc20c1f3aa17acc875b319601f0152c54ba7a36bc0716049c1` | [Plan de construcción, T0](../plan/04_plan_construccion.md) | naochow |

Notas sobre las fechas. ADR-001, ADR-002 y ADR-003 indican una actualización el 2026-10-27, que coincide con el commit 41218ad. ADR-004 y ADR-005 también dicen "Actualizado 2026-10-27". `aidlc/spaces/default/memory/project.md` registra otras fechas para ADR-002, ADR-004 y ADR-005, y esa diferencia queda como pregunta P-11 en el [plan de construcción](../plan/04_plan_construccion.md).

## 2. Plantilla para sesiones COIL entre sedes

Los campos siguen lo que la sección 4.2 del E01 propone registrar en la bitácora. Copiar el bloque por cada sesión.

```markdown
### Sesión AAAA-MM-DD

| Campo | Valor |
| :--- | :--- |
| Fecha y hora en cada sede | |
| Modalidad (síncrona o asíncrona) | |
| Participantes de cada institución | |
| Agenda | |
| Acuerdos técnicos | |
| Decisiones con enlace a ADR o commit | |
| Discrepancias y cómo se resolvieron | |
| Tareas asignadas (tarea del plan, responsable y fecha) | |
| Entregables revisados en forma cruzada | |
| Lecciones de la colaboración intercultural | |
| Pendientes para la próxima sesión | |
```
