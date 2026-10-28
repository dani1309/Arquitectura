# ADR-002: Gestión de Privacidad (PII) y Trazabilidad Criptográfica Inmutable
**Estado:** Aprobado  
**Fecha:** 2026-10-21 (Actualizado 2026-10-27 con Dataset COIL y Ajustes de Diseño)  
**Decisores:** Equipo de Arquitectura Proyecto COIL  
**Fase:** Inception  

---

## 1. Contexto y Enunciado del Problema

En el dataset oficial (`COIL_dataset_glosas_salud_1_2M.csv`), cada glosa médica incluye datos personales identificables (PII) junto con la información clínica:
`Paciente: <nombre>; DNO: <identificador>; SeguroSocial: <identificador>; Edad: <edad>; PerfilCobertura: <perfil>; ServicioSolicitado: <servicio>; Medicacion: <med1>|<med2>|...`

El sistema debe satisfacer simultáneamente dos exigencias críticas:
1. **Protección de Datos Personales (RNF-05):** Ni el nombre del paciente, ni el `DNO` (`DNO-XXXXXXXX`), ni el `SeguroSocial` (`SS-XXX-XX-XXXX`) pueden almacenarse en claro en tablas analíticas, recibos de auditoría o logs de observabilidad.
2. **Trazabilidad Inmutable con Sustento Textual (RF-05, RNF-04):** Cada dictamen (`CUBRE` / `NO_CUBRE`) y liquidación (`100%`, `50%`, `25%`, `0%`) debe registrar la versión del catálogo, el modelo utilizado, las reglas aplicadas, los caracteres exactos (`start_char`, `end_char`) de la glosa que sustentan la extracción y un hash criptográfico inmutable verificable.

---

## 2. Alternativas Evaluadas

### Alternativa A: Cifrado Reversible por Campo con KMS en Base de Datos
* **Descripción:** Cifrar y descifrar individualmente cada campo sensible con AWS KMS en cada lectura o consulta.
* **Desventajas:** Realizar millones de llamadas a KMS por lote dispara el costo y la latencia; además, eliminar o recortar el nombre del paciente de la glosa desplazaría las posiciones de caracteres (`spans`) de las entidades clínicas siguientes.

### Alternativa B: Pseudonimización con `HMAC-SHA256`, Enmascaramiento de Longitud Fija (`#`) y Árbol de Hashes sobre JSON Canónico — **SELECCIONADA**
* **Descripción:**
  1. **Tokenización con Clave Secreta:** Al leer la orden en memoria, el worker calcula:
     $$\text{patient\_token} = \text{HMAC-SHA256}(\text{clave\_secreta}, \text{DNO} \mathbin{\Vert} \text{SeguroSocial})$$
     usando una clave secreta almacenada en AWS Secrets Manager (cargada en caché por el worker).
  2. **Enmascaramiento con Preservación de Longitud:** Dentro de la glosa, cada carácter de los valores de `Paciente`, `DNO` y `SeguroSocial` se reemplaza por `#`. Como la longitud total de la cadena no cambia, los desplazamientos `[start_char, end_char]` de `Edad`, `PerfilCobertura`, `ServicioSolicitado` y `Medicacion` coinciden carácter por carácter tanto en la glosa enmascarada como en la glosa original de `saom-raw`.
  3. **Firma sobre JSON Canónico (`hash_decision`):** La decisión se serializa en JSON canónico (llaves ordenadas alfabéticamente, sin espacios, UTF-8, montos con dos decimales exactos) incluyendo `id_solicitud`, `patient_token`, `catalogo_version`, `modelo_version`, `regla_ids`, `spans`, `perfil_cobertura`, `porcentaje`, `valor_procedimiento` y `valor_aprobado`, y se calcula su `SHA-256`.
  4. **Árbol de Hashes y Evidencia WORM:** Los hashes de las órdenes de un chunk se encadenan para formar `raiz_hash_chunk`, y las raíces de los chunks forman `raiz_hash_lote`, almacenando los recibos en S3 con Object Lock (WORM).

---

## 3. Decisión

Se adopta la **Alternativa B**:
* Pseudonimización determinista mediante **`HMAC-SHA256` con clave secreta**.
* Enmascaramiento in-situ con **`#` preservando la longitud** para mantener intactos los spans `[start_char, end_char]`.
* Cálculo de **`hash_decision` sobre JSON canónico** y verificación jerárquica por orden, chunk y lote.

---

## 4. Consecuencias y Compensaciones

* **Positivas:**
  * Cero exposición de PII en capas analíticas (`saom-curated`), de evidencia (`saom-audit`), de control (DynamoDB) y de observabilidad (CloudWatch).
  * Los índices de caracteres `[start_char, end_char]` nunca se desfasan tras el enmascaramiento.
  * Cualquier alteración de un centavo o de una regla en la tabla analítica rompe inmediatamente la verificación contra el recibo en WORM y la raíz del chunk.
* **Negativas / Mitigaciones:**
  * La rotación de la clave secreta HMAC cambia el `patient_token` generado; por ello la clave se versiona (`key_version`) en los metadatos del lote.
