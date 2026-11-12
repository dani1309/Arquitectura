# Entregable 04: Estructura de Diapositivas y Guion de Sustentación (Pitch Ejecutivo y Técnico)

| Campo | Detalle |
| :--- | :--- |
| **Duración total** | **10 minutos** de presentación + sesión de preguntas del jurado |
| **Expositores** | **Naomi Chow** (Minutos 0:00–3:20) · **Daniel Lopez** (Minutos 3:20–6:50) · **María Fernanda Toro** (Minutos 6:50–10:00) |
| **Demostración en vivo / Evidencia** | Cuenta AWS `329771219583` (`us-east-1`), corrida real de `1.200.000` órdenes en `47,50 s` y tabla Iceberg en Amazon Athena |

---

## 1. Mapa de las 10 Diapositivas y Distribución del Tiempo

| Diapositiva | Título | Expositor(a) | Tiempo | Mensaje Clave / Visual |
| :---: | :--- | :--- | :---: | :--- |
| **1** | Portada y Contexto de la Licitación en Chernovia | **Naomi Chow** | `0:00 – 0:50` | Procesar hasta 12M de órdenes en `< 24 h` (meta del equipo: `3 h` a `1.111 órd/s`), clasificar cobertura y liquidar `100 % / 50 % / 25 % / 0 %`. |
| **2** | Por qué fallan las arquitecturas convencionales (Estado del Arte) | **Naomi Chow** | `0:50 – 2:10` | Orquestar orden por orden con Step Functions + Comprehend Medical cuesta **`244.500 USD/día`** (escalonado AWS) o **`381.000 USD/día`** (Tier 1) y solo soporta inglés; EMR Spot (`~220 USD/día`) excede el Learner Lab (`50 USD`). |
| **3** | Metodología AI-DLC y Requisitos Verificables (`RF` + `RNF`) | **Naomi Chow** | `2:10 – 3:20` | Trazabilidad en 6 pasos con aprobación por etapa: metas del enunciado vs. metas del equipo (`F1 >= 0,92`, `<= 0,50 USD/M`, `0` PII). |
| **4** | Arquitectura Híbrida Serverless por Micro-Lotes (Vista Simplificada) | **Daniel Lopez** | `3:20 – 4:40` | Diagrama `e02_arquitectura_simplificada.png`: S3 Raw → SQS → Particionador por rangos de bytes (`5.000` órd/chunk) → SQS → Workers Lambda `arm64` (`1.769 MB`). |
| **5** | Idempotencia Atómica en DynamoDB y Lección Aprendida en AWS | **Daniel Lopez** | `4:40 – 5:45` | `TransactWriteItems` en `control_lotes` (`PK=LOTE#<id>, SK=CHUNK#<n>`) y hallazgo real: reintento con *exponential backoff* ante `TransactionConflict` en `META`. |
| **6** | Resultados Reales en AWS Learner Lab (`1.200.000` Solicitudes) | **Daniel Lopez** | `5:45 – 6:50` | **`240/240` chunks en `47,50 s`**, $k_{\text{AWS-E2E}} = 4.710,44\text{ órd/s/vCPU}$, `153 MB` RAM, **`0,0189 USD`** totales (`0,0158 USD/M`) y `1.200.000` filas en Apache Iceberg + Athena. |
| **7** | Pipeline Interno del Worker: Privacidad PII y Liquidación `Decimal` | **María Fernanda Toro** | `6:50 – 7:55` | Diagrama `e02_pipeline_worker.png`: `HMAC-SHA256` + enmascaramiento `#` que conserva la longitud exacta de la glosa y los spans `[start_char, end_char]`, más cálculo `Decimal` sin `float`. |
| **8** | Calidad de Extracción Clínica (`Macro-F1 = 0,9886`) | **María Fernanda Toro** | `7:55 – 8:45` | Muestra de 600 glosas fuera de git (`300` limpias con `F1 = 1,0000` + `300` perturbadas en 6 categorías con `F1 = 0,9765` → **`Macro-F1 = 0,9886 >= 0,92`**). |
| **9** | No Repudio Criptográfico de 3 Niveles (`SHA-256`) y Analítica Athena | **María Fernanda Toro** | `8:45 – 9:30` | Verificación desde `saom_analytics.adjudicaciones` en Athena: `hash_decision` → `raiz_hash_chunk` → `raiz_hash_lote` (`100 % OK`) y `57.328.903.464,00` aprobados. |
| **10** | Extrapolación $M/M/c$ a 12M, FinOps y Cierre | **Equipo (Cierre)** | `9:30 – 10:00` | Con $k = 4.710,44$, 10 workers procesan 12M de órdenes en `4,25 min` por **`0,25 USD/día`** (**99,99 %** de ahorro frente a auditoría manual). |

