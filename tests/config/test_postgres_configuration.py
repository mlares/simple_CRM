import pytest
from django.core.exceptions import ImproperlyConfigured

from simple_crm.config.environment import (
    postgres_database_config,
    postgres_database_url,
)

POSTGRES_URL = "postgresql://crm:secret@localhost:5432/simple_crm_crm003_test"


def test_postgres_configuration_is_bounded_and_transaction_safe() -> None:
    configuration = postgres_database_config({"DATABASE_URL": POSTGRES_URL})

    assert configuration["ENGINE"] == "django.db.backends.postgresql"
    assert configuration["CONN_MAX_AGE"] == 60
    assert configuration["CONN_HEALTH_CHECKS"] is True
    assert configuration["ATOMIC_REQUESTS"] is True


@pytest.mark.parametrize(
    "database_url",
    [
        "",
        "sqlite:///tmp/test.sqlite3",
        "not-a-database-url",
        "postgresql://crm:secret@localhost:not-a-port/crm",
        "postgresql:///crm",
    ],
)
def test_postgres_url_rejects_missing_or_malformed_values_without_disclosure(
    database_url: str,
) -> None:
    with pytest.raises(ImproperlyConfigured) as error:
        postgres_database_url({"DATABASE_URL": database_url})

    if database_url:
        assert database_url not in str(error.value)
