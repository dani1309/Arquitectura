# Plan de construcción del prototipo

| Campo | Valor |
| :--- | :--- |
| Paso AI-DLC | 4, Plan |
| Entregable que alimenta | E03 Implementación y E04 Consolidado |
| Estado | Completado y verificado en AWS Academy Learner Lab (`2026-11-11`) |
| Equipo | Naomi Chow, Daniel Lopez y María Fernanda Toro |
| Fuentes | [RF](../inception/01_requisitos_funcionales_bdd.md), [RNF](../inception/02_requisitos_no_funcionales.md), [ADR-001](../inception/adrs/ADR-001-estrategia-procesamiento.md), [ADR-002](../inception/adrs/ADR-002-anonimizacion-pii-y-trazabilidad.md), [ADR-003](../inception/adrs/ADR-003-estrategia-mvp-lab-aws.md), [ADR-004](../design/adrs/ADR-004-computo-workers-lambda.md), [ADR-005](../design/adrs/ADR-005-almacenamiento-poliglota.md), [arquitectura técnica](../design/03_arquitectura_tecnica.md), [enunciado](../enunciado/TrabajoFinal.pdf) |

Este plan solo usa lo que ya está decidido en los RF, los RNF y los ADR. No agrega servicios ni metas nuevas. Lo que no se puede verificar en el repositorio aparece como pendiente, y las contradicciones entre documentos quedan en la sección 7 con su resolución.

## 1. Alcance del prototipo en el Learner Lab

ADR-003 fija que el prototipo procesa las 1.200.000 solicitudes del dataset oficial con servicios serverless compatibles con `LabRole` y un presupuesto de 50 USD, y que la escala de 12 M se sustenta con el modelo M/M/c alimentado con el `k` medido. El alcance sigue esa decisión.

### 1.1 Lo que se implementa

| Componente | Servicio | Requisitos | Fuente |
| :--- | :--- | :--- | :--- |
| Núcleo de adjudicación (validación, pseudonimización con `#`, extracción con spans, cobertura, liquidación con `Decimal`, hash SHA-256) | Librería Python, probada en local y empaquetada para Lambda | RF-01 a RF-05, RNF-04, RNF-05 | Arquitectura sección 5, ADR-002, ADR-004 |
| Zonas de datos `saom-raw`, `saom-ref`, `saom-curated` y `saom-audit` | S3 | RNF-04, RNF-05 | Arquitectura sección 7.1, ADR-005 |
| Colas `lotes-recibidos` y `chunks-adjudicacion` con DLQ y `maxReceiveCount` 3 | SQS | RF-01, RNF-06 | Arquitectura secciones 4 y 8.2 |
| Control de lotes y chunks con idempotencia | DynamoDB on-demand, tabla `control_lotes` | RNF-06 | Arquitectura sección 7.2, ADR-005 |
| Particionador por rangos de bytes de 5.000 filas | Lambda | RF-01 | Arquitectura sección 6.1 |
| Worker de adjudicación con concurrencia de 5 a 10 | Lambda Arm, imagen de contenedor o ZIP según R-01 | RF-01 a RF-05, RNF-06 | ADR-004, arquitectura sección 14 |
| Clave secreta HMAC con `key_version` | Secrets Manager o variable cifrada con KMS | RNF-05 | Arquitectura sección 10 |
| Recibos y manifiestos inmutables | S3 con Object Lock, o Versioning con política que niega el borrado si `LabRole` no lo permite | RF-05, RNF-04 | ADR-003, ADR-005 |
| Telemetría de throughput, rechazos y DLQ | CloudWatch Logs y métricas EMF | RNF-01 | Arquitectura sección 4 |
| Tabla `adjudicaciones` y consultas SQL (prioridad media) | Iceberg sobre S3, Glue Data Catalog y Athena | RNF-04 | ADR-005 |

### 1.2 Lo que queda solo en diseño

