from django.db import migrations

# Iteración 3: "Falta categoría ropa al crear pool".
NUEVAS = ("Ropa",)


def alta_categorias(apps, schema_editor):
    Category = apps.get_model("pools", "Category")
    for nombre in NUEVAS:
        Category.objects.get_or_create(nombre=nombre)


def baja_categorias(apps, schema_editor):
    """Revierte solo si nadie la usó: con pools, la categoría queda (PROTECT)."""
    Category = apps.get_model("pools", "Category")
    Category.objects.filter(nombre__in=NUEVAS, pools__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("pools", "0010_merge_pagos_resena")]

    operations = [migrations.RunPython(alta_categorias, baja_categorias)]
