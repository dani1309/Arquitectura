# Informe de Verificación de Métricas: F1-Score, Rendimiento `k`, Costo y Extrapolación M/M/c (Tarea T5)

| Campo | Valor |
| :--- | :--- |
| **Tarea del plan** | **T5** — Métricas F1 contra la muestra, costo y extrapolación $M/M/c$ (`docs/plan/04_plan_construccion.md`) |
| **Requisitos verificados** | `RNF-01` (SLA y modelo $M/M/c$), `RNF-02` ($\text{Macro-F1} \ge 0,92$), `RNF-03` ($\le 0,50\text{ USD/M}$ y $f \le 0,30$) |
| **Script ejecutable** | [`prototype/evaluacion_f1_t5.py`](../../prototype/evaluacion_f1_t5.py) |

---

## 1. Evaluación de Calidad de Extracción Clínica (`RNF-02`: Meta $\text{F1} \ge 0,92$)

### 1.1. Resultado Global sobre las 600 Glosas (`300 Limpias + 300 Perturbadas`)

| Entidad Clínica | TP | FP | FN | Precision | Recall | F1-Score |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `Edad` | 574 | 0 | 13 | 1.0000 | 0.9779 | **0.9888** |
| `PerfilCobertura` | 574 | 0 | 13 | 1.0000 | 0.9779 | **0.9888** |
| `ServicioSolicitado` | 576 | 0 | 12 | 1.0000 | 0.9796 | **0.9897** |
| `Medicacion` | 1359 | 0 | 35 | 1.0000 | 0.9749 | **0.9873** |
| **Promedio Macro** | — | — | — | **1.0000** | **0.9776** | **0.9886** |

- **Macro-F1 Global (600 glosas)**: **`0.9886`** (Meta `RNF-02`: $\ge 0,9200$) → **CUMPLE**.

### 1.2. Desglose en Subconjunto Limpio (`300 Glosas Oficiales COIL`)

| Entidad Clínica | TP | FP | FN | Precision | Recall | F1-Score |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `Edad` | 300 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| `PerfilCobertura` | 300 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| `ServicioSolicitado` | 300 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| `Medicacion` | 710 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| **Promedio Macro** | — | — | — | **1.0000** | **1.0000** | **1.0000** |

- En glosas limpias que siguen la plantilla oficial COIL, el parser determinista alcanza **`F1 = 1.0000`**, confirmando la hipótesis `P-05` del plan de construcción.

### 1.3. Desglose en Subconjunto Perturbado (`300 Glosas con Ruido / Permutación / OCR`)

| Entidad Clínica | TP | FP | FN | Precision | Recall | F1-Score |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `Edad` | 274 | 0 | 13 | 1.0000 | 0.9547 | **0.9768** |
| `PerfilCobertura` | 274 | 0 | 13 | 1.0000 | 0.9547 | **0.9768** |
| `ServicioSolicitado` | 276 | 0 | 12 | 1.0000 | 0.9583 | **0.9787** |
| `Medicacion` | 649 | 0 | 35 | 1.0000 | 0.9488 | **0.9737** |
| **Promedio Macro** | — | — | — | **1.0000** | **0.9541** | **0.9765** |

- En el subconjunto perturbado, el extractor resuelve con `Precision = 1,0000` las variaciones de espaciado (`P1`), el cambio de orden de campos (`P2`), los perfiles desconocidos (`P3`), los campos omitidos (`P4`) y los separadores vacíos (`P6`). Los únicos falsos negativos ocurren cuando el ruido OCR altera directamente el nombre de la clave antes de `:` (`P5_ETIQUETA_ALTERADA_OCR`), manteniendo un **Macro-F1 en perturbadas de `0.9765`** ($\ge 0,92$).

---

## 2. Fracción de Revisión Manual $f$ y Viabilidad Económica (`RNF-03`)

- **En el dataset oficial COIL (plantilla limpia)**: $f = 0.0000$ ($0,00\%$ de órdenes con `AUDIT_FLAG_CLINICAL_UNCERTAINTY`), lo que arroja un ahorro del **99,99 %** frente a la línea base de auditoría manual ($0,80\text{ USD/orden}$).
- **En la muestra combinada de estrés (con 50 % de glosas perturbadas)**: $f = 0.1667$ (100 de 600 glosas marcadas para revisión humana de segunda línea por campos omitidos o alterados por OCR), muy por debajo del umbral máximo permitido de **$f \le 0,3000$ (30 %)** de `RNF-03`.

---

## 3. Medición Empírica de Throughput $k$ en AWS CloudWatch y Recálculo $M/M/c$ hacia 12 Millones (`RNF-01`)

