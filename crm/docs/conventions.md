# Project conventions

## Runtime and layout

- Python 3.12+, Django 5.2, and the committed `uv.lock` are supported.
- Run all application tooling as `uv run --locked`; system Python is reserved
  for the dependency-free CRM harness check.
- Source belongs under `src/simple_crm/<owning_app>/`; tests mirror that
  ownership below `tests/` and use names beginning with `test_`.
- Django apps use explicit `AppConfig` classes and `simple_crm_*` labels.
- Business-domain models and migrations start in their owning feature, not in
  the foundation.

## Checked commands

- Non-mutating full check: `UV_CACHE_DIR=/tmp/uv-cache ./scripts/verify-fast.sh`
- Clean locked/offline check:
  `UV_CACHE_DIR=/tmp/uv-cache bash scripts/verify-clean.sh`
- Mutating format: `UV_CACHE_DIR=/tmp/uv-cache ./scripts/format.sh`

Ruff targets Python 3.12, djLint checks Django templates, mypy uses
django-stubs with test settings, and pytest-django discovers both application
and harness tests. The Python-3.8-compatible harness checker and its contract
tests are excluded from the Python 3.12 formatter boundary and remain covered
by `crm/init.sh` plus pytest. Never hand-edit `uv.lock`; use UV when an approved
feature changes dependencies.

## Application behavior

- User-visible copy and semantic HTML are in Spanish; the root document uses
  `lang="es-AR"`.
- Code identifiers, comments, and logs are in English. Logs must use structured
  fields and must never include secrets, credentials, or raw imported rows.
- Catch only errors that can be handled. Public errors are generic; diagnostic
  details stay in protected server logs.
- Tests must be deterministic, isolate settings imports when validating
  environment behavior, and simulate dependency failures without network
  access.
- Generated caches, virtual environments, local databases, coverage files,
  and `.env` files are ignored and must not be committed.
- Do not commit credentials, customer data, local environment files, or
  downloaded assets without their source URL, version, license notice, SRI,
  and SHA-256 in `THIRD_PARTY_LICENSES/vendor-assets.json`. Node.js and CDN
  runtime dependencies are not part of this project.

## PostgreSQL operations

Development, integration, staging, and production require a PostgreSQL
`DATABASE_URL`. The generic test settings deliberately remain database-agnostic.
Run normal migrations with `manage.py migrate` against the intended configured
environment. The PostgreSQL 18 acceptance command may run only with
`SIMPLE_CRM_POSTGRES_ACCEPTANCE=1` and a URL whose database name is exactly
`simple_crm_crm003_test`; it first proves that `public` is empty. Never reset,
drop, or recreate a database by wildcard, broad directory path, or an
unverified environment variable.

CRM-019 security acceptance is separately gated by
`SIMPLE_CRM_POSTGRES_SECURITY_ACCEPTANCE=1` and the exact database name
`simple_crm_crm019_security_test`. It receives role passwords only through the
disposable database secret facility, proves role grants and lead-scope RLS,
and cleans up its temporary roles. Never point it at an application database.

Operations acceptance uses `scripts/verify-operations.sh` for repository
artifacts and `scripts/restore-drill.sh` only with
`SIMPLE_CRM_RESTORE_DRILL=1` plus exact disposable source/restore database
names. The same image digest must be promoted to staging and production;
configuration and credentials are external. JSON operational events use route
names and bounded fields only; never log bodies, SQL, raw workbook rows,
credentials, or personal identifiers.

## Fixtures and test data

There are no sales-domain fixtures in the foundation. Domain models and their
fixtures belong to the later feature that owns them; do not invent customer
records to exercise infrastructure. Generic tests use factories or in-memory
data. Once an owning feature provides a versioned fixture, the only supported
load boundary is `manage.py loaddata <versioned-owned-fixture>` under that
feature's documented settings and database. Until then, inspect migration state
without mutation using test settings and `manage.py showmigrations`. PostgreSQL
acceptance begins from an empty dedicated database and loads no fixtures.

## Catalog stewardship

Catalog baseline data is a versioned CRM migration, not an editable fixture.
It uses `get_or_create` by stable code and deliberately never updates an
existing row, so an approved Spanish label survives repeated loading. Maintain
labels, ordering, behavior flags and activation in Django admin as a system
administrator or `Data Stewards` member; never change a code or delete a
catalog/audit row. Deactivate obsolete values instead.

When adding a form that references a catalog, use
`simple_crm.crm.forms.selectable_catalog_values()` or `CatalogChoiceField`.
New objects receive active values only; pass the current value to retain one
inactive historical selection. Do not replace that policy with an unfiltered
hand-written queryset.

## Party master data

Create parties through `simple_crm.crm.services.create_person_party()` or
`create_organization_party()` so subtype creation, contact provenance, and
duplicate warnings remain in one transaction. Treat
`preview_party_creation()` as a warning surface, never as permission to merge;
automatic fuzzy merges are out of scope. Display `raw_value` when a contact
quality state is invalid or ambiguous and use only
`ContactPoint.selectable_for_outreach()` for new outreach choices.

Party changes must preserve `version` and handle `PartyConcurrencyError` as a
readable conflict. Archive through `Party.archive()` and query active work with
`Party.objects.active()`; do not delete a party or use a raw update that skips
the optimistic-concurrency boundary.

