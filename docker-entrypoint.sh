#!/bin/bash
set -e

echo "Waiting for Postgres at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
python - <<'PY'
import os
import socket
import time

host = os.getenv("POSTGRES_HOST", "db")
port = int(os.getenv("POSTGRES_PORT", "5432"))
deadline = time.time() + 60
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit(f"Postgres not reachable at {host}:{port}")
print("Postgres is up.")
PY

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

exec "$@"
