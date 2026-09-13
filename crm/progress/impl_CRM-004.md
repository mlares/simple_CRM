# Implementation report — `CRM-004`

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` dirty completed-feature
  worktree. Existing CRM-001/002/003/023 changes, `PROJECT_STATUS.html`,
  official vendor assets/licenses, and staged bytecode deletion were preserved.
- Requirement IDs: CRM-004-R01, CRM-004-R02, CRM-004-R03, CRM-004-R04,
  CRM-004-R05.
- Acceptance-criterion IDs: CRM-004-AC01, CRM-004-AC02, CRM-004-AC03,
  CRM-004-AC04.
- Allowed scope: task-envelope allowlist only; no lifecycle, task, validator,
  other-app, sales-record, custom-user, team, or OIDC files were modified.
- Assignment: persisted implementer `crm004_catalog_implementer_terra`,
  `gpt-5.6-terra` / `high`; actual runtime matches.
- Dependencies and assumptions: CRM-003 is available. `simple_crm.crm` is the
  approved durable catalog owner; Django admin/built-in groups are the bounded
  temporary maintenance surface, before CRM-005.

## Changed files and decisions

- `src/simple_crm/crm/models.py`: eight controlled catalog models—campaign,
  lead status, interaction channel/outcome, specialty, country, province and
  locality—with unique immutable codes, editable Spanish labels/order/active
  state, useful per-catalog flags, protected geography parents and scoped
  geography uniqueness. Catalog deletion is rejected; `display_label` keeps an
  inactive value readable. `CatalogAuditEntry` records actor/action/change and
  snapshot evidence and rejects editing/deletion.
- `src/simple_crm/crm/forms.py`: reusable active-only queryset and choice field
  that include one supplied current inactive value for historical editing.
- `src/simple_crm/crm/admin.py`: limited admin maintenance with immutable code
  after creation, no catalog deletion, actor-aware saves, and view-only
  append-only audit administration.
- `src/simple_crm/crm/apps.py`: idempotent `post_migrate` creation of the
  built-in `Data Stewards` group, limited strictly to add/change/view
  permissions for the eight catalog models. No custom user, team, or CRM-005
  authorization model was added.
- `src/simple_crm/crm/migrations/0001_initial.py`: deterministic schema,
  checks, unique constraints, protected geography FKs and audit table.
- `src/simple_crm/crm/migrations/0002_seed_baseline_catalogs.py`: approved
  Spanish baseline values loaded with `get_or_create` by stable code only;
  repeating it neither duplicates codes nor overwrites any edited label.
- `src/simple_crm/crm/migrations/0003_postgres_catalog_guards.py`: PostgreSQL
  triggers independently prevent direct catalog code changes/deletion and
  audit-row updates/deletion, while SQLite retains generic model coverage.
- `scripts/verify-postgres-catalogs.sh`: fail-closed, non-disclosing PostgreSQL
  18 gate requiring an empty database named exactly `simple_crm_crm004_test`.
  It migrates, proves no-op migration/seed behavior and proves duplicate code,
  unknown parent FK, direct code update, and audit update/delete fail at the DB
  boundary.
- `tests/crm/` and `tests/integration/test_verify_postgres_catalogs_script.py`:
  deterministic seed, selection, model/audit, constraint, permission/crafted
  admin request, migration-shape and gate-safety coverage.
- `README.md`, `.env.example`, and `crm/docs/{architecture,conventions,verification}.md`:
  owner decision, temporary group boundary, steward/deactivation/audit/seed
  procedures, and safe dedicated test procedure.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-004-AC01 | `0002_seed_baseline_catalogs` uses stable-code `get_or_create` and never updates an existing row | Focused idempotency test passed; the independent PostgreSQL 18 gate edited `GENERAL`, reran the seed, and confirmed one row with the edited label retained | PASS |
| CRM-004-AC02 | `selectable_catalog_values`/`CatalogChoiceField` exclude inactive values unless the current value is supplied | Focused form/queryset test passed: inactive values stay readable and historical-current values remain selectable while new choices exclude them | PASS |
| CRM-004-AC03 | Bounded Data Stewards permissions, no-delete admin policy, immutable code and actor audit | Focused permission tests passed: unauthorized add/change POSTs returned 403; crafted steward code input was ignored while permitted label editing was audited | PASS |
| CRM-004-AC04 | Schema unique/FK constraints and PostgreSQL code/audit guard triggers | Independent PostgreSQL 18 gate exited 0 after empty-schema migration/no-op rerun and verified duplicate code, unknown parent FK, direct code mutation, audit update, and audit deletion are rejected | PASS |

## Verification

Focused catalog verification:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q \
  tests/crm tests/integration/test_verify_postgres_catalogs_script.py
9 passed, 2 non-fatal WhiteNoise static-directory warnings in 0.56s
```

