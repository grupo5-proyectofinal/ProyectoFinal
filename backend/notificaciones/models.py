from django.conf import settings
from django.db import models


class Notificacion(models.Model):
    """Un aviso para un usuario sobre un pool en el que participa.

    `texto` es el cuerpo ya armado en es-AR: el front lo muestra tal cual. Los
    mensajes del chat se agrupan en una sola notificación no leída por pool
    (`cantidad` cuenta cuántos llegaron) para no inundar la bandeja.
    """

    class Tipo(models.TextChoices):
        ESTADO = "estado", "Cambio de estado"
        MENSAJE = "mensaje", "Mensaje nuevo"
        UNION = "union", "Nuevo integrante"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificaciones"
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    pool = models.ForeignKey(
        "pools.Pool",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notificaciones",
    )
    titulo = models.CharField(max_length=255)
    texto = models.CharField(max_length=500, blank=True)
    datos = models.JSONField(default=dict, blank=True)
    cantidad = models.PositiveIntegerField(default=1)
    leida = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-actualizado", "-id"]
        indexes = [
            models.Index(fields=["usuario", "leida"], name="notificacion_usuario_leida_idx")
        ]

    def __str__(self):
        return f"{self.titulo} → {self.usuario}"