| Elemento del diseño | Qué se hace en el prototipo | Justificación del recorte |
| :--- | :--- | :--- |
| API de radicación con API Gateway, URL prefirmada y `GET /lotes/id` | El CSV se sube directo a `saom-raw` desde la consola o la CLI | La cadena que miden los RNF empieza en el evento `ObjectCreated`. La API no cambia el throughput, la trazabilidad ni la privacidad, y en el diseño su costo es marginal (arquitectura sección 11.1) |
| Consolidación cada 15 minutos con EventBridge Scheduler y Step Functions | Una sola consolidación al terminar los 240 chunks | La sección 12 de la arquitectura prevé este disparo para el Learner Lab y P-10 lo confirma sin Step Functions |
| `OPTIMIZE` diario y expiración de snapshots de Iceberg | No se ejecutan | Con una sola corrida no se acumulan archivos pequeños ni snapshots que mantener |
| Object Lock en modo `COMPLIANCE` | Solo si T2 confirma que `LabRole` lo permite | ADR-003 y ADR-005 definen la alternativa con Versioning, negación de borrado y cadena de hashes |
| Un rol IAM de mínimo privilegio por función | Todo corre con `LabRole` | El laboratorio no permite crear roles (arquitectura sección 10) |
| Claves KMS administradas por el cliente, AWS WAF y API key por entidad | Clave administrada por AWS, sin WAF ni API key | Dependen de la API de radicación o de permisos que el laboratorio no da (arquitectura sección 10) |
| Ciclo de vida a Glacier a los 30 días | No se configura | El prototipo no dura 30 días con datos y la regla no afecta ningún RNF medible |
| Padrón externo de afiliación en DynamoDB | No se implementa | El diseño lo marca como opcional, porque el perfil viene en la glosa (ADR-005) |
| Portabilidad del worker a ECS Fargate Spot | No se prueba | ADR-004 la deja como salida futura, y ECS y Fargate se reportan como no disponibles en el laboratorio |
| Concurrencia de hasta 56 workers y volumen de 12 M diarios | Concurrencia máxima de 10 y 1,2 M de órdenes, con extrapolación M/M/c | ADR-003 y RNF-06. La corrida de 12 M (T4b) se descartó |
| Flujo de revisión humana de segunda línea | Solo se marca el flag `AUDIT_FLAG_CLINICAL_UNCERTAINTY` | RF-02 exige marcar la orden para revisión, y ningún RF especifica la herramienta de revisión |
| Rotación de la clave HMAC | Se registra `key_version`, sin rotar | La rotación es una mitigación de operación (arquitectura sección 14, R-05) |

## 2. Tareas

Todas las tareas tienen responsable asignado y han sido completadas y verificadas. Las tareas T0, T5a y T8 no estaban en la lista mínima y se agregaron porque otras tareas dependen de ellas.

