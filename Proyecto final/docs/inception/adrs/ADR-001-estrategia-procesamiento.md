# ADR-001: Selección del Patrón de Procesamiento (Batch vs. Ingesta Continua vs. Arquitectura Híbrida)
**Estado:** Aprobado  
**Fecha:** 2026-10-21  
**Decisores:** Equipo de Arquitectura Proyecto COIL  
**Fase:** Inception  

---

## 1. Contexto y Enunciado del Problema

El sistema de auditoría del pagador estatal debe liquidar **12 millones de órdenes médicas en menos de 24 horas**. Existen dos patrones operativos en la operación real de salud pública:
1. **Flujo Continuo:** Las IPS van radicando órdenes a lo largo del día (~139 órdenes/segundo en promedio sostenido).
2. **Ventana Nocturna / Batch:** Las IPS consolidan su facturación al cierre del turno o mes, enviando grandes volúmenes en bloque que deben liquidarse en una ventana de 3 horas (~1.111 órdenes/segundo).

El enunciado de la licitación y la cátedra exigen una justificación metodológica y económica explícita entre procesamiento por lotes, continuo o híbrido, demostrando escalabilidad, resiliencia y razonabilidad económica.

---

## 2. Alternativas Evaluadas

### Alternativa A: Procesamiento por Lotes Puro (Scheduled Heavy Batch)
* **Descripción:** Las órdenes se acumulan en un repositorio de archivos (S3) durante el día y a una hora fija (ej. 11:00 PM) se levanta un clúster de cómputo masivo (ej. EMR / Spark) para procesar todo el lote de golpe.
* **Ventajas:**
  * Uso de instancias Spot temporales que se apagan al terminar, optimizando el costo unitario.
  * Facilidad para jobs de agregación global y balance financiero al final del ciclo.
* **Desventajas:**
  * Crea cuellos de botella extremos y picos masivos de demanda de vCPUs en ventana corta.
  * Si un fallo ocurre tarde en la ventana de 3 horas, el riesgo de incumplir el SLA de 24h es crítico.
  * Inflexible para prestadores que requieren confirmación temprana de recepción y validación sintáctica.

### Alternativa B: Procesamiento Continuo en Tiempo Real Puro (Real-time Stream)
* **Descripción:** Cada orden recibida por API Gateway se encola en Kinesis Data Streams o Kafka y es procesada inmediatamente de punta a punta (NLP + Dictamen + Liquidación) con AWS Lambda o Flink.
* **Ventajas:**
  * Latencia de adjudicación en segundos por orden.
  * Flujo de procesamiento plano y constante.
* **Desventajas:**
  * Costo prohibitivo: el cómputo de inferencia NLP en streaming 24/7 sin agregación eficiente de batches resulta entre 3x y 5x más costoso por llamada que el procesamiento vectorizado por lotes.
  * Dificultad para manejar picos repentinos de 1.111 órdenes/s sin un sobreaprovisionamiento masivo de infraestructura.

### Alternativa C: Arquitectura Híbrida Desacoplada (Ingesta Continua + Micro-batch / Batch Orquestado) — **SELECCIONADA**
* **Descripción:** 
  1. **Capa de Ingesta Continua (24/7):** API Gateway / S3 multipart upload recibe las órdenes continuamente, valida sintaxis y schema básico en milisegundos, almacena el dato crudo en Amazon S3 y notifica eventos vía Amazon SQS.
  2. **Capa de Procesamiento en Micro-batches / Batches Dinámicos:** Workers elásticos (AWS Glue, ECS/Fargate o Spark) consumen paquetes acumulados de órdenes (batches de 1.000 a 50.000 registros). Si el volumen es bajo, procesa en micro-lotes cada 10-15 minutos; si llega la ventana masiva de radicación, el auto-scaler escala horizontalmente los workers para alcanzar los 1.111 órdenes/segundo.
* **Ventajas:**
  * **Resiliencia:** Desacopla la recepción rápida (evita rechazos por saturación) de la inferencia analítica pesada.
  * **Eficiencia Económica:** Maximiza el rendimiento del NLP al vectorizar inferencias en minilotes sobre GPU/CPU, reduciendo el costo por orden en más de un 70%.
  * **Flexibilidad Operativa:** Satisface tanto la recepción continua como el procesamiento masivo en ventana de 3h.

---

## 3. Decisión

Se adopta la **Alternativa C: Arquitectura Híbrida Desacoplada**.
* Ingesta continua orientada a eventos mediante **Amazon S3 + Amazon SQS/EventBridge**.
* Ejecución de tareas analíticas y de adjudicación en **procesamiento elástico por lotes (micro-batch / batch jobs)**.

---

## 4. Consecuencias y Compensaciones (Trade-offs)

* **Positivas:**
  * Garantiza el cumplimiento del SLA de 3 horas (1.111 órdenes/s) mediante escalado horizontal elástico.
  * Reduce costos al permitir la utilización de instancias Spot y cómputo que se apaga automáticamente cuando las colas quedan vacías.
  * Facilita el aislamiento de errores (Dead Letter Queue para órdenes con problemas sintácticos sin detener el lote).
* **Negativas / Mitigaciones:**
  * Mayor número de componentes que un script monolítico de batch (requiere orquestación con AWS Step Functions o Apache Airflow). Mitigación: Uso de Step Functions serverless en el prototipo para mantener bajo costo operacional.