En la corrida real del dataset oficial `LOTE-COIL-1200K` (`1.200.000` solicitudes en `240` chunks de 5.000 órdenes sobre AWS Lambda `arm64` de `1.769 MB` en la cuenta `329771219583`, ver [`T3_T4_T6_ejecucion_real_aws.md`](T3_T4_T6_ejecucion_real_aws.md)):

- **Duración media real por chunk en CloudWatch (`REPORT Duration`, incluyendo lectura S3 Range + adjudicación + escritura S3 + `TransactWriteItems` en DynamoDB)**: **`1.061,60 ms` (`1,0616 s`)**.
- **Throughput E2E real medido en AWS CloudWatch ($k_{\text{AWS-E2E}}$)**: **`4.710,44 órdenes/s/vCPU`** (y **`14.279,66 órdenes/s/vCPU`** en el núcleo puro de adjudicación según la métrica EMF `ThroughputOrdenesPorSegundo`), superando **11,8 veces** la hipótesis conservadora de diseño $k \ge 400\text{ órdenes/s/vCPU}$ (`P-07`).
- **Tiempo de reloj (muro) de la corrida de 1,2M en AWS (`MaximumConcurrency=10`)**: **`47,50 segundos`** (frente al SLA de `2,4 horas` de `P-16`).

### 3.1. Diferenciación entre Rendimiento Medido (`1,2M`) y Proyectado (`12M`) — Derivación de los `4,25 min` y `7,92 min`

Para evitar cualquier ambigüedad entre las métricas empíricas obtenidas en la cuenta `329771219583` y las proyecciones hacia la escala de licitación (`12.000.000` de órdenes), la tabla siguiente separa explícitamente qué se midió y cómo se calcula cada tiempo proyectado:

| Magnitud | Tipo | Escala | Valor | Fórmula / Origen Exacto |
| :--- | :---: | :---: | ---: | :--- |
| **Duración media por chunk ($T_{\text{chunk}}$)** | **Medido (CloudWatch)** | 1 chunk (`5.000` órd.) | **`1.061,60 ms`** (`1,0616 s`) | Promedio de los registros `REPORT Duration` de `saom-worker` (`1.769 MB` = `1 vCPU`) en CloudWatch Logs. |
| **Throughput unitario E2E ($k_{\text{AWS-E2E}}$)** | **Medido (CloudWatch)** | 1 worker (`1 vCPU`) | **`4.710,44 órd/s/vCPU`** | $k_{\text{AWS-E2E}} = \frac{5.000\text{ órdenes}}{1,0616\text{ s}} = 4.710,44\text{ órdenes/s/vCPU}$. |
| **Tiempo de drenaje puro de cómputo (`1,2M`)** | **Medido (CloudWatch)** | `1,2M` (`240` chunks, `c=10`) | **`25,48 s`** (`0,42 min`) | $T_{\text{drenaje, 1.2M}} = \frac{240\text{ chunks} \times 1,0616\text{ s}}{10\text{ workers}} = 25,48\text{ s}$ de CPU efectiva en workers. |
| **Tiempo de reloj extremo a extremo (`1,2M`)** | **Medido (Reloj E2E)** | `1,2M` (`240` chunks, `c=10`) | **`47,50 s`** (`0,79 min`) | Tiempo real desde la carga del CSV hasta `chunks_completados = 240` (suma `25,48 s` de drenaje + `3,40 s` del particionador + `18,62 s` de *cold starts*, colas SQS y *backoff* en 6 chunks con `TransactionConflict`). |
| **Tiempo de drenaje puro de cómputo (`12M`)** | **Proyectado ($M/M/c$)** | `12M` (`2.400` chunks, `c=10`) | **`254,78 s` (`4,25 min`)** | $T_{\text{drenaje, 12M}} = \frac{2.400\text{ chunks} \times 1,0616\text{ s}}{10\text{ workers}} = \frac{12.000.000\text{ órd.}}{10 \times 4.710,44\text{ órd/s}} = 254,78\text{ s} = \mathbf{4,25\text{ min}}$. |
| **Tiempo de reloj extremo a extremo (`12M`)** | **Proyectado (Lineal E2E)** | `12M` (`2.400` chunks, `c=10`) | **`475,00 s` (`7,92 min`)** | $T_{\text{reloj, 12M}} = 10 \times T_{\text{reloj, 1.2M}} = 10 \times 47,50\text{ s} = 475,0\text{ s} = \mathbf{7,92\text{ min}}$ (incluyendo particionador, SQS y reintentos DynamoDB). |

