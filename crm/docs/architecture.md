# Architecture contract

Simple CRM is a server-rendered Django 5.2 modular monolith. All Python modules
live below `src/simple_crm`; a generic top-level package such as `platform`
must never be added because it could shadow the Python standard library.

## Components and ownership

- `config`: URL composition, environment parsing, and ASGI/WSGI/settings entry
  points. It owns no business rules or records.
- `crm`: durable owner of controlled campaign, lead-status, interaction-channel,
  interaction-outcome, specialty, country, province, and locality catalogs;
  party master data, contacts, and lead lifecycle behavior also belong here.
- `activity`: future interactions, tasks, and reminders.
- `data_quality`: future imports, matching, deduplication, and lineage.
- `reporting`: future queries, metrics, saved views, and exports.
- `identity`: future user profile, authentication integration, and roles.
- `platform`: operational HTTP concerns. It owns the landing page and health
  probes, but not business workflows.

Each component is an explicit Django app with a stable `simple_crm_*` label.
Apps may depend on shared Django abstractions and call another app through a
documented service interface. Templates and views orchestrate requests; they
must not contain persistent business rules. Cross-app model imports and shared
mutable utility modules require an architecture decision before use.

## Persistence and environments

PostgreSQL 18 is the deployed, development, integration, staging, and
production database boundary. The generic `test` settings use SQLite only for
database-agnostic checks; PostgreSQL-specific migration evidence uses the
dedicated `simple_crm_crm003_test` database. Settings validate a PostgreSQL
`DATABASE_URL` at import and fail closed when configuration is absent or
malformed. Connections have bounded lifetimes, health checks, and request
transactions. The platform migration enables `pg_trgm` before search work.
Future records belong to one domain app; cross-domain writes go through the
owner's service layer and a single transaction boundary.

Catalog codes are immutable machine identifiers; Spanish labels, ordering and
activation are steward-maintained. Deactivation preserves readable historical
values but removes them from new-selection querysets. Province belongs to
country and locality to province through protected foreign keys. The audit
ledger is append-only; PostgreSQL triggers independently prevent code/catalog
mutation/deletion and audit update/deletion beyond generic model/admin guards.

Django admin and the built-in `Data Stewards` group are the temporary catalog
surface, limited to add/change/view permissions. Django superusers retain their
native access. This adds no custom users, teams, OIDC, object scopes, or CRM-005
role model.

CRM-005 extends the existing Django user boundary with `simple_crm.identity`:
enabled identity profiles, seeded role/action assignments, teams, explicit
object/team/campaign scopes, and bounded temporary elevations. The policy
service is the only supported visibility boundary for future lists, search,
details, reports, exports, and direct object URLs. OIDC authorization-code with
PKCE is preferred; local Argon2 login is an explicitly enabled outage fallback.

CRM-006 keeps reusable party identities separate from campaign leads. A party
has exactly one database-enforced person or organization subtype. Contact points
are atomic and can be shared across parties; raw evidence/provenance remains
alongside deterministic normalized values. Parties are archived rather than
deleted and use optimistic version checks for edits.

CRM-007 owns the separate lead aggregate: campaign context, explicit party
links, source and readiness fields, assignment history, and immutable stage
history. Lead services are the transaction boundary for create, transition, and
reassignment operations. They use CRM-005 campaign/team scopes and optimistic
locking; URL or request-body identifiers never grant visibility. The lead keeps
a compact next-action commitment until CRM-008 introduces first-class tasks.

CRM-008 owns `simple_crm.activity`: interactions, participant links, tasks, and
append-only activity audit events. Its quick-contact service locks the lead and
atomically coordinates activity writes with an optional CRM-007 stage update;
the CRM-005 policy is re-checked at this boundary. Timeline projection joins
activity with CRM-007 stage and assignment history without copying those
records. Date-only source precision remains explicit.

CRM-009 owns the server-rendered workspace and navigation in
`simple_crm.platform`. Workspace queries compose `visible_leads()` with
scope-aware activity filters and fixed urgency classifications; they do not
reimplement lead or task writes. Human-readable lead numbers are the only
detail-route identifier exposed to sellers, and inaccessible detail requests
fail closed.

