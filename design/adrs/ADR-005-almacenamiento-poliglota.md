# ADR-005: Almacenamiento operativo, analítico y de evidencia

| Campo | Valor |
| :--- | :--- |
| Estado | Aprobado |
| Fecha | 2026-10-21 (Actualizado 2026-10-27 con Dataset Oficial COIL) |
| Fase | Construction, diseño de infraestructura |
| Relacionado | ADR-002 (privacidad y trazabilidad), [03_arquitectura_tecnica.md](../03_arquitectura_tecnica.md) |

---

## 1. Contexto

El sistema tiene tres patrones de acceso a datos que se comportan de forma muy distinta:

| Patrón | Ejemplo | Volumen | Requisito |
| :--- | :--- | :--- | :--- |
| Lectura y escritura puntual por clave | Estado del lote, idempotencia del chunk (y opcionalmente padrón externo si no viene en la glosa) | Miles de escrituras y lecturas por lote/chunk | Latencia de milisegundos, transacciones condicionales y alta concurrencia |
| Consulta analítica | Monto aprobado por `entidad_emisora`, `medio_emisor` y día; órdenes marcadas para revisión; estado de la tabla en una fecha pasada | Barridos sobre millones de filas (1,2 M en prototipo, 12 M/día en producción) | SQL, particionamiento, historial (time-travel) |
| Evidencia legal | Recibo firmado de cada decisión y manifiesto con raíz hash por chunk y lote | Escritura única, lectura ocasional | Inmutabilidad verificable |

En el dataset oficial del proyecto (`COIL_dataset_glosas_salud_1_2M.csv`), el campo `PerfilCobertura` (`PRIORITARIO`, `ESTANDAR`, `COPAGO`) viene incluido dentro de la `glosa` de cada solicitud y su porcentaje de cobertura (100 %, 50 % o 25 %) se resuelve contra `COIL_catalogo_perfiles_cobertura.csv` (257 bytes), alojado junto con `COIL_catalogo_servicios_cubiertos.csv` (2.302 bytes) en el bucket versionado `saom-ref`. Esto elimina la necesidad de realizar 12 millones de lecturas diarias a una tabla de padrón en DynamoDB, aunque el diseño conserva la capacidad de consultar un padrón tokenizado si en producción el pagador decide contrastar el perfil declarado en la glosa contra una base de afiliación externa.

## 2. Alternativas evaluadas

| Alternativa | Problema principal |
| :--- | :--- |
| A. Todo en DynamoDB | Las consultas analíticas exigen exportar o escanear la tabla, y guardar cada orden cuesta unos 7,5 USD diarios solo en escrituras |
| B. Todo en Iceberg sobre S3 | No sirve para búsquedas puntuales de milisegundos ni para contadores atómicos, y muchas escrituras concurrentes generan conflictos de commit |
| C. RDS PostgreSQL | En el laboratorio se limita a instancias medium, 100 GB y sin Multi-AZ, insuficiente para 12 M filas diarias |
| D. Amazon Redshift | Costo continuo y disponibilidad no documentada en el laboratorio |
| E. Almacenamiento políglota | Tres almacenes especializados que se mantienen coherentes mediante `id_solicitud` y `hash_decision` |

## 3. Decisión

Se adopta la **alternativa E**, un almacén por patrón de acceso:

1. **DynamoDB on-demand** para el control operativo de lotes y chunks (tabla única `control_lotes` con transacciones condicionales `TransactWriteItems`). Los catálogos de referencia (`COIL_catalogo_servicios_cubiertos.csv` y `COIL_catalogo_perfiles_cobertura.csv`) se leen desde S3 `saom-ref` y se mantienen en memoria durante la vida del contenedor Lambda.
2. **Apache Iceberg sobre S3**, catalogado en Glue Data Catalog y consultado con Athena, para la tabla `adjudicaciones`. Los workers escriben archivos Parquet en un prefijo de staging y un único consolidador ejecuta `MERGE INTO` cada 15 minutos, `OPTIMIZE` y la expiración de snapshots una vez al día.
3. **Un bucket S3 separado (`saom-audit`) con Object Lock** para los recibos y manifiestos firmados.

El bucket de evidencia se separa de Iceberg a propósito. El mantenimiento de Iceberg (compactación y expiración de snapshots) necesita borrar archivos antiguos, mientras que Object Lock en modo compliance lo impide; si compartieran almacenamiento, uno de los dos dejaría de funcionar.

## 4. Consecuencias

**Positivas.** Cada patrón usa el servicio que lo resuelve con menor costo. El estado del lote para la entidad emisora es inmediato desde DynamoDB, resolver el perfil en memoria con el catálogo oficial ahorra 0,75 USD diarios (12 M de lecturas menos), las consultas analíticas cuestan centavos con Athena y particionamiento por día, y los snapshots de Iceberg más los recibos en WORM permiten reconstruir cualquier decisión.

**Negativas y mitigaciones.** La tabla analítica tiene hasta 15 minutos de retraso respecto al procesamiento, lo que es aceptable porque el SLA es diario. La coherencia entre los tres almacenes se garantiza con `id_solicitud` y `hash_decision` como claves comunes y con la verificación de la sección 7.4 del documento de arquitectura. Si el Learner Lab no permite Object Lock, el prototipo usa versionado y una política que niega el borrado de versiones, y la integridad se demuestra con la cadena de hashes.
