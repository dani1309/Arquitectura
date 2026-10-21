# Especificación de Requisitos Funcionales y Escenarios BDD
**Proyecto:** Arquitectura Distribuida en AWS para Auditoría y Adjudicación Financiera Masiva de Órdenes Médicas (Proyecto COIL - Pagador Estatal)  
**Fase AI-DLC:** Inception  
**Versión:** 1.0.0  

---

## 1. Unificación Conceptual y Reglas de Negocio

### 1.1 Glosario de Entidades
* **Orden Médica / Cuenta Médica:** Unidad indivisible de auditoría. Equivale a la prescripción, consulta y factura radicada por un prestador de salud (IPS) para reclamo financiero ante el pagador estatal.
* **DNO (Documento Nacional de Operación / DNI):** Documento oficial de identidad del usuario (Cédula de Ciudadanía, DNI, Pasaporte) combinado con el Número de Identificación de Seguridad Social (NSS/BPS).
* **Medio Emisor:** Entidad prestadora de servicios de salud (IPS / Prestador Privado o Público) con su código de habilitación y nivel de complejidad asistencial (Nivel 1 al 4).
* **Valor del Procedimiento:** Monto monetario nominal reclamado por el emisor según la tarifa pactada o catálogo SOAT/ISS/FONASA.
* **Perfil del Usuario (Regla de Copago y Cobertura):**
  * **Categoría A (Vulnerabilidad Alta / Régimen Subsidiado / SISBEN A-B):** Cobertura del **100%** del valor aprobado si el medicamento/procedimiento está en el catálogo.
  * **Categoría B (Régimen Contributivo Rango Medio / Ingresos 2-5 SMMLV):** Cobertura del **50%** (copago del 50%).
  * **Categoría C (Régimen Contributivo Rango Alto / Ingresos > 5 SMMLV):** Cobertura del **25%** (copago del 75%).
  * **No Asegurado / Exclusión Explícita / Sin Derechos:** Cobertura del **0%**.

---

## 2. Requisitos Funcionales y Criterios de Aceptación (BDD)

### RF-01: Ingesta y Validación Estructural del Lote de Órdenes
* **Actor:** Prestador de Servicios de Salud (IPS) / Ingestor Automático de Licitación.
* **Descripción:** El sistema debe recibir archivos de órdenes médicas en formato semiestructurado (JSON/Parquet/CSV), validar esquema, tipología de datos, presencia de DNO, medio emisor, valor y glosa médica.
* **Valor de Negocio:** Evitar procesar registros corruptos o incompletos que contaminen el pipeline de adjudicación.

#### Escenarios BDD:
```gherkin
Feature: Validación Estructural de Órdenes Médicas

  Scenario: Ingesta de orden médica con estructura íntegra y campos obligatorios
    Given una orden médica recibida con ID "ORD-2026-9001"
    And un identificador de paciente compuesto por DNO "10203040" y NSS "SS-998877"
    And un medio emisor "IPS Universitaria - Nivel 3" con código de habilitación vigente
    And un valor reclamado de "$150.000 COP"
    And una glosa médica en texto libre no vacía
    When el subsistema de ingesta procesa y valida la estructura de la orden
    Then la orden es marcada con estado "VALIDATED"
    And es encolada para el pipeline de anonimización y análisis NLP.

  Scenario: Rechazo por orden malformada o campos críticos ausentes
    Given una orden médica con ID "ORD-2026-9002" sin valor de procedimiento ni medio emisor
    When el subsistema de ingesta valida la orden
    Then la orden es rechazada con estado "REJECTED_SYNTAX"
    And se genera un registro en la Dead Letter Queue (DLQ) con el detalle del campo faltante
    And no se envía a la etapa de inferencia NLP.
```

---

### RF-02: Extracción y Normalización de Entidades Clínicas (NLP / NER)
* **Actor:** Motor de Procesamiento NLP Distribuido.
* **Descripción:** A partir de la glosa médica no estructurada, extraer: paciente, edad, diagnósticos (mapeados a códigos CIE-10/11) y medicamentos con su posología y principio activo. Debe registrar los caracteres exactos de inicio y fin (`start_char`, `end_char`) dentro del texto original.
* **Valor de Negocio:** Automatizar la comprensión clínica sin intervención humana, permitiendo auditar millones de órdenes en minutos.

#### Escenarios BDD:
```gherkin
Feature: Extracción de Entidades Clínicas desde Texto Libre

  Scenario: Extracción exitosa de diagnóstico y prescripción con posología
    Given una orden con glosa médica:
      """
      Paciente masculino de 58 años de edad consulta por cefalea persistente y cifras tensionales elevadas.
      Se confirma Hipertensión esencial (CIE-10: I10).
      Se formula Losartán 50mg cada 12 horas vía oral por 30 días.
      """
    When el modelo de NLP procesa el texto
    Then extrae la edad "58" con span [19, 21]
    And extrae el diagnóstico "Hipertensión esencial" con código "I10" y span [112, 133]
    And extrae el medicamento "Losartán" con concentración "50mg" y posología "cada 12 horas vía oral por 30 días"
    And calcula un puntaje de confianza de extracción (confidence_score) >= 0.90.

  Scenario: Detección de glosa médica ambigua o ilegible
    Given una glosa médica con texto incoherente o abreviaturas no reconocidas: "pcte dolo rrrr ??? med xxx"
    When el modelo de NLP procesa la glosa y no logra extraer diagnósticos con confianza mínima (>= 0.70)
    Then la orden se etiqueta con "AUDIT_FLAG_CLINICAL_UNCERTAINTY"
    And se marca para revisión en auditoría médica de segunda línea.
```

