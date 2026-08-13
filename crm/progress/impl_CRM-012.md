# Implementation report — CRM-012

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the intentionally
  dirty completed-feature worktree recorded in `progress/current.md`.
- Requirement IDs: CRM-012-R01 through CRM-012-R05
- Acceptance-criterion IDs: CRM-012-AC01 through CRM-012-AC05
- Allowed scope: bounded reporting search service, platform search endpoint and
  template, focused tests, search documentation, and this report.
- Dependencies and assumptions: CRM-006, CRM-007, and CRM-008 are done. The
  centralized `visible_leads` policy is the visibility boundary for search.
- Persisted assignment: `crm012_search_implementer_terra`, `gpt-5.6-terra`,
  high reasoning.
- Runtime note: this environment does not expose switchable model identities
  or a separate Terra process. The work followed the persisted assignment and
  the discrepancy is recorded rather than silently substituting an inherited
  assignment.

## Changed files and decisions

- `src/simple_crm/reporting/search.py`: added bounded query validation,
  permission-first candidate derivation, exact email/phone matching,
  accent-insensitive names and aliases, PostgreSQL full-text/trigram ranking,
  bounded fallback similarity, authorized activity/task matches, stable
  deterministic paging, and human-readable reasons.
- `src/simple_crm/platform/views.py`, `src/simple_crm/platform/urls.py`, and
  `src/simple_crm/platform/templates/platform/search.html`: added the Spanish
  search page with permission-checked lead links and safe empty/error states.
- `tests/reporting/test_search.py`, `tests/platform/test_search_page.py`: added
  service, leakage, abuse, pagination, and endpoint coverage.
- `crm/docs/search.md` and related architecture/convention/verification docs:
  documented the visibility, indexing, input, and non-mutating similarity
  boundaries.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-012-AC01 | Exact normalized contact matching, canonical-name normalization, alias terms, and bounded similarity candidate pool. | Focused fixtures find exact email, normalized phone, accented/unaccented name, alias typo, and one-character variation. | Pass |
| CRM-012-AC02 | Visible leads and visible party IDs are derived before candidate search, notes, counts, ranking, and snippets. | Cross-scope test confirms an outsider's party, lead, and note produce zero results. | Pass |
| CRM-012-AC03 | Search results expose a match reason and a lead-detail URL protected by the existing endpoint policy. | Service and rendered endpoint tests assert reasons, URLs, and Spanish content. | Pass |
| CRM-012-AC04 | PostgreSQL path uses `SearchVector`/`SearchRank` and `TrigramSimilarity`; all result work is bounded and deterministic. | Static checks and focused harness pass; representative timing is recorded by the full local test harness. | Pass |
| CRM-012-AC05 | Query length, wildcard count, page size, and cursor are explicitly bounded and validated. | Boundary tests reject oversized, wildcard-heavy, and malformed cursor input. | Pass |

## Verification

Exact commands run:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format src/simple_crm/reporting/search.py src/simple_crm/platform/views.py src/simple_crm/platform/urls.py tests/reporting/test_search.py tests/platform/test_search_page.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check src/simple_crm/reporting/search.py src/simple_crm/platform/views.py src/simple_crm/platform/urls.py tests/reporting/test_search.py tests/platform/test_search_page.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src/simple_crm/reporting src/simple_crm/platform
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/reporting/test_search.py tests/platform/test_search_page.py
```

Relevant output:

```text
All checks passed!
Success: no issues found in 10 source files
5 passed, 2 warnings in 1.60s
```

The two warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Risks and follow-up

- PostgreSQL p95 timing and query plans require a PostgreSQL-volume staging run;
  the local harness uses SQLite and validates behavior, bounds, and ordering.
- Search similarity is intentionally explanatory and never performs entity
  merging or canonical mutation.
- CRM-012 is implemented but not yet approved or marked done; independent
  validator review is required.
