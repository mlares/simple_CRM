#!/usr/bin/env bash
# Prove CRM-019 database roles and lead-scope RLS on a disposable PostgreSQL 18 DB.
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

: "${DATABASE_URL:?DATABASE_URL must target the dedicated CRM-019 security database}"
: "${SIMPLE_CRM_POSTGRES_SECURITY_ACCEPTANCE:?Set SIMPLE_CRM_POSTGRES_SECURITY_ACCEPTANCE=1 to opt in}"
if [ "$SIMPLE_CRM_POSTGRES_SECURITY_ACCEPTANCE" != "1" ]; then
  echo "SIMPLE_CRM_POSTGRES_SECURITY_ACCEPTANCE must equal 1" >&2
  exit 2
fi

for variable in CRM019_MIGRATOR_PASSWORD CRM019_WEB_PASSWORD CRM019_WORKER_PASSWORD CRM019_REPORTING_PASSWORD; do
  if [ -z "${!variable:-}" ]; then
    echo "$variable must be supplied by the disposable-database secret facility" >&2
    exit 2
  fi
done

export DJANGO_SETTINGS_MODULE=simple_crm.config.settings.integration
export PYTHONDONTWRITEBYTECODE=1
python_bin="${PYTHON_BIN:-.venv/bin/python}"
if [ ! -x "$python_bin" ]; then
  echo "Python environment is unavailable; run uv sync --locked first" >&2
  exit 2
fi

"$python_bin" - <<'PY'
import os
from io import StringIO

import django
import psycopg
from django.core.management import call_command
from django.db import connection
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.errors import InsufficientPrivilege
from psycopg.types.json import Jsonb

django.setup()

if connection.vendor != "postgresql":
    raise SystemExit("Dedicated PostgreSQL 18 database is required")
if connection.settings_dict["NAME"] != "simple_crm_crm019_security_test":
    raise SystemExit("DATABASE_URL must target simple_crm_crm019_security_test")

with connection.cursor() as cursor:
    cursor.execute("SHOW server_version_num")
    version_number = int(cursor.fetchone()[0])
    if not 180000 <= version_number < 190000:
        raise SystemExit("PostgreSQL 18 is required")

migrate_output = StringIO()
call_command("migrate", interactive=False, verbosity=0, stdout=migrate_output)

from simple_crm.crm.models import Campaign, Lead, LeadStatus  # noqa: E402
from simple_crm.platform.models import OutboxJob  # noqa: E402

admin_dsn = os.environ["DATABASE_URL"]
prefix = os.environ.get("CRM019_ROLE_PREFIX", "crm019_acceptance_")
if not prefix.startswith("crm019_acceptance_"):
    raise SystemExit("CRM019_ROLE_PREFIX must use the crm019_acceptance_ prefix")

roles = {
    "migrator": prefix + "migrator",
    "web": prefix + "web",
    "worker": prefix + "worker",
    "reporting": prefix + "reporting",
}
passwords = {
    "migrator": os.environ["CRM019_MIGRATOR_PASSWORD"],
    "web": os.environ["CRM019_WEB_PASSWORD"],
    "worker": os.environ["CRM019_WORKER_PASSWORD"],
    "reporting": os.environ["CRM019_REPORTING_PASSWORD"],
}
if any(len(name) > 63 for name in roles.values()):
    raise SystemExit("CRM019 role names must fit PostgreSQL's identifier limit")

lead_table = Lead._meta.db_table
outbox_table = OutboxJob._meta.db_table
view_name = "crm019_governed_lead_report"
policy_name = "crm019_campaign_scope_policy"
test_campaign_codes = ("CRM019-SEC-A", "CRM019-SEC-B")
created_role_names: list[str] = []
campaigns: list[Campaign] = []
leads: list[Lead] = []


def ident(name: str) -> sql.Identifier:
    return sql.Identifier(name)


def role_dsn(role: str, password: str) -> str:
    values = conninfo_to_dict(admin_dsn)
    values["user"] = roles[role]
    values["password"] = password
    return make_conninfo(**values)


