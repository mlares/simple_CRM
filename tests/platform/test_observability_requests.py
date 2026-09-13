from django.test import Client


def test_request_logs_use_route_names_and_do_not_echo_raw_paths(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level("INFO", logger="simple_crm.observability")
    Client().get("/health/live/", HTTP_X_REQUEST_ID="trace-safe-1")

    events = [
        record for record in caplog.records if record.name == "simple_crm.observability"
    ]
    assert events
    event = events[-1]
    assert event.observability_event == "web.request"
    assert event.observability_fields["route"] == "liveness"
    assert event.getMessage() == "web.request"
    assert "health/live" not in str(event.observability_fields)
