# Entregable 04: Estructura de Diapositivas y Guion de Video (3 a 4 Minutos)

| Campo | Detalle |
| :--- | :--- |
| **Duración objetivo del video** | **3 minutos 30 segundos** (rango permitido: **3:00 a 4:00 minutos**; ~35 s por diapositiva) |
| **Presentación Editable** | [`Entregable_04_Presentacion_Ejecutiva_Salud_COIL.pptx`](Entregable_04_Presentacion_Ejecutiva_Salud_COIL.pptx) (`6` diapositivas ejecutivas 16:9 con diagramas, capturas AWS y notas de orador) |
| **Expositores (70 s c/u)** | **Naomi Chow** (`0:00 – 1:10`) · **Daniel Lopez** (`1:10 – 2:20`) · **María Fernanda Toro** (`2:20 – 3:30`) |
| **Evidencia en vivo incluida** | Cuenta AWS `329771219583` (`us-east-1`), corrida real de `1.200.000` órdenes en `47,50 s`, CloudWatch, DynamoDB `META` y Amazon Athena (Iceberg) |

---

## 1. Mapa de las 6 Diapositivas y Distribución del Tiempo (3:30 min)

| Diapositiva | Título | Expositor(a) | Tiempo | Mensaje Clave / Visual |
| :---: | :--- | :--- | :---: | :--- |
| **1** | Reto de Chernovia y Por Qué Fallan Otras Arquitecturas | **Naomi Chow** | `0:00 – 0:35` | `12M` órdenes en `< 24 h` (meta `3 h`), liquidación `100/50/25/0 %`. Comprehend Medical (`244.500 USD/día` escalonado, solo inglés) y EMR (`~220 USD/día`) son inviables frente a SAOM (**`0,0158 USD/M`**). |
| **2** | Metodología AI-DLC y Requisitos Verificados (`RF` + `RNF`) | **Naomi Chow** | `0:35 – 1:10` | 6 pasos AI-DLC y tabla de cumplimiento: `36/36` tests, `Macro-F1 = 0,9886 >= 0,92`, `0` PII en claro, `<= 0,50 USD/M` e idempotencia exacta. |
| **3** | Arquitectura Serverless por Micro-Lotes e Idempotencia (`ADR-001..005`) | **Daniel Lopez** | `1:10 – 1:45` | Diagrama `e02_arquitectura_simplificada.png`: S3 Raw → SQS → Particionador streaming (`4 MB` RAM, bloques de `5.000` órd.) → Lambda `arm64` (`1.769 MB`) + `TransactWriteItems` con *backoff* ante `TransactionConflict`. |
| **4** | Ejecución Real en AWS Learner Lab (`1.200.000` Órdenes en `47,50 s`) | **Daniel Lopez** | `1:45 – 2:20` | Capturas reales de **CloudWatch (`saom-worker`)** y **DynamoDB (`META`)**: `240/240` chunks, `4.710,44 órd/s/vCPU`, `1.061,60 ms/chunk`, `153 MB` RAM, `0` DLQ y **`0,0189 USD`** totales. |
| **5** | Privacidad PII, `Macro-F1 = 0,9886`, SHA-256 y Apache Iceberg (`T5` + `T6`) | **María Fernanda Toro** | `2:20 – 2:55` | `HMAC-SHA256` + `#` conservando spans `[start_char, end_char]`, `Decimal` sin `float`, `Macro-F1 = 0,9886` (600 glosas), cadena SHA-256 de 3 niveles y captura de **Amazon Athena** (`1.200.000` filas). |
| **6** | Extrapolación a 12M (`4,25` / `7,92 min`), Conciliación FinOps y Cierre | **María Fernanda Toro** | `2:55 – 3:30` | Medido vs. Proyectado (`4,25 min` drenaje puro vs. `7,92 min` E2E) y unificación de costos (`0,25–0,31 USD/M` estimado previo vs. **`0,0158 USD/M`** medido vs. **`0,2483 USD`** lote 12M con operación). |

---

## 2. Guion Detallado Cronometrado para Video (~515 Palabras · 3:30 min a Ritmo Normal)

> **Consejo de grabación:** A un ritmo natural de **145 palabras por minuto**, cada bloque de ~170 palabras dura exactamente **70 segundos**, dejando 20–30 segundos de holgura por debajo del límite de 4 minutos para transiciones entre integrantes o mostrar brevemente la consola de AWS.

### Bloque 1 — Naomi Chow (`0:00` a `1:10` · ~170 palabras)

