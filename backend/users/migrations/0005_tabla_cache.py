"""Tabla de la caché compartida (CACHES en settings), usada por los límites de pedidos.

Se crea con una migración para que exista en todos los entornos (local, CI, tests y
Render) sin pasos manuales: `migrate` ya corre al arrancar el contenedor.
"""

from django.core.management import call_command
from django.db import migrations

TABLA = "poolshop_cache"


def crear(apps, schema_editor):
    call_command("createcachetable", database=schema_editor.connection.alias, verbosity=0)


def borrar(apps, schema_editor):
    schema_editor.execute(f"DROP TABLE IF EXISTS {schema_editor.quote_name(TABLA)}")


class Migration(migrations.Migration):
    dependencies = [("users", "0004_notificar_pagos")]

    operations = [migrations.RunPython(crear, borrar)]
