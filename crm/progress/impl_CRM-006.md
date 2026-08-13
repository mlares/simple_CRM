# Implementation report — CRM-006

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the pre-existing dirty completed-feature worktree recorded in `progress/current.md`.
- Requirement IDs: CRM-006-R01 through CRM-006-R06
- Acceptance-criterion IDs: CRM-006-AC01 through CRM-006-AC05
- Allowed scope: CRM party models, deterministic normalization/services, admin registration, migration, documentation, tests, and this report.
- Out-of-scope files: feature/session/history state, validator report, identity/activity/data-quality/reporting/platform apps, lead/interaction/import/merge records, clinical identities, and workbook cutover.
- Dependencies and assumptions: CRM-004 and CRM-005 are done; `simple_crm.crm` remains the durable owner of party master data; future leads reference these parties rather than duplicating them.
- Persisted assignment: `crm006_party_implementer_terra`, `gpt-5.6-terra`, high reasoning.
- Runtime note: this execution environment does not expose a switchable model identity or launch a separate Terra process. The work followed the persisted Terra assignment and the discrepancy is recorded rather than silently substituting an inherited assignment.

## Changed files and decisions

- `src/simple_crm/crm/models.py`: added `Party`, `Person`, `Organization`, effective-dated `OrganizationPerson`, `PartySpecialty`, `ContactPoint`, `PartyContactPoint`, `Address`, and `PartyAlias`; added subtype XOR, date, uniqueness, suppression, foreign-key, archive, and version safeguards.
- `src/simple_crm/crm/normalization.py`: added lossless comparison normalization for email, Argentinian phone/WhatsApp E.164 values, websites, social values, and names.
- `src/simple_crm/crm/services.py`: added transactional person/organization creation, exact contact and plausible-name warning previews, and a no-automatic-merge boundary.
- `src/simple_crm/crm/migrations/0004_party_domain.py`: added the reviewed schema migration for the party domain.
- `src/simple_crm/crm/admin.py`: exposed bounded party, contact, relationship, specialty, address, and alias administration.
- `tests/crm/test_party_models.py`: added eight focused tests covering constraints, relationships, normalization, suppression, concurrency/archive, warnings, shared institutional contact points, and geography.
- `crm/docs/parties.md`, `crm/docs/architecture.md`, `crm/docs/conventions.md`, `crm/docs/verification.md`, `README.md`: documented party ownership, normalization, provenance, suppression, archival, concurrency, and duplicate-warning contracts.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-006-AC01 | `crm_party_exactly_one_subtype`, foreign keys, effective-date/distinct relationship constraints, and relationship `full_clean()` validation. | `test_party_constraint_requires_exactly_one_subtype`; `test_relationships_validate_party_types_and_effective_dates`; migration drift check. | Pass |
| CRM-006-AC02 | `normalize_contact_value()` preserves raw values and writes deterministic normalized values plus `VALID`, `INVALID`, or `AMBIGUOUS` state. | `test_contact_normalization_preserves_raw_value_and_quality_state`. | Pass |
| CRM-006-AC03 | Suppression is monotonic through the model save path; outreach selection filters active, valid, unsuppressed values; provenance and links remain retained. | `test_suppression_survives_edits_and_removes_outreach_selection`; full suite. | Pass |
| CRM-006-AC04 | Party `version` increments on save and stale instances raise `PartyConcurrencyError`; archive uses the same boundary. | `test_archiving_preserves_relationships_and_stale_edits_are_rejected`. | Pass |
| CRM-006-AC05 | Transactional creation invokes `preview_party_creation()` and returns exact-contact/plausible-name warnings without merging; archived parties leave active querysets. | `test_creation_preview_warns_on_exact_contact_and_plausible_name_without_merging`; lifecycle test. | Pass |

## Verification

Exact final application verification:

```text
./crm/init.sh
```

Relevant output:

```text
[OK] harness metadata is valid
All checks passed!
99 files already formatted
Success: no issues found in 53 source files
153 passed, 10 warnings in 3.76s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
```

Additional checks:

```text
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run
No changes detected

.venv/bin/pytest -q tests/crm/test_party_models.py
8 passed
```

The disposable PostgreSQL 18 attempt was blocked by sandbox Docker socket
permissions after launch and was stopped with elevated permission. No shared or
application database was touched. The generic suite exercises the same schema
constraints on SQLite; PostgreSQL-specific runtime evidence remains a staging
verification step.

Warnings are the existing non-fatal WhiteNoise warning about the absent default
`staticfiles/` directory during test-client setup.

## Risks and follow-up

- Future import and merge workflows must use the contact suppression and party
  services rather than bulk updates that bypass model invariants.
- A dedicated PostgreSQL acceptance test for the new party constraints should
  be run when Docker/PostgreSQL access is available.
- CRM-006 is implemented but is not approved or marked done by this report;
  independent validator review is required.
