# Validation report — `CRM-004`

## Verdict

`APPROVED`

All five requirements and all four acceptance criteria pass. In addition to
the complete generic and clean-environment matrix, the independently executed
acceptance gate passed against the reserved fresh PostgreSQL 18 database. That
execution proved initial emptiness, migration repeatability, seed idempotency,
database constraints, immutable catalog codes, and append-only audit guards
without disclosing or persisting the ephemeral connection value.

## Independence and scope

- Validator: `crm002_foundation_validator`; persisted assignment and actual
  runtime `gpt-5.6-sol`, reasoning effort `high`, source `role_default`. No
  runtime discrepancy was observed.
- Implementer: `crm004_catalog_implementer_terra`; persisted and reported
  runtime `gpt-5.6-terra`, reasoning effort `high`, source `role_default`.
  Implementer and validator are distinct agents, and this validator did not
  implement CRM-004.
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188`, the recorded
  dirty completed-feature baseline, plus the current full diff, source,
  migrations, scripts, tests, docs, reports, lifecycle metadata, worktree, and
  staged state.
- Allowed validator write target: `crm/progress/validation_CRM-004.md` only.
  No application, configuration, script, test, feature-state, task-envelope,
  current/history, database, or staged file was modified by this validator.

## Requirement evidence

| Requirement ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-004-R01 | Eight concrete models, initial migration, baseline migration, admin registration, and model/migration tests. | PASS | Campaign, lead status, interaction channel, interaction outcome, specialty, country, province, and locality are owned by `simple_crm.crm`; no sales-domain record was added. |
| CRM-004-R02 | `CatalogBase`, behavior fields, geography constraints, admin read-only policy, ORM tests, PostgreSQL guard migration, and successful real verifier. | PASS | Stable codes are unique and rejected on model save and by the PostgreSQL trigger; Spanish labels, ordering, activation, and bounded behavior flags remain editable. |
| CRM-004-R03 | Protected geography FKs, model deletion guard, inactive display/selection helpers, focused tests, PostgreSQL triggers, admin policy, and real gate. | PASS | Deactivation preserves readable values and current inactive selections while excluding them from new choices. Model deletion is rejected and production triggers protect historical catalog rows. |
| CRM-004-R04 | `0002_seed_baseline_catalogs.py`, repeated-seed focused test, migration no-drift check, and successful PostgreSQL verifier. | PASS | The seed uses stable-code `get_or_create`; both generic and real PostgreSQL evidence prove an edited label survives rerun and the stable code remains singular. The second migration run is a no-op. |
| CRM-004-R05 | Django admin classes, `Data Stewards` post-migrate provisioning, exact permission-set test, unauthorized/crafted POST tests, model audit ledger, PostgreSQL audit trigger, docs, and real gate. | PASS | Stewards receive only add/change/view for the eight catalogs, never delete or audit permissions. Admin mutations carry the actor; unauthorized/crafted requests are bounded; PostgreSQL rejected direct audit update and deletion. |

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-004-AC01 | Seed source plus `test_baseline_seed_is_idempotent_and_preserves_steward_label`; full and focused suites. | PASS | Re-running the approved seed keeps one `GENERAL` campaign row and preserves the deliberately edited Spanish label. The seed consistently creates only missing stable codes. |
| CRM-004-AC02 | `selectable_catalog_values`, `CatalogChoiceField`, inactive display behavior, and focused test. | PASS | An inactive value renders with `(inactivo)`, is absent from a new choice queryset, and remains included when it is the current historical value. No sales record was invented merely to demonstrate the policy. |
| CRM-004-AC03 | Exact Data Stewards permission assertion, no-delete admin policy, unauthorized add/change POSTs, and crafted steward code POST. | PASS | A staff user without catalog permissions receives 403 and cannot mutate data; a steward can edit allowed fields but a crafted `code` value cannot change the stable code. The group has exactly 24 catalog add/change/view permissions and no delete permission. |
| CRM-004-AC04 | SQLite constraint test, migration DDL, fail-closed probes, and one successful reserved PostgreSQL 18 acceptance execution. | PASS | On the initially empty dedicated database, migrations applied successfully and the second run was a no-op. PostgreSQL rejected a duplicate catalog code and an unknown geography parent independently of forms; it also rejected direct code mutation and audit-row update/deletion. |

## Verification

All generic task-envelope commands were run exactly from the repository root.
The required PostgreSQL command was also run with its ephemeral connection
value present only in the process environment; that value is intentionally
omitted below.

| Exact command | Relevant output | Result |
| --- | --- | --- |
| `timeout 60s ./crm/init.sh` | Initial full run: harness metadata valid; `79 files already formatted`; mypy clean; `135 passed, 6 warnings`; Django/migration, repository-safety, vendor, and deployment checks passed. Final proportional rerun after the external handoff: `80 files already formatted`, the same 135 tests passed, and `[harness] ready`. | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .` | `All checks passed!` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .` | `79 files already formatted` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src` | `Success: no issues found in 38 source files` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q` | `135 passed, 6 warnings in 2.46s`; warnings are the known absent default `staticfiles/` directory during test-client middleware setup. | PASS |
| `DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py check` | `System check identified no issues (0 silenced).` | PASS |
| `DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py makemigrations --check --dry-run` | `No changes detected` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/crm tests/integration/test_verify_postgres_catalogs_script.py` | `9 passed, 2 warnings in 0.56s`; warnings are the same test-client staticfiles warning. | PASS |
| `bash scripts/verify-vendored-assets.sh` | `vendored assets verified` | PASS |
| `bash scripts/verify-repository-safety.sh` | `repository safety scan passed` | PASS |
| `UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-clean.sh` | Created `/tmp/simple-crm-verify.cWngxzWh/.venv`, installed 74 locked packages there, then passed lint/format/mypy, all 135 tests, Django/migration, safety, vendor, and deployment checks. | PASS |
| Required PostgreSQL acceptance command (ephemeral `DATABASE_URL` omitted) | Exit 0: `PostgreSQL catalog acceptance passed: constraints, immutable audit, and idempotent seeds`. | PASS |
| `git diff --check` | No output; exit 0. | PASS |

