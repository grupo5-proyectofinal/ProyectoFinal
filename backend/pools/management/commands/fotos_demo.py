"""Pone las fotos reales (`pools/demo/fotos/<clave>.jpg`) en los pools de la demo ya cargados.

    python manage.py fotos_demo

Es idempotente: un pool que ya tiene su foto real no se toca, así que corre en cada
arranque (ver `arranque.sh`) y, si no hay demo cargada, no hace nada. Reemplaza las
imágenes ilustrativas que dibujaba la primera versión de `poblar_demo`.
"""

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from pools.demo import datos, imagenes
from pools.models import Pool, PoolImage


class Command(BaseCommand):
    help = "Reemplaza las imágenes ilustrativas de los pools de la demo por fotos reales."

    def handle(self, *args, **options):
        cambiados = 0
        for spec in datos.POOLS:
            foto = imagenes.foto_real(spec["clave"])
            if foto is None:
                continue
            marca = f"foto-{spec['clave']}"
            pools = Pool.objects.filter(
                creador__email__endswith="@" + datos.DOMINIO_EMAIL,
                nombre_producto=spec["producto"],
            ).prefetch_related("imagenes")
            for pool in pools:
                anteriores = list(pool.imagenes.all())
                if any(marca in imagen.imagen.name for imagen in anteriores):
                    continue
                with transaction.atomic():
                    PoolImage.objects.create(
                        pool=pool,
                        imagen=ContentFile(foto, name=f"{marca}.jpg"),
                        orden=0,
                    )
                    archivos = [(i.imagen.name, i.imagen.storage) for i in anteriores]
                    for imagen in anteriores:
                        imagen.delete()
                    for nombre, almacen in archivos:
                        transaction.on_commit(lambda n=nombre, a=almacen: a.delete(n))
                cambiados += 1
        self.stdout.write(f"Fotos reales puestas en {cambiados} pools de la demo.")
