# Segmentos y vistas guardadas

Los segmentos se expresan como JSON estructurado con tres claves: `and`,
`or` y `sort`. Cada condición usa únicamente un campo y operador de la lista
tipada del servicio; no se aceptan rutas ORM, columnas, SQL ni expresiones.
Los grupos OR están limitados en cantidad y tamaño, y sus condiciones se
validan antes de construir cualquier `Q`.

La consulta empieza con `visible_leads(actor)`. Por lo tanto el alcance de
campaña, equipo u objeto se aplica antes del conteo, la paginación y cualquier
filtro de relación. El orden siempre agrega `pk` como desempate para que un
cursor no duplique ni omita filas con el mismo valor de orden.

Las vistas privadas sólo pertenecen a su creador. Una vista compartida debe
ser creada y aprobada por un gerente; al ejecutarla, su definición se vuelve
a aplicar con el alcance del usuario que la abre y nunca amplía permisos.
Copiar crea una vista privada nueva; renombrar y archivar conservan el
registro y la versión estructurada original.
