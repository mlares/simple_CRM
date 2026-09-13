# Simple CRM

Base de una aplicación web en español para que el equipo comercial gestione
clientes, oportunidades, interacciones y tareas. El proyecto usa Django 5.2,
Python 3.12 y dependencias administradas exclusivamente con UV.

## Preparación local

```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync --locked --all-groups
export DATABASE_URL='postgresql://crm:local-password@localhost:5432/simple_crm'
UV_CACHE_DIR=/tmp/uv-cache uv run --locked python manage.py migrate
UV_CACHE_DIR=/tmp/uv-cache uv run --locked python manage.py runserver
```

`manage.py` usa `simple_crm.config.settings.development` de forma
predeterminada y requiere `DATABASE_URL` de PostgreSQL. La portada estará en
`http://127.0.0.1:8000/`; la sonda de proceso en `/health/live/` y la de base
de datos en `/health/ready/`. La suite genérica usa el módulo `test` y SQLite;
la aceptación de PostgreSQL se ejecuta sólo contra PostgreSQL 18 dedicado.

## Verificación y formato

```bash
UV_CACHE_DIR=/tmp/uv-cache ./scripts/verify-fast.sh
UV_CACHE_DIR=/tmp/uv-cache bash scripts/verify-clean.sh
UV_CACHE_DIR=/tmp/uv-cache ./scripts/format.sh
```

Los dos primeros comandos no modifican fuentes. `verify-clean.sh` crea y
elimina un entorno virtual temporal, trabaja sin red usando el lockfile y la
caché local, y ejecuta toda la verificación rápida. `format.sh` sí modifica
archivos y debe invocarse de manera explícita.

## Configuración desplegada

Staging y producción no heredan valores de desarrollo. Requieren:

- `DJANGO_SECRET_KEY`: clave aleatoria fuerte de al menos 50 caracteres;
- `DJANGO_ALLOWED_HOSTS`: nombres de host exactos separados por coma, sin
  comodines ni URLs;
- `DATABASE_URL`: URL `postgresql://` o `postgres://`;
- `DJANGO_DEBUG=false` si se declara;
- cookies seguras; cualquier valor explícito falso para
  `DJANGO_SESSION_COOKIE_SECURE` o `DJANGO_CSRF_COOKIE_SECURE` es rechazado.

Consulte [.env.example](.env.example) para nombres y formatos sin secretos.
La arquitectura y las reglas de contribución viven en `crm/docs/`.

## Estado de entrega

El estado actual está resumido en [PROJECT_STATUS.html](PROJECT_STATUS.html).
Hay 20 de 23 funcionalidades cerradas (87,0%). CRM-020 está en
`changes_requested`: sus defectos de código quedaron resueltos y el harness
completo alcanza 229 pruebas, pero la validación independiente retuvo la
aprobación por falta de evidencia externa obligatoria. Faltan el registro de
promoción del mismo digest entre staging y producción, el ensayo de despliegue
y rollback, el recorrido de observabilidad, la restauración aislada y firmada
desde backup/PITR con RPO/RTO medidos y artefactos cifrados, y las pruebas de
disparo/recuperación de las cuatro alertas requeridas. CRM-021 sigue pendiente:
depende de CRM-020 y no hay ningún workbook fuente presente; CRM-022
también sigue pendiente.

## Operación y recuperación

El mismo digest de imagen se promueve a staging y producción. `Dockerfile`
construye una imagen bloqueada y no root; `docker/entrypoint.sh web` inicia
Gunicorn y `docker/entrypoint.sh worker` inicia el trabajador acotado de
recordatorios. La configuración, las credenciales y la base PostgreSQL se
inyectan desde la plataforma de despliegue.

Los eventos operativos son JSON, tienen `X-Request-ID` y omiten cuerpos,
SQL, credenciales y datos personales. Las SLI, alertas y runbooks están en
[`ops/observability.yaml`](ops/observability.yaml) y
[`ops/runbooks.md`](ops/runbooks.md). Verifique los artefactos con
`bash scripts/verify-operations.sh`; el simulacro de restauración requiere una
orden explícita y dos bases PostgreSQL desechables con nombres exactos.

