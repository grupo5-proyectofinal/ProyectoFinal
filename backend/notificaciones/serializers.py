from rest_framework import serializers

from .models import Notificacion


class NotificacionSerializer(serializers.ModelSerializer):
    """Un aviso de la bandeja. `pool_titulo` evita otra consulta en el front."""

    pool_titulo = serializers.CharField(source="pool.titulo", read_only=True, default=None)

    class Meta:
        model = Notificacion
        fields = (
            "id",
            "tipo",
            "pool",
            "pool_titulo",
            "titulo",
            "texto",
            "datos",
            "cantidad",
            "leida",
            "creado",
            "actualizado",
        )
        read_only_fields = fields
