# Especificación de Requisitos No Funcionales (RNF)
**Proyecto:** Arquitectura Distribuida en AWS para Auditoría y Adjudicación Financiera Masiva de Órdenes Médicas (Proyecto COIL)  
**Fase AI-DLC:** Inception  
**Versión:** 1.0.0  

---

## Matriz de Requisitos No Funcionales Cuantificables

| ID | Atributo de Calidad | Métrica Objetivo (Licitación Producción) | Métrica Objetivo (Prototipo AWS Lab) | Método de Medición / Verificación | Criterio de Aceptación (Pass/Fail) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RNF-01** | **Rendimiento / Throughput** | Procesar **12M órdenes en < 24 h**:<br>• Flujo continuo: $\ge 139\text{ órdenes/s}$<br>• Ventana batch (3 h): $\ge 1.111\text{ órdenes/s}$ | Procesar lote de **100.000 a 1.000.000 registros** a un throughput proporcional $\ge 100 - 300\text{ órdenes/s}$. | Benchmark con JMeter / Locust / scripts de carga midiendo tiempo total de pipeline en CloudWatch. | **Pass:** Pipeline finaliza dentro del SLA definido sin pérdida de mensajes ni time-out en los workers. |
| **RNF-02** | **Precisión NLP (NER)** | **Macro F1-score $\ge 0,92$** en extracción de entidades clínicas: paciente, edad, diagnósticos, medicamentos y dosis. | **F1-score $\ge 0,92$** evaluado sobre dataset de prueba sintético con ground truth etiquetado. | Matriz de confusión, Precision, Recall y Macro F1 calculado con scikit-learn / seqeval sobre conjunto de test reservado (20% del dataset). | **Pass:** $\text{F1} \ge 0,92$ global en las 4 entidades clave.<br>**Fail:** $\text{F1} < 0,92$. |
| **RNF-03** | **Eficiencia Económica** | **Reducción de costos $\ge 70\%$** frente al costo de auditoría médica manual tradicional. | Costo por orden procesada en AWS calculado mediante AWS Pricing Calculator y métricas reales de laboratorio. | Fórmula de ahorro: $\frac{\text{Costo Manual} - \text{Costo AWS}}{\text{Costo Manual}} \times 100$.<br>Línea base manual: $\$0,80\text{ USD/orden}$. Meta AWS: $\le \$0,24\text{ USD/orden}$ (idealmente $< \$0,05$). | **Pass:** Reducción porcentual calculada $\ge 70\%$, con desglose detallado de cómputo, storage y data transfer. |
| **RNF-04** | **Trazabilidad e Inmutabilidad** | 100% de las decisiones auditables con: versión de regla, versión de catálogo, spans de texto y hash SHA-256. | 100% de las órdenes del prototipo almacenan payload de auditoría inmutable en S3 Object Lock o tabla de auditoría con hash encadenado. | Auditoría forense automatizada: dada una orden al azar, verificar reconstrucción exacta de la decisión a partir de su log y hash. | **Pass:** Cero discrepancias en la verificación de integridad criptográfica sobre el 100% de la muestra. |
| **RNF-05** | **Privacidad y Protección PII** | Anonimización / Enmascaramiento obligatorio de DNO y nombres antes de etapas de inferencia analítica o almacenamiento no restringido. | Enmascaramiento mediante SHA-256 con salt secreto (`HMAC-SHA256`) o generación sintética libre de datos reales de pacientes. | Inspección de payloads en colas SQS, buckets S3 y logs de CloudWatch para certificar ausencia de texto en claro con datos sensibles. | **Pass:** Cero apariciones de nombres o números de documento legibles en logs ni capas analíticas intermedias. |
| **RNF-06** | **Escalabilidad Horizontal** | Auto-scaling dinámico de nodos de procesamiento para absorber picos de carga sin degradación del throughput. | Escalabilidad demostrable mediante paralelismo de tareas (workers en contenedores/Glue/Lambdas o nodos Spark según permisos del Lab). | Prueba de estrés con ráfagas escalonadas monitoreando CPU/Memory en CloudWatch y crecimiento elástico de workers. | **Pass:** Tiempo medio de respuesta y throughput se mantienen dentro del SLA al duplicar el volumen de entrada. |

---

## 3. Condiciones de Extrapolación del Laboratorio a Producción

Dado que el entorno de desarrollo es el **AWS Academy Learner Lab** (con límites de $100 USD de crédito, cuota restringida de vCPUs y ausencia de ciertos servicios avanzados administrados):
1. **Factor de Escala:** El prototipo valida la corrección funcional, la precisión del NLP y la tasa de throughput por vCPU/worker con un lote de **100.000 a 1.000.000 de órdenes sintéticas**.
2. **Modelo Matemático de Extrapolación:**
   $$\text{Throughput Total Requerido} = \frac{12.000.000\text{ órdenes}}{3 \times 3600\text{ s}} \approx 1.111,1\text{ órdenes/segundo}$$
   Si cada vCPU o worker procesa $k$ órdenes/segundo, la arquitectura teórica de producción dimensiona:
   $$N_{\text{workers}} = \left\lceil \frac{1.111,1}{k} \times 1,25 \right\rceil \quad (\text{con un margen de seguridad del } 25\%)$$
3. **Validación de Presupuesto:** Se presenta el costeo granular comparando el costo de correr el lote masivo en instancias Spot / Graviton frente a la auditoría médica tradicional.
