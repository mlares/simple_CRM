# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2 AS builder

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /build

RUN python -m venv "$VIRTUAL_ENV" \
    && pip install --no-cache-dir --disable-pip-version-check uv==0.12.1

COPY pyproject.toml uv.lock README.md ./
RUN uv export --locked --no-dev --no-emit-project --format requirements-txt \
    > requirements.txt \
    && pip install --no-cache-dir --requirement requirements.txt

COPY src ./src
COPY manage.py ./manage.py
RUN pip install --no-cache-dir --no-deps .
RUN DJANGO_SETTINGS_MODULE=simple_crm.config.settings.base \
    DJANGO_STATIC_ROOT=/build/staticfiles \
    python manage.py collectstatic --noinput --clear

FROM python:3.12-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2 AS runtime

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_STATIC_ROOT=/app/staticfiles \
    XDG_RUNTIME_DIR=/tmp/simplecrm-runtime \
    HOME=/tmp/simplecrm-runtime \
    DJANGO_SETTINGS_MODULE=simple_crm.config.settings.production

RUN groupadd --system --gid 10001 simplecrm \
    && useradd --system --uid 10001 --gid 10001 --home-dir /tmp/simplecrm-runtime --no-create-home simplecrm \
    && install --directory --owner=10001 --group=10001 --mode=0700 /tmp/simplecrm-runtime

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=10001:10001 src ./src
COPY --from=builder --chown=10001:10001 /build/staticfiles ./staticfiles
COPY --chown=10001:10001 manage.py README.md pyproject.toml ./
COPY --chown=10001:10001 docker ./docker

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8000), timeout=3).close()"

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["web"]
