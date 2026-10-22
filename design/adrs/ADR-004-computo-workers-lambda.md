# ADR-004: Cómputo de los workers de adjudicación

| Campo | Valor |
| :--- | :--- |
| Estado | Propuesto |
| Fecha | 2026-10-21 |
| Fase | Construction, diseño de infraestructura |
| Relacionado | ADR-001 (ruta híbrida), ADR-003 (prototipo en Learner Lab), [03_arquitectura_tecnica.md](../03_arquitectura_tecnica.md) |

---

## 1. Contexto

ADR-001 fijó que los workers consumen órdenes acumuladas desde una cola y escalan horizontalmente. Falta decidir **en qué servicio corren**. El worker ejecuta un modelo NER en CPU, necesita entre 2 y 56 unidades de cómputo concurrentes según el rendimiento del modelo (sección 8 del documento de arquitectura) y debe funcionar tanto en el Learner Lab como en la propuesta de producción.

El Learner Lab impone restricciones que pesan en la decisión. Solo permite instancias EC2 de tamaño nano a large, con un máximo de 32 vCPU y nueve instancias simultáneas por región, no permite crear roles IAM (todo usa `LabRole`) y la documentación pública del laboratorio no lista ECS, Fargate, Glue ni EMR. Un reporte de terceros indica además que ECS y Fargate no están disponibles en ningún Learner Lab. Lambda, SQS, S3, DynamoDB, Step Functions y CloudWatch sí aparecen como disponibles.

## 2. Alternativas evaluadas

| Criterio | A. Lambda con imagen de contenedor | B. ECS Fargate (Spot) | C. AWS Glue (Spark) | D. EC2 Auto Scaling |
| :--- | :--- | :--- | :--- | :--- |
| Disponible en el Learner Lab | Sí, documentado | Dudoso, reportado como no disponible | No documentado | Sí, hasta 32 vCPU |
| Escalado con la cola | Nativo, mapeo SQS de hasta 1.250 invocaciones | Requiere política de escalado por profundidad de cola | Por trabajo, no por mensaje | Requiere política y AMI propia |
| Escala a cero | Sí | Sí, con escalado configurado | Sí | Difícil, siempre hay mínimo |
| Costo por vCPU-hora (us-east-1) | 0,106 USD x86, 0,085 USD Arm | 0,049 USD (1 vCPU y 2 GB), hasta 70 % menos en Spot | Unos 0,11 USD (0,44 USD por DPU de 4 vCPU) | Unos 0,048 USD en m5.large |
| Operación | Mínima, sin red ni servidores | Media, requiere VPC y salida a internet o endpoints | Media | Alta, parches y AMI |
| Límites relevantes | 15 minutos por invocación, imagen de hasta 10 GB | Sin límite práctico de duración | Arranque de un minuto o más por trabajo | Cuotas del laboratorio |

## 3. Decisión

Se adopta la **alternativa A**, workers en AWS Lambda empaquetados como imagen de contenedor para arquitectura Arm, consumiendo la cola `chunks-adjudicacion` con un mensaje por invocación y una concurrencia máxima configurada en el mapeo.

El código del worker se organiza como una librería con un adaptador delgado por plataforma, de modo que la **misma imagen** pueda ejecutarse en ECS Fargate Spot sin reescribir lógica si alguna de estas condiciones aparece en producción.

1. El modelo necesita GPU o supera los límites de memoria o de imagen de Lambda.
2. El rendimiento medido `k` es tan bajo que el cómputo deja de ser despreciable en el costo total.
3. Un chunk razonable no cabe en 15 minutos.

## 4. Consecuencias

**Positivas.** Es la única opción con disponibilidad documentada en el laboratorio que además escala de forma nativa con SQS, lo que reduce el riesgo de no poder demostrar el prototipo. No requiere VPC ni NAT Gateway, que en el laboratorio cobra por hora. Los servicios regionales de Lambda ya operan en varias zonas de disponibilidad.

**Negativas y mitigaciones.** Lambda cuesta aproximadamente el doble por vCPU-hora que Fargate bajo demanda. Con 12 M órdenes diarias la diferencia es de 1 a 5 USD por día según `k`, menor que el costo de operar y asegurar la red de Fargate, y la puerta hacia Fargate queda abierta por la imagen compartida. El arranque en frío incluye cargar el modelo y se amortiza porque cada invocación procesa 5.000 órdenes. Arm reduce el precio en 20 %, pero exige comprobar que todas las dependencias tengan ruedas `aarch64`; si alguna falla, se usa x86.
