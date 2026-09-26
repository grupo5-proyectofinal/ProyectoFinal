from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Category, Membership, Pool, PoolImage

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "nombre")


class UsuarioPublicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "foto")
        read_only_fields = fields


class PoolImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoolImage
        fields = ("id", "imagen", "orden")
        read_only_fields = ("id",)

    def validate_imagen(self, value):
        formato = getattr(getattr(value, "image", None), "format", None)
        if formato not in ("JPEG", "PNG"):
            raise serializers.ValidationError("Solo se aceptan imágenes JPEG o PNG.")
        return value


class MembershipSerializer(serializers.ModelSerializer):
    usuario = UsuarioPublicoSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "usuario", "cantidad")
        read_only_fields = ("id", "usuario")


class PoolSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    creador = UsuarioPublicoSerializer(read_only=True)
    disponible = serializers.IntegerField(read_only=True)
    imagenes = PoolImageSerializer(many=True, read_only=True)
    miembros = MembershipSerializer(source="memberships", many=True, read_only=True)

    class Meta:
        model = Pool
        fields = (
            "id",
            "titulo",
            "nombre_producto",
            "descripcion",
            "categoria",
            "categoria_nombre",
            "enlace",
            "precio_unitario",
            "cantidad_total",
            "cantidad_creador",
            "min_por_integrante",
            "fecha_caducidad",
            "tipo_pago",
            "direccion",
            "ciudad",
            "estado",
            "creador",
            "vistas",
            "disponible",
            "imagenes",
            "miembros",
            "creado",
            "actualizado",
        )
        read_only_fields = ("estado", "creador", "vistas", "creado", "actualizado")

    INMUTABLES_CON_MIEMBROS = (
        "titulo",
        "nombre_producto",
        "precio_unitario",
        "cantidad_total",
        "direccion",
        "ciudad",
    )

    def validate(self, attrs):
        instance = self.instance
        total = attrs.get("cantidad_total", getattr(instance, "cantidad_total", None))
        creador = attrs.get("cantidad_creador", getattr(instance, "cantidad_creador", 1))
        comprometido = creador
        if instance is not None:
            comprometido += sum(m.cantidad for m in instance.memberships.all())
        if total is not None and comprometido > total:
            campo = (
                "cantidad_total"
                if "cantidad_total" in attrs and "cantidad_creador" not in attrs
                else "cantidad_creador"
            )
            raise serializers.ValidationError(
                {campo: "El comprometido supera la cantidad total."}
            )
        if instance is not None and instance.memberships.exclude(
            usuario=instance.creador
        ).exists():
            for campo in self.INMUTABLES_CON_MIEMBROS:
                if campo in attrs and attrs[campo] != getattr(instance, campo):
                    raise serializers.ValidationError(
                        {campo: "Campo inmutable una vez que hay otros miembros."}
                    )
        return attrs


class CantidadSerializer(serializers.Serializer):
    cantidad = serializers.IntegerField(min_value=1)
