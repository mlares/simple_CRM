#!/usr/bin/env sh
set -eu

case "${1:-web}" in
  web)
    exec gunicorn simple_crm.config.wsgi:application \
      --bind "0.0.0.0:${PORT:-8000}" \
      --workers "${WEB_CONCURRENCY:-2}" \
      --worker-tmp-dir "${XDG_RUNTIME_DIR:?XDG_RUNTIME_DIR must be set}" \
      --access-logfile - \
      --error-logfile - \
      --capture-output
    ;;
  worker)
    shift
    exec python manage.py run_worker "$@"
    ;;
  *)
    echo "Uso: docker/entrypoint.sh {web|worker}" >&2
    exit 64
    ;;
esac
