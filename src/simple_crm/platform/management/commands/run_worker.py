"""Run the bounded transactional outbox worker process."""

from __future__ import annotations

import time

from django.core.management.base import BaseCommand, CommandError

from simple_crm.config.observability import record_event
from simple_crm.platform.jobs import run_worker_once


class Command(BaseCommand):
    help = "Ejecuta el trabajador acotado de notificaciones y recordatorios."

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--interval", type=int, default=15)
        parser.add_argument("--limit", type=int, default=25)

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        interval = options["interval"]
        limit = options["limit"]
        if interval <= 0 or limit <= 0:
            raise CommandError("interval y limit deben ser positivos")
        record_event("worker.start", component="worker")
        while True:
            run_worker_once(limit=limit)
            if options["once"]:
                return
            time.sleep(interval)