Additional independent evidence:

- With a harmless placeholder URL, setting
  `SIMPLE_CRM_POSTGRES_ACCEPTANCE=0` exited 2 with only
  `SIMPLE_CRM_POSTGRES_ACCEPTANCE must equal 1`. A separate harmless wrong-name
  probe with the opt-in enabled exited 1 with only
  `DATABASE_URL must target simple_crm_crm004_test`. Neither probe disclosed
  its supplied value or attempted acceptance against an application database.
- The gated verifier checks PostgreSQL major version 18, exact database name,
  and an initially empty `public` schema before migration. It then requires a
  no-op second migrate; preserves an edited seed label; and expects duplicate
  code, unknown parent, direct code mutation, audit update, and audit deletion
  to fail. The real exit-0 execution passed only after every one of those
  assertions completed. A subsequent independent attempt against the consumed
  database stopped at `Dedicated database must be empty before acceptance`,
  additionally confirming the empty-schema guard without changing the database.
- The first attempt from the filesystem sandbox could not reach loopback and
  exited with a generic connection error before database activity. The same
  exact command was then run once under the approved local-network escalation
  and completed in 0.73 seconds with the sanitized success line above. It was
  not rerun after consuming the pristine database.
- The focused tests exercise repeatable seeding, inactive selection semantics,
  ORM code/deletion/audit immutability, database uniqueness/FK constraints,
  exact steward permission bounds, unauthorized admin requests, and a crafted
  steward code-change request.

## Findings

- PostgreSQL acceptance: the one authorized execution used the fresh reserved
  PostgreSQL 18 database named `simple_crm_crm004_test`, confirmed its `public`
  schema was initially empty, applied migrations, proved the repeat run was a
  no-op, and completed every catalog constraint/guard assertion. The ephemeral
  connection value is absent from this report.
- Security: the temporary admin boundary is permission-gated and delete-free;
  crafted and unauthorized requests cannot mutate catalog codes/data. Audit
  rows are immutable at the model layer, and PostgreSQL guard definitions cover
  all eight catalog tables plus the audit table. The real gate confirmed direct
  code mutation and audit update/deletion are rejected at the database layer.
- Architecture and scope: catalog ownership stays in `simple_crm.crm`; the
  implementation adds no lead, contact, interaction, party, task, assignment,
  custom user/team/OIDC/object-scope, cloud/provider, or production-database
  work. Django built-in group/permission integration remains bounded and does
  not preempt CRM-005.
- Repository state: all accumulated CRM-001/CRM-023/CRM-002/CRM-003 work was
  preserved. Untracked `PROJECT_STATUS.html` remains present, and the
  pre-existing staged deletion of
  `src/simple_crm/__pycache__/__init__.cpython-312.pyc` remains staged. This
  validator made no staged-state change.
- Regression: every generic, focused, clean-environment, and PostgreSQL
  acceptance check passed. No unresolved implementation, scope, security,
  architecture, acceptance, or regression defect remains.
