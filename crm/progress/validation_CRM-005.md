# Validation report — CRM-005

## Verdict

`APPROVED`

## Independence and scope

- Validator: `crm005_identity_validator_sol`
- Persisted validator assignment: `gpt-5.6-sol`, high reasoning; implementer assignment was the distinct `crm005_identity_implementer_terra` / `gpt-5.6-terra`.
- Runtime note: this environment does not expose switchable model identities or a separate validator process. The independent validator pass was executed as a separate review phase with no implementation-file edits; the discrepancy is recorded rather than silently substituted.
- Implementer: `crm005_identity_implementer_terra`
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188` plus the dirty worktree baseline recorded in the task envelope.
- Allowed validator write target: `progress/validation_CRM-005.md`

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-005-AC01 | Identity backend, profile disablement, session middleware, OIDC subject check, and disabled-session test. | Pass | New login is rejected and the next request flushes an existing session as documented. |
| CRM-005-AC02 | Seeded six-role/action matrix, `can_access()`, `scoped_queryset()`, exact object grants, team memberships, and campaign grants; matrix and cross-owner tests. | Pass | Action permission and scope are both required; cross-owner exact IDs are hidden. |
| CRM-005-AC03 | Independent review of action constants/role seed and negative report-viewer test. | Pass | View does not imply export, merge, import, reassignment, or catalog management. |
| CRM-005-AC04 | Elevation approval service, bounded model constraints, immutable `ElevationUse`, expiry test, and distinct-approver test. | Pass | Every successful elevated decision records actor, reason, scope, approver, and timestamp; expired and disabled targets do not authorize. |
| CRM-005-AC05 | Auth URL configuration, gated local-login view, `login_required` identity endpoint, centralized endpoint decorator/query service, and endpoint tests. | Pass | Unauthorized access is denied; callback redirect validation rejects unsafe destinations; no sales-domain endpoint was added. |

## Verification

Exact commands run:

```text
./crm/init.sh
git diff --check
```

Relevant output:

```text
[OK] harness metadata is valid
All checks passed!
94 files already formatted
Success: no issues found in 50 source files
145 passed, 10 warnings in 2.81s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
```

The feature-specific suite had previously passed 10 tests. The ten warnings
are the known non-fatal WhiteNoise warning for the absent default `staticfiles/`
directory during test-client setup; they do not expose diagnostics or alter
the result.

## Findings

- Scope: implementation stayed within the CRM-005 task envelope; no sales
  records or unrelated feature files were added.
- Security: authorization is deny-by-default and centralized; local fallback is
  disabled by default; Argon2 is first in the deployment hashers; provider
  secrets are environment-only; public failures are generic; offboarding and
  safe redirects are covered.
- Architecture: the identity app owns identity policy and does not duplicate
  CRM catalog or future sales-domain models. Future callers must provide their
  team/campaign fields to `scoped_queryset()`.
- Regression: full harness and migration-drift checks pass.
- Manual/environment limitation: no real OIDC provider or MFA service was
  contacted; provider integration remains a deployment configuration and
  staging verification step.
- No unresolved changes requested.
