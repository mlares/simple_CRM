# Implementation report — CRM-016

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the intentionally
  dirty completed-feature worktree recorded in `progress/current.md`.
- Requirement IDs: CRM-016-R01 through CRM-016-R06
- Acceptance-criterion IDs: CRM-016-AC01 through CRM-016-AC05
- Allowed scope: governance audit, privacy bundle, suppression, retention
  preview/approval/execution, migration, focused tests, docs, and this report.
- Dependencies and assumptions: CRM-005, CRM-006, CRM-007, CRM-010, CRM-011,
  and CRM-015 are done. Existing domain audits remain intact; this feature adds
  safe cross-feature governance evidence and workflows.
- Persisted assignment: `crm016_privacy_implementer_terra`, `gpt-5.6-terra`,
  high reasoning.
- Runtime note: this environment does not expose switchable model identities or
  a separate Terra process. The work followed the persisted assignment and the
  discrepancy is recorded rather than silently substituting an inherited
  assignment.

## Changed files and decisions

- `src/simple_crm/data_quality/models.py` and
  `src/simple_crm/data_quality/migrations/0003_privacy_governance.py`: added
  immutable governance audit, privacy case, retention category, legal hold,
  and retention decision records.
- `src/simple_crm/data_quality/privacy.py`: added global audit authorization,
  safe privacy bundles, case completion, durable contact suppression, preview-
  first retention with legal-hold exclusion, explicit approval/execution, and
  metadata-only governance audits.
- `tests/data_quality/test_privacy_governance.py`: added authorization,
  redaction, case audit, suppression durability, legal-hold, retention, and
  commercial-policy tests.
- `crm/docs/privacy.md` plus architecture/convention/verification docs:
  documented policy and non-destructive retention boundaries.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-016-AC01 | Immutable GovernanceAuditEvent with actor/action/target/correlation/reason/before/after/metadata and audit gate. | Immutability and reviewer authorization tests pass. | Pass |
| CRM-016-AC02 | PrivacyBundle joins party/contact/suppression, leads, activity, tasks, source links, and export metadata with note/payload redaction. | End-to-end bundle test finds related records and proves unrestricted note text is absent. | Pass |
| CRM-016-AC03 | Suppression delegates to durable ContactPoint suppression and no normal reactivation is allowed. | Suppression regression test passes; existing import/merge/report/export suites remain green. | Pass |
| CRM-016-AC04 | Retention category, preview, legal hold, approval, and non-destructive executed decision state. | Hold exclusion and explicit approval/execution test passes. | Pass |
| CRM-016-AC05 | Safe metadata-only governance audit and clinical-data guidance. | Full harness and redaction assertions pass; no payload/note logging is introduced. | Pass |

## Verification

Exact commands run:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format src/simple_crm/data_quality/models.py src/simple_crm/data_quality/privacy.py src/simple_crm/data_quality/migrations/0003_privacy_governance.py tests/data_quality/test_privacy_governance.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check src/simple_crm/data_quality tests/data_quality/test_privacy_governance.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src/simple_crm/data_quality
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py makemigrations --check --dry-run
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/data_quality/test_privacy_governance.py
timeout 60s ./crm/init.sh
```

Relevant output:

```text
All checks passed!
Success: no issues found in 10 source files
No changes detected
3 passed in 1.76s
196 passed, 19 warnings in 5.36s
[harness] ready
```

The warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Risks and follow-up

- Retention execution is deliberately non-destructive; future legal-approved
  deletion/archival workers must remain previewed, held-aware, and audited.
- PostgreSQL database-level audit permissions and production log sampling remain
  staging follow-ups; generic application immutability and redaction pass.
- CRM-016 is implemented but not yet approved or marked done; independent
  validator review is required.
