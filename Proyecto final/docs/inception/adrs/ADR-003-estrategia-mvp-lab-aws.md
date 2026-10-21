# ADR-003: Estrategia de Prototipo en AWS Learner Lab y Extrapolación de Capacidad a Escala de Producción
**Estado:** Aprobado  
**Fecha:** 2026-10-21  
**Decisores:** Equipo de Arquitectura Proyecto COIL  
**Fase:** Inception  

---

## 1. Contexto y Enunciado del Problema

El proyecto tiene dos realidades operativas que deben conciliarse con rigor metodológico:
1. **La Propuesta Teórica de Licitación (Target de Producción):** Procesamiento de 12.000.000 de órdenes médicas en menos de 24 horas (o ventana de 3 horas a 1.111 órdenes/s), requiriendo clústeres masivos de cómputo distribuido (ej. EMR con decenas de instancias Graviton, data lakehouse con Apache Iceberg y data warehouse en Redshift).
2. **El Entorno de Validación Práctica (Entregable 3 - Prototipo Funcional):** La plataforma de despliegue y evaluación es el **AWS Academy Learner Lab**, que impone límites estrictos de presupuesto ($100 USD totales), cuotas de vCPU limitadas y restricciones en el aprovisionamiento de clústeres pesados de EMR o instancias de GPU dedicadas para modelos fundacionales LoRA.

Intentar correr los 12 millones de registros en el laboratorio provocaría el agotamiento inmediato de créditos y el bloqueo de la cuenta del laboratorio, imposibilitando la entrega de evidencias.

---

## 2. Alternativas Evaluadas

### Alternativa A: Intentar ejecutar la arquitectura completa de producción en el Lab
* **Descripción:** Levantar clústeres de EMR, Redshift Serverless y modelos LLM pesados en el Learner Lab.
* **Riesgo:** Alto riesgo de fallo catastrófico (exceder límite presupuestario de $100 USD, cuotas denegadas por AWS y fallo en la entrega del proyecto).

### Alternativa B: Prototipo Simulado únicamente en Local (Mocks)
* **Descripción:** Correr simulaciones en la máquina de desarrollo sin usar los servicios de AWS.
* **Riesgo:** Incumple el requisito formal de la rúbrica (el prototipo debe correr en la plataforma del laboratorio de AWS y demostrar métricas reales).

### Alternativa C: Estrategia Prototipo MVP Escalable en Lab + Modelo Formal de Extrapolación a 12M — **SELECCIONADA**
* **Descripción:**
  1. **En el AWS Learner Lab (MVP Práctico):**
     * Desplegar la arquitectura núcleo utilizando servicios permitidos y costo-eficientes: S3 (Data Lake), AWS Lambda / ECS Fargate o AWS Glue / PySpark local en una instancia EC2 optimizada.
     * Ejecutar un pipeline de prueba con un dataset sintético representativo de **100.000 a 1.000.000 de órdenes médicas**.
     * Utilizar un modelo NLP optimizado y cuantizado (ej. spaCy / Transformers ligeros en ONNX o fine-tuned RoBERTa-médico cuantizado en CPU) para garantizar el **F1-score $\ge 0,92$**.
     * Medir el throughput unitario ($\text{órdenes/segundo/vCPU}$), el consumo de memoria y el costo real en centavos de dólar.
  2. **En el Documento de Licitación (Escalamiento Teórico a 12M):**
     * Demostrar matemáticamente que la arquitectura escala horizontalmente de manera lineal:
       $$\text{Nodos Teóricos} = \frac{\text{Throughput Meta (1.111 ops/s)}}{\text{Throughput Medido en Prototipo por Nodo}} \times 1,25$$
     * Extrapolar el costo de producción utilizando AWS Pricing Calculator para instancias Spot Graviton3/4 y almacenamiento en S3 Standard + Glacier.

---

## 3. Decisión

Se adopta la **Alternativa C**:
* El prototipo de laboratorio se concentrará en validar **integridad funcional, BDD, precisión NLP ($\ge 0,92$) y trazabilidad criptográfica** sobre un lote representativo de órdenes sintéticas (100k a 1M).
* El cumplimiento de la meta de los 12 millones y la reducción del 70% de costos se demostrará mediante una memoria de cálculo basada en las métricas de rendimiento observadas en el prototipo.

---

## 4. Consecuencias y Compensaciones

* **Positivas:**
  * Garantiza la viabilidad económica y técnica dentro del saldo del Learner Lab.
  * Proporciona evidencia empírica real (logs, métricas de CloudWatch, matrices de confusión) para el Entregable 3.
  * Cumple plenamente con la exigencia del profesor de tener una metodología rigurosa y defendible.
* **Negativas / Mitigaciones:**
  * El evaluador podría cuestionar la extrapolación si no está bien sustentada. Mitigación: Documentar curvas de escalabilidad empíricas y benchmarks de latencia por etapa.