Full required matrix:

```text
timeout 60s ./crm/init.sh
harness metadata valid; fast suite passed; 135 passed, 6 non-fatal warnings

PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .
All checks passed!

PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .
79 files already formatted

PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src
Success: no issues found in 38 source files

PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q
135 passed, 6 non-fatal WhiteNoise static-directory warnings

DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test ... manage.py check
System check identified no issues (0 silenced).

DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test ... makemigrations --check --dry-run
No changes detected

bash scripts/verify-vendored-assets.sh
vendored assets verified

bash scripts/verify-repository-safety.sh
repository safety scan passed

UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-clean.sh
Created isolated temporary environment; full locked/offline matrix passed with
135 passed, 6 non-fatal warnings, no migration drift, asset and safety checks.

git diff --check
No output (passed)
```

PostgreSQL acceptance chronology and final resolution:

```text
UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-postgres-catalogs.sh
exit 1
scripts/verify-postgres-catalogs.sh: line 8: DATABASE_URL: DATABASE_URL must target the dedicated CRM-004 test database
```

This initial attempt intentionally failed before opening a connection and did
not disclose any URL. Once the fresh dedicated handoff was available, the
independent validator executed the same gated PostgreSQL 18 acceptance command
with its ephemeral connection value only in the process environment. It exited
0 with the sanitized output:

```text
PostgreSQL catalog acceptance passed: constraints, immutable audit, and idempotent seeds
```

That execution proved the initially empty schema, applied migrations, required
a no-op second migration run, preserved an edited seed label without duplicate
code, and proved the database rejects duplicate codes, unknown geography
parents, direct stable-code mutation, and audit update/deletion. The validator
is independent (`crm002_foundation_validator`, `gpt-5.6-sol` / `high`); this
implementer is `crm004_catalog_implementer_terra`, `gpt-5.6-terra` / `high`.
An early ad-hoc `makemigrations` invocation without a test settings module also
failed as designed because development requires `DATABASE_URL`; the prescribed
test-settings drift command above passed.

## Final resolution

All four acceptance criteria now have generic and, where required,
independently executed PostgreSQL 18 evidence. The ephemeral connection value
was never written to this report. The dedicated acceptance database is
single-use because the gate correctly requires an initially empty schema; any
future rerun needs a newly provisioned empty database named exactly
`simple_crm_crm004_test`.

## Correction loop — PostgreSQL evidence closure

- Actual correction runtime: `crm004_catalog_implementer_terra`,
  `gpt-5.6-terra` / `high`, matching the persisted assignment.
- The independent validator found no implementation defect; no application,
  migration, script, test, or documentation correction was necessary.
- The fresh no-volume PostgreSQL 18 handoff named exactly
  `simple_crm_crm004_test` was consumed once by the independent validator. Its
  successful sanitized result is recorded above; this implementer did not
  connect to, consume, or otherwise alter it, and no connection value is
  recorded here.
- `git diff --check` was re-run after this report-only note and passed with no
  output. The dirty baseline, `PROJECT_STATUS.html`, vendor assets/licenses,
  and staged bytecode deletion remain preserved.
