# Especificación de Requisitos Funcionales y Escenarios BDD
**Proyecto:** Arquitectura Distribuida en AWS para Auditoría y Adjudicación Financiera Masiva de Órdenes Médicas (Proyecto COIL - Sistema de Salud de Chernovia)  
**Fase AI-DLC:** Inception  
**Versión:** 1.1.0 (Alineado con el Dataset Oficial COIL 1,2M y Diseño Técnico)  

---

## 1. Unificación Conceptual y Reglas de Negocio (Dataset Oficial COIL)

### 1.1 Esquema del Dataset Principal (`COIL_dataset_glosas_salud_1_2M.csv`)
Cada registro representa una **Orden / Solicitud Médica** indivisible de auditoría (~300 bytes por fila) con las siguientes 6 columnas:
* **`id_solicitud`:** Identificador único de la solicitud (ej. `CHV-0000001`).
* **`fecha_solicitud`:** Marca temporal de recepción (`YYYY-MM-DD HH:MM:SS`, distribuida en 3 días hábiles: `2026-05-04` a `2026-05-06`).
* **`glosa`:** Texto semiestructurado (~213 caracteres en promedio) con la información clínica y del paciente bajo la plantilla:
  `Paciente: <nombre>; DNO: <identificador>; SeguroSocial: <identificador>; Edad: <edad>; PerfilCobertura: <perfil>; ServicioSolicitado: <servicio>; Medicacion: <med1>|<med2>|...`
* **`medio_emisor`:** Canal de ingreso de la solicitud (`Hospital Público`, `Clínica Aliada`, `Farmacia Aliada`, `Portal Ciudadano`, `Ventanilla Física`, `App Móvil Salud`, `Call Center`).
* **`valor_procedimiento`:** Valor monetario reclamado por el procedimiento solicitado (entero positivo).
* **`entidad_emisora`:** Institución prestadora (IPS) que radica la solicitud (ej. `Hospital Central de Chernovia`, `Unidad de Salud Valle Claro`, `Instituto Ambulatorio Novaterra`, etc.).

### 1.2 Identificadores Personales (PII) y Enmascaramiento
* **`DNO` (Documento Nacional de Operación / Identidad):** Identificador con formato `DNO-XXXXXXXX` (ej. `DNO-23291911`).
* **`SeguroSocial`:** Número de seguridad social con formato `SS-XXX-XX-XXXX` (ej. `SS-173-47-2763`).
* **`patient_token`:** Pseudónimo criptográfico determinista calculado mediante `HMAC-SHA256(clave_secreta, DNO || SeguroSocial)`. En la glosa procesada, los valores de `Paciente`, `DNO` y `SeguroSocial` se reemplazan carácter por carácter con `#` (preservando la longitud exacta del texto para no alterar los desplazamientos `start_char` y `end_char` de las entidades clínicas).

### 1.3 Catálogo de Servicios Cubiertos (`COIL_catalogo_servicios_cubiertos.csv`)
Contiene los **20 servicios habilitados** (`COV-001` a `COV-020`) en el sistema público de salud de Chernovia, definiendo para cada uno:
* `codigo_servicio`, `servicio`, `categoria`, `medicaciones_referencia` (separadas por `|` o `ninguna`), `valor_min_referencia`, `valor_max_referencia` y `cubre_sistema_publico = SI`.
* Cualquier `ServicioSolicitado` que no figure en este catálogo (ej. *Tratamiento spa terapéutico premium*, *Ortodoncia estética avanzada*, *Blanqueamiento dental estético*, *Terapia antiedad experimental*, *Medicina alternativa no certificada*, *Programa de fertilidad premium electiva*, etc.) se dictamina como **`NO_CUBRE`**.

### 1.4 Perfil de Cobertura (`COIL_catalogo_perfiles_cobertura.csv`)
El porcentaje de liquidación cuando el servicio está cubierto depende del campo `PerfilCobertura` extraído de la glosa:
* **`PRIORITARIO`:** Cobertura del **100%** (población prioritaria).
* **`ESTANDAR`:** Cobertura del **50%** (cobertura parcial media para población general).
* **`COPAGO`:** Cobertura del **25%** (cobertura parcial baja con copago extendido).
* **Servicio `NO_CUBRE` o perfil inválido:** Cobertura del **0%** (monto aprobado = `0.00`).

---

## 2. Requisitos Funcionales y Criterios de Aceptación (BDD)

### RF-01: Ingesta, Particionamiento y Validación Estructural de Solicitudes
* **Actor:** Entidad Emisora (IPS) / Particionador y Validador del Worker.
* **Descripción:** El sistema debe recibir lotes CSV de solicitudes médicas, dividirlos en bloques (chunks) de 5.000 órdenes por rango de bytes y validar estructuralmente cada fila (`id_solicitud`, `fecha_solicitud`, `glosa`, `medio_emisor`, `valor_procedimiento > 0`, `entidad_emisora`).
* **Aislamiento de Fallas de Datos vs. Infraestructura:** Una orden individual malformada se marca como `REJECTED_SYNTAX` y se registra en el prefijo `rechazos/` sin detener el procesamiento del resto del chunk. La *Dead Letter Queue* (DLQ) se reserva exclusivamente para fallos técnicos del chunk tras 3 reintentos.

