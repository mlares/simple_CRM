# Validation report — `CRM-003`

## Verdict

`APPROVED`

All five requirements and all four acceptance criteria pass. The bounded
provenance correction preserves the verified official HTMX notice bytes and
checksum while accurately recording SPDX `0BSD`, the `Zero-Clause BSD`
header, and a `0BSD` filename. The prior sanitized PostgreSQL 18 acceptance
evidence remains valid and the consumed database was not contacted again.

## Independence and scope

- Validator: `crm002_foundation_validator`; persisted assignment and actual
  runtime `gpt-5.6-sol`, reasoning effort `high`, source `role_default`. No
  runtime discrepancy was observed.
- Implementer: `crm003_postgres_implementer_terra`; persisted and reported
  runtime `gpt-5.6-terra`, reasoning effort `high`, source `role_default`.
  The implementer and validator are distinct agents, and this validator did
  not implement CRM-003.
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188`, the
  recorded dirty completed-feature baseline, plus current source, assets,
  manifests, scripts, tests, docs, lifecycle metadata, reports, worktree, and
  staged state.
- Allowed validator write target: `crm/progress/validation_CRM-003.md` only.
  No source, asset, license, manifest, script, test, feature-state,
  task-envelope, current/history, database, container, or staged file was
  modified by this validator.

## Requirement evidence

| Requirement ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-003-R01 | PostgreSQL-only environment settings, connection helper, platform migration, acceptance script, and successful reserved-database execution. | PASS | The sanitized acceptance execution exited 0 only after confirming PostgreSQL major 18, an initially empty dedicated database, successful migrations, `pg_trgm`, and a no-op second migration run. |
| CRM-003-R02 | URL/config helpers, settings variants, 38 focused tests, fail-closed cases, repository scan, and connection configuration. | PASS | `DATABASE_URL` is required and non-PostgreSQL/malformed values fail generically without disclosure. Connections use `CONN_MAX_AGE=60`, health checks, and `ATOMIC_REQUESTS=True`; no real credential is persisted. |
| CRM-003-R03 | `0001_enable_pg_trgm.py`, migration-shape test, acceptance script, and successful real database gate. | PASS | The migration contains `TrigramExtension`; the real acceptance run queried and found `pg_trgm` after applying migrations. |
| CRM-003-R04 | Local Bootstrap/HTMX files, template paths, WhiteNoise storage, manifest, independently recomputed checksums/SRI, official notices, static finder/collection, tests, and verifier. | PASS | Bootstrap remains 5.3.8/MIT. HTMX remains 2.0.10 with unchanged official bytes and license SHA-256, now accurately recorded as SPDX `0BSD` at `THIRD_PARTY_LICENSES/htmx-2.0.10-0BSD.txt` with exact `Zero-Clause BSD` header. The verifier/tests enforce the exact name/version/license/header tuples plus existing runtime SHA-256, SRI, license checksum, local resolution, and collection. |
| CRM-003-R05 | README, `.env.example`, architecture, conventions, verification docs, and documented non-mutating fixture procedure. | PASS | Bootstrap, migration, fixture/defer boundary, bounded reset, and verification are documented without broad destructive commands. Sales fixtures remain deferred to their future owning features; PostgreSQL acceptance stays empty and fixture-free. |

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-003-AC01 | One pristine reserved PostgreSQL 18 execution plus script inspection. | PASS | The authorized acceptance execution exited 0 with `PostgreSQL migration acceptance passed: empty apply and no-op rerun`. That success is reachable only after the script checks major version 18, confirms zero `public` tables, applies migrations, verifies second-run no-op, and finds `pg_trgm`. Connection details are intentionally neither reproduced nor persisted. |
| CRM-003-AC02 | Focused configuration/settings tests and parser/source inspection. | PASS | Development, integration, staging, and production reject missing or malformed database configuration with actionable generic errors and no value leakage. |
| CRM-003-AC03 | Rendered page tests, filesystem and static-finder resolution, guarded collectstatic, manifest storage, local template paths, asset verifiers, and Node/CDN scan. | PASS | Bootstrap CSS and HTMX JS resolve locally, collect into the manifest, and match pinned hashes. The Spanish page references only Django static paths; no public CDN, package manifest, Node runtime, or frontend build tool exists. |
| CRM-003-AC04 | Repository safety verifier, examples, fixture/source review, secret/provider scan, and staged state. | PASS | No real secret, production credential, customer data, or customer fixture was found. Examples and test markers are disposable, and repository safety passes. |

## Verification

The PostgreSQL acceptance command was run once against the pristine reserved
database. Its connection value is deliberately omitted from this durable
report. The authorized execution exited 0 and printed only:

```text
PostgreSQL migration acceptance passed: empty apply and no-op rerun
```

All generic task-envelope commands ran exactly from the repository root:

| Exact command | Relevant output | Result |
| --- | --- | --- |
| `timeout 60s ./crm/init.sh` | Final correction revalidation: harness valid; `71 files already formatted`; mypy clean; `126 passed, 4 warnings`; safety, semantic vendor, Django, migration, and deployment checks passed; harness ready. | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .` | `All checks passed!` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .` | `71 files already formatted` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src` | `Success: no issues found in 31 source files` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q` | `126 passed, 4 warnings in 2.30s`; warnings are the existing missing default `staticfiles/` directory during test-client middleware setup. | PASS |
| `DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py check` | `System check identified no issues (0 silenced).` | PASS |
| `DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py makemigrations --check --dry-run` | `No changes detected` | PASS |
| `timeout 60s bash scripts/verify-static.sh` | No output; exit 0 after checking both collected versioned files and their manifest entries in a guarded temporary root. | PASS |
| `bash scripts/verify-vendored-assets.sh` | `vendored assets verified`; exit 0 after exact provenance tuple, checksum, SRI, and semantic license-header checks. | PASS |
| `bash scripts/verify-repository-safety.sh` | `repository safety scan passed`; exit 0. | PASS |
| `UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-clean.sh` | Created `/tmp/simple-crm-verify.sK7EAgJP/.venv`, installed 74 locked packages, then passed 126 tests and all generic/static/semantic-vendor/deployment checks. | PASS |
| `git diff --check` | No output; exit 0. | PASS |

Additional independent evidence:

- SHA-256, SHA-384 SRI, and license SHA-256 were recomputed independently from
  the files. All matched the manifest:

  - Bootstrap: runtime SHA-256
    `d85327d99c7a3ee1f9b5d0500d1370acea3ad2db39c163c2f51f232baedbdede`,
    SRI
    `sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB`,
    license SHA-256
    `4620c84ad5ce8602ff65640ed6b7c8b78ebb9e036584f0ebc1ccc88206a4bb51`.
  - HTMX: runtime SHA-256
    `71ea67185bfa8c98c39d31717c6fce5d852370fcdfd129db4543774d3145c0de`,
    SRI
    `sha384-H5SrcfygHmAuTDZphMHqBJLc3FhssKjG7w/CeCpFReSfwBWDTKpkzPP8c+cLsK+V`,
    license SHA-256
    `d3d2456f76414f2456104660ebd65aff1c04cd7966b942bdabd63f3cdb316a38`.
- Django static finders independently returned resolved paths for both
  `vendor/bootstrap/5.3.8/bootstrap.min.css` and
  `vendor/htmx/2.0.10/htmx.min.js`; the exact collectstatic verifier also
  confirmed both physical files and both `staticfiles.json` entries.
- The earlier combined focused configuration, migration, static, safety,
  vendor, page, and health command passed all 38 tests. Final provenance
  revalidation passed all 8 static/vendor/page/health tests. The documented
  non-mutating `showmigrations` procedure had exited 0 and listed
  `simple_crm_platform 0001_enable_pg_trgm` without loading fixtures.
- Independent final provenance recomputation reported, for both assets,
  `tuple=True, sha256=True, sri=True, license_sha256=True, header=True`.
  Bootstrap resolves to `bootstrap-5.3.8-MIT.txt`; HTMX resolves only to
  `htmx-2.0.10-0BSD.txt`. The former false HTMX MIT path is absent.
- README, architecture/conventions/verification docs, and the current
  implementation report contain no false current claim that HTMX is MIT. This
  final validation report supersedes its own earlier finding with the verified
  Zero-Clause BSD/0BSD result.

## Findings

- Provenance: the former HTMX license-label defect is resolved. The verifier
  now rejects any mismatch in the expected Bootstrap/HTMX
  name/version/license/header set and verifies the notice begins with the
  declared exact header, in addition to runtime/checksum/SRI checks.
- PostgreSQL/security: the real PostgreSQL 18 gate passed with a pristine,
  empty, dedicated no-volume database. URL parsing, bounded connections,
  transactions, opt-in/name/empty-schema safeguards, extension verification,
  no-op proof, and non-disclosure are satisfactory. No connection detail is
  present in this report.
- Architecture/scope: local WhiteNoise delivery, stable versioned template
  paths, database boundaries, and fixture ownership follow the contracts. No
  sales model/migration/fixture, production provider provisioning, customer
  data, CDN runtime dependency, Node manifest, or frontend build tooling was
  found.
- Repository state: all accumulated completed-feature work was preserved. The
  pre-existing staged deletion of
  `src/simple_crm/__pycache__/__init__.cpython-312.pyc` remains staged; the
  validator made no staged-state change.
- Regression: every executable acceptance and generic check passes. The
  PostgreSQL database was deliberately not contacted again; its prior
  sanitized evidence proves PostgreSQL 18, initial emptiness, migration apply,
  `pg_trgm`, and second-run no-op. No unresolved scope, security, provenance,
  architecture, or regression finding remains.
