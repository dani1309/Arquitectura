# Dataset sintético COIL – Sistema de Salud de Chernovia

## Archivos incluidos
1. `COIL_dataset_glosas_salud_1_2M.csv`
2. `COIL_catalogo_servicios_cubiertos.csv`
3. `COIL_catalogo_perfiles_cobertura.csv`

## Descripción general
Este conjunto de datos sintético fue creado para el proyecto COIL de Big Data y Metodología de la Investigación.
El archivo principal contiene **1,200,000** solicitudes médicas generadas artificialmente, distribuidas en **3 días hábiles**.

## Esquema del archivo principal
- `id_solicitud`: identificador único de la solicitud
- `fecha_solicitud`: fecha y hora de recepción de la solicitud
- `glosa`: texto semiestructurado con la información del paciente y del servicio solicitado
- `medio_emisor`: canal por el cual ingresó la solicitud
- `valor_procedimiento`: valor monetario del procedimiento solicitado
- `entidad_emisora`: institución que emite o radica la solicitud

## Estructura de la glosa
Cada glosa sigue esta plantilla:

`Paciente: <nombre>; DNO: <identificador>; SeguroSocial: <identificador>; Edad: <edad>; PerfilCobertura: <perfil>; ServicioSolicitado: <servicio>; Medicacion: <med1>|<med2>|...`

## Regla esperada del ejercicio
1. Si `ServicioSolicitado` aparece en `COIL_catalogo_servicios_cubiertos.csv`, la solicitud se considera **cubierta**.
2. El porcentaje de cobertura se toma de `COIL_catalogo_perfiles_cobertura.csv`.
3. Si el servicio **no** está en el catálogo cubierto, el valor cubierto esperado es **0**.
