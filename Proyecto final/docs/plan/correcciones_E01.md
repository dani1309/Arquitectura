# Correcciones propuestas al Entregable 01

| Campo | Valor |
| :--- | :--- |
| Documento revisado | [Entregable_01_Propuesta_Arquitectura_Salud_COIL.docx](../../entregables/E01/Entregable_01_Propuesta_Arquitectura_Salud_COIL.docx) |
| Contraste con | [enunciado](../enunciado/TrabajoFinal.pdf), [diccionario de datos](../../data/ref/COIL_diccionario_datos.md), [RF](../inception/01_requisitos_funcionales_bdd.md), [RNF](../inception/02_requisitos_no_funcionales.md), ADR-001 a ADR-005 y [arquitectura técnica](../design/03_arquitectura_tecnica.md) |
| Estado | Propuesta para revisión del equipo. El .docx no se modificó |

Cada fila resume el texto actual del E01, explica por qué choca con el repositorio, el dataset o el enunciado, y propone un cambio puntual. Si el E01 ya se entregó (pendiente de confirmar), estas correcciones sirven para el documento consolidado del E04.

## 1. Metas del equipo frente a metas del enunciado

El enunciado pide procesar 12 millones de consultas en menos de 24 horas, clasificar si cubre o no cubre, calcular 100 %, 50 % o 25 % según el perfil del usuario y registrar una salida trazable. Evalúa tiempo total, costo de operación, escalabilidad y trazabilidad, y habla de "costo razonable". Las metas siguientes no aparecen en el enunciado y el E01 debería presentarlas como metas propias del equipo.

| Meta | Dónde aparece en el E01 | Dónde aparece en el repositorio | ¿Está en el enunciado? |
| :--- | :--- | :--- | :--- |
| F1 mayor o igual a 0,92 | 1.2, 2.1, 3.1, 3.4, 3.5, 3.6, 4.1, 4.2 y 5.2 | RNF-02 | No |
| Ahorro mayor o igual a 70 % | 1.2, 1.3, 2.1, 2.2, 3.1, 3.4, 3.5, 3.6, 4.1, 4.2, 5.1 y 5.2 | RNF-03 | No, el enunciado pide costo razonable |
| Ventana de 3 horas a 1.111 órdenes por segundo | 1.2, 1.3, 2.1, 3.1, 3.5, 4.1, 4.2, 5.1 y 5.2 | RNF-01 y ADR-001 | No, el enunciado fija menos de 24 horas |
| Revisión humana menor al 4 % del volumen | 5.2, capa 5 | No aparece. La arquitectura (sección 11.2) solo fija el umbral de 30 % para cumplir RNF-03 | No |

Cambio propuesto. Agregar en la sección 2 una tabla que separe los requisitos del enunciado de las metas del equipo, y en cada mención de las metas usar "meta del equipo".

## 2. Correcciones por sección