---

## 2. Guion Detallado Palabra por Palabra por Expositor

### Bloque 1 — Naomi Chow (Minutos `0:00` a `3:20`: Problema, Estado del Arte y AI-DLC)

- **[Diapositiva 1 · `0:00–0:50`]**:
  > *"Buenas tardes. Somos Naomi Chow, Daniel Lopez y María Fernanda Toro, y presentamos el Sistema de Adjudicación de Órdenes Médicas (SAOM) para el Sistema Público de Salud de Chernovia. El reto de la licitación exige procesar hasta 12 millones de consultas médicas en menos de 24 horas, extraer de cada glosa clínica la identificación del paciente, la edad, el servicio solicitado y la medicación, cruzar el servicio contra el catálogo normativo vigente (`COV-001` a `COV-020`), liquidar el pago al 100 %, 50 %, 25 % o 0 % según el perfil del afiliado y dejar evidencia auditable de cada centavo aprobado."*
- **[Diapositiva 2 · `0:50–2:10`]**:
  > *"En el Entregable 01 contrastamos 52 referencias técnicas y encontramos por qué las arquitecturas típicas fracasan a esta escala. Primero, si orquestamos orden por orden con AWS Step Functions e invocamos una API cognitiva por caracteres como Amazon Comprehend Medical, cada glosa de 213 caracteres paga el mínimo de 300 caracteres (3 unidades). Para 12 millones de órdenes son 36 millones de unidades diarias: incluso aplicando los tramos oficiales de descuento de AWS, la factura asciende a 244.500 dólares por día (o 381.000 dólares a tarifa plana de Tier 1), y además Comprehend Medical solo procesa inglés. Segundo, levantar un clúster EMR de 384 vCPU cuesta unos 220 dólares diarios y choca con las restricciones del AWS Academy Learner Lab, cuyo presupuesto total es de 50 dólares. Por eso diseñamos una tercera vía: micro-lotes de 5.000 órdenes sobre AWS Lambda Graviton2."*
- **[Diapositiva 3 · `2:10–3:20`]**:
  > *"Trabajamos bajo la metodología AI-DLC en seis pasos trazables. Separamos con rigor los requisitos del enunciado (< 24 horas y costo razonable) de las metas internas de ingeniería de nuestro equipo: ventana batch de 3 horas (`1.111 órdenes/s`), `Macro-F1 >= 0,92` sobre las cuatro entidades clínicas, costo en laboratorio `<= 0,50 USD por millón` y cero exposición de PII. Le doy paso a Daniel para mostrar la arquitectura técnica y la ejecución en vivo en AWS."*

---

### Bloque 2 — Daniel Lopez (Minutos `3:20` a `6:50`: Arquitectura Simplificada, Idempotencia y Corrida de 1,2M en AWS)

- **[Diapositiva 4 · `3:20–4:40`]**:
  > *"Gracias, Naomi. Como se observa en nuestro diagrama de arquitectura simplificada, desacoplamos la ingesta de la adjudicación en 8 pasos. El archivo CSV crudo llega a `saom-raw` y notifica a la cola `lotes-recibidos`. La función `saom-particionador` recorre el archivo en streaming con memoria constante de 4 MB, valida la cabecera de 6 columnas sin cargar los 360 MB en RAM y publica en la cola `chunks-adjudicacion` 240 descriptores livianos que contienen únicamente el rango exacto de bytes `[byte_inicio, byte_fin]` de cada bloque de 5.000 órdenes. Así reducimos en 5.000 veces las llamadas de coordinación. Luego, hasta 10 workers `saom-worker` en AWS Lambda Arm64 (`1.769 MB` = 1 vCPU completa) descargan solo su rango de bytes desde S3 (`Range=bytes=inicio-fin`) y adjudican en paralelo."*
