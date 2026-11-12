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

| Escenario y Ventana (12M órdenes) | $\lambda$ (órdenes/s) | $k$ (órd/s/vCPU) | $N$ workers ($M/M/c$) | Utilización $\rho$ | $P(\text{espera})$ | $W_q$ (cola) | Tiempo servicio / chunk |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Hipótesis Conservadora `P-07` — 24 h** | 138.89 | 400.00 | **1** | 0.3472 | 0.3472 | 6.649 s | 12.50 s |
| **Hipótesis Conservadora `P-07` — 3 h** | 1111.11 | 400.00 | **4** (`c=10` con 2,5x) | 0.6944 | 0.4201 | 4.296 s | 12.50 s |
| **Medición Real AWS CloudWatch — 24 h** | 138.89 | 4710.44 | **1** | 0.0295 | 0.0295 | 0.032 s | 1.06 s |
| **Medición Real AWS CloudWatch — 3 h** | 1111.11 | 4710.44 | **1** (`c=10` configurado) | 0.2359 | 0.2359 | 0.328 s | 1.06 s |

---

## 4. Costo Real Medido en AWS frente al Presupuesto de 50 USD (`RNF-03`)

| Escenario | Cómputo Lambda Arm64 | S3 + SQS + DynamoDB + Athena | Costo Total Nube | Costo por Millón | Meta `RNF-03` ($\le 0,50\text{ USD/M}$) |
| :--- | ---: | ---: | ---: | ---: | :--- |
| **Corrida Real Prototipo en AWS (1,2M · 240 chunks, `505,37 GB-s`)** | **0.0067 USD** | 0,0122 USD | **0.0189 USD** | **0.0158 USD/M** | **CUMPLE** (0,038 % del crédito de 50 USD) |
| **Corrida Prototipo ($k=400$ conservador de diseño)** | 0.0691 USD | 0,0122 USD | **0.0813 USD** | 0.0734 USD/M | **CUMPLE** |
| **Producción Licitación (12M · 2.400 chunks, con $k_{\text{AWS}}=4.710,44$)** | **0.0587 USD** | 0,1896 USD | **0.2483 USD** | **0.0207 USD/M** | **CUMPLE** |
| **Producción Licitación (12M · 2.400 chunks, con $k=400$ conservador)** | 0.6910 USD | 0,1896 USD | **0.8806 USD** | **0.0734 USD/M** | **CUMPLE** |