#### Escenarios BDD:
```gherkin
Feature: Validación Estructural de Solicitudes Médicas COIL

  Scenario: Ingesta de solicitud médica con estructura íntegra y campos obligatorios
    Given una solicitud médica recibida con id_solicitud "CHV-0000001" y fecha "2026-05-06 10:09:31"
    And una glosa con DNO "DNO-23291911", SeguroSocial "SS-173-47-2763" y PerfilCobertura "ESTANDAR"
    And un medio_emisor "Farmacia Aliada" y entidad_emisora "Unidad de Salud Valle Claro"
    And un valor_procedimiento de 84617
    When el validador del worker verifica el esquema de la fila
    Then la solicitud es marcada con estado "VALIDATED"
    And pasa en memoria a la etapa de pseudonimización y extracción clínica.

  Scenario: Aislamiento de fila malformada sin abortar el chunk
    Given un chunk de 5000 solicitudes donde la fila "CHV-0000002" carece de valor_procedimiento o tiene glosa vacía
    When el worker procesa el chunk
    Then la solicitud "CHV-0000002" se marca con estado "REJECTED_SYNTAX"
    And se escribe su detalle sin PII en el prefijo "rechazos/" de S3 curated
    And las 4999 solicitudes restantes del chunk continúan su adjudicación normal sin enviar el mensaje a la DLQ.
```

---

### RF-02: Pseudonimización y Extracción de Entidades Clínicas con Spans Exactos
* **Actor:** Pseudonimizador y Extractor Clínico (NLP / NER) del Worker.
* **Descripción:** Generar el `patient_token` con `HMAC-SHA256(clave_secreta, DNO || SeguroSocial)`, enmascarar con `#` de igual longitud los campos `Paciente`, `DNO` y `SeguroSocial` en la glosa, y extraer `Edad`, `PerfilCobertura`, `ServicioSolicitado` y la lista de `Medicacion` registrando los desplazamientos exactos de caracteres (`start_char`, `end_char`) y la confianza de extracción.
* **Valor de Negocio:** Automatizar la lectura clínica protegiendo datos sensibles (PII) sin invalidar las posiciones de caracteres que sirven de prueba legal.

#### Escenarios BDD:
```gherkin
Feature: Pseudonimización y Extracción de Entidades desde la Glosa COIL

  Scenario: Extracción exitosa de servicio, perfil y medicación conservando spans
    Given la solicitud "CHV-0000001" con glosa:
      """
      Paciente: Paula Vargas Ramírez; DNO: DNO-23291911; SeguroSocial: SS-173-47-2763; Edad: 14; PerfilCobertura: ESTANDAR; ServicioSolicitado: Terapia física ambulatoria; Medicacion: acetaminofén|diclofenaco tópico|naproxeno|ciclobenzaprina
      """
    When el pseudonimizador y el extractor clínico procesan la glosa
    Then se genera el patient_token HMAC-SHA256 a partir de "DNO-23291911" y "SS-173-47-2763"
    And los valores de Paciente, DNO y SeguroSocial quedan enmascarados con "#" conservando los 238 caracteres de longitud total
    And extrae la edad 14, el perfil "ESTANDAR" y el servicio "Terapia física ambulatoria" con sus spans exactos [start_char, end_char]
    And extrae las 4 medicaciones ["acetaminofén", "diclofenaco tópico", "naproxeno", "ciclobenzaprina"] con sus respectivos spans
    And registra un puntaje de confianza (confidence_score) >= 0.92.

  Scenario: Detección de glosa con incertidumbre clínica o formato alterado
    Given una solicitud cuya glosa presenta texto truncado o confianza de extracción menor a 0.70
    When el extractor clínico evalúa la glosa
    Then la solicitud se etiqueta con el flag "AUDIT_FLAG_CLINICAL_UNCERTAINTY"
    And se marca para revisión en auditoría médica humana de segunda línea.
```

---

### RF-03: Dictamen de Cobertura contra Catálogo Normativo (`COIL_catalogo_servicios_cubiertos.csv`)
* **Actor:** Motor de Cobertura del Worker.
* **Descripción:** Contrastar el `ServicioSolicitado` extraído contra el catálogo oficial versionado (`COIL_catalogo_servicios_cubiertos.csv`) para emitir dictamen `CUBRE` (asociando el `codigo_servicio` entre `COV-001` y `COV-020`) o `NO_CUBRE`. Adicionalmente, verificar si el `valor_procedimiento` se encuentra dentro del rango `[valor_min_referencia, valor_max_referencia]` y si la medicación corresponde a `medicaciones_referencia`.
* **Valor de Negocio:** Evitar pagos por prestaciones estéticas, experimentales o excluidas del sistema público de salud de Chernovia.

