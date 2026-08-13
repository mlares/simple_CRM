# Implementation report — CRM-018

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the intentionally
  dirty completed-feature worktree recorded in `progress/current.md`.
- Requirement IDs: CRM-018-R01 through CRM-018-R06
- Acceptance-criterion IDs: CRM-018-AC01 through CRM-018-AC05
- Persisted implementer assignment: `crm018_accessibility_implementer_terra`,
  `gpt-5.6-terra`, high reasoning.
- Runtime note: this environment does not expose switchable model identities or
  a separate Terra process. The implementation followed the persisted role
  assignment and records that discrepancy rather than silently substituting an
  inherited assignment.

## Changed files and decisions

- `src/simple_crm/platform/static/platform/accessibility.css`: added local
  focus-visible, skip-link, touch-target, and narrow-table defaults without a
  remote dependency or drag-only interaction.
- Critical platform templates and the temporary local-login template: added
  Spanish document metadata, skip navigation, a `#contenido` target, local
  accessibility styles, visible labels/error regions, responsive wrappers, and
  ordinary native forms/links.
- `src/simple_crm/platform/views.py` and `urls.py`: added the public `/ayuda/`
  route and replaced the placeholder Help navigation target with a real link.
- `templates/platform/help.html`: added the Spanish “Cómo trabajamos” guide
  covering Today, leads, contact logging, search, saved views, quality, and a
  maintained glossary.
- `tests/platform/test_accessibility_contract.py`: added static presentation,
  native-form, guide, and rendered-page contract tests.
- `crm/docs/accessibility.md` plus architecture, convention, and verification
  updates: documented the presentation contract and required manual release
  checks.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-018-AC01 | Critical pages retain ordinary links/forms, keyboard skip navigation, semantic landmarks, and visible control focus. | Accessibility contract and existing page tests pass; a manual keyboard traversal remains a release follow-up. | Pass |
| CRM-018-AC02 | Every critical template has Spanish language metadata, descriptive metadata, semantic main content, labels/status regions, and local focus styling. | Static contract suite and template lint pass; automated browser axe evidence remains a manual follow-up because no browser runner is installed. | Pass |
| CRM-018-AC03 | Local CSS supplies 44-pixel-class controls and responsive card/table behavior; no required action relies on hover or drag. | CSS contract, rendered-page, and template checks pass; 200%/phone screenshots remain a manual release follow-up. | Pass |
| CRM-018-AC04 | Search, segments, reports, notifications, login, and navigation use native methods and no required `hx-*` behavior; `/ayuda/` works without authentication. | No-JavaScript static contract and rendered guide/home tests pass. | Pass |
| CRM-018-AC05 | Local login errors have a text alert region; critical forms retain posted values through Django form/request rendering and show field labels. | Login/template contract and existing authentication/page suites pass; screen-reader focus announcement remains a manual release follow-up. | Pass |

## Verification

Exact commands run:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/djlint src/simple_crm/platform/templates src/simple_crm/identity/templates --check
PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/platform/test_accessibility_contract.py tests/platform/test_pages_and_health.py tests/platform/test_search_page.py tests/platform/test_segments_page.py
timeout 60s ./crm/init.sh
git diff --check
```

Relevant output:

```text
14 passed, 10 warnings in 2.08s
Success: no issues found in 81 source files
210 passed, 22 warnings in 5.95s
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
```

The warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Risks and follow-up

- A real browser accessibility scan, keyboard-only session, 200% zoom review,
  phone viewport check, and screen-reader pass should be completed before
  release; this environment has no browser automation tool installed.
- The local stylesheet establishes a strong baseline but does not replace
  product-specific contrast, screen-reader, or interaction review for future
  form states.
