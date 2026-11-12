# Evidencia de Ejecución Real en AWS Academy Learner Lab (Tareas T3, T4 y T6)

| Campo | Valor |
| :--- | :--- |
| **Fecha de ejecución UTC** | `2026-11-11 23:58:04 UTC` |
| **Cuenta AWS Learner Lab** | `329771219583` (`arn:aws:sts::329771219583:assumed-role/voclabs/user5274396=daniel_lopez`) |
| **Región y Rol IAM** | `us-east-1` · `arn:aws:iam::329771219583:role/LabRole` |
| **Paquete desplegado** | `prototype/dist/saom_lambda_bundle.zip` (`17.737 bytes`, SHA-256 `2fc3dc25d1d0f38b7f5d790135a2bdfa7725827040f5be560bb893c538ff45b6`) |
| **Evidencia cruda JSON** | [`docs/verificacion/resultados_aws_t3_t4_t6.json`](resultados_aws_t3_t4_t6.json) |

---

## 1. Inventario de Recursos Desplegados en AWS (`us-east-1`)

| Servicio AWS | Recurso / Identificador Real | Configuración Aplicada |
| :--- | :--- | :--- |
| **Amazon S3 (Raw)** | `s3://saom-raw-329771219583` | `BlockPublicAccess=True`, almacena lotes CSV en `ingesta/fecha=YYYY-MM-DD/lote=<id>.csv` |
| **Amazon S3 (Ref)** | `s3://saom-ref-329771219583` | `Versioning=Enabled`, almacena `catalogo/version=COIL-2026.1/*.csv` |
| **Amazon S3 (Curated)** | `s3://saom-curated-329771219583` | `staging/`, `rechazos/` y tabla Apache Iceberg `iceberg/adjudicaciones/` |
| **Amazon S3 (Audit WORM)** | `s3://saom-audit-329771219583` | `Versioning=Enabled` + Bucket Policy `DenyDeleteAuditReceipts` (`s3:DeleteObject`, `s3:DeleteObjectVersion`) |
| **Amazon SQS (Ingesta)** | `https://sqs.us-east-1.amazonaws.com/329771219583/lotes-recibidos` | `VisibilityTimeout=1800 s`, dispara `saom-particionador` |
| **Amazon SQS (Trabajo)** | `https://sqs.us-east-1.amazonaws.com/329771219583/chunks-adjudicacion` | `VisibilityTimeout=1800 s`, `maxReceiveCount=3` hacia DLQ, dispara `saom-worker` |
| **Amazon SQS (DLQ)** | `https://sqs.us-east-1.amazonaws.com/329771219583/chunks-adjudicacion-dlq` | Cola de mensajes fallidos para diagnóstico |
| **Amazon DynamoDB** | `control_lotes` (`PAY_PER_REQUEST`) | Clave primaria compuesta `(PK, SK)` para `META` y `CHUNK#00000..00239` |
| **AWS Lambda (Particionador)** | `saom-particionador` (`python3.12`, `arm64`) | `1.769 MB` (1 vCPU Graviton2), `Timeout=300 s`, `LabRole` |
| **AWS Lambda (Worker)** | `saom-worker` (`python3.12`, `arm64`) | `1.769 MB` (1 vCPU Graviton2), `Timeout=300 s`, `MaximumConcurrency=10` en SQS |
| **AWS Glue / Athena** | `saom_analytics.adjudicaciones` | Tabla **Apache Iceberg** (`Parquet`) consultada mediante Amazon Athena |

---

## 2. Resultado de la Tarea T3: Prueba de Integración e Idempotencia (`LOTE-T3-INTEGRACION`)

Se cargó en `s3://saom-raw-329771219583/ingesta/fecha=2026-11-11/lote=LOTE-T3-INTEGRACION.csv` (`2.990.464 bytes`) un lote con **10.000 órdenes válidas + 1 fila malformada (`CHV-9999999` con valor negativo `-15000`)**, dividido en **3 chunks** (`chunk=00000` con 5.000 filas, `chunk=00001` con 5.000 filas y `chunk=00002` con 1 fila):