## Lead lifecycle

Create, transition, and reassign leads through `simple_crm.crm.lead_services`.
Use explicit `LeadPartyRole` values for links, `visible_leads()` for scoped
lists, and expected versions for direct edits. Never edit or delete
`LeadStageHistory`; it is append-only. An `EN_GESTION` lead needs a description
and due date for its next task or a documented reason, and closing needs a
closure reason. Reassignment must close the prior primary assignment and add a
new history row in the same transaction.

## Activity and tasks

Use `simple_crm.activity.services.quick_contact()` for the seller's contact
workflow. Pass CRM catalog codes for channel and outcome, a governed
`InteractionResult`, and preserve a missing exact time as `None`. Never turn
`Sin acción` into an interaction. Create or mutate tasks through the activity
services so completion/reschedule timestamps and audit events remain coherent;
use `lead_timeline()` for permission-scoped event ordering.

## Seller workspace

Build Today and lead detail views from `simple_crm.platform.workspace` helpers.
Keep urgency labels and ordering explicit, use `visible_leads()` before any
related activity query, and show an empty state when no actionable work is
visible. Templates use Spanish labels and human-readable lead numbers; never
render table names, foreign keys, SQL terms, or raw primary keys. Presentation
views do not write domain records directly.

## Search

Use `simple_crm.reporting.search.search()` for global lookup. It must derive
visible leads through `visible_leads()` before reading identity, contact, lead,
or activity text; input, page size, and cursor remain bounded. Return a
human-readable match reason and a permission-checked lead URL. Similarity is a
review aid only and never mutates canonical records.

Use `simple_crm.reporting.services.execute_definition()` for guided segments.
Only its typed field/operator allow-list may build ORM predicates; saved views
store structured definitions, never SQL. Apply `visible_leads()` before counts
and use the stable sort tie-breaker for cursors.

Use `simple_crm.reporting.metrics.dashboard()` for governed reports. Metric
definitions, occurrence-date semantics, scope, freshness, and `as_of` metadata
come from the service; templates must not calculate KPIs or bypass
`visible_leads()`.

Use `simple_crm.reporting.exports.request_export()` and
`materialize_export()` for files. Require `BULK_EXPORT`, snapshot structured
definitions and fields, reapply scope at materialization, neutralize formula
controls, and never log full file contents.

Use `simple_crm.data_quality.privacy.privacy_bundle()` for governed personal
data lookup, `suppress_contact_point()` for durable suppression, and the
preview/approve/execute retention sequence. Governance audit metadata must be
safe summaries, never unrestricted notes or file payloads.

## Transactional jobs

Use `simple_crm.platform.jobs.schedule_task_reminder()` from an activity
transaction; never enqueue a reminder after commit from a template or view.
Reminder payloads contain stable task/lead references only. Use
`run_worker_once()` as the bounded deployment adapter, preserve the job's
provider idempotency key, and treat expired leases as retries or dead letters.
Operator projections must use `operator_jobs()` and must not expose payload
values, notification bodies, or provider credentials. Notification preferences
default to digest and escalation requires administrative authorization.

## Accessible presentation

Keep critical templates in Spanish with `lang="es-AR"`, a unique descriptive
title, visible field labels, a skip link to `#contenido`, and semantic heading
order. Use ordinary `href` links and native `method` forms first; HTMX is an
optional enhancement and must not be required to complete a normal action.
Load the local accessibility stylesheet, preserve visible `:focus-visible`
feedback, and use text alongside any status color. Prefer cards or a
`.table-responsive` wrapper at narrow widths, and never hide a required action
behind a hover-only or drag-only interaction.

## Security boundaries

Use `url_has_allowed_host_and_scheme()` for every post-authentication redirect,
keep CSRF tokens on state-changing forms, and return generic operational
errors. Do not log credentials, full payloads, database URLs, or exception
arguments. Preserve bounded service limits for search, exports, and imports;
never widen a query or upload limit in a view. Production roles and secrets
are provisioned outside source control, and PostgreSQL privilege/RLS evidence
must be captured on a disposable acceptance database.

## Import staging

Use `preview_workbook()` for `.xlsx` staging and never write canonical parties,
leads, contacts, interactions, or tasks during upload/preview. Preserve raw
source values and coordinates, use checksum/parser/application-version
idempotency, and route approval/application through the data-steward service
with a nonblank reason. Do not auto-correct ambiguous rows; keep source
lineage and rejection evidence for the quality workflow.

## Quality and merge

Use `find_exact_candidates()` or `find_fuzzy_candidate()` to create review
records; never merge from a similarity score. Require `review_candidate()` and
then `merge_approved_candidate()` with an explicit reason. Inspect
`preview_merge()` first, preserve suppressed contacts and source links, and
archive duplicate parties instead of deleting them. Record all issue and merge
decisions through the quality services.

## Identity and authorization

Use `simple_crm.identity.policy.can_access()` for a detail or direct-object
decision, `require_access()` for an endpoint, and `scoped_queryset()` for any
list, search, report, or export. Every caller supplies an action and normalized
object/team/campaign scope. Do not infer visibility from a template, URL
parameter, Django `is_staff`, or a view-only permission. Temporary elevation
must be created through `grant_temporary_elevation()` so its reason,
approver, expiry, and subsequent use audit are preserved.