## PostgreSQL 18 y activos locales

Para la aceptación de migraciones use únicamente una base desechable vacía
llamada `simple_crm_crm003_test`; nunca apunte esta orden a desarrollo,
staging o producción:

```bash
export DATABASE_URL='postgresql://crm:local-password@localhost:5432/simple_crm_crm003_test'
export SIMPLE_CRM_POSTGRES_ACCEPTANCE=1
UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-postgres.sh
```

La orden comprueba PostgreSQL 18, exige que `public` esté vacío, migra y prueba
que la segunda ejecución no cambia nada. Para reiniciar esa base, elimínela o
recréela sólo mediante la herramienta administrada que identifica exactamente
`simple_crm_crm003_test`; no use comandos recursivos ni comodines. Los activos
Bootstrap y HTMX se sirven desde `static/vendor/`; su procedencia y checksum
están en `THIRD_PARTY_LICENSES/vendor-assets.json`.

## Catálogos controlados

`simple_crm.crm` es el propietario durable de campañas, estados de lead,
canales y resultados de interacción, especialidades y geografía. Cada valor
tiene código estable inmutable, etiqueta española editable, orden y estado
activo. Los valores inactivos siguen visibles en referencias históricas, pero
no se ofrecen al crear una selección nueva; no se eliminan, se desactivan.

El grupo integrado de Django `Data Stewards` tiene solamente permisos de ver,
crear y modificar estos catálogos en `/admin/`; los administradores del
sistema conservan su acceso nativo. Es una frontera temporal: identidad,
equipos, OIDC y autorización por alcance pertenecen a CRM-005. Cada cambio
genera auditoría append-only con actor, cambio y snapshot. El baseline se carga
por migración y sólo crea códigos faltantes, sin sobrescribir etiquetas editadas.

La aceptación PostgreSQL de catálogos exige una base PostgreSQL 18 vacía y
desechable llamada exactamente `simple_crm_crm004_test`:

```bash
export DATABASE_URL='postgresql://crm:local-password@localhost:5432/simple_crm_crm004_test'
export SIMPLE_CRM_POSTGRES_ACCEPTANCE=1
UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-postgres-catalogs.sh
```

Demuestra restricciones de códigos y geografía, inmutabilidad de código y
auditoría en base, y repetición idempotente del seed. No la ejecute contra otra
base ni reutilice una que ya contenga tablas.

## Identidad y autorización

CRM-005 mantiene la cuenta local de Django como límite de identidad y agrega
perfiles habilitados, seis roles comerciales, permisos de acción separados,
equipos y alcances explícitos por objeto, equipo o campaña. La autorización es
denegada por defecto: toda decisión exige identidad habilitada, acción y
alcance. Las consultas de listas, búsqueda, reportes y exportaciones deben usar
el servicio central de `simple_crm.identity.policy`.

OIDC es el acceso normal y usa authorization-code con PKCE; la MFA la exige el
proveedor. Configure `OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`,
`OIDC_CLIENT_SECRET` y `OIDC_REDIRECT_URI` sólo mediante el entorno. El acceso
local con Argon2 está deshabilitado por defecto y sólo se habilita durante una
indisponibilidad de OIDC con `DJANGO_LOCAL_AUTH_FALLBACK_ENABLED=true`; debe
deshabilitarse cuando el proveedor vuelva a estar disponible. La baja de una
identidad rechaza nuevos accesos y elimina la sesión existente en la próxima
petición. Consulte [el contrato de identidad](crm/docs/identity.md) para la
matriz de roles y el protocolo de elevación temporal.

## Partes y contactos

CRM-006 agrega el maestro reutilizable de partes: cada parte es exactamente una
persona o una organización, con relaciones efectivas entre organizaciones y
personas, especialidades, domicilios, aliases y puntos de contacto atómicos. Un
punto de contacto institucional puede compartirse sin convertirlo en un
identificador personal. Los valores originales y su procedencia se conservan;
los correos se comparan en minúsculas y los teléfonos válidos se normalizan a
E.164 cuando el número argentino es inequívoco.

