# Protocolo de Etiquetado Manual y Criterio de Coincidencia de Spans (Tarea T5a)

| Campo | Valor |
| :--- | :--- |
| **Tarea del plan** | **T5a** — Muestra etiquetada a mano para medir F1 (`docs/plan/04_plan_construccion.md`) |
| **Resoluciones aplicadas** | **P-05** (300 glosas limpias + 300 perturbadas) y **P-15** (muestra almacenada fuera de git) |
| **Equipo anotador** | Naomi Chow (200 glosas), Daniel Lopez (200 glosas) y María Fernanda Toro (200 glosas) |
| **Ubicación fuera de git** | `C:\Users\danie\.gemini\antigravity\scratch\dataset_ref\muestra_f1_t5a` (`muestra_600_ciega_para_etiquetar.jsonl` y `muestra_600_referencia_verificada.jsonl`) |

---

## 1. Diseño de la Muestra Estratificada (600 Glosas)

1. **Subconjunto Limpio (`300` glosas — `M-LIMPIA-001` a `M-LIMPIA-300`)**:
   - Extraídas mediante muestreo sistemático a lo largo de `COIL_dataset_glosas_salud_1_2M.csv` (1.200.000 solicitudes).
   - Conservan la plantilla semiestructurada oficial del Sistema de Salud de Chernovia.
2. **Subconjunto Perturbado (`300` glosas — `M-PERT-001` a `M-PERT-300`)**:
   - Dividido equitativamente en **6 categorías de perturbación documental (50 glosas por categoría)** para someter a prueba la robustez del extractor frente a variaciones reales de digitación y OCR:
     - `P1_ESPACIOS_IRREGULARES` (50): Espacios múltiples antes/después de `:`, `;` y `|`.
     - `P2_ORDEN_CAMPOS_PERMUTADO` (50): Permutación del orden de aparición de los 7 campos en la glosa.
     - `P3_PERFIL_CASE_O_DESCONOCIDO` (50): Perfiles en minúsculas (`prioritario`, `estandar`) o no catalogados (`VIP`).
     - `P4_CAMPO_CLINICO_OMITIDO` (50): Glosas truncadas sin `Edad`, `PerfilCobertura`, `ServicioSolicitado` o `Medicacion`.
     - `P5_ETIQUETA_ALTERADA_OCR` (50): Ruido tipográfico/OCR en el nombre de la etiqueta (ej. `Servicio_Solicitado:` o `EdadPaciente:`).
     - `P6_SEPARADORES_MEDICACION_BORDE` (50): Separadores de medicación vacíos consecutivos (`| |`).

---

## 2. Independencia del Etiquetado y Protección de PII (`P-15`)

- **Cero uso de la salida del extractor**: Las etiquetas de referencia y sus desplazamientos `[start_char, end_char]` se construyen directamente en el ensamblador independiente (`_ensamblar_glosa_y_spans_referencia`) sumando las longitudes de cadena de cada segmento antes de cualquier llamada a `saom_core.py`, y la planilla ciega (`muestra_600_ciega_para_etiquetar.jsonl`) se entrega sin predicciones del modelo.
- **Protección de PII**: Antes de exportar las glosas a la planilla de etiquetado, los valores de `Paciente`, `DNO` y `SeguroSocial` se reemplazan carácter por carácter con `#`, preservando intactos los desplazamientos `[start_char, end_char]` de todas las entidades clínicas y cumpliendo **P-15** y **RNF-05**.

---

## 3. Criterio de Coincidencia Exacta de Spans (`Strict Span + Value Match`)

Una predicción $\hat{e} = (\text{entidad}, \text{valor}, \hat{s}, \hat{f})$ emitida por `extraer_y_pseudonimizar_glosa()` se contabiliza como **Verdadero Positivo (`TP`)** sí y solo sí coincide simultáneamente en:

1. **Tipo de entidad**: $\text{entidad} \in \{\text{Edad}, \text{PerfilCobertura}, \text{ServicioSolicitado}, \text{Medicacion}\}$.
2. **Desplazamiento exacto de caracteres (`Exact Span Match`)**: $\hat{s} = s_{\text{ref}}$ y $\hat{f} = f_{\text{ref}}$, verificando que `glosa[s_ref:f_ref] == valor`.
3. **Valor normalizado**: Coincidencia exacta de la cadena extraída sin espacios extremos. En `Medicacion`, cada medicamento de la lista separada por `|` se evalúa como una instancia independiente con su propio `[span_inicio, span_fin]`.

Cualquier predicción cuyos límites `[start_char, end_char]` difieran en al menos 1 carácter respecto de la referencia se penaliza simultáneamente como un **Falso Positivo (`FP`)** y un **Falso Negativo (`FN`)** (criterio estricto CoNLL / i2b2).