| ID | Tarea | Depende de | MoSCoW | Criterio de terminado verificable | Responsable |
| :--- | :--- | :--- | :--- | :--- | :--- |
| T0 | Obtener el dataset `COIL_dataset_glosas_salud_1_2M.csv` y fijar su ubicación local fuera de git | Ninguna | Must | El archivo existe en la ruta acordada, tiene 1.200.000 filas más la cabecera de 6 columnas de RF-01 y su SHA-256 queda anotado en la bitácora. **Cumplida el 2026-11-09** | Naomi Chow |
| T1 | Núcleo local en Python con validación, pseudonimización con `#`, extracción con spans, cobertura, liquidación con `Decimal` y hash SHA-256 | Ninguna | Must | Hay un test por cada escenario BDD de RF-01 a RF-05 y todos pasan en local (`25 passed`). Para cada entidad clínica extraída se cumple que el texto en `[start_char, end_char]` coincide en la glosa original y en la enmascarada. La liquidación no usa `float`. Cambiar un centavo o un carácter del JSON canónico cambia el `hash_decision`. El escaneo de PII de RNF-05 sobre las salidas de los tests da cero coincidencias. **Cumplida el 2026-11-10** ([`saom_core.py`](../../prototype/saom_core.py), [`test_bdd_rf01_rf05.py`](../../prototype/test_bdd_rf01_rf05.py)) | María Fernanda Toro |
| T2 | Infraestructura en el Learner Lab con buckets, SQS con DLQ y DynamoDB, más las pruebas tempranas de R-01. Se hace en paralelo con T1 | Ninguna | Must | Los recursos de la sección 1.1 existen en `us-east-1` (cuenta `329771219583`). Queda escrito en [`docs/verificacion/R01_verificacion_learner_lab.md`](../verificacion/R01_verificacion_learner_lab.md) el resultado de cada prueba de R-01 con su evidencia (`LabRole`, Object Lock alternativo con Versioning + `DenyDeleteAuditReceipts`, concurrencia Lambda, Glue Data Catalog, Secrets Manager y consulta de costos). No queda ningún recurso con costo fijo por hora. El procedimiento de apagado (`teardown`) está documentado. **Cumplida el 2026-11-11** | Daniel Lopez |
| T3 | Particionador y worker Lambda | T1, T2 | Must | Un CSV de prueba con varios chunks y una fila malformada (`LOTE-T3-INTEGRACION`, `10.001` filas) recorre la cadena completa en local (`6 passed`) y en AWS (`4,83 s`). Al final `chunks_completados` es igual a `chunks_totales` (`3/3`), la fila malformada (`CHV-9999999`) está en `rechazos/`, la DLQ está vacía (`0`) y reenviar un mensaje ya procesado no cambia los contadores de `META` (`duplicados_ignorados = 1`, RNF-06). **Cumplida el 2026-11-11** ([`lambda_handlers.py`](../../prototype/lambda_handlers.py), [`T3_T4_T6_ejecucion_real_aws.md`](../verificacion/T3_T4_T6_ejecucion_real_aws.md)) | Daniel Lopez |
| T4 | Corrida con el dataset de 1,2 M y medición del throughput real `k` | T0, T3 | Must | Los 240 chunks de `LOTE-COIL-1200K` terminan en **`47,50 s`**. `ordenes_validas` (`1.200.000`) más `ordenes_rechazadas` (`0`) suman 1.200.000. La DLQ queda en `0`. El 100 % de las órdenes válidas tiene `hash_decision` y existen la `raiz_hash_chunk` de cada chunk y la `raiz_hash_lote` (`78dbff2ea6b365f3399315b1377111bc3ec23939ce539a101378b3f8b648869e`). El `k` medido en CloudWatch es **`4.710,44 órdenes/s/vCPU`** (`1.061,60 ms/chunk`). El escaneo de PII de RNF-05 sobre `saom-curated`, `saom-audit`, DynamoDB y los logs da cero coincidencias. **Cumplida el 2026-11-11** ([`T3_T4_T6_ejecucion_real_aws.md`](../verificacion/T3_T4_T6_ejecucion_real_aws.md)) | Daniel Lopez y Naomi Chow |
| T4b | Corrida de 12 M con el dataset replicado e ids nuevos. Descartada por el equipo | T4 | Won't | No aplica porque la tarea se descartó | No aplica |
| T5a | Muestra etiquetada a mano para medir F1 | T0 | Must | Existe una muestra de 300 glosas etiquetadas más 300 perturbadas (`600` glosas en total, 200 por integrante), guardada fuera de git, con etiquetas de `Edad`, `PerfilCobertura`, `ServicioSolicitado` y `Medicacion` y sus spans exactos. El protocolo de etiquetado y el criterio de coincidencia exacta quedan documentados en [`docs/verificacion/T5a_protocolo_etiquetado_y_spans.md`](../verificacion/T5a_protocolo_etiquetado_y_spans.md). **Cumplida el 2026-11-11** | Naomi Chow, Daniel Lopez y María Fernanda Toro |
| T5 | Métricas, es decir F1 contra la muestra, costo real y extrapolación M/M/c con el `k` medido | T1, T4, T5a | Must | Informe en [`docs/verificacion/T5_informe_metricas_f1_mmc_costo.md`](../verificacion/T5_informe_metricas_f1_mmc_costo.md) con precision, recall y F1 por entidad y **Macro-F1 = `0,9886`** (`1,0000` en limpias y `0,9765` en perturbadas, superando `>= 0,92`). Incluye el costo real en AWS de **`0,0189 USD`** (`0,0158 USD/millón` `<= 0,50 USD/millón`), la fracción `f = 0,0000` en plantilla oficial (`0,1667` bajo estrés `<= 0,30`), y `N = 1` (`c = 10`), `rho = 0,2359` y `Wq = 0,328 s` (`4,25 min` de drenaje) para 12 M recalculados con `k = 4.710,44`. **Cumplida el 2026-11-11** | María Fernanda Toro |
| T6 | Consolidación en Iceberg y consultas en Athena | T2, T3 | Should | El `MERGE INTO` deja en `saom_analytics.adjudicaciones` exactamente **`1.200.000` filas**. Repetir el `MERGE` sobre `chunk_id = 0` mantiene **`1.200.000` filas** (`0` duplicados). Consultas ejecutadas de monto aprobado por `entidad_emisora`, `medio_emisor` y `dia_solicitud` (`57.328.903.464,00` aprobados). Verificación de tres niveles (sección 7.4) desde `CHV-0000001..0000005` en Iceberg con `100 %` de éxito. **Cumplida el 2026-11-11** ([`T3_T4_T6_ejecucion_real_aws.md`](../verificacion/T3_T4_T6_ejecucion_real_aws.md)) | Daniel Lopez |
| T8 | Paquete de evidencia del E03 | T4, T5, T6 | Must | Están todos los elementos de la sección 5 con enlace a su archivo en [`entregables/E03/Entregable_03_Prototipo_Evidencia_Salud_COIL.docx`](../../entregables/E03/Entregable_03_Prototipo_Evidencia_Salud_COIL.docx) y en `docs/verificacion/`. **Cumplida el 2026-11-11** | Naomi Chow y María Fernanda Toro |
| T7 | Documento consolidado y pitch del E04 | T5, T8 | Must | Están el documento consolidado ([`Entregable_04_Documento_Consolidado_Salud_COIL.docx`](../../entregables/E04/Entregable_04_Documento_Consolidado_Salud_COIL.docx)) y el guion del pitch ([`Entregable_04_Guion_Pitch_Sustentacion_COIL.docx`](../../entregables/E04/Entregable_04_Guion_Pitch_Sustentacion_COIL.docx)) en `entregables/E04/`, junto con el [E01 v2 corregido](../../entregables/E01/Entregable_01_Propuesta_Arquitectura_Salud_COIL_v2.docx) y el [E02 simplificado](../../entregables/E02/Entregable_02_Diseno_Tecnico_Salud_COIL.docx). **Cumplida el 2026-11-11** | Naomi Chow, Daniel Lopez y María Fernanda Toro |

