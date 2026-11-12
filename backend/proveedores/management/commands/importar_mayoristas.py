"""Carga o actualiza el directorio de mayoristas desde un CSV curado por el equipo.

    python manage.py importar_mayoristas mayoristas.csv

Columnas: nombre, sitio_url, rubros (nombres separados por ";"), provincia, ciudad,
compra_minima, envio, medios_pago, verificado (si/no), descripcion (opcional).
Los proveedores importados quedan aprobados. Es idempotente: si el sitio ya
existe (mismo dominio) se actualizan sus datos en vez de duplicarlo. El repo no
trae datos: la lista la arma el equipo.
"""

import csv

from django.core.management.base import BaseCommand, CommandError

from ...importacion import importar_filas


class Command(BaseCommand):
    help = "Importa mayoristas desde un CSV (nombre, sitio_url, rubros, provincia…)."

    def add_arguments(self, parser):
        parser.add_argument("archivo")

    def handle(self, *args, archivo, **options):
        try:
            with open(archivo, encoding="utf-8-sig", newline="") as entrada:
                filas = list(csv.DictReader(entrada))
        except OSError as error:
            raise CommandError(f"No se pudo leer {archivo}: {error}") from error

        resultado = importar_filas(filas)
        for error in resultado["errores"]:
            self.stderr.write(f"Fila {error['fila']}: {error['motivo']} Se saltea.")
        for advertencia in resultado["advertencias"]:
            self.stderr.write(f"Fila {advertencia['fila']}: {advertencia['motivo']}")
        self.stdout.write(
            "Mayoristas: "
            f"{resultado['creados']} nuevos, "
            f"{resultado['actualizados']} actualizados, "
            f"{resultado['salteados']} salteados."
        )
