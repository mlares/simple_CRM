# Security threat model and verification checklist

CRM-019 follows the selected OWASP ASVS 5.0 Level 2 target for a business
application containing personal and commercial data. The primary threats are
unauthorized cross-scope reads, privilege escalation, CSRF and session theft,
unsafe redirects, upload/parser abuse, spreadsheet formula injection, secret
disclosure, dependency compromise, and database-role overreach.

## Controls

- Django CSRF middleware, secure HttpOnly SameSite cookies, HTTPS redirect,
  HSTS, clickjacking denial, content-type sniffing protection, same-origin
  referrer/COOP/CORP policy, and a self-hosted CSP are deployment defaults.
- ORM query construction, template escaping, centralized identity scopes,
  bounded search/segment/report/export/import services, formula neutralization,
  safe upload labels, and validated login redirects are the application
  boundaries. UI hiding is never an authorization control.
- Request bodies are capped at 10 MiB and cache-backed limits cover local login
  and expensive read routes. Production must use a shared cache for consistent
  limits across web processes.
- Secrets are environment/deployment-secret inputs only. The repository scan
  rejects private-key, token-like, and accidental environment-file material;
  errors return generic messages without database URLs or exception payloads.

## Database roles and RLS acceptance boundary

Production should provision separate roles: `crm_migrator` for migrations,
`crm_web` for ordinary application DML without DDL, `crm_worker` for outbox
and delivery tables plus only the required referenced business rows, and
`crm_reporting` for governed read-only views. Backup credentials remain
outside the application role set. No role password or connection string is
stored in this repository.

Selective PostgreSQL row-level security should be enabled for lead-scoped
reporting tables only after the deployment sets a transaction-local identity
scope; the application policy remains authoritative until that context is
proven in staging. The dedicated PostgreSQL acceptance run must prove direct
SQL privileges, cross-scope denial, and that `crm_web` cannot create roles,
alter tables, or read migration secrets. SQLite cannot prove these controls.

## Release checklist

1. Run `bash scripts/verify-security.sh` and retain the dependency/static
   output, including any approved exception with owner and expiry.
2. Run `manage.py check --deploy --fail-level WARNING` with production-like
   settings and inspect HTTPS, cookie, HSTS, framing, referrer, and CSP headers
   through the ingress/proxy.
3. Run the dedicated PostgreSQL role/RLS acceptance procedure against a fresh
   disposable database; never test privileges against production data.
4. Rotate deployment secrets through the secret facility, verify logs contain
   only safe identifiers, and invalidate the previous credentials.
5. Exercise CSRF, authorization, redirect, upload, formula, and generic-error
   regression tests before release.
