# ADR-005: Almacenamiento operativo, analítico y de evidencia

| Campo | Valor |
| :--- | :--- |
| Estado | Propuesto |
| Fecha | 2026-10-21 |
| Fase | Construction, diseño de infraestructura |
| Relacionado | ADR-002 (privacidad y trazabilidad), [03_arquitectura_tecnica.md](../03_arquitectura_tecnica.md) |

---

## 1. Contexto

El sistema tiene tres patrones de acceso a datos que se comportan de forma muy distinta.

| Patrón | Ejemplo | Volumen | Requisito |
| :--- | :--- | :--- | :--- |
| Lectura y escritura puntual por clave | Perfil del afiliado, estado del lote, idempotencia del chunk | 12 M lecturas diarias, miles de escrituras | Latencia de milisegundos y alta concurrencia |
| Consulta analítica | Monto aprobado por IPS y día, órdenes marcadas para revisión, estado de la tabla en una fecha pasada | Barridos sobre millones de filas | SQL, particionamiento, historial |
| Evidencia legal | Recibo firmado de cada decisión | Escritura única, lectura ocasional | Inmutabilidad verificable |

## 2. Alternativas evaluadas

| Alternativa | Problema principal |
| :--- | :--- |
| A. Todo en DynamoDB | Las consultas analíticas exigen exportar o escanear la tabla, y guardar cada orden cuesta unos 7,5 USD diarios solo en escrituras |
| B. Todo en Iceberg sobre S3 | No sirve para búsquedas puntuales de milisegundos ni para contadores atómicos, y muchas escrituras concurrentes generan conflictos de commit |
| C. RDS PostgreSQL | En el laboratorio se limita a instancias medium, 100 GB y sin Multi-AZ, insuficiente para 12 M filas diarias |
| D. Amazon Redshift | Costo continuo y disponibilidad no documentada en el laboratorio |
| E. Almacenamiento políglota | Tres almacenes que deben mantenerse coherentes |

## 3. Decisión

Se adopta la **alternativa E**, un almacén por patrón de acceso.

1. **DynamoDB on-demand** para el control de lotes y chunks (tabla única `control_lotes`) y para el padrón tokenizado (`padron`).
2. **Apache Iceberg sobre S3**, catalogado en Glue Data Catalog y consultado con Athena, para la tabla `adjudicaciones`. Los workers escriben Parquet en un prefijo de staging y un único consolidador ejecuta `MERGE INTO` cada 15 minutos, `OPTIMIZE` y la expiración de snapshots una vez al día.
3. **Un bucket S3 separado con Object Lock** para los recibos y manifiestos firmados.

El bucket de evidencia se separa de Iceberg a propósito. El mantenimiento de Iceberg (compactación y expiración de snapshots) necesita borrar archivos, mientras que Object Lock en modo compliance lo impide; si compartieran almacenamiento, uno de los dos dejaría de funcionar.

## 4. Consecuencias

**Positivas.** Cada patrón usa el servicio que lo resuelve con menor costo. El estado del lote para la IPS es inmediato desde DynamoDB, las consultas analíticas cuestan centavos con Athena y particionamiento por día, y los snapshots de Iceberg más los recibos en WORM permiten reconstruir cualquier decisión.

**Negativas y mitigaciones.** La tabla analítica tiene hasta 15 minutos de retraso respecto al procesamiento, lo que es aceptable porque el SLA es diario. La coherencia entre los tres almacenes se garantiza con `order_id` y `hash_decision` como claves comunes y con la verificación de la sección 7.4 del documento de arquitectura. Si el Learner Lab no permite Object Lock, el prototipo usa versionado y una política que niega el borrado de versiones, y la integridad se demuestra con la cadena de hashes.
