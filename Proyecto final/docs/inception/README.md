# Documentación de Fase: Inception
**Proyecto:** Arquitectura Distribuida en AWS para Auditoría y Adjudicación Financiera Masiva de Órdenes Médicas  
**Entorno:** Licitación Proyecto COIL (Target 12M órdenes) + Prototipo AWS Academy Learner Lab  
**Metodología:** AI-DLC (AWS Labs)  

---

## Estructura de Entregables de Inception

```
docs/inception/
├── README.md                                          # Este índice general
├── 01_requisitos_funcionales_bdd.md                   # RF-01 al RF-05 en formato Gherkin (Given/When/Then)
├── 02_requisitos_no_funcionales.md                    # Matriz de calidad cuantificable y modelo de extrapolación
└── adrs/
    ├── ADR-001-estrategia-procesamiento.md            # Justificación: Ingesta Continua + Batch Desacoplado
    ├── ADR-002-anonimizacion-pii-y-trazabilidad.md    # Manejo de DNO, HIPAA/GDPR, Spans y Hash SHA-256
    └── ADR-003-estrategia-mvp-lab-aws.md              # Estrategia MVP Lab vs Producción 12M
```

### Resumen de Decisiones Clave y Reglas de Negocio Fijadas:
1. **Unidad de Medida:** "Orden Médica / Cuenta Médica" auditada.
2. **Identificador del Paciente (DNO):** Documento Nacional de Operación / Identidad + Número de Seguro Social, pseudonimizados mediante HMAC-SHA256 antes del procesamiento.
3. **Escalonamiento de Liquidación:** Basado en el perfil del usuario (Categoría A: 100%, Categoría B: 50%, Categoría C: 25%, No asegurado / Exclusión: 0%).
4. **Metas Técnicas del Equipo:** $F_1\text{-score} \ge 0,92$ (evaluado contra ground-truth sintético) y reducción de costos $\ge 70\%$.
5. **Ruta de Procesamiento:** Arquitectura Híbrida Desacoplada (Ingesta Continua con amortiguador S3/SQS + Procesamiento masivo elástico por lotes).