- **[Diapositiva 5 · `4:40–5:45`]**:
  > *"Para garantizar tolerancia a fallos e idempotencia (`RNF-06`), cada worker escribe con claves deterministas en S3 y ejecuta una transacción atómica `TransactWriteItems` en DynamoDB `control_lotes` con la condición `attribute_not_exists(SK) OR estado <> COMPLETADO`. En la prueba en vivo `LOTE-T3-INTEGRACION`, procesamos 10.001 órdenes con una fila corrupta (`CHV-9999999`) en 4,83 segundos: la fila corrupta quedó aislada en `rechazos/` con cero PII y, al reenviar intencionalmente el chunk 0, DynamoDB ignoró el duplicado sin alterar un solo centavo de `META`. Además, al correr los 240 chunks en paralelo en AWS descubrimos que cuando varios workers actualizan el contador `META` en el mismo milisegundo ocurre un `TransactionConflict`; implementamos reintento con exponential backoff distinguiendo conflictos transitorios de duplicados reales."*
- **[Diapositiva 6 · `5:45–6:50`]**:
  > *"Con ese mecanismo corrimos en nuestra cuenta del Learner Lab (`329771219583`) el dataset oficial completo de 1.200.000 solicitudes (`LOTE-COIL-1200K`). Los 240 chunks terminaron en **47,50 segundos** de reloj con cero mensajes en la DLQ. Según los registros `REPORT` de CloudWatch, cada chunk de 5.000 órdenes tardó en promedio **1.061,60 milisegundos** extremo a extremo, lo que arroja un throughput real en la nube de **4.710,44 órdenes por segundo por vCPU** y un consumo máximo de memoria de apenas **153 MB**. Toda la corrida de 1,2 millones de órdenes consumió `505,37 GB-s`, costando **0,0067 dólares en Lambda** y **0,0189 dólares en total** (`0,0158 USD por millón`). Finalmente, consolidamos las 1.200.000 filas en Apache Iceberg con `MERGE INTO` desde Amazon Athena verificando cero duplicados.Continúa María Fernanda con el núcleo clínico, F1 y trazabilidad."*

---

### Bloque 3 — María Fernanda Toro (Minutos `6:50` a `10:00`: Privacidad PII, Evaluación F1 = 0,9886, Cadena SHA-256 y Cierre)

- **[Diapositiva 7 · `6:50–7:55`]**:
  > *"Gracias, Daniel. Dentro de cada worker, nuestro núcleo `saom_core.py` resuelve dos problemas críticos: privacidad clínica y exactitud financiera. Antes de extraer cualquier entidad, el nombre del paciente, el DNO y el Seguro Social se pseudonimizan en un `patient_token` con `HMAC-SHA256` y se reemplazan en la glosa carácter por carácter con el símbolo `#`. Como el reemplazo conserva exactamente la longitud de la cadena, los desplazamientos `[start_char, end_char]` de `Edad`, `PerfilCobertura`, `ServicioSolicitado` y `Medicacion` son idénticos en la glosa original y en la enmascarada, logrando cero coincidencias de PII en S3, DynamoDB y CloudWatch. Y toda la liquidación usa `Decimal` con redondeo financiero `ROUND_HALF_UP`, prohibiendo `float`."*
- **[Diapositiva 8 · `7:55–8:45`]**:
  > *"Para verificar `RNF-02` (`F1 >= 0,92`) sin sesgo, construimos fuera de git una muestra estratificada de 600 glosas (200 por cada integrante): 300 glosas limpias del dataset oficial y 300 glosas sometidas a 6 tipos de perturbación documental (espacios irregulares, cambio de orden de campos, perfiles fuera de catálogo, campos omitidos, ruido OCR en etiquetas y separadores vacíos). Bajo coincidencia exacta de span y valor, obtuvimos `F1 = 1,0000` en las 300 limpias, `F1 = 0,9765` en las 300 perturbadas y un **Macro-F1 global de `0,9886`**, superando ampliamente el umbral de `0,92`."*