def privilege(role: str, table: str, privilege_name: str) -> bool:
    with psycopg.connect(admin_dsn) as admin:
        return bool(
            admin.execute(
                "SELECT has_table_privilege(%s, %s, %s)",
                (role, table, privilege_name),
            ).fetchone()[0]
        )


def schema_privilege(role: str, privilege_name: str) -> bool:
    with psycopg.connect(admin_dsn) as admin:
        return bool(
            admin.execute(
                "SELECT has_schema_privilege(%s, 'public', %s)",
                (role, privilege_name),
            ).fetchone()[0]
        )


def expect_denied(role: str, statement: sql.Composed | sql.SQL, message: str) -> None:
    try:
        with psycopg.connect(
            role_dsn(role, passwords[role]), autocommit=True
        ) as role_connection:
            role_connection.execute(statement)
    except InsufficientPrivilege:
        return
    raise SystemExit(message)


try:
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        database_name = connection.settings_dict["NAME"]
        for role_key, role in roles.items():
            exists = admin.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)
            ).fetchone()
            if exists:
                raise SystemExit("CRM-019 acceptance roles must not pre-exist")
            admin.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}"
                ).format(ident(role), sql.Literal(passwords[role_key]))
            )
            created_role_names.append(role)

        for role in roles.values():
            admin.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    ident(database_name), ident(role)
                )
            )
            admin.execute(
                sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(ident(role))
            )

        admin.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")

        admin.execute(
            sql.SQL("GRANT CREATE ON SCHEMA public TO {}").format(
                ident(roles["migrator"])
            )
        )
        admin.execute(
            sql.SQL("GRANT SELECT, INSERT, UPDATE ON {} TO {}").format(
                ident(lead_table), ident(roles["web"])
            )
        )
        sequence_name = admin.execute(
            "SELECT pg_get_serial_sequence(%s, 'id')", (lead_table,)
        ).fetchone()[0]
        if not sequence_name:
            raise SystemExit("Lead primary-key sequence was not found")
        sequence_schema, sequence_identifier = sequence_name.split(".", 1)
        admin.execute(
            sql.SQL("GRANT USAGE, SELECT ON SEQUENCE {}.{} TO {}").format(
                ident(sequence_schema), ident(sequence_identifier), ident(roles["web"])
            )
        )
        admin.execute(
            sql.SQL("GRANT SELECT, UPDATE ON {} TO {}").format(
                ident(outbox_table), ident(roles["worker"])
            )
        )
        admin.execute(
            sql.SQL(
                "CREATE VIEW {} AS "
                "SELECT lead_number, campaign_id, lifecycle, data_readiness "
                "FROM {} WHERE campaign_id::text = "
                "current_setting('simple_crm.campaign_id', true)"
            ).format(ident(view_name), ident(lead_table))
        )
        admin.execute(
            sql.SQL("GRANT SELECT ON {} TO {}").format(
                ident(view_name), ident(roles["reporting"])
            )
        )
    if Campaign.objects.filter(code__in=test_campaign_codes).exists():
        raise SystemExit("CRM-019 acceptance campaign codes must not pre-exist")
    campaigns = [
        Campaign.objects.create(code=code, label=code, is_active=True)
        for code in test_campaign_codes
    ]
    stage = LeadStatus.objects.filter(is_active=True).first()
    if stage is None:
        raise SystemExit("Seeded lead status is required for the RLS acceptance")
    leads = [
        Lead.objects.create(
            lead_number=f"{code}-LEAD",
            campaign=campaign,
            current_stage=stage,
            source_attribution={"acceptance": "CRM-019"},
        )
        for code, campaign in zip(test_campaign_codes, campaigns, strict=True)
    ]

    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(
            sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY").format(
                ident(lead_table)
            )
        )
        admin.execute(
            sql.SQL("ALTER TABLE {} FORCE ROW LEVEL SECURITY").format(
                ident(lead_table)
            )
        )
        admin.execute(
            sql.SQL(
                "CREATE POLICY {} ON {} USING (campaign_id::text = "
                "current_setting('simple_crm.campaign_id', true)) WITH CHECK "
                "(campaign_id::text = current_setting('simple_crm.campaign_id', true))"
            ).format(ident(policy_name), ident(lead_table))
        )

    if not schema_privilege(roles["migrator"], "CREATE"):
        raise SystemExit("Migrator role lacks documented schema CREATE privilege")
    if schema_privilege(roles["web"], "CREATE"):
        raise SystemExit("Web role has unexpected schema CREATE privilege")
    if privilege(roles["web"], "django_migrations", "SELECT"):
        raise SystemExit("Web role can read migration metadata")
    if not privilege(roles["web"], lead_table, "SELECT"):
        raise SystemExit("Web role lacks lead SELECT privilege")
    if not privilege(roles["reporting"], view_name, "SELECT"):
        raise SystemExit("Reporting role lacks governed-view SELECT privilege")
    if privilege(roles["reporting"], lead_table, "SELECT"):
        raise SystemExit("Reporting role can bypass the governed view")
    if not privilege(roles["worker"], outbox_table, "UPDATE"):
        raise SystemExit("Worker role lacks outbox UPDATE privilege")

    with psycopg.connect(role_dsn("migrator", passwords["migrator"]), autocommit=True) as migrator:
        migrator.execute("CREATE TABLE crm019_migrator_probe (id integer)")
        migrator.execute("DROP TABLE crm019_migrator_probe")

    expect_denied(
        "web",
        sql.SQL("CREATE TABLE crm019_forbidden_table (id integer)"),
        "Web role can create tables",
    )
    expect_denied(
        "web",
        sql.SQL("ALTER TABLE {} ADD COLUMN forbidden integer").format(
            ident(lead_table)
        ),
        "Web role can alter application tables",
    )
    expect_denied(
        "web",
        sql.SQL("CREATE ROLE crm019_forbidden_role"),
        "Web role can create database roles",
    )

    with psycopg.connect(role_dsn("web", passwords["web"])) as web:
        with web.transaction():
            web.execute(
                "SELECT set_config('simple_crm.campaign_id', %s, true)",
                (str(campaigns[0].pk),),
            )
            visible = web.execute(
                sql.SQL("SELECT count(*) FROM {}").format(ident(lead_table))
            ).fetchone()[0]
            cross_scope_update = web.execute(
                sql.SQL("UPDATE {} SET source_attribution = %s WHERE id = %s").format(
                    ident(lead_table)
                ),
                (Jsonb({"attempt": "cross-scope"}), leads[1].pk),
            ).rowcount
    if visible != 1 or cross_scope_update != 0:
        raise SystemExit("Lead RLS did not deny the cross-scope read/write")

    with psycopg.connect(role_dsn("reporting", passwords["reporting"])) as reporting:
        with reporting.transaction():
            reporting.execute(
                "SELECT set_config('simple_crm.campaign_id', %s, true)",
                (str(campaigns[0].pk),),
            )
            governed_rows = reporting.execute(
                sql.SQL("SELECT count(*) FROM {} ").format(ident(view_name))
            ).fetchone()[0]
    if governed_rows != 1:
        raise SystemExit("Reporting role cannot read the governed scoped view")

    print("PostgreSQL security acceptance passed: role grants and lead RLS")
finally:
    cleanup_errors: list[str] = []
    try:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(
                sql.SQL("DROP VIEW IF EXISTS {} CASCADE").format(ident(view_name))
            )
            admin.execute(
                sql.SQL("DROP POLICY IF EXISTS {} ON {}").format(
                    ident(policy_name), ident(lead_table)
                )
            )
            admin.execute(
                sql.SQL("ALTER TABLE {} DISABLE ROW LEVEL SECURITY").format(
                    ident(lead_table)
                )
            )
            # Catalog rows and their audit history are immutable by design.
            # This database is disposable; retain those rows and discard the
            # database after acceptance instead of bypassing the guard trigger.
            for role in created_role_names:
                admin.execute(sql.SQL("DROP OWNED BY {} CASCADE").format(ident(role)))
                admin.execute(sql.SQL("DROP ROLE {}").format(ident(role)))
    except Exception as error:  # pragma: no cover - cleanup diagnostics
        print(f"CRM-019 acceptance cleanup error: {type(error).__name__}: {error}")
        cleanup_errors.append(type(error).__name__)
    if cleanup_errors:
        raise SystemExit("CRM-019 acceptance cleanup failed")
PY
