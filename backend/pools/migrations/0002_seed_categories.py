from django.db import migrations

CATEGORIAS = ["Alimentos", "Bebidas", "Limpieza", "Hogar", "Electrónica", "Otros"]


def crear_categorias(apps, schema_editor):
    Category = apps.get_model("pools", "Category")
    for nombre in CATEGORIAS:
        Category.objects.get_or_create(nombre=nombre)


def borrar_categorias(apps, schema_editor):
    Category = apps.get_model("pools", "Category")
    Category.objects.filter(nombre__in=CATEGORIAS).delete()


class Migration(migrations.Migration):
    dependencies = [("pools", "0001_initial")]

    operations = [migrations.RunPython(crear_categorias, borrar_categorias)]
