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
from django.db import transaction

from pools.confianza import dominio_de
from pools.models import Category
from pools.producto import limpiar_enlace

from ...models import Proveedor

CAMPOS_TEXTO = ("provincia", "ciudad", "compra_minima", "envio", "medios_pago", "descripcion")
SI = {"si", "sí", "s", "true", "1", "x", "yes"}


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
        categorias = {c.nombre.lower(): c for c in Category.objects.all()}
        creados = actualizados = salteados = 0
        with transaction.atomic():
            for numero, fila in enumerate(filas, start=2):
                nombre = (fila.get("nombre") or "").strip()
                url = limpiar_enlace((fila.get("sitio_url") or "").strip())
                dominio = (dominio_de(url) or "").removeprefix("www.") if url else ""
                if not nombre or not dominio:
                    self.stderr.write(f"Fila {numero}: falta nombre o sitio_url válido, se saltea.")
                    salteados += 1
                    continue
                datos = {campo: (fila.get(campo) or "").strip() for campo in CAMPOS_TEXTO}
                datos.update(
                    nombre=nombre[:120],
                    sitio_url=url,
                    verificado=(fila.get("verificado") or "").strip().lower() in SI,
                    estado=Proveedor.Estado.APROBADO,
                )
                proveedor = Proveedor.objects.filter(dominio=dominio).first()
                if proveedor is None:
                    proveedor = Proveedor.objects.create(**datos)
                    creados += 1
                else:
                    for campo, valor in datos.items():
                        setattr(proveedor, campo, valor)
                    proveedor.save()
                    actualizados += 1
                rubros = []
                for nombre_rubro in (fila.get("rubros") or "").split(";"):
                    categoria = categorias.get(nombre_rubro.strip().lower())
                    if categoria is not None:
                        rubros.append(categoria)
                    elif nombre_rubro.strip():
                        self.stderr.write(f"Fila {numero}: rubro desconocido «{nombre_rubro.strip()}».")
                proveedor.rubros.set(rubros)
        self.stdout.write(
            f"Mayoristas: {creados} nuevos, {actualizados} actualizados, {salteados} salteados."
        )
