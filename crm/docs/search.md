# Búsqueda global

La búsqueda global recibe una consulta acotada y devuelve resultados sólo de
leads que la identidad actual puede ver. El alcance se aplica antes de leer,
ordenar, contar o paginar resultados; por eso un registro fuera de campaña o
equipo no puede alterar el total, el ranking ni los fragmentos mostrados.

Se consultan nombres normalizados, aliases, correos y teléfonos normalizados,
números de lead y notas autorizadas de interacciones y tareas. Cada resultado
explica el motivo de coincidencia y enlaza al detalle del lead, donde vuelve a
comprobarse el permiso.

La entrada tiene un límite de 120 caracteres, páginas de hasta 50 resultados,
cursor acotado y rechazo de comodines abusivos. Los resultados se ordenan por
puntaje, tipo e identificador para producir una paginación determinista.

En PostgreSQL se prepara un vector `simple` y similitud `pg_trgm` sobre los
campos de identidad y alias. El backend SQLite del harness usa una reserva
determinista de candidatos acotada, sin cambiar las reglas de visibilidad.
La similitud nunca fusiona ni modifica partes canónicas.
