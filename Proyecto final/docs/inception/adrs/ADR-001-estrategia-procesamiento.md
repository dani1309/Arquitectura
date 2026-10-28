# ADR-001: Selección del Patrón de Procesamiento (Batch vs. Ingesta Continua vs. Arquitectura Híbrida)
**Estado:** Aprobado  
**Fecha:** 2026-10-21 (Actualizado 2026-10-27 con Dataset COIL)  
**Decisores:** Equipo de Arquitectura Proyecto COIL  
**Fase:** Inception  

---

## 1. Contexto y Enunciado del Problema

El sistema de auditoría del pagador estatal (**Sistema de Salud de Chernovia**) debe adjudicar financieramente **12 millones de órdenes médicas en menos de 24 horas** (y en el prototipo procesar el dataset oficial `COIL_dataset_glosas_salud_1_2M.csv` de **1.200.000 solicitudes** provenientes de 10 entidades emisoras y 7 canales de atención). Existen dos patrones operativos en salud pública:
1. **Flujo Continuo:** Las entidades emisoras (`Hospital Público`, `Clínica Aliada`, `Farmacia Aliada`, `Portal Ciudadano`, `App Móvil Salud`, etc.) radican lotes a lo largo del día (~139 órdenes/segundo en promedio sostenido).
2. **Ventana Concentrada / Ráfaga:** Las entidades consolidan su radicación al cierre de jornada, enviando volúmenes masivos que deben liquidarse en una ventana exigente de 3 horas (~1.111 órdenes/segundo).

El enunciado exige justificar metodológica y económicamente entre procesamiento por lotes, continuo o híbrido.

---

## 2. Alternativas Evaluadas

### Alternativa A: Procesamiento por Lotes Puro (Scheduled Heavy Batch)
* **Descripción:** Acumular los archivos CSV en S3 durante todo el día y a una hora fija levantar un clúster masivo para procesar las 12 millones de órdenes de una sola vez.
* **Ventajas:** Simplicidad conceptual para agregaciones globales al cierre del día.
* **Desventajas:**
  * Picos extremos de demanda de cómputo en una ventana corta y alto impacto si un fallo ocurre al final de la ventana.
  * Sin retroalimentación temprana para las IPS sobre errores estructurales de radicación.

### Alternativa B: Procesamiento Continuo Orden por Orden en Tiempo Real (Pure Streaming)
* **Descripción:** Enviar cada orden individualmente por API Gateway y Kinesis/SQS para ejecutar una invocación por orden de extremo a extremo.
* **Ventajas:** Latencia de segundos por solicitud individual.
* **Desventajas:**
  * **Costo prohibitivo en AWS:** Cobrar 12 millones de llamadas diarias en API Gateway, SQS, S3 PUT y Lambda multiplica el costo por más de 100x frente al empaquetamiento en bloques.

### Alternativa C: Arquitectura Híbrida Orientada a Eventos (Ingesta Continua + Procesamiento por Chunks / Micro-batch) — **SELECCIONADA**
* **Descripción:**
  1. **Ingesta Continua (24/7):** Las entidades emisoras solicitan una URL prefirmada a API Gateway y suben sus archivos CSV directamente a `saom-raw` en S3.
  2. **Particionamiento y Amortiguación:** Un particionador ligero divide cada archivo CSV en descriptores de **chunks de 5.000 órdenes** (rangos de bytes) y los publica en la cola SQS `chunks-adjudicacion`.
  3. **Procesamiento Paralelo en Micro-lotes:** $N$ workers en AWS Lambda (Arm) consumen un chunk por invocación (2.400 chunks diarios para 12M, o 240 chunks para el dataset de 1,2M), escriben Parquet en staging y recibos firmados en WORM, y un consolidador integra la tabla Apache Iceberg cada 15 minutos con `MERGE INTO`.

---

## 3. Decisión

Se adopta la **Alternativa C: Arquitectura Híbrida Desacoplada por Chunks**.
* Ingesta continua mediante **URLs prefirmadas de Amazon S3 + eventos a Amazon SQS**.
* Procesamiento paralelo en **chunks de 5.000 órdenes** y consolidación analítica cada 15 minutos sobre **Apache Iceberg**.

---

## 4. Consecuencias y Compensaciones (Trade-offs)

* **Positivas:**
  * Cumple tanto el flujo continuo (24 h) como la ventana de 3 horas (1.111 órdenes/s) escalando el número de workers concurrentes ($N$ entre 2 y 56).
  * Reduce drásticamente el costo de nube a **~$3,02 USD/día** para 12M de órdenes al cobrar solicitudes de SQS, S3 y Lambda por cada 5.000 órdenes en lugar de por orden individual.
  * Aísla órdenes con errores de sintaxis (`REJECTED_SYNTAX`) sin detener el resto del lote.
* **Negativas / Mitigaciones:**
  * La tabla analítica Iceberg presenta una latencia de actualización de hasta 15 minutos respecto a la ingesta, lo cual es plenamente compatible con el SLA diario del pagador estatal.
