"""Correlation-aware structured observability without sensitive payloads."""

from __future__ import annotations

import contextvars
import hashlib
import json
import logging
import re
import threading
import time
import uuid
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from django.db import connection

_CORRELATION_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "simple_crm_correlation_id", default="-"
)
_TRACE_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "simple_crm_trace_id", default="-"
)
_CORRELATION_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_METRICS: Counter[str] = Counter()
_METRICS_LOCK = threading.Lock()
_SAFE_FIELDS = frozenset(
    {
        "component",
        "route",
        "method",
        "status",
        "duration_ms",
        "db_queries",
        "db_duration_ms",
        "job_type",
        "job_reference",
        "state",
        "outcome",
        "format",
        "row_count",
        "error_type",
        "attempts",
        "count",
        "backlog",
        "age_seconds",
        "metric",
        "value",
    }
)


def new_correlation_id() -> str:
    """Return an opaque identifier suitable for logs and response headers."""

    return uuid.uuid4().hex


def accepted_correlation_id(value: str | None) -> str:
    """Keep caller-supplied IDs bounded; do not echo arbitrary header content."""

    candidate = (value or "").strip()
    return (
        candidate if _CORRELATION_PATTERN.fullmatch(candidate) else new_correlation_id()
    )


@contextmanager
def correlation_context(correlation_id: str) -> Iterator[None]:
    correlation_token = _CORRELATION_ID.set(correlation_id)
    trace_token = _TRACE_ID.set(correlation_id)
    try:
        yield
    finally:
        _CORRELATION_ID.reset(correlation_token)
        _TRACE_ID.reset(trace_token)


def job_correlation_id(*, job_id: int, idempotency_key: str) -> str:
    """Return a bounded opaque correlation ID stable across a job's retries."""

    material = f"simple-crm-job-correlation:{job_id}:{idempotency_key}".encode()
    return hashlib.sha256(material).hexdigest()[:32]


def safe_job_reference(*, job_id: int, idempotency_key: str) -> str:
    """Return a short opaque reference without exposing job or payload identifiers."""

    material = f"simple-crm-job-reference:{job_id}:{idempotency_key}".encode()
    return hashlib.sha256(material).hexdigest()[:16]


def current_correlation_id() -> str:
    return _CORRELATION_ID.get()


def current_trace_id() -> str:
    return _TRACE_ID.get()


def record_metric(name: str, value: int = 1) -> None:
    """Increment a bounded metric name; labels never contain user data."""

    if not name or len(name) > 120 or not re.fullmatch(r"[a-z0-9_.-]+", name):
        return
    with _METRICS_LOCK:
        _METRICS[name] += value


def metrics_snapshot() -> dict[str, int]:
    with _METRICS_LOCK:
        return dict(sorted(_METRICS.items()))


def reset_metrics() -> None:
    with _METRICS_LOCK:
        _METRICS.clear()


def _safe_fields(fields: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in fields.items()
        if key in _SAFE_FIELDS and isinstance(value, (bool, float, int, str))
    }


def record_event(event: str, **fields: object) -> None:
    """Emit an allow-listed operational event without payloads or identities."""

    logging.getLogger("simple_crm.observability").info(
        event,
        extra={
            "observability_event": event,
            "observability_fields": _safe_fields(fields),
            "observability_correlation_id": current_correlation_id(),
            "observability_trace_id": current_trace_id(),
        },
    )


class JsonLogFormatter(logging.Formatter):
    """Serialize stable operational fields while excluding message payloads."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "observability_event", "log"),
            "message": getattr(record, "observability_event", "log"),
            "correlation_id": getattr(
                record, "observability_correlation_id", current_correlation_id()
            ),
            "trace_id": getattr(record, "observability_trace_id", current_trace_id()),
            "span_id": uuid.uuid4().hex[:16],
        }
        payload.update(_safe_fields(getattr(record, "observability_fields", {})))
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class QueryStats:
    """Count database calls and duration without recording SQL or parameters."""

    def __init__(self) -> None:
        self.count = 0
        self.duration_ms = 0.0

    def __call__(
        self,
        execute: Callable[..., Any],
        sql: str,
        params: Any,
        many: bool,
        context: Any,
    ) -> Any:
        started = time.perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            self.count += 1
            self.duration_ms += (time.perf_counter() - started) * 1000
            record_metric("database.queries.total")


def _route_name(request: Any) -> str:
    match = getattr(request, "resolver_match", None)
    return str(getattr(match, "url_name", None) or "unresolved")


class ObservabilityMiddleware:
    """Add a safe request ID, request metrics, DB timings, and JSON events."""

    def __init__(self, get_response: Callable[[Any], Any]) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        correlation_id = accepted_correlation_id(request.headers.get("X-Request-ID"))
        started = time.perf_counter()
        query_stats = QueryStats()
        response = None
        status = 500
        with correlation_context(correlation_id):
            try:
                with connection.execute_wrapper(query_stats):
                    response = self.get_response(request)
                status = response.status_code
                return response
            except Exception as error:
                record_event(
                    "web.request",
                    component="web",
                    route=_route_name(request),
                    method=request.method,
                    status=status,
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                    db_queries=query_stats.count,
                    db_duration_ms=round(query_stats.duration_ms, 2),
                    error_type=type(error).__name__,
                )
                raise
            finally:
                record_metric("http.requests.total")
                if response is not None:
                    response["X-Request-ID"] = correlation_id
                    record_event(
                        "web.request",
                        component="web",
                        route=_route_name(request),
                        method=request.method,
                        status=status,
                        duration_ms=round((time.perf_counter() - started) * 1000, 2),
                        db_queries=query_stats.count,
                        db_duration_ms=round(query_stats.duration_ms, 2),
                    )
