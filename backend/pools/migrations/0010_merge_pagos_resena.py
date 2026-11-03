from django.db import migrations


class Migration(migrations.Migration):
    """Une las dos ramas de migraciones: pagos (main) y reseñas (iteración 2)."""

    dependencies = [
        ("pools", "0009_pagos_recepcion"),
        ("pools", "0009_resena"),
    ]

    operations = []