| Sección | Texto actual resumido | Problema | Cambio propuesto |
| :--- | :--- | :--- | :--- |
| Portada y 1.1 | El contexto se basa en ADRES, Fonasa, DATASUS, NHSBSA y CMS, con cifras de Medicare | El E01 nunca nombra al Sistema de Salud de Chernovia ni al dataset COIL. El enunciado habla de "un gobierno federal" y el dataset es de Chernovia | Mantener los casos internacionales como antecedentes y agregar un párrafo que ubique la licitación en Chernovia con el dataset COIL de 1.200.000 solicitudes en 3 días hábiles (diccionario de datos), con 10 entidades emisoras y 7 canales (ADR-001) |
| 1.2, ítem 1 | Se extraen de texto clínico no estructurado el paciente, la edad, los diagnósticos y los medicamentos con posología (principio activo, concentración, dosis, frecuencia y cantidad) | La glosa del dataset es semiestructurada y sigue una plantilla fija con `Paciente`, `DNO`, `SeguroSocial`, `Edad`, `PerfilCobertura`, `ServicioSolicitado` y `Medicacion`, que es solo una lista de nombres. No hay diagnósticos ni posología. El enunciado dice "identificación del paciente, edad y medicación" | Describir la plantilla real y la extracción de RF-02, es decir `Edad`, `PerfilCobertura`, `ServicioSolicitado` y `Medicacion` con spans, más la pseudonimización de `Paciente`, `DNO` y `SeguroSocial` |
| 1.2, ítem 2 | La entidad clínica extraída se cruza con "el catálogo normativo vigente" | No dice qué campo se cruza ni con qué catálogo | Indicar que `ServicioSolicitado` se cruza con `COIL_catalogo_servicios_cubiertos.csv` (`COV-001` a `COV-020`) según RF-03 |
| 1.2, ítem 3 | El porcentaje de 100, 50 o 25 % depende de la edad, la patología y el grupo terapéutico | El porcentaje sale de `PerfilCobertura` cruzado con `COIL_catalogo_perfiles_cobertura.csv` (`PRIORITARIO` 100 %, `ESTANDAR` 50 %, `COPAGO` 25 %). El enunciado dice "según el perfil del usuario" y el diccionario de datos lo confirma en su regla 2 | Reemplazar por la regla de RF-04, con 0 % cuando el servicio no está cubierto |
| 1.2, ventana de 3 horas | La ventana de 3 horas se presenta como requisito y se cita [10] | Es meta del equipo (sección 1 de este documento). Hay que verificar que [10] diga eso | Marcarla como meta del equipo y verificar la cita |
| 1.3, Costo y Escalabilidad | La reducción de costos se logra con "cómputo distribuido efímero e instancias Spot" y "cómputo distribuido en memoria" | Describe EMR con Spot. ADR-004 eligió Lambda Arm consumiendo chunks de 5.000 órdenes desde SQS | Describir el cómputo como workers Lambda por chunks que escalan con la cola (ADR-001 y ADR-004) |
| 1.3, Trazabilidad | Linaje por columna, versión de regla y offsets de caracteres | Falta la protección de PII. La glosa trae nombre e identificadores, y ADR-002 y RNF-05 exigen pseudonimizarlos | Agregar la pseudonimización con `HMAC-SHA256`, el enmascaramiento con `#` que conserva los spans y el `hash_decision` sobre JSON canónico (ADR-002) |
| 2.1 | El objetivo general es auditar mediante NLP, con F1 mayor o igual a 0,92, ahorro mayor o igual a 70 % y ventana de 3 horas | Las tres metas son del equipo. "NLP" sobredimensiona una extracción sobre plantilla fija | Redactar el objetivo con los requisitos del enunciado y poner las metas del equipo como indicadores |
| 2.2, objetivo 1 | Caracterizar órdenes y glosas con paciente, edad, diagnósticos y medicamentos | No hay diagnósticos en el dataset | Usar los campos del diccionario de datos |
| 2.2, objetivo 3 | Arquitectura Lakehouse de cinco capas con EMR Graviton2, Spark, Spark NLP, SparkRules e Iceberg | Contradice ADR-004 (Lambda), ADR-005 (DynamoDB, Iceberg y bucket WORM) y ADR-003, que descarta EMR en el Learner Lab | Describir la arquitectura de la sección 4 del documento de arquitectura técnica |
| 2.2, objetivo 4 | Demostrar un ahorro mayor o igual a 70 % frente a COTS y a serverless por caracteres | La línea base del 70 % no coincide con RNF-03, que la mide frente a la auditoría médica manual de 0,80 USD por orden con revisión manual menor al 30 %. Además el E01 compara contra tres líneas base distintas en 1.2, 2.2 y 5.1 | Usar una sola línea base, la de RNF-03, o dejar la decisión al equipo (pregunta C-02) |
| 3.1, PICO | La intervención es batch con Spark en EMR o Glue y el comparador es serverless con Lambda, Step Functions y Comprehend Medical. La población incluye evoluciones e historia clínica | La alternativa elegida, Lambda por micro-lotes (ADR-001, alternativa C), no está en el PICO. Las evoluciones y la historia clínica no existen en el dataset | Agregar la ruta híbrida por chunks como intervención y ajustar la población a las glosas COIL |
| 3.4 C | El serverless puro pierde eficiencia porque Step Functions cobra 10 transiciones por orden y Comprehend Medical cobra por bloques de 100 caracteres, con glosas de 500 caracteres. Además obliga a externalizar el contexto del paciente | El costo con el que se descarta serverless es el de procesar orden por orden con Step Functions y Comprehend, no el del diseño elegido. La arquitectura usa Lambda por chunks de 5.000 órdenes, no usa Comprehend y cuesta 3,02 USD por día para 12 M (sección 11.1). La glosa real promedia unos 213 caracteres (RF sección 1.1). El catálogo y el perfil se cargan en memoria, sin externalizar contexto | Precisar que la crítica aplica a la orquestación por orden y a las APIs por carácter, y que el patrón por micro-lotes evita ambos |
| 3.5, fila AWS Architecture Benchmarks | EMR de 185 a 260 USD por día supera a Glue y a Step Functions | Choca con los 3,02 USD por día del diseño elegido. Además tiene un `$` suelto (ver sección 3) | Agregar una fila con el diseño elegido o aclarar que la comparación no lo incluye |
| 3.5, fila Khan SparkRules | Lotes masivos de 12 millones de órdenes | La cifra coincide exactamente con la del problema del curso. Hay que verificar que [16] valide ese volumen | Verificar contra la fuente y, si no lo dice, quitar la cifra |
| 3.5, síntesis de benchmarks | La tabla justifica F1 con químicos, enfermedades, dosis, frecuencia y aserciones | Ninguna de esas entidades existe en la glosa COIL. RNF-02 mide F1 sobre `Edad`, `PerfilCobertura`, `ServicioSolicitado` y `Medicacion` | Reducir la tabla a antecedente y aclarar que el extractor del proyecto trabaja sobre la plantilla (arquitectura sección 8.1, punto 3) |
| 3.6, brecha 1 | Spark NLP en EMR Spot cuesta unos 220 USD por día, un ahorro mayor al 99 % frente a APIs por carácter | El diseño elegido cuesta 3,02 USD por día (0,25 USD por millón). Además tiene un `$` suelto (ver sección 3) | Comparar contra el costo del diseño elegido |
| 3.6, brecha 2 | El pagador debe cruzar con catálogos colombianos (CUPS, CUM, RIPS, SOAT) | El proyecto usa los catálogos COIL de Chernovia | Mencionar los catálogos colombianos como ejemplo de soberanía normativa y nombrar los catálogos COIL como los del proyecto |
| 3.6, brecha 3 | Se propone SparkRules con DMN 1.3 y códigos de razón | La trazabilidad del diseño se basa en catálogos versionados (`catalogo_version`), `regla_ids`, spans y `hash_decision` (RF-05 y ADR-002) | Describir el mecanismo de trazabilidad del diseño |
| 3.6, brecha 4 | Se desacopla Iceberg de un cómputo efímero en EMR | El cómputo elegido es Lambda (ADR-004) | Cambiar EMR por los workers Lambda |
| 4, introducción y 4.1 | Ruta crítica de 6 fases (diagnóstico, PRISMA, diseño Lakehouse, construcción en PySpark, pruebas de escala y FinOps) | No menciona AI-DLC, que es la metodología del repositorio con 6 pasos (problema, requisitos, arquitectura, plan, implementación y verificación), aprobación por paso, requisitos BDD y ADR. Tampoco sigue la ruta sugerida del enunciado (comprensión, estado del arte, formulación, diseño técnico, implementación y evaluación) | Describir AI-DLC y agregar una tabla que relacione sus 6 pasos con las fases del enunciado y con los entregables E01 a E04 |
| 4.1, Fase 1 | Especificación formal de reglas DRL y DMN 1.3, esquema con diagnóstico | No existen reglas DRL ni DMN en el repositorio. Las reglas son los dos catálogos CSV y los escenarios BDD de RF-03 y RF-04 | Nombrar los catálogos COIL y los escenarios BDD como la especificación de reglas |
| 4.1, Fases 3 y 4 | Lakehouse con EventBridge, EMR, SparkRules, Medallion, Redshift y SHACL, y pipeline en PySpark sobre EMR con Spark NLP en español | Contradice ADR-004 y ADR-005 y la arquitectura técnica | Describir el diseño y el plan de construcción ([04_plan_construccion.md](04_plan_construccion.md)) |
| 4.1, Fase 5 | Generar un dataset sintético de 12 millones de órdenes | El curso entrega un dataset oficial de 1.200.000 solicitudes y ADR-003 decide extrapolar a 12 M con el modelo M/M/c | Usar el dataset oficial y la extrapolación. La corrida de 12 M queda como opción T4b del plan |
| 4.1, Fase 6 | Costos con AWS Calculator comparando EMR, Glue, Step Functions y COTS | El repositorio calcula costos con `modelo_capacidad_costo.py` | Citar el modelo del repositorio y el costo real que mida T5 |
| 4.2 | La bitácora se lleva por hitos semanales. Pone como ejemplo de acuerdo elegir Graviton2 Spot en lugar de Glue | El ejemplo contradice ADR-004. La bitácora ya existe en el repositorio | Cambiar el ejemplo por una decisión registrada y enlazar [bitacora_decisiones.md](../bitacora/bitacora_decisiones.md) |
| 5.1, introducción | Se recomienda Spark en EMR Graviton2 Spot, con ahorro de 78 a 99 % frente a serverless, Glue y COTS | Contradice ADR-004. El ahorro se mide contra una línea base distinta de RNF-03 | Presentar el diseño elegido y su costo de la sección 11 de la arquitectura técnica |
| 5.1, tabla, opción A | Step Functions con 10 pasos por orden más Comprehend Medical con 500 caracteres por glosa, 153.000 USD por día | Es el escenario orden por orden que ADR-001 ya descartó (alternativa B), con una glosa de más del doble del promedio real | Rotularla como comparador por orden y, si se conserva, recalcularla con unos 213 caracteres por glosa |
| 5.1, tabla, opción B | Serverless optimizado, unos 8.500 USD por día | Tiene un `$` suelto (ver sección 3) | Corregir el formato |
| 5.1, tabla, opción D2 | Clúster EMR con 24 nodos c6g.4xlarge (384 vCPU) | No se puede demostrar en el Learner Lab, que según ADR-004 permite como máximo 32 vCPU y nueve instancias, y no lista EMR | Agregar la fila del diseño elegido (Lambda Arm por chunks, 3,02 USD por día) y dejar D2 como alternativa evaluada |
| 5.2, capas 1 a 5 | Ingesta de JSON, Parquet, CSV, RIPS y FHIR, extracción en EMR con diagnóstico y negaciones, SparkRules con SHACL, S3 Tables con Lake Formation y Redshift, revisión humana menor al 4 % | El dataset es CSV. Los servicios no coinciden con los contenedores de la arquitectura técnica (sección 4). El 4 % no tiene sustento en el repositorio | Reemplazar la tabla por los contenedores de la arquitectura técnica y quitar o marcar el 4 % como meta del equipo sin medir |
| 6, referencias | Lista de [1] a [51] | El cuerpo cita [57] en 3.4 C (Comprehend Medical solo en inglés) y esa entrada no existe. Las entradas [7], [9], [18], [27], [31], [36], [38], [40], [42], [46] y [50] no se citan en el cuerpo | Agregar o corregir [57] y citar o retirar las entradas sin cita |

