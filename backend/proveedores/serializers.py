from rest_framework import serializers

from pools.confianza import analizar_enlace, dominio_de
from pools.models import Category
from pools.producto import limpiar_enlace

from .costos import Parametros, comparar
from .models import Comparacion, Oferta, ParametroCosto, PrecioHistorico, Proveedor

MAX_OFERTAS = 10
PUNTOS_HISTORIAL = 12


def parametros_vigentes():
    return Parametros.desde_valores(dict(ParametroCosto.objects.values_list("clave", "valor")))


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


class ParametroCostoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParametroCosto
        fields = ("clave", "nombre", "valor", "ayuda", "actualizado")
        read_only_fields = ("clave", "nombre", "ayuda", "actualizado")

    def validate_valor(self, value):
        if value < 0:
            raise serializers.ValidationError("No puede ser negativo.")
        return value


class OfertaSerializer(serializers.ModelSerializer):
    comparacion = serializers.PrimaryKeyRelatedField(queryset=Comparacion.objects.all())
    proveedor = serializers.PrimaryKeyRelatedField(
        queryset=Proveedor.objects.filter(estado=Proveedor.Estado.APROBADO),
        required=False,
        allow_null=True,
    )
    tienda = serializers.CharField(max_length=120, required=False, allow_blank=True)

    class Meta:
        model = Oferta
        fields = (
            "id",
            "comparacion",
            "proveedor",
            "tienda",
            "url",
            "precio_unitario",
            "moneda",
            "cantidad_minima",
            "costo_envio",
            "impuestos_pct",
            "es_importacion",
            "derechos_pct",
            "notas",
        )

    def validate_url(self, value):
        return limpiar_enlace(value) if value else value

    def validate_moneda(self, value):
        moneda = (value or "ARS").strip().upper()
        if len(moneda) != 3 or not moneda.isalpha():
            raise serializers.ValidationError("Usá el código de 3 letras (ARS, USD, EUR).")
        return moneda

    def validate_comparacion(self, value):
        request = self.context["request"]
        if value.creador_id != request.user.id:
            raise serializers.ValidationError("Solo quien creó la comparación puede editarla.")
        if self.instance is None and value.ofertas.count() >= MAX_OFERTAS:
            raise serializers.ValidationError(f"Una comparación admite hasta {MAX_OFERTAS} ofertas.")
        return value

    def validate(self, attrs):
        movida = (
            self.instance is not None
            and "comparacion" in attrs
            and attrs["comparacion"] != self.instance.comparacion
        )
        if movida:
            raise serializers.ValidationError({"comparacion": "No se puede mover de comparación."})
        tienda = (attrs.get("tienda") or "").strip()
        if not tienda and self.instance is None:
            proveedor = attrs.get("proveedor")
            tienda = proveedor.nombre if proveedor else (dominio_de(attrs.get("url", "")) or "")
            if not tienda:
                raise serializers.ValidationError({"tienda": "Poné el nombre de la tienda."})
            attrs["tienda"] = tienda.removeprefix("www.")[:120]
        return attrs


class ComparacionSerializer(serializers.ModelSerializer):
    creador = serializers.SerializerMethodField()
    ofertas = serializers.SerializerMethodField()
    resumen = serializers.SerializerMethodField()
    puede_editar = serializers.SerializerMethodField()
    cantidad_ofertas = serializers.SerializerMethodField()

    class Meta:
        model = Comparacion
        fields = (
            "id",
            "titulo",
            "producto",
            "cantidad",
            "pool",
            "creador",
            "puede_editar",
            "cantidad_ofertas",
            "ofertas",
            "resumen",
            "creado",
            "actualizado",
        )
        read_only_fields = ("creado", "actualizado")

    def get_creador(self, obj):
        return {"id": obj.creador_id, "username": obj.creador.username}

    def get_puede_editar(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.id == obj.creador_id)

    def get_cantidad_ofertas(self, obj):
        anotado = getattr(obj, "total_ofertas", None)
        return anotado if anotado is not None else len(obj.ofertas.all())

    def _calculo(self, obj):
        cache = self.context.setdefault("_calculos", {})
        if obj.pk not in cache:
            parametros = self.context.get("parametros") or parametros_vigentes()
            cache[obj.pk] = comparar(list(obj.ofertas.all()), obj.cantidad, parametros)
        return cache[obj.pk]

    def get_ofertas(self, obj):
        if not self.context.get("con_ofertas", False):
            return None
        filas, resumen = self._calculo(obj)
        resultado = []
        for oferta, costo in filas:
            datos = OfertaSerializer(oferta, context=self.context).data
            datos.pop("comparacion", None)
            # El prefetch trae los últimos puntos del más nuevo al más viejo.
            historial = sorted(oferta.historial.all(), key=lambda p: (p.fecha, p.id))
            resultado.append(
                {
                    **datos,
                    "proveedor_nombre": oferta.proveedor.nombre if oferta.proveedor else None,
                    "costo": costo,
                    "es_mejor": costo["total"] is not None and costo["total"] == resumen["mejor_total"],
                    "historial": [
                        {"precio": str(p.precio), "fecha": p.fecha.isoformat()} for p in historial
                    ],
                }
            )
        return resultado

    def get_resumen(self, obj):
        if not self.context.get("con_ofertas", False):
            return None
        return self._calculo(obj)[1]

    def validate_pool(self, pool):
        if pool is None:
            return pool
        request = self.context["request"]
        if pool.creador_id != request.user.id:
            raise serializers.ValidationError("Solo el creador del pool puede armar su comparación.")
        otras = Comparacion.objects.filter(pool=pool)
        if self.instance is not None:
            otras = otras.exclude(pk=self.instance.pk)
        if otras.exists():
            raise serializers.ValidationError("Este pool ya tiene una comparación.")
        return pool


def registrar_precio(oferta):
    PrecioHistorico.objects.create(oferta=oferta, precio=oferta.precio_unitario, moneda=oferta.moneda)
