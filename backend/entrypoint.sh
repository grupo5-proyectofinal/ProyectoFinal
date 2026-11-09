#!/bin/sh
# Espera a que la base de datos esté disponible antes de migrar y levantar el
# servidor. Evita el fallo de arranque cuando el DNS de `db` todavía no resolvió
# (docker/podman compose) o cuando la base de Render tarda en aceptar conexiones.
#
# La espera usa la configuración real de Django, así funciona igual con
# POSTGRES_HOST/POSTGRES_PORT (compose) que con DATABASE_URL (Render).
# Se puede ajustar el máximo con DB_WAIT_SEGUNDOS (por defecto 90).
set -eu

LIMITE="${DB_WAIT_SEGUNDOS:-90}"

echo "Esperando a la base de datos (máximo ${LIMITE}s)…"
if ! DB_WAIT_SEGUNDOS="$LIMITE" python - <<'PY'
import os
import sys
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connections
from django.db.utils import OperationalError

limite = int(os.environ.get("DB_WAIT_SEGUNDOS", "90"))
inicio = time.monotonic()
ultimo_error = None
while time.monotonic() - inicio < limite:
    try:
        connections["default"].ensure_connection()
        sys.exit(0)
    except OperationalError as exc:
        ultimo_error = exc
        time.sleep(1)

print(f"ERROR: no se pudo conectar a la base tras {limite}s: {ultimo_error}", file=sys.stderr)
sys.exit(1)
PY
then
	echo "ERROR: la base de datos no respondió. Revisá POSTGRES_HOST/DATABASE_URL." >&2
	exit 1
fi

python manage.py migrate --noinput
exec python manage.py runserver 0.0.0.0:8000
