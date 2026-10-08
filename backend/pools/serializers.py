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
    integrantes = serializers.SerializerMethodField()
    mi_cantidad = serializers.SerializerMethodField()
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
            "latitud",
            "longitud",
            "estado",
            "creador",
            "vistas",
            "disponible",
            "integrantes",
            "mi_cantidad",
            "imagenes",
            "miembros",
            "creado",
            "actualizado",
        )
        read_only_fields = (
            "latitud",
            "longitud",
            "estado",
            "creador",
            "vistas",
            "creado",
            "actualizado",
        )

    def get_integrantes(self, obj):
        """Personas participando: creador + memberships. Usa la anotación si está."""
        anotado = getattr(obj, "integrantes", None)
        if anotado is not None:
            return anotado + 1
        return obj.memberships.count() + 1

    def get_mi_cantidad(self, obj):
        """Cantidad reservada por el usuario logueado, o None."""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        for membresia in obj.memberships.all():
            if membresia.usuario_id == user.id:
                return membresia.cantidad
        if obj.creador_id == user.id:
            return obj.cantidad_creador
        return None

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
