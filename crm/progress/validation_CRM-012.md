# Validation report — CRM-012

## Verdict

`APPROVED`

## Independence and scope

- Validator: `crm012_search_validator_sol`
- Persisted validator assignment: `gpt-5.6-sol`, high reasoning; implementer
  assignment was the distinct `crm012_search_implementer_terra` /
  `gpt-5.6-terra`.
- Runtime note: this environment does not expose switchable model identities or
  a separate validator process. The independent validator pass was executed as
  a separate review phase with no implementation-file edits; the discrepancy
  is recorded rather than silently substituted.
- Implementer: `crm012_search_implementer_terra`
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188` plus the dirty
  worktree baseline recorded in the task envelope.
- Allowed validator write target: `progress/validation_CRM-012.md`

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-012-AC01 | Search service exact contact normalization, canonical-name/alias matching, PostgreSQL text/trigram path, bounded fallback similarity, and fixtures. | Pass | Exact email/phone, accent-insensitive names, alias text, and one-character similarity are found with deterministic reasons. |
| CRM-012-AC02 | `visible_leads()` boundary, visible party ID derivation, authorized interaction/task querysets, and cross-scope test. | Pass | Out-of-scope parties, leads, notes, totals, ranking, and snippets do not enter the result set. |
| CRM-012-AC03 | `SearchResult` reason/url fields, protected lead-detail route, Spanish template, and endpoint test. | Pass | Every result explains its match and links to a human-readable, permission-checked lead detail. |
| CRM-012-AC04 | PostgreSQL `SearchVector`/`SearchRank`/`TrigramSimilarity` path, bounded candidate limits, stable sort, and verification output. | Pass | The production path has indexed text/trigram hooks; local full-harness timing is green, with PostgreSQL-volume p95 retained as staging follow-up. |
| CRM-012-AC05 | Query, wildcard, cursor, page-size validation and boundary tests. | Pass | Oversized, wildcard-heavy, malformed, and out-of-range input is rejected without unbounded search work. |

## Verification

Exact commands run:

```text
python -m json.tool crm/feature_list.json >/dev/null
python -m json.tool crm/progress/tasks/CRM-012.json >/dev/null
timeout 60s ./crm/init.sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/reporting/test_search.py tests/platform/test_search_page.py
git diff --check
```

Relevant output:

```text
Success: no issues found in 68 source files
181 passed, 15 warnings in 4.62s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
5 passed, 2 warnings in 1.61s
```

The warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Findings

- Scope: implementation is limited to permission-scoped search, safe Spanish
  rendering, bounded input, tests, and documentation. Saved filters, reports,
  exports, and search-driven merging remain separate features.
- Security: scope is applied before candidate construction and ranking, and
  direct result links continue through the existing lead-detail authorization
  boundary.
- Architecture: PostgreSQL full-text/trigram expressions are isolated behind
  the PostgreSQL backend check; the SQLite fallback is bounded and preserves
  the same visibility and deterministic ordering rules.
- Regression: full harness, formatting/linting, type checks, template checks,
  migration drift, system checks, repository safety, vendored assets, and
  focused search tests pass.
- Environment limitation: representative PostgreSQL p95 query-plan evidence
  requires a PostgreSQL-volume staging run; the local generic harness uses
  SQLite and validates behavior and bounds.
- No unresolved changes requested.
