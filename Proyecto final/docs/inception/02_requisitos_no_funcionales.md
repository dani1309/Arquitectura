# Especificación de Requisitos No Funcionales (RNF)
**Proyecto:** Arquitectura Distribuida en AWS para Auditoría y Adjudicación Financiera Masiva de Órdenes Médicas (Proyecto COIL - Sistema de Salud de Chernovia)  
**Fase AI-DLC:** Inception  
**Versión:** 1.1.0 (Alineado con el Dataset Oficial COIL 1,2M y Diseño Técnico)  

---

## Matriz de Requisitos No Funcionales Cuantificables

| ID | Atributo de Calidad | Métrica Objetivo (Licitación Producción) | Métrica Objetivo (Prototipo AWS Lab) | Método de Medición / Verificación | Criterio de Aceptación (Pass/Fail) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RNF-01** | **Rendimiento / Throughput** | Procesar **12M órdenes en < 24 h**:<br>• Flujo continuo: $\ge 139\text{ órdenes/s}$<br>• Ventana batch (3 h): $\ge 1.111\text{ órdenes/s}$ | Procesar el dataset oficial **`COIL_dataset_glosas_salud_1_2M.csv` (1.200.000 solicitudes, ~360 MB, 240 chunks de 5.000 órdenes)** midiendo throughput real $k$ ($\text{órdenes/s/vCPU}$). | Benchmark de extremo a extremo y telemetría EMF en CloudWatch midiendo tiempo por chunk y tasa de drenaje. | **Pass:** Los 240 chunks finalizan dentro del SLA sin pérdida de mensajes y proyectan cumplimiento para 12M con $N \le 56$ workers. |
| **RNF-02** | **Precisión NLP (NER)** | **Macro F1-score $\ge 0,92$** en extracción de entidades de la glosa: `Edad`, `PerfilCobertura`, `ServicioSolicitado` y `Medicacion` con sus spans `[start_char, end_char]`. | **Macro F1-score $\ge 0,92$** evaluado sobre el dataset oficial COIL (incluyendo perturbaciones de prueba). | Matriz de confusión, Precision, Recall y Macro F1 por entidad sobre las solicitudes evaluadas. | **Pass:** $\text{F1} \ge 0,92$ global en las entidades extraídas.<br>**Fail:** $\text{F1} < 0,92$. |
| **RNF-03** | **Eficiencia Económica** | **Reducción de costos $\ge 70\%$** frente al costo de auditoría médica manual tradicional ($\approx \$0,80\text{ USD/orden}$). | Costo por millón de órdenes en AWS $\le \$0,50\text{ USD}$ y consumo total del prototipo muy por debajo del límite de **$\$50\text{ USD}$** del Learner Lab. | Modelo de costo unitario (`modelo_capacidad_costo.py`): $\text{Costo Efectivo} = \text{Costo Nube} + f \times \text{Costo Manual}$. | **Pass:** Reducción $\ge 70\%$ manteniendo la fracción de revisión manual $f < 30\%$ y costo de nube $\approx \$0,25 - \$0,31\text{ USD/millón}$. |
| **RNF-04** | **Trazabilidad e Inmutabilidad** | 100% de las decisiones firmadas sobre JSON canónico con: `id_solicitud`, `patient_token`, `catalogo_version`, `modelo_version`, `regla_ids`, spans y `hash_decision` SHA-256. | 100% de las órdenes del dataset de 1,2M generan `hash_decision`, raíz de chunk (`raiz_hash_chunk`) y raíz de lote (`raiz_hash_lote`). | Verificación forense en tres niveles: recalcular hash desde Iceberg/Parquet, contrastar con recibo en S3 WORM y validar raíz del chunk en el manifiesto. | **Pass:** Cero discrepancias en la verificación de integridad criptográfica sobre el 100% de la muestra auditada. |
| **RNF-05** | **Privacidad y Protección PII** | Pseudonimización obligatoria de `DNO` y `SeguroSocial` con `HMAC-SHA256(clave_secreta, ...)` y enmascaramiento de `Paciente`, `DNO` y `SeguroSocial` con `#` de igual longitud. | Ningún archivo en `saom-curated`, `saom-audit`, tabla DynamoDB ni log de CloudWatch contiene nombres, `DNO-XXXXXXXX` ni `SS-XXX-XX-XXXX` en claro. | Escaneo automatizado con expresiones regulares (`DNO-\d+`, `SS-\d{3}-\d{2}-\d{4}`) sobre salidas Parquet, recibos JSONL y logs. | **Pass:** Cero coincidencias de PII en claro fuera del bucket `saom-raw`. |
| **RNF-06** | **Escalabilidad Horizontal** | Escalado automático de workers Lambda (Arm) acoplados a la cola SQS `chunks-adjudicacion`. | Procesamiento paralelo por chunks independientes de 5.000 órdenes con concurrencia controlada en el Learner Lab ($c \le 10$). | Prueba de carga con los 240 chunks en SQS verificando escalado de invocaciones y ausencia de conflictos gracias a claves deterministas. | **Pass:** Escalado lineal sin duplicación de registros ante reintentos de SQS. |

---

## 3. Condiciones de Extrapolación del Laboratorio (1,2M) a Producción (12M)

El entorno de validación es el **AWS Academy Learner Lab**, que cuenta con un presupuesto total de **$\$50\text{ USD}$**, uso obligatorio del rol `LabRole` y restricciones en servicios no listados (como EMR o Fargate).

1. **Factor de Escala Exacto ($1:10$):** El dataset oficial del proyecto (`COIL_dataset_glosas_salud_1_2M.csv`) contiene exactamente **1.200.000 solicitudes** (~360 MB), lo que representa el **10% exacto** del volumen diario de la licitación (12.000.000 de órdenes).
2. **Modelo Matemático de Extrapolación ($M/M/c$):**
   $$\lambda_{\text{3h}} = \frac{12.000.000\text{ órdenes}}{3 \times 3600\text{ s}} \approx 1.111,1\text{ órdenes/segundo}$$
   A partir del throughput unitario $k$ ($\text{órdenes/segundo/vCPU}$) medido empíricamente sobre el dataset de 1,2M, el número de workers concurrentes requeridos en producción se dimensiona con un margen de seguridad del 25%:
   $$N_{\text{workers}} = \left\lceil \frac{1.111,1}{k} \times 1,25 \right\rceil$$
3. **Protección del Presupuesto de $\$50\text{ USD}$:** Procesar los 1,2 millones de registros en AWS Lambda Arm consume menos de **$\$0,35\text{ USD}$** por corrida completa, permitiendo realizar múltiples ejecuciones de prueba y dejar evidencia verificable sin riesgo de agotar el crédito del laboratorio.