## 3. Restos de LaTeX y formato

| Patrón | Cantidad | Dónde | Cambio propuesto |
| :--- | :--- | :--- | :--- |
| `\,%` | 109 | En todo el documento, por ejemplo "10\,%" en 1.1 y "70\,%" en 1.2 | Reemplazar por " %" (con espacio fino o normal, según el estilo del documento) |
| `$` pegado al final | 3 | 3.5, fila AWS Architecture Benchmarks ("USD/día$"), 3.6 brecha 1 ("≥ 0,92$") y 5.1 opción B ("USD/día$") | Borrar el `$` sobrante |
| Moneda escrita dos veces | Varias | Por ejemplo "$903.000 millones de dólares" y "$3.000 USD" | Usar un solo formato, por ejemplo "3.000 USD" |

## 4. Preguntas para el equipo

| ID | Pregunta |
| :--- | :--- |
| C-01 | ¿El E01 ya se entregó? Si es así, ¿estas correcciones van al E04 o se entrega una versión corregida? |
| C-02 | ¿Qué línea base del 70 % se adopta, la de RNF-03 (auditoría manual) o las del E01 (COTS, serverless o arquitecturas transaccionales)? |
| C-03 | RNF-03 fija la auditoría manual en unos 0,80 USD por orden sin citar fuente. ¿De dónde sale esa cifra? |
| C-04 | El enunciado habla de 12 millones de consultas en menos de 24 horas y no dice que sean diarias. El E01, los RNF y la arquitectura calculan costos por día como si el volumen se repitiera cada día. ¿Se mantiene esa lectura? |
| C-05 | ¿Qué fuente corresponde a la cita [57]? |
