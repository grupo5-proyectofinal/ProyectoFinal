"""Directorio de mayoristas (Iteración 3, "funcionalidades que diferenciarán tu
plataforma").

- `Proveedor`: directorio curado de sitios mayoristas. Lo carga el equipo (o un
  CSV con `importar_mayoristas`); los usuarios pueden sugerir sitios, que quedan
  pendientes hasta que el staff los aprueba.
"""

from django.conf import settings
from django.db import models

from pools.confianza import dominio_de


class Proveedor(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de revisión"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"

    nombre = models.CharField(max_length=120)
    sitio_url = models.URLField(max_length=500)
    dominio = models.CharField(max_length=255, blank=True, db_index=True, editable=False)
    descripcion = models.TextField(blank=True)
    rubros = models.ManyToManyField("pools.Category", blank=True, related_name="proveedores")
    provincia = models.CharField(max_length=60, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    compra_minima = models.CharField(max_length=120, blank=True)
    envio = models.CharField(max_length=255, blank=True)
    medios_pago = models.CharField(max_length=255, blank=True)
    verificado = models.BooleanField(default=False)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    sugerido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proveedores_sugeridos",
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-verificado", "nombre"]
        verbose_name_plural = "proveedores"

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        dominio = dominio_de(self.sitio_url) or ""
        self.dominio = dominio.removeprefix("www.")
        super().save(*args, **kwargs)
