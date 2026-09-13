# Validation report — CRM-018

## Verdict

`APPROVED`

## Independence and scope

- Validator: `crm018_accessibility_validator_sol`
- Persisted validator assignment: `gpt-5.6-sol`, high reasoning; the
  implementer assignment was the distinct
  `crm018_accessibility_implementer_terra` / `gpt-5.6-terra`.
- Runtime note: this environment does not expose switchable model identities
  or a separate validator process. The validator pass was executed after the
  implementation phase against the actual files and rendered/test contracts,
  with no implementation-file edits; the discrepancy is recorded rather than
  silently substituted.
- Implementer: `crm018_accessibility_implementer_terra`
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188` plus the dirty
  worktree baseline recorded in the task envelope.
- Validator write target: `progress/validation_CRM-018.md`

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-018-AC01 | Critical templates, native links/forms, skip links, semantic landmarks, and local `:focus-visible` styling. | Pass | Contract and existing page tests pass; a manual keyboard traversal remains a release follow-up. |
| CRM-018-AC02 | Spanish metadata, descriptions, labels, status/error regions, and local focus stylesheet on every critical page. | Pass | Static contract, template lint, and full harness pass; no browser axe runner is installed here, so a real scan remains a release follow-up. |
| CRM-018-AC03 | Responsive Bootstrap layout, card/table overflow, 44-pixel-class control defaults, and accessible details summary. | Pass | Contract and rendered-page tests pass; 200% zoom and phone screenshots remain manual release evidence. |
| CRM-018-AC04 | Search/segments/reports/notifications/login forms and public help navigation without required `hx-*` behavior. | Pass | Native-form contract and public home/help tests pass; disabling JavaScript does not remove the ordinary links/forms. |
| CRM-018-AC05 | Local-login field labels and alert regions, plus Spanish contextual guide and glossary. | Pass | Login/template contract passes; screen-reader focus/error announcement remains a manual release follow-up. |

## Verification

Exact commands run independently:

```text
python3 crm/scripts/harness_check.py
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
[OK] harness metadata is valid
All checks passed!
168 files already formatted
0 files would be updated.
Success: no issues found in 81 source files
14 passed, 10 warnings in 2.08s
210 passed, 22 warnings in 5.93s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
```

The warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Findings

- Scope: implementation is limited to Spanish presentation, local responsive
  and keyboard defaults, public guidance/glossary, native form behavior, and
  focused tests/docs. No SPA, mobile application, offline sync, or remote
  asset dependency was added.
- Security and privacy: help content reinforces commercial-only data handling;
  existing permission and scoped-domain services remain unchanged.
- Usability: lead detail now uses explicit progressive disclosure for
  supplementary metadata; common actions remain visible first.
- Environment limitation: browser-level axe, screen-reader, keyboard-only,
  zoom, and phone-viewport evidence require a staging/browser pass and remain
  documented follow-ups, not hidden assumptions.
- No unresolved changes requested.
