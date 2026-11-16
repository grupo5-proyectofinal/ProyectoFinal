"""Quita las tablas de la app `proveedores` (directorio de mayoristas y comparador de costo).

La app ya no existe en el código: esta migración limpia lo que quedó en bases ya
desplegadas. En una base nueva las tablas no existen y no hace nada.
"""

from django.db import migrations

TABLAS = (
    "proveedores_oferta",
    "proveedores_preciohistorico",
    "proveedores_comparacion",
    "proveedores_parametrocosto",
    "proveedores_proveedor_rubros",
    "proveedores_proveedor",
)


class Migration(migrations.Migration):
    dependencies = [("pools", "0020_quitar_eliminacion")]

    operations = [
        *(migrations.RunSQL(f"DROP TABLE IF EXISTS {t} CASCADE", migrations.RunSQL.noop) for t in TABLAS),
        migrations.RunSQL("DELETE FROM django_migrations WHERE app = 'proveedores'", migrations.RunSQL.noop),
    ]
