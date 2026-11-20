#!/bin/sh
# Arranque del contenedor de producción (Dockerfile de la raíz, Render).
#
# Con POBLAR_DEMO=true carga los datos de la demo (`poblar_demo`) en segundo plano,
# para que el servicio levante el puerto enseguida aunque la carga tarde unos
# minutos en el plan free. El comando es idempotente: en cada reinicio ve que la
# demo ya está y no hace nada.
set -eu

python manage.py migrate --noinput
python manage.py check --deploy --fail-level ERROR || echo 'AVISO: revisá los errores de arriba'

# Con POBLAR_DEMO=true carga la demo y, después, sus fotos reales. Sin la variable
# igual pone las fotos en una demo ya cargada (idempotente: si no hay demo o ya las
# tiene, no hace nada).
if [ "${POBLAR_DEMO:-false}" = "true" ]; then
	(python manage.py poblar_demo || echo 'AVISO: falló poblar_demo, revisá el log'
	 python manage.py fotos_demo || echo 'AVISO: falló fotos_demo, revisá el log') &
else
	(python manage.py fotos_demo || echo 'AVISO: falló fotos_demo, revisá el log') &
fi

exec gunicorn config.wsgi --bind "0.0.0.0:${PORT:-8000}" --workers 2