Los valores inválidos o ambiguos conservan su texto y estado de calidad. La
supresión es durable y excluye el contacto del alcance de outreach. Antes de
crear una parte, `preview_party_creation()` devuelve advertencias por
coincidencia exacta de email/teléfono o similitud de nombre; no hay merge
automático. Las partes se archivan, no se eliminan, y sus ediciones usan
control optimista de versión. Consulte [el contrato de partes](crm/docs/parties.md).

## Leads

CRM-007 modela los leads por separado de las partes reutilizables y enlaza cada
persona u organización mediante un rol explícito. El lead conserva campaña,
etapa, preparación de datos, origen, propietario, historial append-only y un
próximo paso mínimo. Las transiciones, reasignaciones y creaciones pasan por
servicios atómicos con control optimista y autorización por campaña/equipo;
los candidatos repetidos generan advertencias sin merge automático. Consulte
[el contrato de ciclo de vida de leads](crm/docs/lead_lifecycle.md).

## Interacciones y tareas

CRM-008 ofrece el flujo de contacto rápido: registra fecha de ocurrencia,
canal, dirección, resultado gobernado, participantes, nota y actor; conserva
la diferencia entre fecha de ocurrencia y fecha de carga. Puede crear la tarea
siguiente, cambiar la etapa y auditar todo en una sola transacción. `Sin acción`
no es una interacción, las tareas mantienen estados y fechas coherentes, y la
línea de tiempo combina interacciones con historial de etapas y asignaciones
respetando el alcance del usuario. Consulte [el contrato de actividad](crm/docs/activity.md).

## Espacio de trabajo

CRM-009 agrega las vistas server-rendered `Hoy` y detalle de lead. Muestran
trabajo vencido, para hoy, respuestas, seguimientos estancados y elementos sin
responsable en un orden de urgencia transparente y respetando el alcance del
usuario. La navegación usa etiquetas en español, estados vacíos útiles y el
número legible del lead; las escrituras siguen en los servicios de leads y
actividad. Consulte [el contrato del espacio de trabajo](crm/docs/workspace.md).

## Importaciones

CRM-010 recibe hojas `.xlsx` de forma acotada y conserva checksum, versión del
parser, bytes fuente, hoja, coordenada, fila cruda, clasificación y evidencia
de errores antes de cualquier aprobación. Las repeticiones son idempotentes;
sólo un responsable de datos puede aprobar o aplicar, y cada paso queda
auditado por separado. La carga no modifica datos canónicos automáticamente.
Consulte [el contrato de importaciones](crm/docs/imports.md).

## Calidad y merges gobernados

CRM-011 prioriza incidencias de calidad y genera candidatos exactos o
similares con evidencia. La similitud nunca fusiona por sí sola: un responsable
de datos debe revisar, aprobar y justificar la operación. La vista previa
enumera relaciones, contactos, aliases y trazabilidad; la fusión aprobada
preserva supresión y procedencia, archiva el duplicado y audita el antes y el
después. Consulte [el contrato de calidad](crm/docs/quality.md).

## Fixtures

No existen todavía fixtures de ventas: los modelos y fixtures de dominio
pertenecen a sus futuras funcionalidades propietarias. Las pruebas genéricas
actuales usan factories o datos en memoria, sin clientes ni datos de producción.
Cuando una funcionalidad propietaria agregue un fixture versionado, cárguelo
explícitamente con `manage.py loaddata <versioned-owned-fixture>` dentro de ese
entorno y propiedad documentados. Mientras no exista uno, la inspección segura
es no mutante:

```bash
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test \
  UV_CACHE_DIR=/tmp/uv-cache uv run --locked python manage.py showmigrations
```

La aceptación PostgreSQL comienza siempre con la base dedicada vacía; no carga
fixtures ni reutiliza datos de pruebas anteriores.
