# Informes gobernados

Las definiciones de métricas viven en `simple_crm.reporting` y registran
propietario, descripción, numerador, denominador, reglas de inclusión,
semántica temporal, versión y fecha de vigencia. Las plantillas sólo muestran
el resultado del servicio, nunca reconstruyen una métrica.

El dashboard aplica primero `visible_leads(actor)`. Los conteos, dimensiones y
categorías se calculan desde ese conjunto; las interacciones usan
`occurrence_date` y las tareas vencidas usan el día local de Córdoba. Las
interacciones de resultado `ATTEMPTED` no forman parte del denominador de
respuesta y las notas de marcador `Sin acción` quedan excluidas.

Cada respuesta incluye período seleccionado, alcance, indicador de frescura,
cantidad de resultados y hora `as_of`, además de la definición versionada de
cada KPI. La similitud, los filtros y los informes son consultas de lectura;
no escriben registros comerciales.