| Métrica / Criterio Verificable (`T3`) | Valor Medido en AWS | Estado |
| :--- | :--- | :--- |
| **Tiempo extremo a extremo (S3 → SQS → Lambda → DynamoDB)** | **`4,83 segundos`** | **CUMPLE** |
| **Estado final en `control_lotes` (`PK=LOTE#LOTE-T3-INTEGRACION`)** | `PROCESADO` (`chunks_completados = 3 / 3`) | **CUMPLE** |
| **Órdenes válidas / Órdenes rechazadas** | `10.000` válidas / `1` rechazada (`10.001` totales) | **CUMPLE** |
| **Aislamiento de fila malformada en `rechazos/`** | `{"id_solicitud": "CHV-9999999", "estado": "REJECTED_SYNTAX", "motivo": "valor_procedimiento inválido"}` | **CUMPLE** |
| **PII en claro dentro de `rechazos/` (`RNF-05`)** | **`0` coincidencias** | **CUMPLE** |
| **Mensajes en DLQ (`chunks-adjudicacion-dlq`)** | **`0` mensajes** | **CUMPLE** |
| **Prueba de idempotencia (`RNF-06`, reenvío de `chunk_id=0`)** | `duplicados_ignorados = 1`, `chunks_procesados = 0`; contadores `META` inalterados (`suma_aprobada = 475070357.5`) | **CUMPLE** |
| **Raíz SHA-256 del lote (`raiz_hash_lote`)** | `6a80888fc96d1909d081beeed5e299dbc341205207bc07daeadc3f12fafddf4a` | **CUMPLE** |

---

## 3. Resultado de la Tarea T4: Corrida Completa del Dataset Oficial (`LOTE-COIL-1200K` · 1.200.000 Solicitudes)

Se subió el dataset oficial `COIL_dataset_glosas_salud_1_2M.csv` (`360.354.593 bytes`) a `s3://saom-raw-329771219583/ingesta/fecha=2026-11-11/lote=LOTE-COIL-1200K.csv`. `saom-particionador` generó **240 descriptores de chunk de 5.000 órdenes** en SQS `chunks-adjudicacion`, que fueron drenados en paralelo por `saom-worker` (`MaximumConcurrency=10`):

| Métrica / Criterio Verificable (`T4`) | Valor Medido en AWS | Estado frente a Requisitos |
| :--- | :--- | :--- |
| **Chunks completados / Chunks totales** | **`240 / 240`** (`estado = PROCESADO`) | **CUMPLE** (100 % de los chunks) |
| **Órdenes válidas + rechazadas contabilizadas** | **`1.200.000` válidas + `0` rechazadas = `1.200.000`** | **CUMPLE** (`RF-01`, `RNF-06`) |
| **Órdenes con incertidumbre clínica (`f`)** | `0` (`f = 0,0000` en plantilla limpia oficial) | **CUMPLE** (`RNF-03`: $f \le 0,30$) |
| **Suma total reclamada (`Decimal`)** | **`1.583.859.890.309,00`** | Exactitud centesimal (`RF-04`) |
| **Suma total aprobada (`Decimal`)** | **`57.328.903.464,00`** | Exactitud centesimal (`RF-04`) |
| **Raíz criptográfica del lote (`raiz_hash_lote`)** | `78dbff2ea6b365f3399315b1377111bc3ec23939ce539a101378b3f8b648869e` | **CUMPLE** (`RF-05`, `RNF-04`) |
| **Manifiesto WORM en `saom-audit`** | `s3://saom-audit-329771219583/manifiestos/lote=LOTE-COIL-1200K.json` (con las 240 `raiz_hash_chunk`) | **CUMPLE** |
| **Mensajes en DLQ (`chunks-adjudicacion-dlq`)** | **`0` mensajes** | **CUMPLE** |
| **Tiempo de reloj (muro) de la corrida (10 workers)** | **`47,50 segundos`** (`0,79 minutos`) | **CUMPLE** (SLA prototipo $\le 2,4\text{ h}$) |
| **Duración media por chunk en CloudWatch (`REPORT`)** | **`1.061,60 ms`** (`1,06 s` por bloque de 5.000 órdenes con I/O S3+DDB) | **CUMPLE** |
| **Throughput real E2E en CloudWatch ($k_{\text{AWS-E2E}}$)** | **`4.710,44 órdenes/s/vCPU`** (`5.000 / 1,0616 s`) | Supera **11,8x** la hipótesis $k \ge 400$ (`P-07`) |
| **Throughput del núcleo en memoria ($k_{\text{EMF-Core}}$)** | **`14.279,66 órdenes/s/vCPU`** (métrica EMF `ThroughputOrdenesPorSegundo`) | **CUMPLE** |
| **Memoria máxima consumida en Lambda (`Max Memory Used`)** | **`153,0 MB`** (sobre `1.769 MB` asignados = 8,6 % de uso) | Sin riesgo de OOM |
| **Cómputo total facturado en Lambda (`Billed Duration`)** | `292.540 ms` = **`505,37 GB-s`** (`0,0067 USD` en Arm64) | **CUMPLE** |
| **Costo total real de la corrida de 1,2M en AWS** | **`0,0189 USD`** (`0,0067 USD` Lambda + `0,0122 USD` S3/SQS/DDB = **`0,0158 USD/M`**) | **CUMPLE** (`RNF-03`: $\le 0,50\text{ USD/M}$) |
| **Escaneo de PII en S3, DynamoDB y CloudWatch (`RNF-05`)** | **`0` coincidencias de PII en claro** | **CUMPLE** (`RNF-05`) |

