"""Importación de mayoristas desde un CSV, compartida por el comando y la API.

Columnas: nombre, sitio_url, rubros (nombres separados por ";"), provincia, ciudad,
compra_minima, envio, medios_pago, verificado (si/no), descripcion.
Los proveedores importados quedan aprobados. Es idempotente: si el sitio ya existe
(mismo dominio) se actualizan sus datos en vez de duplicarlo.
"""

import csv
import io

from django.db import transaction

from pools.confianza import dominio_de
from pools.models import Category
from pools.producto import limpiar_enlace

from .models import Proveedor

CAMPOS_TEXTO = ("provincia", "ciudad", "compra_minima", "envio", "medios_pago", "descripcion")
SI = {"si", "sí", "s", "true", "1", "x", "yes"}
COLUMNAS_OBLIGATORIAS = ("nombre", "sitio_url")
MAX_ERRORES = 20


def importar_archivo(archivo):
    """Lee un archivo subido (bytes o texto) y devuelve el resultado de la importación."""
    contenido = archivo.read()
    if isinstance(contenido, bytes):
        try:
            contenido = contenido.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError("El archivo tiene que ser un CSV en UTF-8.") from error

    lector = csv.DictReader(io.StringIO(contenido, newline=""))
    columnas = {nombre.strip() for nombre in (lector.fieldnames or [])}
    if not set(COLUMNAS_OBLIGATORIAS) <= columnas:
        raise ValueError("El CSV debe tener al menos las columnas nombre y sitio_url.")

    filas = list(lector)
    if not filas:
        raise ValueError("El CSV no tiene filas de datos.")
    return importar_filas(filas)


def importar_filas(filas):
    """Crea/actualiza proveedores por dominio y devuelve un resumen con errores."""
    categorias = {categoria.nombre.lower(): categoria for categoria in Category.objects.all()}
    creados = actualizados = salteados = 0
    errores = []
    advertencias = []

    with transaction.atomic():
        # start=2: la fila 1 es el encabezado.
        for numero, fila in enumerate(filas, start=2):
            nombre = (fila.get("nombre") or "").strip()
            url = limpiar_enlace((fila.get("sitio_url") or "").strip())
            dominio = (dominio_de(url) or "").removeprefix("www.") if url else ""
            if not nombre or not dominio:
                salteados += 1
                errores.append(
                    {"fila": numero, "motivo": "Falta nombre o sitio_url válido."}
                )
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
                nombre_rubro = nombre_rubro.strip()
                if not nombre_rubro:
                    continue
                categoria = categorias.get(nombre_rubro.lower())
                if categoria is None:
                    advertencias.append(
                        {"fila": numero, "motivo": f"Rubro desconocido: {nombre_rubro}."}
                    )
                else:
                    rubros.append(categoria)
            proveedor.rubros.set(rubros)

    return {
        "creados": creados,
        "actualizados": actualizados,
        "salteados": salteados,
        "errores": errores[:MAX_ERRORES],
        "total_errores": len(errores),
        "advertencias": advertencias[:MAX_ERRORES],
        "total_advertencias": len(advertencias),
    }
