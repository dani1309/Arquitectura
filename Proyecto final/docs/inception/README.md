# Documentación de Fase: Inception
**Proyecto:** Arquitectura Distribuida en AWS para Auditoría y Adjudicación Financiera Masiva de Órdenes Médicas (Sistema de Salud de Chernovia)  
**Entorno:** Licitación Proyecto COIL (Target 12M órdenes) + Prototipo AWS Academy Learner Lab ($50 USD, Dataset Oficial 1,2M)  
**Metodología:** AI-DLC (AWS Labs)  

---

## Estructura de Entregables de Inception

```
docs/inception/
├── README.md                                          # Este índice general
├── 01_requisitos_funcionales_bdd.md                   # RF-01 al RF-05 en formato Gherkin (alineado al dataset COIL)
├── 02_requisitos_no_funcionales.md                    # Matriz cuantificable y extrapolación 1:10 (1,2M -> 12M)
└── adrs/
    ├── ADR-001-estrategia-procesamiento.md            # Justificación: Ingesta Continua + Chunks de 5.000 órdenes
    ├── ADR-002-anonimizacion-pii-y-trazabilidad.md    # HMAC-SHA256 con clave secreta, enmascaramiento # y JSON canónico
    └── ADR-003-estrategia-mvp-lab-aws.md              # Estrategia Prototipo 1,2M en Learner Lab ($50 USD) vs 12M
```

### Resumen de Decisiones Clave y Reglas Oficiales del Dataset COIL:
1. **Unidad de Medida y Dataset Oficial:** Solicitud médica en `COIL_dataset_glosas_salud_1_2M.csv` (1.200.000 filas, ~360 MB, 6 columnas: `id_solicitud`, `fecha_solicitud`, `glosa`, `medio_emisor`, `valor_procedimiento`, `entidad_emisora`).
2. **Privacidad y Pseudonimización:** `DNO` y `SeguroSocial` se tokenizan mediante `HMAC-SHA256(clave_secreta, DNO || SeguroSocial)` generando `patient_token`, y en la glosa se reemplazan `Paciente`, `DNO` y `SeguroSocial` carácter por carácter con `#` para conservar los spans `[start_char, end_char]`.
3. **Dictamen de Cobertura (`COIL_catalogo_servicios_cubiertos.csv`):** Si `ServicioSolicitado` pertenece a los 20 servicios del catálogo (`COV-001` a `COV-020`), el dictamen es `CUBRE`; en caso contrario (12 servicios estéticos/experimentales/no certificados), es `NO_CUBRE` (0%).
4. **Escalonamiento de Liquidación (`COIL_catalogo_perfiles_cobertura.csv`):** Basado en `PerfilCobertura` extraído de la glosa:
   - `PRIORITARIO` $\to$ **100%**
   - `ESTANDAR` $\to$ **50%**
   - `COPAGO` $\to$ **25%**
   - Servicio `NO_CUBRE` $\to$ **0%**
5. **Metas Técnicas del Equipo:** $F_1\text{-score} \ge 0,92$, reducción de costos $\ge 70\%$ y presupuesto del Learner Lab protegido en **$\$50\text{ USD}$**.