---

## 4. Resultado de la Tarea T6: Consolidación en Apache Iceberg y Consultas en Amazon Athena

Se creó en AWS Glue Data Catalog la base de datos `saom_analytics`, la tabla externa `staging_adjudicaciones` y la tabla **Apache Iceberg (`Parquet`)** `saom_analytics.adjudicaciones` sobre `s3://saom-curated-329771219583/iceberg/adjudicaciones/`:

1. **Idempotencia de `MERGE INTO` (`RNF-06`)**:
   - Filas en `saom_analytics.adjudicaciones` tras el primer `MERGE INTO`: **`1.200.000` filas**.
   - Filas en `saom_analytics.adjudicaciones` tras repetir `MERGE INTO` sobre `chunk_id = 0`: **`1.200.000` filas** (`0` filas duplicadas).

2. **Consulta Analítica 1 — Liquidación por `dia_solicitud` en Athena**:

| Día de Solicitud | Órdenes Adjudicadas | Total Reclamado | Total Aprobado |
| :--- | ---: | ---: | ---: |
| `2026-05-04` | 402.000 | 529.215.196.182,00 | 19.155.939.616,75 |
| `2026-05-05` | 396.000 | 522.711.751.027,00 | 18.950.939.658,50 |
| `2026-05-06` | 402.000 | 531.932.943.100,00 | 19.222.024.188,75 |
| **Total Lote Oficial** | **1.200.000** | **1.583.859.890.309,00** | **57.328.903.464,00** |

3. **Consulta Analítica 2 — Liquidación por `medio_emisor` en Athena**:

| Medio Emisor | Órdenes Adjudicadas | Total Reclamado | Total Aprobado |
| :--- | ---: | ---: | ---: |
| `Portal Ciudadano` | 336.326 | 444.237.492.166,00 | 16.056.799.788,75 |
| `Hospital Público` | 240.427 | 317.767.457.864,00 | 11.498.647.265,75 |
| `App Móvil Salud` | 216.232 | 285.142.528.571,00 | 10.337.148.686,25 |
| `Clínica Aliada` | 143.938 | 190.275.498.761,00 | 6.860.234.214,75 |
| `Farmacia Aliada` | 95.818 | 127.393.050.151,00 | 4.586.382.661,00 |
| `Call Center` | 83.696 | 109.398.141.612,00 | 4.012.726.904,25 |
| `Ventanilla Física` | 83.563 | 109.645.721.184,00 | 3.976.963.943,25 |

4. **Verificación Criptográfica de 3 Niveles desde Filas de Iceberg (`RNF-04`, Sección 7.4)**:

| `id_solicitud` | `hash_decision` en Iceberg (`Athena`) | Nivel 1 (`hash_decision`) | Nivel 2 (`raiz_hash_chunk`) | Nivel 3 (`raiz_hash_lote`) |
| :--- | :--- | :---: | :---: | :---: |
| `CHV-0000001` | `fd94a57f2baba2dbd7c381b1983a05ce6f8a956b77bea375052e59b1c895a6af` | **OK** | **OK** | **OK** |
| `CHV-0000002` | `c34c069ad05c55dab953b0837463c0206d9994c1612e3e645c2c781314be7a67` | **OK** | **OK** | **OK** |
| `CHV-0000003` | `41980f2d4358ea8d3043b43ecadf9f0ad789b60cf118579139f24fecd5782ba9` | **OK** | **OK** | **OK** |
| `CHV-0000004` | `ec5e40399cc42965809881dd78b23ad2630f5e1193f2a6326748111ced7b836f` | **OK** | **OK** | **OK** |
| `CHV-0000005` | `142c2046b098973376926ee17a04fce6a6c378d6b184fae93a39ad68d2b92309` | **OK** | **OK** | **OK** |