- **[Diapositiva 1 · `0:00–0:35`]**:
  > *"Hola, somos Naomi Chow, Daniel Lopez y María Fernanda Toro, y presentamos SAOM, el Sistema de Adjudicación de Órdenes Médicas para el Ministerio de Salud de Chernovia. El reto exige procesar hasta 12 millones de órdenes diarias en menos de 24 horas —con una meta interna de nuestro equipo de 3 horas—, extraer cuatro entidades clínicas de cada glosa, liquidar al 100, 50, 25 o 0 por ciento y dejar auditoría verificable sin exponer PII. Al evaluar 52 fuentes técnicas demostramos que orquestar orden por orden con Step Functions y Comprehend Medical cuesta 244.500 dólares al día por su mínimo de 300 caracteres y solo opera en inglés, mientras que un clúster EMR de 220 dólares diarios excede los 50 dólares del Learner Lab. Por eso diseñamos una arquitectura por micro-lotes de 5.000 órdenes en AWS Lambda Arm64."*
- **[Diapositiva 2 · `0:35–1:10`]**:
  > *"Aplicamos la metodología AI-DLC en seis pasos trazables, separando los requisitos del enunciado de nuestras metas de ingeniería: `Macro-F1 >= 0,92`, costo `<= 0,50 USD por millón`, cero datos personales en claro e idempotencia exacta, todo verificado con 36 pruebas automatizadas y ejecución real en AWS. Le doy paso a Daniel para mostrar la arquitectura y los resultados en la nube."*

---

### Bloque 2 — Daniel Lopez (`1:10` a `2:20` · ~170 palabras)

- **[Diapositiva 3 · `1:10–1:45`]**:
  > *"Gracias, Naomi. Como muestra nuestro diagrama de 8 pasos, cuando el CSV llega a `saom-raw`, la función `saom-particionador` lo recorre en streaming con solo 4 MB de RAM y publica en SQS descriptores livianos con los rangos exactos de bytes de cada bloque de 5.000 órdenes, reduciendo 5.000 veces la coordinación. Hasta 10 workers Lambda `arm64` leen solo su rango con `S3 Range GET` y consolidan atómicamente en DynamoDB `control_lotes`. En la prueba `T3` aislamos una fila corrupta en `rechazos/` sin PII e ignoramos reenvíos duplicados; y al correr los 240 chunks en paralelo resolvimos la contención `TransactionConflict` sobre el ítem `META` mediante exponential backoff con jitter."*
- **[Diapositiva 4 · `1:45–2:20`]**:
  > *"Con esto ejecutamos en nuestra cuenta de AWS (`329771219583`) el dataset oficial completo de 1.200.000 órdenes (`LOTE-COIL-1200K`). Como muestran las capturas reales de CloudWatch y DynamoDB, los 240 chunks finalizaron en **47,50 segundos** de reloj con cero errores y cero mensajes en la DLQ, a una media de `1.061,60 ms` por chunk —es decir, **4.710,44 órdenes por segundo por vCPU**— consumiendo apenas `153 MB` de RAM y **0,0189 dólares totales**. Continúa María Fernanda."*

---

### Bloque 3 — María Fernanda Toro (`2:20` a `3:30` · ~175 palabras)

- **[Diapositiva 5 · `2:20–2:55`]**:
  > *"Gracias, Daniel. En cada worker, `saom_core.py` pseudonimiza paciente, DNO y Seguro Social con `HMAC-SHA256` y los enmascara con `#` conservando la longitud exacta de la glosa, de modo que los spans `[start_char, end_char]` no se desplazan y logramos cero PII en S3, DynamoDB y CloudWatch. Sobre 600 glosas evaluadas fuera de git —300 limpias y 300 con ruido OCR y permutaciones— obtuvimos un **Macro-F1 de `0,9886`**, usando `Decimal` exacto sin `float`. Además, como ven en la captura de Amazon Athena, consolidamos las 1.200.000 filas en Apache Iceberg con doble `MERGE INTO` sin duplicados y verificamos la cadena SHA-256 de tres niveles hasta `raiz_hash_lote`."*
- **[Diapositiva 6 · `2:55–3:30`]**:
  > *"Para cerrar, diferenciamos lo medido de lo proyectado a 12 millones (`2.400` chunks con 10 workers): el drenaje puro de cómputo es `2.400 × 1,0616 / 10 = 4,25 minutos`, y el tiempo de reloj extremo a extremo escalando colas y particionador es `7,92 minutos`, ambos muy por debajo de 3 horas. En costos, frente al estimado teórico previo de `0,25 a 0,31 USD/M`, el gasto real medido en AWS fue **`0,0158 USD por millón`**, proyectando **`0,1890 USD` lineal** o **`0,2483 USD` por el lote diario completo de 12 millones** con retención S3 y compactación Iceberg (`0,0207 USD/M`). Muchas gracias."*

---

## 3. Banco de Defensa Técnica (Para Sesión de Preguntas o Anexos)