| Escenario y Ventana (12M órdenes) | $\lambda$ (órdenes/s) | $k$ (órd/s/vCPU) | $N$ workers ($M/M/c$) | Utilización $\rho$ | $P(\text{espera})$ | $W_q$ (cola) | Tiempo servicio / chunk | Drenaje puro (`c=10`) | Reloj E2E proyectado (`c=10`) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Hipótesis Conservadora `P-07` — 24 h** | 138,89 | 400,00 | **1** | 0,3472 | 0,3472 | 6,649 s | 12,50 s | 50,00 min | ~55,00 min |
| **Hipótesis Conservadora `P-07` — 3 h** | 1.111,11 | 400,00 | **4** (`c=10` con 2,5x) | 0,6944 | 0,4201 | 4,296 s | 12,50 s | 50,00 min | ~55,00 min |
| **Con $k$ Medido en AWS — 24 h** | 138,89 | 4.710,44 | **1** | 0,0295 | 0,0295 | 0,032 s | 1,06 s | **4,25 min** | **7,92 min** |
| **Con $k$ Medido en AWS — 3 h** | 1.111,11 | 4.710,44 | **1** (`c=10` configurado) | 0,2359 | 0,2359 | 0,328 s | 1,06 s | **4,25 min** | **7,92 min** |

---

## 4. Conciliación y Unificación de las Cifras Económicas (`RNF-03`)

A lo largo del ciclo AI-DLC aparecen cuatro cifras económicas que corresponden a momentos y escalas distintas del proyecto. La tabla siguiente las unifica en un único marco coherente, diferenciando **el costo por millón (`USD/M`)** del **costo por lote completo (`1,2M` vs. `12M`)**:

| Escenario Económico | Tipo de Cifra | Volumen del Lote | Cómputo Lambda Arm64 | S3 + SQS + DynamoDB + Athena / Operación | **Costo Total del Lote** | **Costo Unitario por Millón (`USD/M`)** | Explicación y Origen de la Cifra |
| :--- | :---: | :---: | ---: | ---: | ---: | ---: | :--- |
| **1. Estimación Teórica Previa (Diseño E01/E02 con $k=400$)** | Estimado pre-ejecución | `1.200.000` (`240` chunks) | `0,0691 USD` (`~5.184 GB-s`) | `0,2309 USD` (incluyendo margen operativo inicial) | **`~0,3000 USD`** | **`0,25 – 0,31 USD/M`** | Estimación inicial en `ADR-003` y `RNF-03` (`P-06`) antes de ejecutar en AWS, asumiendo conservadoramente `12,50 s/chunk` ($k=400$). |
| **2. Corrida Real en AWS Learner Lab (`LOTE-COIL-1200K`)** | **Medido en AWS** | `1.200.000` (`240` chunks) | **`0,0067 USD`** (`505,37 GB-s` reales) | **`0,0122 USD`** (`S3` `0,0025` + `DDB` `0,0012` + `SQS` `0,0002` + `CW/Athena` `0,0083`) | **`0,0189 USD`** | **`0,0158 USD/M`** | **Costo real medido** en la cuenta `329771219583`: $\frac{0,0189\text{ USD}}{1,2\text{ M}} = \mathbf{0,0158\text{ USD/M}}$ (16 veces menor que el estimado previo porque $k$ real fue `4.710,44`). |
| **3. Escalamiento Lineal Directo `10×` a Producción (`12M`)** | Proyectado lineal puro | `12.000.000` (`2.400` chunks) | **`0,0674 USD`** (`5.053,7 GB-s`) | **`0,1216 USD`** (`10 ×` solicitudes S3, SQS, DynamoDB y CloudWatch) | **`0,1890 USD`** | **`0,0158 USD/M`** | Multiplicación directa $10 \times 0,0189\text{ USD}$ de los mismos servicios ejecutados en el prototipo. |
| **4. Producción Completa `12M` con Sobrecarga Operativa** | **Proyectado producción** | `12.000.000` (`2.400` chunks) | **`0,0587 USD`** (`2.400` chunks $\times 1,0616\text{ s}$) | **`0,1896 USD`** (añade retención S3 30 días, compactación diaria Iceberg/Athena y API Gateway) | **`0,2483 USD`** (`~0,25 USD/lote`) | **`0,0207 USD/M`** | **`0,2483 USD` (`~0,25 USD`) es el costo del lote diario completo de 12 millones**, lo que equivale a **`0,0207 USD por millón`** ($\frac{0,2483\text{ USD}}{12\text{ M}}$), cumpliendo holgadamente la meta $\le 0,50\text{ USD/M}$. |
