# Exportaciones gobernadas

Una exportación requiere el permiso separado `BULK_EXPORT`. La solicitud
captura una definición estructurada validada, una lista explícita de columnas,
el alcance actual, un motivo y una clave de idempotencia. Materializar vuelve
a ejecutar la definición con la identidad actual; cambiar una vista después
de solicitar no cambia el snapshot.

Sólo se ofrecen columnas comerciales seguras. CSV usa UTF-8 y XLSX usa un
libro simple con encabezados conocidos; valores que comienzan con `=`, `+`,
`-` o `@` se neutralizan para evitar inyección de fórmulas. La materialización
tiene un límite de filas, checksum SHA-256, intentos, vencimiento y estado.

Las auditorías registran solicitud, denegación, materialización y descarga sin
copiar payloads completos ni credenciales. Un archivo vencido deja su
metadata/auditoría retenida, pero no puede descargarse.
