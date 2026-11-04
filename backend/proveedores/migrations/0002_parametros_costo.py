from decimal import Decimal

from django.db import migrations

# Valores de referencia para la estimación (los edita el staff en /admin/mayoristas).
# El tipo de cambio arranca en 0 = "no cargado": las ofertas en esa moneda no se
# convierten hasta que alguien lo carga (no se inventa una cotización).
PARAMETROS = [
    ("tipo_cambio_usd", "Tipo de cambio USD → ARS", "0", "Pesos por dólar. Cargalo antes de comparar importaciones."),
    ("tipo_cambio_eur", "Tipo de cambio EUR → ARS", "0", "Pesos por euro."),
    ("tasa_estadistica_pct", "Tasa estadística (%)", "3", "Valor de referencia: revisalo según la normativa vigente."),
    ("iva_importacion_pct", "IVA de importación (%)", "21", "Valor de referencia: revisalo según el producto."),
    ("percepciones_pct", "Percepciones (%)", "0", "IVA adicional / Ganancias / IIBB, si aplican."),
]


def cargar(apps, schema_editor):
    Parametro = apps.get_model("proveedores", "ParametroCosto")
    for clave, nombre, valor, ayuda in PARAMETROS:
        Parametro.objects.get_or_create(
            clave=clave, defaults={"nombre": nombre, "valor": Decimal(valor), "ayuda": ayuda}
        )


def borrar(apps, schema_editor):
    apps.get_model("proveedores", "ParametroCosto").objects.filter(
        clave__in=[p[0] for p in PARAMETROS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("proveedores", "0001_inicial")]

    operations = [migrations.RunPython(cargar, borrar)]
