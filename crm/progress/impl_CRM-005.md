# Implementation report — CRM-005

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the pre-existing dirty completed-feature worktree recorded in `progress/current.md`.
- Requirement IDs: CRM-005-R01 through CRM-005-R06
- Acceptance-criterion IDs: CRM-005-AC01 through CRM-005-AC05
- Allowed scope: `simple_crm.identity`, identity settings and URLs, identity tests, identity documentation, and this report.
- Out-of-scope files: feature state, session/history state, validator report, CRM sales-domain apps and records, enterprise IdP provisioning, and shared accounts.
- Dependencies and assumptions: CRM-003 is complete; Django's built-in user remains the account boundary; future sales records will provide team/campaign/object fields to `scoped_queryset()`.
- Persisted assignment: `crm005_identity_implementer_terra`, `gpt-5.6-terra`, high reasoning.
- Runtime note: this execution environment does not expose a switchable model identity or launch a separate Terra process. The work followed the persisted Terra assignment and this discrepancy is recorded rather than silently substituting an inherited assignment.

## Changed files and decisions

- `src/simple_crm/identity/models.py`: added enabled identity profiles, six-role/action data, teams and memberships, explicit object/team/campaign grants, temporary elevations, and immutable elevation-use evidence.
- `src/simple_crm/identity/policy.py`: centralized deny-by-default action plus scope decisions, scoped query filtering, endpoint decorator, and elevation approval/use recording.
- `src/simple_crm/identity/oidc.py`: added provider discovery, authorization-code exchange, S256 PKCE, stable-subject linking, and generic provider failures.
- `src/simple_crm/identity/views.py`, `urls.py`, and `templates/identity/local_login.html`: added OIDC start/callback, explicitly gated local fallback, logout, and an authenticated identity endpoint.
- `src/simple_crm/identity/backends.py`, `middleware.py`, `apps.py`: reject disabled authentication and flush existing sessions after offboarding; create profiles for Django users.
- `src/simple_crm/identity/permissions.py`, `admin.py`: declared the role/action matrix and bounded administration surface.
- `src/simple_crm/identity/migrations/0001_initial.py`, `0002_seed_roles.py`: persisted the authorization schema and idempotently seeded the six role catalog plus action matrix.
- `src/simple_crm/config/settings/base.py`, `src/simple_crm/config/urls.py`: installed identity middleware/backend, Argon2-first hashing, OIDC environment inputs, explicit fallback flag, login URL, and auth routes.
- `tests/identity/` and `tests/config/test_identity_configuration.py`: covered role/action combinations, cross-owner object visibility, team/campaign scopes, negative view-only actions, offboarding, OIDC state/PKCE setup, local fallback gating, and elevation expiry/audit.
- `crm/docs/identity.md`, `crm/docs/architecture.md`, `crm/docs/conventions.md`, `crm/docs/verification.md`, `README.md`: documented authentication, offboarding, scope policy, fallback operation, and elevation controls.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-005-AC01 | `IdentityAuthenticationBackend`, `IdentitySessionMiddleware`, `IdentityProfile.disable()` and OIDC subject checks implement the documented next-request session flush policy. | `test_disabled_identity_cannot_authenticate_and_existing_session_is_flushed` | Pass |
| CRM-005-AC02 | `RolePermission`, `ScopeGrant`, `TeamMembership`, `can_access()`, and `scoped_queryset()` require both action and scope and distinguish global, team, campaign, and exact-object visibility. | `test_every_seeded_role_has_an_explicit_action_matrix`; `test_team_campaign_and_exact_object_scope_hide_cross_owner_records` | Pass |
| CRM-005-AC03 | Action values are independent; no view-only role receives bulk export, merge, import, reassignment, or catalog management. | `test_view_only_never_implies_sensitive_actions_or_catalog_management` | Pass |
| CRM-005-AC04 | `grant_temporary_elevation()` requires a distinct scoped approver and expiry; `ElevationUse` is append-only and records actor, reason, scope, approver, and timestamp. | `test_temporary_elevation_requires_approval_expires_and_audits_use`; `test_elevation_requires_distinct_approver_and_matching_scope` | Pass |
| CRM-005-AC05 | OIDC/local auth routes are explicit, local fallback is disabled by default, and future business callers have `require_access()`/`scoped_queryset()` as the single authorization boundary. | Authentication endpoint tests plus full Django integration suite | Pass |

## Verification

Exact final command:

```text
./crm/init.sh
```

Relevant output:

```text
[OK] harness metadata is valid
All checks passed!
93 files already formatted
Success: no issues found in 50 source files
145 passed, 10 warnings in 2.81s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
```

Additional feature checks:

```text
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run
No changes detected

.venv/bin/pytest -q tests/identity tests/config/test_identity_configuration.py
10 passed, 4 warnings
```

Warnings are the existing non-fatal WhiteNoise warning about the absent default
`staticfiles/` directory during test-client setup; no test or safety check
failed.

## Risks and follow-up

- The OIDC client deliberately has no provider network dependency in tests; a
  deployment still needs a provider configuration and a provider-specific
  security review before production enablement.
- Future domain models must pass their exact content type and team/campaign
  field names to the policy service; duplicating scope logic in a view is out
  of contract.
- CRM-005 is implemented but is not approved or marked done by this report;
  independent validator review is required.
