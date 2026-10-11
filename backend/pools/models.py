from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


def validar_fecha_caducidad(fecha):
    hoy = timezone.localdate()
    if fecha < hoy:
        raise ValidationError("La fecha de caducidad debe ser futura.")
    if fecha > hoy + timedelta(days=30):
        raise ValidationError("La fecha de caducidad no puede superar los 30 días.")


class Category(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.nombre


class Pool(models.Model):
    class TipoPago(models.TextChoices):
        EFECTIVO = "efectivo", "Efectivo"
        TRANSFERENCIA = "transferencia", "Transferencia"
        SIN_ESPECIFICAR = "sin_especificar", "Sin especificar"

    class Estado(models.TextChoices):
        ABIERTO = "abierto", "Abierto"
        LISTO = "listo", "Listo"
        EN_CURSO = "en_curso", "En curso"
        FINALIZADO = "finalizado", "Finalizado"
        CANCELADO = "cancelado", "Cancelado"

    titulo = models.CharField(max_length=200)
    nombre_producto = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="pools")
    enlace = models.URLField(blank=True)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_total = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    cantidad_creador = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    min_por_integrante = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    fecha_caducidad = models.DateField(validators=[validar_fecha_caducidad])
    tipo_pago = models.CharField(
        max_length=20, choices=TipoPago.choices, default=TipoPago.SIN_ESPECIFICAR
    )
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTO)
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pools_creados"
    )
    vistas = models.PositiveIntegerField(default=0)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return self.titulo

    @property
    def disponible(self):
        usado = self.cantidad_creador + sum(m.cantidad for m in self.memberships.all())
        return max(self.cantidad_total - usado, 0)

    def actualizar_estado(self, disponible=None):
        """Mantiene abierto/listo según el disponible; no toca otros estados.

        Devuelve True si cambió el estado (para guardar con update_fields).
        """
        if self.estado not in (self.Estado.ABIERTO, self.Estado.LISTO):
            return False
        valor = self.disponible if disponible is None else disponible
        nuevo = self.Estado.LISTO if valor == 0 else self.Estado.ABIERTO
        if nuevo == self.estado:
            return False
        self.estado = nuevo
        return True

    def solicitud_pendiente(self):
        """La solicitud de eliminación activa del pool, o None."""
        return self.solicitudes_eliminacion.filter(
            estado=SolicitudEliminacion.Estado.PENDIENTE
        ).first()

    def vencio(self, hoy=None):
        """True si el pool es un abierto cuya fecha ya pasó (la fecha vale todo el día)."""
        return self.estado == self.Estado.ABIERTO and self.fecha_caducidad < (
            hoy or timezone.localdate()
        )

    def caducar(self, hoy=None):
        """Cancela el pool si venció, sin pisar otra transición. True si lo canceló.

        El update es condicional para no cancelar un pool que otra transición
        (p. ej. un unirse que lo completó) dejó en listo.
        """
        hoy = hoy or timezone.localdate()
        if not self.vencio(hoy):
            return False
        cancelados = Pool.objects.filter(
            pk=self.pk, estado=self.Estado.ABIERTO, fecha_caducidad__lt=hoy
        ).update(estado=self.Estado.CANCELADO)
        if cancelados == 0:
            return False
        self.estado = self.Estado.CANCELADO
        registrar_evento(self, EventoPool.Tipo.EXPIRADO)
        return True


def expirar_vencidos():
    """Cancela los pools abiertos vencidos y devuelve la lista de pks cancelados.

    Idempotente: tras la primera corrida no quedan abiertos vencidos.
    """
    hoy = timezone.localdate()
    vencidos = Pool.objects.filter(estado=Pool.Estado.ABIERTO, fecha_caducidad__lt=hoy)
    return [pool.pk for pool in vencidos if pool.caducar(hoy)]


class SolicitudEliminacion(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"
        CANCELADA = "cancelada", "Cancelada"

    pool = models.ForeignKey(
        Pool, on_delete=models.CASCADE, related_name="solicitudes_eliminacion"
    )
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PENDIENTE
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"Eliminación de {self.pool} ({self.estado})"


class VotoEliminacion(models.Model):
    solicitud = models.ForeignKey(
        SolicitudEliminacion, on_delete=models.CASCADE, related_name="votos"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="votos_eliminacion"
    )
    acepta = models.BooleanField()
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creado"]
        constraints = [
            models.UniqueConstraint(
                fields=["solicitud", "usuario"], name="unique_voto_eliminacion_solicitud_usuario"
            )
        ]

    def __str__(self):
        return f"Voto de {self.usuario} en {self.solicitud}"


class PoolImage(models.Model):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="imagenes")
    imagen = models.ImageField(upload_to="pools/")
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]

    def __str__(self):
        return f"Imagen {self.pk} de {self.pool}"


class Membership(models.Model):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="memberships")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # PII del miembro, aportada al unirse y visible solo para el creador del pool
    # (regla en MembershipSerializer). blank=True: las memberships previas a la
    # feature no tienen estos datos; la obligatoriedad se valida en el boundary.
    telefono = models.CharField(max_length=30, blank=True)
    mensaje = models.CharField(max_length=500, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pool", "usuario"], name="unique_membership_pool_usuario")
        ]

    def __str__(self):
        return f"{self.usuario} en {self.pool} ({self.cantidad})"


class Mensaje(models.Model):
    """Un mensaje del chat del pool, visible para sus integrantes.

    El texto se normaliza y valida en el boundary (`MensajeSerializer`); el
    `max_length` queda como respaldo a nivel de base.
    """

    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="mensajes")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mensajes"
    )
    texto = models.CharField(max_length=1000)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ascendente por id: el chat se lee como conversación y el polling pide
        # "lo nuevo" con `id > desde`.
        ordering = ["id"]
        indexes = [models.Index(fields=["pool", "id"], name="mensaje_pool_id_idx")]

    def __str__(self):
        return f"Mensaje {self.pk} de {self.autor} en {self.pool}"


class EventoPool(models.Model):
    """Un cambio del pool, para el historial que ven sus integrantes.

    `actor` nulo significa que lo hizo el sistema (p. ej. la expiración).
    `datos` guarda solo lo necesario para el texto del evento: nunca PII del
    miembro (teléfono/mensaje).
    """

    class Tipo(models.TextChoices):
        CREADO = "creado", "Creado"
        EDICION = "edicion", "Edición"
        IMAGEN = "imagen", "Imagen"
        UNION = "union", "Unión"
        SALIDA = "salida", "Salida"
        CANTIDAD = "cantidad", "Cantidad"
        ESTADO = "estado", "Estado"
        EXPIRADO = "expirado", "Expirado"
        SOLICITUD_ELIMINACION = "solicitud_eliminacion", "Solicitud de eliminación"
        VOTO_ELIMINACION = "voto_eliminacion", "Voto de eliminación"

    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="eventos")
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="eventos_pool",
    )
    datos = models.JSONField(default=dict, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Lo más nuevo primero: el timeline se lee como un feed.
        ordering = ["-creado", "-id"]

    def __str__(self):
        return f"{self.get_tipo_display()} en {self.pool}"


def registrar_evento(pool, tipo, actor=None, datos=None):
    """Registra un cambio del pool en su historial. `actor=None` es el sistema."""
    return EventoPool.objects.create(pool=pool, tipo=tipo, actor=actor, datos=datos or {})
