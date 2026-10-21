# ADR-002: Gestión de Privacidad (PII) y Trazabilidad Criptográfica Inmutable
**Estado:** Aprobado  
**Fecha:** 2026-10-21  
**Decisores:** Equipo de Arquitectura Proyecto COIL  
**Fase:** Inception  

---

## 1. Contexto y Enunciado del Problema

Las órdenes médicas contienen información de salud altamente confidencial (PHI) y datos de identificación personal (PII), tales como el **DNO** (Documento Nacional de Identidad), nombres del paciente y número de seguro social.
Al mismo tiempo, la ley de auditoría médica gubernamental exige:
1. **Privacidad por Diseño (Compliance GDPR / Ley 1581 / HIPAA):** Los motores analíticos de NLP, logs de auditoría masivos y capas analíticas no deben almacenar identificadores personales en texto claro.
2. **Trazabilidad Inmutable:** Cada dictamen (Cubre / No Cubre) y liquidación financiera (100%, 50%, 25%, 0%) debe ser jurídicamente defendible, indicando exactamente:
   - Qué versión del catálogo normativo se usó.
   - Qué reglas de negocio se activaron.
   - Qué caracteres exactos del texto libre de la glosa clínica sustentan la decisión (`start_char`, `end_char`).
   - Firma de integridad que impida la alteración retroactiva del fallo de auditoría.

---

## 2. Alternativas Evaluadas

### Alternativa A: Cifrado Reversible de Extremo a Extremo en Base de Datos Relacional
* **Descripción:** Guardar el DNO cifrado con KMS en una tabla SQL y desencriptar cada vez que un proceso analítico lo requiera.
* **Desventajas:** Alto costo en llamadas a KMS para 12 millones de registros en pocas horas; expone el dato en memoria en múltiples etapas; no garantiza inmutabilidad ni ligadura estricta a los spans del texto clínico.

### Alternativa B: Anonimización Irreversible mediante Tokenización Hash con Salt Secreto + Trazabilidad en Payload Inmutable (WORM) — **SELECCIONADA**
* **Descripción:**
  1. **Pseudonimización en Ingesta:** Al ingresar la orden, el par `(DNO, NSS)` se transforma inmediatamente en un `patient_token` usando `HMAC-SHA256` con un salt administrado en AWS Secrets Manager. Los nombres de pila se eliminan o enmascaran en la glosa.
  2. **Preservación de Spans de Texto:** El motor NLP no solo devuelve la entidad clínica sino sus índices de caracteres en el texto de la glosa:
     `{"entity": "Hipertension", "code": "I10", "span": [112, 133], "confidence": 0.96}`
  3. **Certificado de Adjudicación Inmutable (Decision Hash):** Se calcula un hash criptográfico SHA-256 consolidando:
     $$\text{Hash} = \text{SHA256}(\text{OrderUUID} + \text{RulesApplied} + \text{CatalogVersion} + \text{TextSpans} + \text{ApprovedAmount})$$
  4. **Almacenamiento WORM:** El resultado se guarda en formato columnar (Parquet / Iceberg) en S3 con políticas de Object Lock (WORM - Write Once, Read Many).

---

## 3. Decisión

Se adopta la **Alternativa B**:
* Uso de **HMAC-SHA256** para generar tokens sintéticos de pacientes en la etapa de ingesta.
* Retención de **spans de texto (`start`, `end`)** para sustentar cada entidad clínica extraída.
* Generación de un **Recibo Criptográfico de Adjudicación** persistido en almacenamiento inmutable.

---

## 4. Consecuencias y Compensaciones

* **Positivas:**
  * Cumplimiento total de regulaciones de privacidad de datos de salud sin perder correlación analítica.
  * Respaldo jurídico contundente: cualquier ente de control puede verificar la autenticidad matemática de una liquidación recalculando el SHA-256.
  * Cero sobrecosto de descifrado en masa durante el procesamiento analítico.
* **Negativas / Mitigaciones:**
  * Si el pagador estatal necesita contactar al paciente por una anomalía médica, se requiere un servicio de bóveda (*token vault*) con control de acceso estricto y auditoría reforzada para re-identificar el DNO original.