#### Escenarios BDD:
```gherkin
Feature: Dictamen de Cobertura Normativa en Chernovia

  Scenario: Servicio incluido en el catálogo oficial de servicios cubiertos
    Given una solicitud con ServicioSolicitado "Control de hipertensión arterial"
    And Medicacion extraída "losartán|enalapril"
    And un valor_procedimiento de 124225
    And el catálogo vigente donde "Control de hipertensión arterial" tiene código "COV-009", cubre_sistema_publico "SI" y rango [50000, 130000]
    When el motor de cobertura evalúa la solicitud
    Then emite dictamen "CUBRE"
    And asocia la regla normativa "COV-009" y categoría "Crónicos".

  Scenario: Servicio estético o experimental no incluido en el catálogo oficial
    Given una solicitud con ServicioSolicitado "Tratamiento spa terapéutico premium" y valor_procedimiento 903765
    When el motor de cobertura consulta el catálogo oficial COIL
    Then emite dictamen "NO_CUBRE"
    And asocia la causal "GLOSA-EXCL-SERVICIO-NO-CUBIERTO"
    And fija el porcentaje de cobertura en 0%.
```

---

### RF-04: Liquidación Financiera Escalonada (100%, 50%, 25%, 0%)
* **Actor:** Liquidador Financiero del Worker.
* **Descripción:** Calcular el monto exacto aprobado (`valor_aprobado`) y el copago aplicando el porcentaje de `COIL_catalogo_perfiles_cobertura.csv` según `PerfilCobertura` (`PRIORITARIO` = 100%, `ESTANDAR` = 50%, `COPAGO` = 25%) cuando el dictamen es `CUBRE`, o `0%` cuando es `NO_CUBRE`, utilizando aritmética `Decimal` con dos decimales y redondeo `ROUND_HALF_UP`.
* **Valor de Negocio:** Exactitud financiera determinista que garantiza que dos ejecuciones produzcan exactamente el mismo centavo y el mismo hash criptográfico.

#### Escenarios BDD:
```gherkin
Feature: Liquidación Financiera Escalonada según Perfil COIL

  Scenario Outline: Cálculo determinista del monto cubierto con ejemplos reales del dataset
    Given una solicitud "<IdSolicitud>" con valor_procedimiento de <ValorProcedimiento>
    And un ServicioSolicitado "<Servicio>" cuyo dictamen es "<Dictamen>"
    And un PerfilCobertura "<Perfil>"
    When el liquidador financiero calcula la adjudicación con precisión Decimal(18,2)
    Then el porcentaje de cobertura aplicado es <Porcentaje>%
    And el valor_aprobado a girar a la entidad emisora es "<ValorAprobado>"

    Examples:
      | IdSolicitud | Servicio                            | ValorProcedimiento | Dictamen   | Perfil      | Porcentaje | ValorAprobado |
      | CHV-0000001 | Terapia física ambulatoria          | 84617              | CUBRE      | ESTANDAR    | 50         | 42308.50      |
      | CHV-0000002 | Suministro de antihipertensivos     | 53874              | CUBRE      | PRIORITARIO | 100        | 53874.00      |
      | CHV-0000004 | Tratamiento spa terapéutico premium | 903765             | NO_CUBRE   | PRIORITARIO | 0          | 0.00          |
      | CHV-0000005 | Medicina alternativa no certificada | 661684             | NO_CUBRE   | COPAGO      | 0          | 0.00          |
      | CHV-0000006 | Hemograma completo                  | 49134              | CUBRE      | PRIORITARIO | 100        | 49134.00      |
```

---

### RF-05: Trazabilidad Criptográfica Inmutable y Árbol de Hashes por Chunk y Lote
* **Actor:** Generador de Recibo y Escritor Idempotente del Worker.
* **Descripción:** Serializar cada decisión en **JSON canónico** (llaves ordenadas alfabéticamente, sin espacios en blanco, codificación UTF-8, montos formateados con dos decimales) incluyendo `id_solicitud`, `patient_token`, `catalogo_version`, `modelo_version`, `regla_ids`, `spans`, `perfil_cobertura`, `porcentaje`, `valor_procedimiento` y `valor_aprobado`, y calcular su `hash_decision` SHA-256. Al cierre del chunk, calcular la raíz hash del chunk (`raiz_hash_chunk`).
* **Valor de Negocio:** Respaldo probatorio inmutable verificable por cualquier ente de control en tres niveles (orden, chunk y lote).

#### Escenarios BDD:
```gherkin
Feature: Trazabilidad Criptográfica Inmutable sobre JSON Canónico

  Scenario: Generación de recibo firmado y verificación de integridad
    Given la solicitud "CHV-0000001" liquidada con dictamen "CUBRE", regla "COV-005" y valor_aprobado "42308.50"
    And catalogo_version "COIL-2026.1" y modelo_version "coil-ner-v1.0"
    When el generador de recibo construye el JSON canónico de la decisión
    Then calcula el hash_decision SHA-256 de 64 caracteres hexadecimales
    And persiste el recibo en el almacenamiento de auditoría (WORM) y la fila en formato Parquet para la tabla Iceberg
    And cualquier modificación posterior de un solo centavo o carácter produce un hash distinto y es detectada en la verificación.
```