La ruta crítica es T1 y T2 en paralelo, luego T3, T4, T5, T8 y T7. T0 tiene que estar listo antes de que termine T3 para no frenar T4, y T5a puede avanzar en paralelo con T1, T2 y T3.

## 3. Grafo de dependencias

```mermaid
flowchart LR
    T0["T0 Dataset disponible"]
    T1["T1 Núcleo local y tests BDD"]
    T2["T2 Infraestructura y pruebas R-01"]
    T3["T3 Particionador y worker Lambda"]
    T4["T4 Corrida 1,2 M y medición de k"]
    T5a["T5a Muestra etiquetada a mano"]
    T5["T5 F1, costo real y M/M/c"]
    T6["T6 Iceberg y Athena"]
    T8["T8 Evidencia E03"]
    T7["T7 Documento consolidado y pitch"]

    T1 --> T3
    T2 --> T3
    T0 --> T4
    T3 --> T4
    T0 --> T5a
    T1 --> T5
    T4 --> T5
    T5a --> T5
    T2 --> T6
    T3 --> T6
    T4 --> T8
    T5 --> T8
    T6 -.-> T8
    T5 --> T7
    T8 --> T7
```

Versión en texto del grafo. Las flechas con puntos (`..>`) son dependencias opcionales.

```
T0  --> T4, T5a
T1  --> T3, T5
T2  --> T3, T6
T3  --> T4, T6
T4  --> T5, T8
T5a --> T5
T5  --> T8, T7
T6  ..> T8    (Should)
T8  --> T7
```

## 4. Corrida de 12 M descartada

El diseño calcula el costo de cómputo del prototipo de 1,2 M en 0,07 USD con `k` de 400, 0,28 USD con `k` de 100 y 1,13 USD con `k` de 25 (arquitectura sección 11.3). El modelo de cómputo de `modelo_capacidad_costo.py` es lineal en el número de órdenes, así que 12 M cuestan diez veces eso en cómputo. Ese cálculo no incluye S3, SQS, DynamoDB, CloudWatch ni Athena, que hay que sumar.

El equipo descartó T4b. La escala de 12 M se sustenta con la extrapolación M/M/c de ADR-003.

## 5. Evidencia que pide la rúbrica del E03

