"""Tareas que corren solas cada hora (cron de Render o servicio `scheduler` de compose).

Un solo punto de entrada para no tener que tocar la infraestructura cada vez que
se agrega una tarea: se suman acá.
"""

import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

# flushexpiredtokens: borra los refresh vencidos de la blacklist de JWT (cada
# login/refresh agrega una fila; sin limpieza la tabla crece sin límite).
TAREAS = ("expirar_pools", "flushexpiredtokens")

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Corre las tareas periódicas de PoolShop (caducidad de pools, recordatorios)."

    def handle(self, *args, **options):
        fallidas = []
        for tarea in TAREAS:
            try:
                call_command(tarea, stdout=self.stdout, stderr=self.stderr)
            except Exception:
                # Una tarea rota no frena a las demás; el traceback queda en el log.
                logger.exception("Falló la tarea periódica %s.", tarea)
                fallidas.append(tarea)
        if fallidas:
            # Código de salida != 0: el cron de Render marca la corrida como fallida.
            raise CommandError(f"Fallaron: {', '.join(fallidas)}.")