---

### RF-03: Dictamen de Cobertura contra Catálogo Normativo
* **Actor:** Motor de Reglas Normativas del Estado (PBS / Plan de Beneficios en Salud).
* **Descripción:** Cruzar las entidades clínicas extraídas (diagnósticos y medicamentos) contra el catálogo normativo oficial vigente para emitir dictamen binario: `CUBRE` o `NO_CUBRE`.
* **Valor de Negocio:** Cumplimiento estricto del marco legal en salud pública, evitando pagos indebidos por tecnologías no cubiertas.

#### Escenarios BDD:
```gherkin
Feature: Dictamen de Cobertura Normativa

  Scenario: Medicamento incluido en el catálogo oficial para la patología indicada
    Given un diagnóstico extraído "I10" (Hipertensión esencial)
    And un medicamento extraído "Losartán 50mg"
    And el catálogo normativo vigente versión "2026.Q4" donde "Losartán 50mg" cubre patología "I10"
    When el motor de reglas evalúa la pertinencia
    Then emite un dictamen de cobertura "CUBRE"
    And asocia la regla normativa "RULE-PBS-CARDIO-104-v2026.4".

  Scenario: Medicamento cosmético o fuera de guía clínica (No cubierto)
    Given un medicamento prescrito "Toxina Botulínica con fines cosméticos"
    When se contrasta con el catálogo de exclusiones explícitas de la ley
    Then emite un dictamen de cobertura "NO_CUBRE"
    And genera la causal de glosa "GLOSA-EXCL-04: Procedimiento cosmético no amparado"
    And fija el porcentaje de liquidación en 0%.
```

---

### RF-04: Liquidación Financiera Escalonada (100%, 50%, 25%, 0%)
* **Actor:** Módulo de Liquidación y Adjudicación Financiera.
* **Descripción:** Calcular el monto exacto a girar al prestador aplicando la tarifa del procedimiento, el dictamen de cobertura y el perfil socioeconómico del usuario.
* **Valor de Negocio:** Determinación precisa del flujo de caja estatal y cobro de copagos según la capacidad de pago del usuario.

#### Escenarios BDD:
```gherkin
Feature: Liquidación Financiera Escalonada

  Scenario Outline: Cálculo del monto a girar según el perfil del usuario y cobertura
    Given una orden médica con valor del procedimiento de <ValorReclamado>
    And un dictamen de cobertura <Dictamen>
    And un usuario con perfil de aseguramiento <PerfilUsuario>
    When el motor financiero liquida la cuenta médica
    Then el porcentaje de adjudicación asignado es <Porcentaje>%
    And el monto liquidado a girar a la IPS es <MontoGiro>

    Examples:
      | ValorReclamado | Dictamen   | PerfilUsuario    | Porcentaje | MontoGiro   |
      | 100000         | "CUBRE"    | "CATEGORIA_A"    | 100        | 100000      |
      | 100000         | "CUBRE"    | "CATEGORIA_B"    | 50         | 50000       |
      | 100000         | "CUBRE"    | "CATEGORIA_C"    | 25         | 25000       |
      | 100000         | "NO_CUBRE" | "CATEGORIA_A"    | 0          | 0           |
      | 100000         | "CUBRE"    | "NO_ASEGURADO"   | 0          | 0           |
```

---

### RF-05: Trazabilidad Inmutable y Bitácora de Evidencias
* **Actor:** Subsistema de Auditoría y Cumplimiento Legal.
* **Descripción:** Cada decisión de adjudicación debe registrar una firma criptográfica SHA-256 compuesta por: ID de orden, versión del catálogo normativo, reglas disparadas, spans de texto utilizados y monto resultante.
* **Valor de Negocio:** Respaldo blindado ante auditorías de la Contraloría, Procuraduría o demandas de los prestadores.

#### Escenarios BDD:
```gherkin
Feature: Trazabilidad Criptográfica Inmutable

  Scenario: Generación del recibo de adjudicación con sustento textual
    Given una orden médica liquidada exitosamente con ID "ORD-2026-9001"
    And las reglas aplicadas "RULE-PBS-CARDIO-104-v2026.4" y "RULE-COPAGO-CAT-B"
    And los caracteres de soporte en la glosa original [112..133] y [147..155]
    When se consolida el registro de auditoría
    Then el sistema genera un paquete de auditoría JSON que contiene:
      | Campo            | Valor                                      |
      | order_id         | ORD-2026-9001                              |
      | rule_ids         | ["RULE-PBS-CARDIO-104-v2026.4", "RULE-B"]  |
      | text_spans       | [{"start": 112, "end": 133}, {"start": 147, "end": 155}] |
      | adjudication_hash| SHA-256 inmutable de la decisión          |
    And almacena el registro en un almacenamiento WORM o tabla con versionamiento inmutable.
```