El enunciado describe el E03 como "Prototipo funcional en AWS, pruebas, evidencia y alcance implementado", con producto "Código y resultados". La rúbrica evalúa "Prototipo funcional, uso pertinente de AWS y evidencia de pruebas". El enunciado no detalla formato ni contenido mínimo. La columna de evidencia es una propuesta del equipo para cubrir cada criterio.

| Criterio del enunciado | Evidencia propuesta | Tarea |
| :--- | :--- | :--- |
| Prototipo funcional | Registro de la corrida de 1,2 M con los conteos de `control_lotes`, la DLQ vacía o con causas anotadas y la `raiz_hash_lote` | T4 |
| Uso pertinente de AWS | Inventario de recursos creados frente a la sección 1.1, resultado de las pruebas de R-01 y relación de cada recorte de la sección 1.2 con su justificación | T2, T8 |
| Evidencia de pruebas | Salida de los tests BDD de RF-01 a RF-05, prueba de idempotencia de T3, escaneo de PII de RNF-05 y verificación de tres niveles de RNF-04 | T1, T3, T4, T6 |
| Resultados | Informe de T5 con `k`, F1 por entidad, costo real, fracción `f` de revisión y dimensionamiento M/M/c para 12 M | T5 |
| Código | Código del núcleo, del particionador y del worker con su versión en git | T1, T3 |
| Alcance implementado | Tabla final de lo implementado y lo que quedó solo en diseño, actualizada desde la sección 1 | T8 |

## 6. Riesgos que afectan el plan

| Riesgo | Efecto en el plan | Tarea que lo cierra |
| :--- | :--- | :--- |
| R-01, permisos de `LabRole` sobre Object Lock, ECR y concurrencia de Lambda | Cambia el empaquetado del worker y el mecanismo WORM | T2 |
| R-02, el `k` real define `N` y el costo | Cambia la extrapolación | T4 |
| Dataset no disponible. **Cerrado por T0** | Bloqueaba T4 y T5a | T0 |
| Disponibilidad de Glue Data Catalog en el laboratorio | Bloquea T6 | T2 |

## 7. Preguntas para el equipo

Son contradicciones o vacíos entre los documentos. La columna Resolución registra lo que decidió el equipo.

