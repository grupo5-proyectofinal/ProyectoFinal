from rest_framework import serializers

from pools.confianza import analizar_enlace, dominio_de
from pools.models import Category
from pools.producto import limpiar_enlace

from .models import Proveedor


class ProveedorSerializer(serializers.ModelSerializer):
    rubros = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all(), required=False
    )
    rubros_nombres = serializers.SerializerMethodField()

    class Meta:
        model = Proveedor
        fields = (
            "id",
            "nombre",
            "sitio_url",
            "dominio",
            "descripcion",
            "rubros",
            "rubros_nombres",
            "provincia",
            "ciudad",
            "compra_minima",
            "envio",
            "medios_pago",
            "verificado",
            "estado",
            "creado",
        )
        read_only_fields = ("dominio", "estado", "creado")

    def get_rubros_nombres(self, obj):
        return [c.nombre for c in obj.rubros.all()]

    def validate_sitio_url(self, value):
        return limpiar_enlace(value)

    def validate(self, attrs):
        url = attrs.get("sitio_url")
        if url:
            dominio = (dominio_de(url) or "").removeprefix("www.")
            if not dominio:
                raise serializers.ValidationError({"sitio_url": "Ingresá la dirección del sitio."})
            repetidos = Proveedor.objects.filter(dominio=dominio)
            if self.instance is not None:
                repetidos = repetidos.exclude(pk=self.instance.pk)
            if repetidos.exists():
                raise serializers.ValidationError(
                    {"sitio_url": "Ese sitio ya está en el directorio (o en revisión)."}
                )
        return attrs


class ProveedorDetalleSerializer(ProveedorSerializer):
    """Detalle: además, el análisis del sitio y los pools que lo usan."""

    analisis = serializers.SerializerMethodField()
    pools_activos = serializers.SerializerMethodField()
    pools_total = serializers.SerializerMethodField()

    class Meta(ProveedorSerializer.Meta):
        fields = (*ProveedorSerializer.Meta.fields, "analisis", "pools_activos", "pools_total")

    def get_analisis(self, obj):
        return analizar_enlace(obj.sitio_url, uso=self.context.get("pools_total", 0))

    def get_pools_activos(self, obj):
        return self.context.get("pools_activos", [])

    def get_pools_total(self, obj):
        return self.context.get("pools_total", 0)
