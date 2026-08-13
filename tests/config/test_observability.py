import json
import logging

from django.test import Client, override_settings

from simple_crm.config.observability import (
    JsonLogFormatter,
    accepted_correlation_id,
    correlation_context,
    job_correlation_id,
    record_event,
    reset_metrics,
    safe_job_reference,
)


def test_correlation_ids_are_bounded_and_untrusted_values_are_replaced() -> None:
    assert accepted_correlation_id("sales-request-42") == "sales-request-42"
    generated = accepted_correlation_id("../../secret?token=1")
    assert generated != "../../secret?token=1"
    assert len(generated) == 32


def test_json_formatter_contains_only_safe_correlation_fields() -> None:
    record = logging.LogRecord(
        "simple_crm.observability",
        logging.INFO,
        __file__,
        1,
        "operation completed",
        (),
        None,
    )
    record.observability_event = "domain.lead.create"
    record.observability_fields = {
        "component": "domain",
        "status": 201,
        "secret": "must-not-appear",
    }

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["event"] == "domain.lead.create"
    assert payload["status"] == 201
    assert "secret" not in payload
    assert "must-not-appear" not in json.dumps(payload)


def test_job_correlation_and_reference_are_bounded_opaque_values() -> None:
    correlation_id = job_correlation_id(job_id=42, idempotency_key="reminder:task:7")
    reference = safe_job_reference(job_id=42, idempotency_key="reminder:task:7")

    assert correlation_id == job_correlation_id(
        job_id=42, idempotency_key="reminder:task:7"
    )
    assert len(correlation_id) == 32
    assert len(reference) == 16
    assert "42" not in correlation_id
    assert "reminder" not in reference


def test_json_formatter_snapshots_job_correlation_and_safe_reference(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level("INFO", logger="simple_crm.observability")
    with correlation_context("job-correlation-7"):
        record_event(
            "jobs.failed",
            component="worker",
            job_reference="a1b2c3d4e5f60708",
            secret="must-not-appear",
        )

    payload = json.loads(JsonLogFormatter().format(caplog.records[-1]))
    assert payload["correlation_id"] == "job-correlation-7"
    assert payload["job_reference"] == "a1b2c3d4e5f60708"
    assert "secret" not in payload


def test_request_correlation_metrics_and_protected_metrics_endpoint() -> None:
    reset_metrics()
    client = Client()
    response = client.get("/", HTTP_X_REQUEST_ID="seller-request-7")

    assert response.status_code == 200
    assert response["X-Request-ID"] == "seller-request-7"
    assert client.get("/health/metrics/").status_code == 404

    with override_settings(OBSERVABILITY_METRICS_TOKEN="metrics-token"):
        metrics_response = client.get(
            "/health/metrics/", HTTP_X_METRICS_TOKEN="metrics-token"
        )

    assert metrics_response.status_code == 200
    assert metrics_response.json()["metrics"]["http.requests.total"] >= 1
    reset_metrics()