| ID | Documentos | Contradicción o vacío | Resolución |
| :--- | :--- | :--- | :--- |
| P-01 | RF-02 | El escenario dice que la glosa de `CHV-0000001` tiene 238 caracteres, pero el texto del propio escenario mide 235 caracteres (239 bytes en UTF-8). ¿Se corrige la cifra o el texto del ejemplo no es el del dataset? | La cifra de RF-02 pasa de 238 a 235 caracteres |
| P-02 | RF-01 y RF-04 | RF-01 usa `CHV-0000002` como fila malformada y RF-04 la usa como orden válida de "Suministro de antihipertensivos". ¿Cuál corresponde al dataset? | RF-01 usa `CHV-9999999` como fila malformada y `CHV-0000002` queda como orden válida en RF-04 |
| P-03 | RF-03 y arquitectura sección 7.3 | RF-03 pide verificar el rango de valor y las medicaciones de referencia, pero no dice qué pasa si no se cumplen. La arquitectura sugiere el flag `VALOR_FUERA_RANGO_REF`. ¿Solo se marca o cambia el dictamen? ¿Y si la medicación no está en `medicaciones_referencia`? | Solo se agregan los flags `AUDIT_FLAG_VALOR_FUERA_RANGO_REF` y `AUDIT_FLAG_MEDICACION_NO_REFERENCIA`. El dictamen no cambia y RF-03 tiene un escenario BDD para esto |
| P-04 | RF-02 | Se exige confianza mayor o igual a 0,92 y se marca revisión por debajo de 0,70. No está definido qué pasa entre 0,70 y 0,92 ni cómo se calcula la confianza en un extractor léxico | El extractor es un parser determinista. La confianza es campos válidos / 7 y se guarda como dato. `AUDIT_FLAG_CLINICAL_UNCERTAINTY` se marca si falta o es inválido `Edad`, `ServicioSolicitado` o `Medicacion`, o si `PerfilCobertura` falta en la glosa. Si `PerfilCobertura` viene escrito pero no está en el catálogo, se marca solo `AUDIT_FLAG_PERFIL_DESCONOCIDO` |
| P-05 | RNF-02 | Dice que el F1 se evalúa "sobre el dataset oficial", que no trae etiquetas de referencia. El plan propone una muestra etiquetada a mano (T5a). Falta confirmar tamaño y protocolo | El F1 se mide sobre 300 glosas etiquetadas más 300 perturbadas. En glosas limpias se espera F1 cercano a 1 porque la plantilla es fija |
| P-06 | RNF sección 3, RNF-03, ADR-003, arquitectura secciones 2 y 11.3 | El costo de una corrida de 1,2 M aparece como menor a 0,35 USD, menor a 0,30 USD y hasta 1,13 USD según `k`. RNF-03 pide 0,50 USD o menos por millón en el laboratorio y su criterio de aceptación habla de 0,25 a 0,31 USD por millón. ¿Cuál es la meta? | La meta del laboratorio es 0,50 USD o menos por millón. Los demás valores son estimaciones |
| P-07 | Arquitectura secciones 8.1 y 14 | La sección 8.1 afirma que el extractor supera fácilmente un `k` de 400, y R-02 dice que `k` se mide. ¿Se trata como hipótesis hasta T4? | `k >= 400` es una hipótesis a medir en T4. El M/M/c aplica a la ingesta de 24 h y en la ventana de 3 h importa el tiempo de drenaje y no `Wq` |
| P-08 | ADR-004 y ADR-005 | ADR-004 dice que la documentación del laboratorio no lista Glue, y ADR-005 usa Glue Data Catalog para Iceberg | Glue se verifica en T2. Si no está disponible, T6 se omite |
| P-09 | ADR-002 y arquitectura sección 7.4 | ADR-002 habla de "árbol de hashes" y de hashes que "se encadenan". La arquitectura define la raíz como SHA-256 de la concatenación ordenada, que es una lista plana y no un árbol de Merkle. ¿Qué algoritmo se implementa? | Se implementa la concatenación ordenada de hashes con SHA-256 |
| P-10 | ADR-003 y arquitectura sección 12 | ADR-003 incluye Step Functions entre los servicios del prototipo. La arquitectura permite consolidar al completar los 240 chunks sin Step Functions | El prototipo consolida una vez al final, sin Step Functions |
| P-11 | ADR-004, ADR-005, `aidlc/.../project.md` y git | ADR-004 y ADR-005 tienen fecha 2026-10-21, entraron al repositorio en 148cf96 el 2026-10-22 y `project.md` los registra como decididos el 2026-10-27. `project.md` también fecha ADR-002 el 2026-10-27, y el ADR dice 2026-10-21 | Queda sin impacto |
| P-12 | Arquitectura, ADR-004 y ADR-005 | Se rotulan como fase "Construction", y el README los trata como paso 3 Arquitectura | La fase pasa a "Paso 3, Arquitectura" en los tres documentos |
| P-13 | RF-01 y T4b | El ejemplo `CHV-0000001` tiene siete dígitos, con un máximo de 9.999.999 ids. Para 12 M hace falta otro formato y que el validador lo acepte | Cerrada porque T4b se descartó |
| P-14 | RF-04 y arquitectura sección 7.3 | RF-04 y la tabla Iceberg mencionan el copago (`valor_copago`), pero ninguna regla dice cómo se calcula, ni para `CUBRE` ni para `NO_CUBRE` | `valor_copago = valor_procedimiento - valor_aprobado` siempre |
| P-15 | RNF-05 y T5a | La muestra etiquetada sale de glosas con nombres e identificadores, aunque sean sintéticos. ¿Se versiona en git o se guarda fuera, como el dataset? | La muestra de 300 glosas etiquetadas más 300 perturbadas se guarda fuera de git |
| P-16 | RNF-01 | El criterio del prototipo dice "dentro del SLA", pero no define el SLA para la corrida de 1,2 M | El SLA de la corrida de 1,2 M es de 2,4 h |
| P-17 | RF-04 y arquitectura sección 5 | Un perfil inválido liquida al 0 %, pero no está definido qué dictamen y qué flag lleva esa orden | Liquida al 0 % y el dictamen depende del servicio. Si el perfil falta en la glosa se marca `AUDIT_FLAG_CLINICAL_UNCERTAINTY`, y si viene escrito pero no está en el catálogo se marca solo `AUDIT_FLAG_PERFIL_DESCONOCIDO` |
