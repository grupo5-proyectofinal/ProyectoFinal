"""Mayoristas y comparador de costo final (Iteración 3, "funcionalidades que
diferenciarán tu plataforma").

- `Proveedor`: directorio curado de sitios mayoristas. Lo carga el equipo (o un
  CSV con `importar_mayoristas`); los usuarios pueden sugerir sitios, que quedan
  pendientes hasta que el staff los aprueba.
- `Comparacion` / `Oferta`: el mismo producto en varios proveedores, comparado
  por costo total (precio + envío + impuestos + aduana estimada), no por el
  precio publicado.
- `ParametroCosto`: tipo de cambio y alícuotas que usa la estimación. Son
  valores de referencia que edita el staff: la UI los muestra como estimación.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from pools.confianza import dominio_de

MONEDA_LOCAL = "ARS"


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


class ParametroCosto(models.Model):
    """Valor de referencia para la estimación del costo final (lo edita el staff)."""

    clave = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=120)
    valor = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal(0))
    ayuda = models.CharField(max_length=255, blank=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["clave"]

    def __str__(self):
        return f"{self.nombre}: {self.valor}"


class Comparacion(models.Model):
    titulo = models.CharField(max_length=200)
    producto = models.CharField(max_length=200, blank=True)
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comparaciones"
    )
    # Comparador de un pool: lo ven sus integrantes ("elegimos el más barato").
    pool = models.OneToOneField(
        "pools.Pool", on_delete=models.CASCADE, null=True, blank=True, related_name="comparacion"
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-actualizado"]

    def __str__(self):
        return self.titulo


class Oferta(models.Model):
    comparacion = models.ForeignKey(Comparacion, on_delete=models.CASCADE, related_name="ofertas")
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name="ofertas"
    )
    tienda = models.CharField(max_length=120)
    url = models.URLField(max_length=2000, blank=True)
    precio_unitario = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    moneda = models.CharField(max_length=3, default=MONEDA_LOCAL)
    cantidad_minima = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    costo_envio = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal(0), validators=[MinValueValidator(0)]
    )
    impuestos_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal(0),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    es_importacion = models.BooleanField(default=False)
    derechos_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal(0),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    notas = models.CharField(max_length=255, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.tienda} ({self.comparacion})"


class PrecioHistorico(models.Model):
    """Cada precio que tuvo una oferta: alimenta la tendencia (sparkline)."""

    oferta = models.ForeignKey(Oferta, on_delete=models.CASCADE, related_name="historial")
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=3, default=MONEDA_LOCAL)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "id"]