CRM-010 owns lossless source staging and lineage in
`simple_crm.data_quality`. Upload/preview writes never touch canonical CRM
records. Batch checksums and parser/application versions make reruns idempotent;
approval and application are separate steward-authorized, audited transactions.
Ambiguous canonical correction remains with the later governed quality/cutover
features.

CRM-011 owns reviewable quality issues and match candidates in the same data
quality app. Exact identifiers create deterministic candidates and fuzzy names
create evidence-only review candidates. Approved merges are the only path that
redirects canonical relationships; they lock parties, preserve contact
suppression, aliases, and source lineage, archive the duplicate, and append an
audited before/after record.

CRM-012 owns the reporting search boundary. It derives visible leads through
the centralized identity policy before inspecting party, contact, lead, or
activity text. Search similarity is explanatory only and cannot mutate or
merge canonical records.

CRM-013 keeps guided filters and saved views in `simple_crm.reporting` as
structured JSON validated by an allow-list. Saved-view execution rebuilds the
query through the requesting identity's visible leads, so sharing a definition
never shares data outside that identity's scope.

CRM-014 keeps metric semantics in versioned reporting catalog records. Its
dashboard service is read-only, scope-first, and returns definition and
timeframe metadata with each projection so templates cannot silently redefine
business KPIs.

CRM-015 keeps export requests and artifacts in the reporting boundary. Export
permission is separate from view permission; materialization reapplies current
scope, uses an explicit safe field layout, and retains audit metadata after
artifact expiry.

CRM-016 keeps privacy cases, legal holds, retention decisions, suppression
workflow, and safe cross-feature governance audit in `data_quality`. Privacy
bundles require audit authorization and redact unrestricted notes/files;
retention execution is approval-gated and non-destructive by default.

CRM-017 keeps transactional outbox jobs and notification preferences in
`simple_crm.platform`. Task services create, replace, and cancel reminder jobs
inside their existing transactions. The worker polls bounded batches with row
leases, stable provider idempotency keys, safe retry summaries, and dead-letter
review; it does not introduce a broker or send external messages by itself.

CRM-018 keeps the critical experience server-rendered and progressively
enhanced. Shared local accessibility defaults provide visible focus, skip
navigation, touch-sized controls, and responsive overflow without introducing
a SPA or a remote asset dependency. The public Spanish help page is the
maintained user guide and glossary.

CRM-019 keeps deployment security in `config` and application authorization in
the existing identity policy. A small local middleware adds CSP and
permissions headers; Django remains authoritative for CSRF, HTTPS, cookies,
HSTS, framing, and content-type checks. The opt-in
`scripts/verify-postgres-security.sh` procedure proves deployment role grants
and campaign-scoped lead RLS on a disposable PostgreSQL database. Database
role/RLS enforcement is defense in depth and never a reason to bypass scoped
services.

CRM-020 keeps operations provider-neutral. One locked multi-stage image runs
Gunicorn web processes or the bounded outbox worker as a non-root user;
staging and production supply configuration externally. Correlation-aware JSON
events and aggregate metrics belong to the configuration/platform boundary and
never contain request bodies, SQL, credentials, or personal payloads. Managed
PostgreSQL backup/PITR and encrypted object storage are deployment contracts;
the repository provides gated restore-drill and runbook adapters rather than a
cloud-specific implementation.

Django stores timezone-aware datetimes in UTC (`USE_TZ=True`) and presents
business time in `America/Argentina/Cordoba`. The primary UI locale is
Argentine Spanish.

## Stable operational interfaces

- `/health/live/` is a dependency-free, non-cached process check returning
  only `{"status":"ok"}`.
- `/health/ready/` executes `SELECT 1`, is non-cached, and returns only a
  generic ready/unavailable state with HTTP 200/503.
- `simple_crm.config.settings.{development,test,staging,production}` are the
  supported settings modules.
- `manage.py`, `config.asgi`, and `config.wsgi` are the supported process entry
  points.
- Bootstrap 5.3.8 and HTMX 2.0.10 are versioned local static dependencies;
  runtime templates must never load CDN assets. WhiteNoise serves collected,
  manifest-versioned static files in deployed settings.

Expected user errors must be represented without tracebacks. Operational
errors may be logged server-side by later observability work, but HTTP bodies
must not expose exception text, credentials, hostnames, backend versions, or
stack traces. New dependencies, components, or stable interfaces require a
feature-list decision before implementation.
