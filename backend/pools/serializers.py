from rest_framework import serializers

from .models import Category, Membership, Pool, PoolImage


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "nombre")


class PoolImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoolImage
        fields = ("id", "imagen", "orden")
        read_only_fields = ("id",)


class MembershipSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="usuario.email", read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "usuario", "email", "cantidad")
        read_only_fields = ("id", "usuario", "email")


class PoolSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    creador_email = serializers.EmailField(source="creador.email", read_only=True)
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
            "creador_email",
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
        if total is not None and creador > total:
            raise serializers.ValidationError(
                {"cantidad_creador": "No puede superar la cantidad total."}
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