- **[Diapositiva 9 · `8:45–9:30`]**:
  > *"En trazabilidad (`RNF-04`), implementamos una cadena SHA-256 de tres niveles: cada orden se firma sobre su JSON canónico (`hash_decision`), cada chunk concatena los hashes ordenados por `id_solicitud` (`raiz_hash_chunk`) y el cierre del lote genera `raiz_hash_lote` en el manifiesto WORM de `saom-audit`. Desde Amazon Athena consultamos las 1.200.000 órdenes en Iceberg —que suman `1,58 billones` reclamados y `57.328 millones` aprobados en los tres días del lote— y comprobamos los tres niveles criptográficos de punta a punta."*
- **[Diapositiva 10 · `9:30–10:00`]**:
  > *"En conclusión, al introducir el throughput real medido en AWS ($k = 4.710,44\text{ órdenes/s/vCPU}$) en nuestro modelo de colas $M/M/c$, procesar los 12 millones de órdenes de la licitación toma apenas **4,25 minutos** con 10 workers y cuesta **0,25 dólares por lote diario**, cumpliendo todos los requisitos funcionales y no funcionales con 36 pruebas automatizadas y evidencia real en AWS. Muchas gracias; quedamos atentos a sus preguntas."*

---

## 3. Banco de Defensa Técnica (Preguntas Frecuentes del Jurado)

| Posible Pregunta del Jurado | Respuesta Técnica Concreta con Datos del Proyecto |
| :--- | :--- |
| **1. ¿Por qué usaron un parser determinista en lugar de un LLM o Comprehend Medical?** | Porque las glosas de Chernovia siguen una plantilla semiestructurada de 7 campos (`ADR-004`). Un parser determinista logra `F1 = 1,0000` en la plantilla oficial (`0,9886` incluyendo ruido OCR/permutación), procesa a `4.710 órdenes/s/vCPU` con `0,0158 USD/millón` y ofrece explicabilidad determinista (`regla_ids` + spans), mientras que Comprehend Medical cuesta `244.500 USD/día` y solo soporta inglés. Si una glosa llega truncada o alterada por OCR en un campo obligatorio, el sistema activa `AUDIT_FLAG_CLINICAL_UNCERTAINTY` y la deriva a revisión humana de segunda línea. |
| **2. ¿Cómo garantizan que el enmascaramiento de PII no desplace los spans `[start_char, end_char]`?** | En `extraer_y_pseudonimizar_glosa()` (`prototype/saom_core.py`), los valores de `Paciente`, `DNO` y `SeguroSocial` se sustituyen carácter por carácter por `'#' * len(valor)`. Como la longitud en caracteres antes y después de cada `;` permanece invariante, cualquier índice `glosa[start_char:end_char]` apunta exactamente a la misma subcadena clínica, lo cual está verificado en `test_t1_spans_iguales_en_glosa_original_y_enmascarada`. |
| **3. ¿Qué ocurrió en DynamoDB cuando corrieron los 240 chunks en paralelo en AWS?** | Los 10 workers concurrentes intentaban actualizar atómicamente su registro `CHUNK#` y sumar al contador único `META` del lote mediante `TransactWriteItems`. En 6 de los 240 chunks coincidieron dos escrituras en el mismo milisegundo sobre `META`, generando `TransactionConflict`. Inspeccionamos `CancellationReasons` para distinguir `ConditionalCheckFailed` (chunk duplicado ya procesado, que se ignora) de `TransactionConflict` (contención transitoria en `META`, que se reintenta con *exponential backoff* + *jitter*), logrando `240/240` chunks exactos en `47,50 s`. |
| **4. ¿Cómo resolvieron la restricción de S3 Object Lock en el Learner Lab?** | La sonda `verify-r01` detectó que `LabRole` deniega `s3:PutObjectLockConfiguration` al crear el bucket. Se activó automáticamente la contingencia definida en `ADR-003` y `ADR-005`: **S3 Versioning + Bucket Policy `DenyDeleteAuditReceipts`** (que bloquea `s3:DeleteObject` y `s3:DeleteObjectVersion` sobre `recibos/*`) combinada con la verificación criptográfica SHA-256 de tres niveles (`hash_decision` → `raiz_hash_chunk` → `raiz_hash_lote`). |
