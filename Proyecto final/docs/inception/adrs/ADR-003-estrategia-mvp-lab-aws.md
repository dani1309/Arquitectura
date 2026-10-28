# ADR-003: Estrategia de Prototipo en AWS Learner Lab y Extrapolación de Capacidad a Escala de Producción
**Estado:** Aprobado  
**Fecha:** 2026-10-21 (Actualizado 2026-10-27 con Dataset COIL 1,2M y Presupuesto $50 USD)  
**Decisores:** Equipo de Arquitectura Proyecto COIL  
**Fase:** Inception  

---

## 1. Contexto y Enunciado del Problema

El proyecto debe responder a dos escalas complementarias:
1. **Meta de Licitación (Producción):** Procesar **12.000.000 de órdenes médicas diarias** en menos de 24 horas ($\ge 138,9\text{ órdenes/s}$) o en una ventana concentrada de 3 horas ($\ge 1.111,1\text{ órdenes/s}$).
2. **Entorno de Demostración (Entregable 3 - Prototipo en AWS Academy Learner Lab):** El laboratorio dispone de un presupuesto total de **$\$50\text{ USD}$**, exige utilizar el rol preconfigurado `LabRole` y restringe la creación de clústeres pesados (EMR, Fargate o instancias grandes). Por su parte, el dataset oficial entregado para el proyecto (`COIL_dataset_glosas_salud_1_2M.csv`) contiene **1.200.000 solicitudes médicas** (~360 MB), lo que equivale exactamente a **1/10 del volumen diario de producción**.

---

## 2. Alternativas Evaluadas

### Alternativa A: Aprovisionar Clústeres Pesados Permanentes (EMR / Redshift / EC2 grandes)
* **Riesgo:** Bloqueo inmediato por políticas de IAM del Learner Lab o agotamiento acelerado de los $\$50\text{ USD}$ de crédito por recursos encendidos en reposo.

### Alternativa B: Simulación Puramente Local sin Despliegue en Nube
* **Riesgo:** Incumple el requisito de ejecutar el prototipo sobre servicios reales de AWS.

### Alternativa C: Prototipo Cloud-Native Serverless sobre el Dataset Oficial de 1,2M (Escala 1:10) + Extrapolación $M/M/c$ a 12M — **SELECCIONADA**
* **Descripción:**
  1. **Ejecución Real sobre 1,2M de Solicitudes (240 chunks de 5.000 órdenes):**
     * Utilizar servicios serverless disponibles en el Learner Lab que escalan a cero cuando no hay carga: **Amazon S3, Amazon SQS, AWS Lambda (Arm), Amazon DynamoDB on-demand, AWS Step Functions, Amazon Athena (Apache Iceberg) y Amazon CloudWatch**.
     * Procesar el archivo oficial `COIL_dataset_glosas_salud_1_2M.csv` junto con `COIL_catalogo_servicios_cubiertos.csv` y `COIL_catalogo_perfiles_cobertura.csv` con concurrencia controlada ($c \le 10$ workers en el laboratorio), consumiendo menos de **$\$0,35\text{ USD}$** por corrida completa.
  2. **Medición Empírica y Extrapolación con Teoría de Colas ($M/M/c$):**
     * Medir en el prototipo el rendimiento real $k$ ($\text{órdenes/segundo/vCPU}$) y el $F_1\text{-score}$ de extracción clínica.
     * Con el valor empírico de $k$, calcular mediante `modelo_capacidad_costo.py` el número exacto de workers $N$, el factor de utilización $\rho$, el tiempo de espera en cola $W_q$ (fórmula C de Erlang) y el costo diario para las **12.000.000 de órdenes** de la licitación.

---

## 3. Decisión

Se adopta la **Alternativa C**:
* Validar el prototipo procesando las **1.200.000 órdenes del dataset oficial COIL** en servicios serverless compatibles con `LabRole` y presupuesto de **$\$50\text{ USD}$**.
* Sustentar la escala de 12M mediante el modelo matemático $M/M/c$ alimentado con el throughput unitario $k$ medido en las pruebas.

---

## 4. Consecuencias y Compensaciones

* **Positivas:**
  * Costo cero en reposo (escala a cero), protegiendo los $\$50\text{ USD}$ del laboratorio.
  * El factor de escala entre el dataset oficial (1,2M) y la meta de licitación (12M) es exactamente $1:10$, lo que hace la extrapolación directa, transparente y auditable.
* **Negativas / Mitigaciones:**
  * El laboratorio limita la concurrencia de Lambda y algunas funciones administrativas de S3 (como Object Lock); si `LabRole` restringe Object Lock en el bucket de auditoría, el prototipo activa S3 Versioning con política de denegación de borrado y verifica la inmutabilidad mediante el árbol de hashes SHA-256.
