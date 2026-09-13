# Identity and authorization contract

CRM-005 keeps Django's built-in user as the local account boundary and adds a
CRM identity profile. A profile is enabled only while its user is active and
`disabled_at` is empty. Offboarding sets both markers, the authentication
backend rejects new sessions, and `IdentitySessionMiddleware` flushes an
existing session on its next request. OIDC callbacks for the disabled subject
are rejected.

## Authentication

OIDC is the normal path. `/auth/oidc/start/` creates a state, nonce, and
S256 PKCE verifier in the session, discovers the provider endpoints, and starts
the authorization-code flow. `/auth/oidc/callback/` validates state, exchanges
the code, and links the stable provider `sub` to a local identity. Provider
MFA remains the provider's responsibility. Configure `OIDC_ISSUER_URL`,
`OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, and `OIDC_REDIRECT_URI` through the
environment; no token or client secret is stored in the repository.

The local password form is a temporary outage fallback, not a parallel login
path. It is available only when `DJANGO_LOCAL_AUTH_FALLBACK_ENABLED=true` is
explicitly set, and the shared password-hasher order puts Argon2 first. It
must be disabled again when OIDC is restored. Shared accounts are prohibited.

## Roles and actions

The migration seeds exactly six role codes: `sales_representative`,
`sales_manager`, `data_steward`, `report_viewer`,
`privacy_audit_reviewer`, and `system_administrator`. The policy service uses
the separate action codes `view`, `create`, `change`, `reassign`, `merge`,
`import`, `resolve_quality`, `audit_view`, `bulk_export`, `manage_catalog`, and
`elevate_access`; view never implies another action.

Every allow decision requires an enabled identity, an action permission, and
an active scope. Scopes are global, team, campaign, or exact object. Team
membership grants team visibility; campaign and object grants are explicit.
Callers use `scoped_queryset()` for lists, search, reports, and exports and
`can_access()`/`require_access()` for detail and direct-object endpoints.
Unauthorized callers receive an empty queryset or `PermissionDenied`; callers
must not reproduce these rules in templates or views.

## Temporary elevation

An approver with `elevate_access` and the requested scope can grant one action
to another enabled identity until a bounded expiry. A non-empty reason,
distinct approver, scope, and approval are required. Each successful use
creates an immutable `ElevationUse` record containing actor, reason, scope,
approver, and timestamp. Expired or revoked elevations never authorize.