| Posible Pregunta del Jurado | Respuesta Técnica Concreta con Datos del Proyecto |
| :--- | :--- |
| **1. ¿Por qué usaron un parser determinista en lugar de un LLM o Comprehend Medical?** | Porque las glosas de Chernovia siguen una plantilla semiestructurada de 7 campos (`ADR-004`). Un parser determinista logra `F1 = 1,0000` en la plantilla oficial (`0,9886` incluyendo ruido OCR/permutación), procesa a `4.710 órdenes/s/vCPU` con `0,0158 USD/millón` y ofrece explicabilidad determinista (`regla_ids` + spans), mientras que Comprehend Medical cuesta `244.500 USD/día` y solo soporta inglés. Si una glosa llega truncada o alterada por OCR en un campo obligatorio, el sistema activa `AUDIT_FLAG_CLINICAL_UNCERTAINTY` y la deriva a revisión humana de segunda línea. |
| **2. ¿Cómo garantizan que el enmascaramiento de PII no desplace los spans `[start_char, end_char]`?** | En `extraer_y_pseudonimizar_glosa()` (`prototype/saom_core.py`), los valores de `Paciente`, `DNO` y `SeguroSocial` se sustituyen carácter por carácter por `'#' * len(valor)`. Como la longitud en caracteres antes y después de cada `;` permanece invariante, cualquier índice `glosa[start_char:end_char]` apunta exactamente a la misma subcadena clínica, lo cual está verificado en `test_t1_spans_iguales_en_glosa_original_y_enmascarada`. |
| **3. ¿Qué ocurrió en DynamoDB cuando corrieron los 240 chunks en paralelo en AWS?** | Los 10 workers concurrentes intentaban actualizar atómicamente su registro `CHUNK#` y sumar al contador único `META` del lote mediante `TransactWriteItems`. En 6 de los 240 chunks coincidieron dos escrituras en el mismo milisegundo sobre `META`, generando `TransactionConflict`. Inspeccionamos `CancellationReasons` para distinguir `ConditionalCheckFailed` (chunk duplicado ya procesado, que se ignora) de `TransactionConflict` (contención transitoria en `META`, que se reintenta con *exponential backoff* + *jitter*), logrando `240/240` chunks exactos en `47,50 s`. |
| **4. ¿Cómo resolvieron la restricción de S3 Object Lock en el Learner Lab?** | La sonda `verify-r01` detectó que `LabRole` deniega `s3:PutObjectLockConfiguration` al crear el bucket. Se activó automáticamente la contingencia definida en `ADR-003` y `ADR-005`: **S3 Versioning + Bucket Policy `DenyDeleteAuditReceipts`** (que bloquea `s3:DeleteObject` y `s3:DeleteObjectVersion` sobre `recibos/*`) combinada con la verificación criptográfica SHA-256 de tres niveles (`hash_decision` → `raiz_hash_chunk` → `raiz_hash_lote`). |
| **5. ¿Cómo se concilian las cifras de `0,0158 USD/M`, `0,2483 USD` y `0,25–0,31 USD/M`?** | Corresponden a tres escenarios claramente diferenciados: **1)** `0,25 a 0,31 USD por millón` fue la **estimación teórica previa de diseño** (`E01/E02`) antes de ejecutar en AWS, cuando asumíamos conservadoramente $k=400\text{ órd/s/vCPU}$ (`12,5 s/chunk`). **2)** **`0,0158 USD por millón`** es el **costo unitario real medido en AWS** en la corrida de 1,2M (`0,0189 USD / 1,2M`), que al escalar linealmente por 10 da **`0,1890 USD` para un lote de 12M**. **3)** **`0,2483 USD`** (aprox. `0,25 USD` por lote diario) no es un costo por millón, sino el **costo del lote completo de 12 millones en producción** incluyendo retención mensual en S3 y compactación diaria de Iceberg/Athena, lo que equivale a **`0,0207 USD por millón`** (`0,2483 / 12`). |
| **6. ¿De dónde salen los `4,25 minutos` para 12 millones y qué diferencia hay entre el tiempo medido y el proyectado?** | En la corrida real de 1,2M (`240` chunks con 10 workers), medimos dos tiempos: **a)** la duración media de un chunk en un worker Lambda según CloudWatch (`1,0616 s`, equivalente a $k = 4.710,44\text{ órd/s/vCPU}$ y `25,48 s` de drenaje puro para 240 chunks) y **b)** el tiempo total de reloj extremo a extremo (`47,50 s`, que añade particionador, colas SQS y *backoff* en DynamoDB). Al proyectar a 12 millones (`2.400` chunks con 10 workers): el **tiempo de drenaje puro de cómputo en workers** es $\frac{2.400 \times 1,0616\text{ s}}{10} = 254,78\text{ s} = \mathbf{4,25\text{ minutos}}$, mientras que el **tiempo de reloj extremo a extremo proyectado** (incluyendo sobrecarga de colas y coordinación) es $10 \times 47,50\text{ s} = 475,0\text{ s} = \mathbf{7,92\text{ minutos}}$. Ambos están muy por debajo de la meta de 3 horas (`180 min`). |
