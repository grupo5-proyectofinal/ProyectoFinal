import re

from django.contrib.auth import get_user_model
from PIL import Image
from rest_framework import serializers

from .confianza import analizar_enlace, conteos_dominio, dominio_de
from .models import (
    Category,
    EventoPool,
    Membership,
    Mensaje,
    Pool,
    PoolImage,
    Resena,
    SolicitudEliminacion,
    VotoEliminacion,
)
from .producto import limpiar_enlace
from .variantes import (
    cupos_por_variante,
    normalizar_reparto,
    validar_atributos_pool,
    variantes_vigentes,
)

User = get_user_model()
LARGO_ENLACE = Pool._meta.get_field("enlace").max_length


class CategorySerializer(serializers.ModelSerializer):
    # Atributos efectivos (propios + heredados del padre) con sus opciones.
    atributos = serializers.SerializerMethodField()
    # Solo los propios: los que se editan en /admin/categorias.
    propios = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "nombre", "padre", "atributos", "propios")

    def get_atributos(self, obj):
        return [{"nombre": a.nombre, "opciones": a.opciones} for a in obj.atributos_efectivos()]

    def get_propios(self, obj):
        return [{"nombre": a.nombre, "opciones": a.opciones} for a in obj.atributos.all()]

    def validate_nombre(self, value):
        # Se normaliza antes de chequear duplicados: "Ropa  Deportiva" y
        # "ropa deportiva" son la misma categoría (el UniqueValidator mira el texto crudo).
        nombre = " ".join(value.split())
        if not nombre:
            raise serializers.ValidationError("Poné un nombre.")
        repetidas = Category.objects.filter(nombre__iexact=nombre)
        if self.instance is not None:
            repetidas = repetidas.exclude(pk=self.instance.pk)
        if repetidas.exists():
            raise serializers.ValidationError("Ya existe una categoría con ese nombre.")
        return nombre

    def validate_padre(self, padre):
        # Un solo nivel: Ropa > Remera, nunca Ropa > Remera > Manga corta.
        if padre is None:
            return padre
        if padre.padre_id is not None:
            raise serializers.ValidationError("Elegí una categoría principal como padre.")
        if self.instance is not None and (
            padre.pk == self.instance.pk or self.instance.subcategorias.exists()
        ):
            raise serializers.ValidationError("Una categoría con subcategorías no puede tener padre.")
        return padre


class AtributosCategoriaSerializer(serializers.Serializer):
    """Reemplaza los atributos propios de una categoría: [{nombre, opciones}]."""

    MAX_OPCIONES = 40

    atributos = serializers.ListField(child=serializers.DictField(), max_length=10)

    def validate_atributos(self, atributos):
        limpios, nombres = [], set()
        for atributo in atributos:
            nombre = " ".join(str(atributo.get("nombre", "")).split())[:40]
            if not nombre:
                raise serializers.ValidationError("Cada atributo necesita un nombre.")
            if nombre.lower() in nombres:
                raise serializers.ValidationError(f"«{nombre}» está repetido.")
            nombres.add(nombre.lower())
            opciones = atributo.get("opciones")
            if not isinstance(opciones, list):
                raise serializers.ValidationError(f"Las opciones de {nombre} tienen que ser una lista.")
            vistas, unicas = set(), []
            for opcion in opciones:
                texto = " ".join(str(opcion).split())[:40]
                if texto and texto.lower() not in vistas:
                    vistas.add(texto.lower())
                    unicas.append(texto)
            if not unicas:
                raise serializers.ValidationError(f"{nombre} necesita al menos una opción.")
            if len(unicas) > self.MAX_OPCIONES:
                raise serializers.ValidationError(f"{nombre} admite hasta {self.MAX_OPCIONES} opciones.")
            limpios.append({"nombre": nombre, "opciones": unicas})
        return limpios


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
        # `imagen` usa CampoImagen (config/imagenes.py): acepta HEIC/WEBP/… y los
        # guarda como JPEG; lo que llega acá ya es JPEG o PNG.


class MembershipSerializer(serializers.ModelSerializer):
    """Serializa una membresía con privacidad por rol.

    Solo en acciones de detalle (`exponer_datos_miembros=True`, nunca en
    listados):

    - `pago_estado`, `recepcion_confirmada` y `monto` los ven todos (el estado
      de los pagos es parte de la coordinación del pool);
    - `pago_motivo_rechazo` y `tiene_comprobante` solo el creador del pool y
      el propio miembro;
    - `telefono` y `mensaje` (PII) solo el creador.

    Fuera de esos casos las claves se omiten por completo — la regla vive acá
    y no en el front ni en cada caller.
    """

    usuario = UsuarioPublicoSerializer(read_only=True)
    monto = serializers.SerializerMethodField()
    tiene_comprobante = serializers.SerializerMethodField()

    CAMPOS_DETALLE = ("pago_estado", "recepcion_confirmada", "monto")
    # Lo ven el creador y el propio miembro: pago y variantes pedidas (talle/color).
    CAMPOS_PAGO_PRIVADOS = ("pago_motivo_rechazo", "tiene_comprobante", "detalle")
    CAMPOS_PII = ("telefono", "mensaje")

    class Meta:
        model = Membership
        fields = (
            "id",
            "usuario",
            "cantidad",
            "telefono",
            "mensaje",
            "pago_estado",
            "pago_motivo_rechazo",
            "tiene_comprobante",
            "recepcion_confirmada",
            "monto",
            "detalle",
        )
        read_only_fields = fields

    def get_monto(self, obj):
        return str(obj.pool.precio_unitario * obj.cantidad)

    def get_tiene_comprobante(self, obj):
        return bool(obj.comprobante)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = self._usuario()
        detalle = self.context.get("exponer_datos_miembros", False) and user is not None
        es_creador = detalle and user.id == instance.pool.creador_id
        es_dueno = detalle and user.id == instance.usuario_id
        ocultar = []
        if not detalle:
            ocultar += self.CAMPOS_DETALLE
        if not (es_creador or es_dueno):
            ocultar += self.CAMPOS_PAGO_PRIVADOS
        if not es_creador:
            ocultar += self.CAMPOS_PII
        for campo in ocultar:
            data.pop(campo, None)
        return data

    def _usuario(self):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        return user


class MensajeSerializer(serializers.ModelSerializer):
    """Un mensaje del chat. Contrato: {id, autor, texto, creado}.

    Sirve para leer y para escribir: el texto se normaliza (strip) y se valida
    acá — vacío o >1000 → 400. `autor` reusa la forma pública de usuario del
    resto de la API.
    """

    autor = UsuarioPublicoSerializer(read_only=True)
    texto = serializers.CharField(
        max_length=1000,
        error_messages={
            "required": "El texto es obligatorio.",
            "blank": "El texto no puede estar vacío.",
            "null": "El texto no puede estar vacío.",
            "invalid": "El texto no es válido.",
            "max_length": "El texto no puede superar los {max_length} caracteres.",
        },
    )

    class Meta:
        model = Mensaje
        fields = ("id", "autor", "texto", "creado")
        read_only_fields = ("id", "autor", "creado")


class PoolSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    # Categoría principal (Higiene personal) cuando el pool está en una subcategoría
    # (Perfume): las tarjetas muestran las dos, como el inicio y los filtros.
    categoria_padre_nombre = serializers.CharField(
        source="categoria.padre.nombre", read_only=True, default=None
    )
    creador = UsuarioPublicoSerializer(read_only=True)
    disponible = serializers.IntegerField(read_only=True)
    integrantes = serializers.SerializerMethodField()
    mi_cantidad = serializers.SerializerMethodField()
    imagenes = PoolImageSerializer(many=True, read_only=True)
    miembros = MembershipSerializer(source="memberships", many=True, read_only=True)
    analisis_enlace = serializers.SerializerMethodField()
    # Dato calculado (unitario × cantidad total): no se guarda ni se edita.
    precio_total = serializers.SerializerMethodField()
    # Variantes que ofrece el pool (Talle/Color…). DRF ya parsea el JSON que llega
    # como texto en multipart ("Crear pool" manda FormData por las imágenes).
    atributos = serializers.JSONField(required=False)
    # Objetivo opcional por combinación: [{"atributos": {"Talle": "S"}, "cantidad": 6}].
    reparto = serializers.JSONField(required=False)
    # Cupo restante agregado (sin detalle de cada miembro) para el comprador.
    cupos_variantes = serializers.SerializerMethodField()
    # Las mismas variantes como lista ordenada como la categoría (jsonb no guarda
    # el orden de las claves): [{"nombre": "Talle", "opciones": ["S", "M"]}, ...].
    variantes = serializers.SerializerMethodField()

    class Meta:
        model = Pool
        fields = (
            "id",
            "titulo",
            "nombre_producto",
            "descripcion",
            "categoria",
            "categoria_nombre",
            "categoria_padre_nombre",
            "enlace",
            "analisis_enlace",
            "precio_unitario",
            "cantidad_total",
            "precio_total",
            "cantidad_creador",
            "min_por_integrante",
            "fecha_caducidad",
            "tipo_pago",
            "atributos",
            "reparto",
            "cupos_variantes",
            "variantes",
            "alias_cbu",
            "titular_cuenta",
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

    # Datos de la cuenta para transferir: solo para el creador y los integrantes.
    CAMPOS_COBRO = ("alias_cbu", "titular_cuenta")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get("mi_cantidad") is None:  # None = no participa del pool
            for campo in self.CAMPOS_COBRO:
                data.pop(campo, None)
        return data

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

    def validate_enlace(self, value):
        # Mismo criterio que la vista previa: sin utm_*, tracking_id ni fragmento.
        return limpiar_enlace(value)

    def get_cupos_variantes(self, obj):
        # Solo en el detalle: en listados no se necesita y sería una consulta extra.
        if not self.context.get("exponer_datos_miembros"):
            return {}
        request = self.context.get("request")
        return cupos_por_variante(obj, getattr(request, "user", None))

    def get_variantes(self, obj):
        return [
            {"nombre": nombre, "opciones": opciones}
            for nombre, opciones in variantes_vigentes(obj).items()
        ]

    def get_precio_total(self, obj):
        return f"{obj.precio_unitario * obj.cantidad_total:.2f}"

    def get_analisis_enlace(self, obj):
        """Análisis propio del enlace, o None cuando el pool no tiene enlace.

        El conteo de uso sale del lote (`conteos_dominio` en el contexto) para no
        consultar por pool en listados; en serializaciones sueltas se cuenta una
        vez para el único enlace.
        """
        if not obj.enlace:
            return None
        conteos = self.context.get("conteos_dominio")
        if conteos is None:
            conteos = conteos_dominio([obj.enlace])
        return analizar_enlace(obj.enlace, uso=conteos.get(dominio_de(obj.enlace), 0))

    INMUTABLES_CON_MIEMBROS = (
        "atributos",
        "reparto",
        "categoria",
        "titulo",
        "nombre_producto",
        "precio_unitario",
        "cantidad_total",
        "direccion",
        "ciudad",
    )

    def validate(self, attrs):
        instance = self.instance
        if "atributos" in attrs or "categoria" in attrs:
            categoria = attrs.get("categoria", getattr(instance, "categoria", None))
            atributos = attrs.get("atributos", getattr(instance, "atributos", {}))
            attrs["atributos"] = validar_atributos_pool(categoria, atributos)
        if "reparto" in attrs or "atributos" in attrs or "cantidad_total" in attrs:
            if instance is not None and "atributos" not in attrs:
                atributos_pool = variantes_vigentes(instance)
            else:
                atributos_pool = attrs.get("atributos", getattr(instance, "atributos", {}))
            total_reparto = attrs.get(
                "cantidad_total", getattr(instance, "cantidad_total", None)
            )
            reparto = attrs.get("reparto", getattr(instance, "reparto", []))
            attrs["reparto"] = normalizar_reparto(atributos_pool, reparto, total_reparto)
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


class EnlaceProductoSerializer(serializers.Serializer):
    # 2000: los links de MercadoLibre y Amazon con parámetros pasan de 200.
    enlace = serializers.URLField(
        max_length=LARGO_ENLACE,
        error_messages={
            "required": "Pegá el enlace del producto.",
            "blank": "Pegá el enlace del producto.",
            "invalid": "Ingresá un enlace válido (https://…).",
            "max_length": "El enlace no puede superar los {max_length} caracteres.",
        },
    )

    def validate_enlace(self, value):
        return limpiar_enlace(value)


class CantidadSerializer(serializers.Serializer):
    cantidad = serializers.IntegerField(min_value=1)
    # Reparto por variante; se valida contra el pool en la vista (validar_detalle).
    detalle = serializers.JSONField(required=False)


class UnionSerializer(serializers.Serializer):
    """Payload de unirse: `{cantidad, telefono, mensaje}`. Valida en el boundary."""

    TELEFONO_PATRON = re.compile(r"\+?[\d\s\-().]{6,30}")

    cantidad = serializers.IntegerField(min_value=1)
    detalle = serializers.JSONField(required=False)
    telefono = serializers.CharField(
        error_messages={
            "required": "El teléfono es obligatorio.",
            "blank": "El teléfono es obligatorio.",
        }
    )
    mensaje = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_telefono(self, value):
        if len(value) > 30:
            raise serializers.ValidationError("El teléfono no puede superar los 30 caracteres.")
        digitos = sum(c.isdigit() for c in value)
        if not self.TELEFONO_PATRON.fullmatch(value) or digitos < 6:
            raise serializers.ValidationError("El teléfono no es válido.")
        return value

    def validate_mensaje(self, value):
        valor = value.strip()
        if len(valor) > 500:
            raise serializers.ValidationError("El mensaje no puede superar los 500 caracteres.")
        return valor


class ComprobanteSerializer(serializers.Serializer):
    """Payload de subir comprobante: un JPEG, PNG o PDF de hasta 5 MB."""

    MAX_BYTES = 5 * 1024 * 1024

    comprobante = serializers.FileField(
        error_messages={
            "required": "El comprobante es obligatorio.",
            "empty": "El archivo está vacío.",
            "invalid": "El archivo no es válido.",
        }
    )

    def validate_comprobante(self, value):
        if value.size > self.MAX_BYTES:
            raise serializers.ValidationError("El comprobante no puede superar los 5 MB.")
        if not (self._es_pdf(value) or self._es_imagen(value)):
            raise serializers.ValidationError("Solo se aceptan comprobantes JPEG, PNG o PDF.")
        value.seek(0)
        return value

    @staticmethod
    def _es_pdf(value):
        value.seek(0)
        return value.read(5) == b"%PDF-"

    @staticmethod
    def _es_imagen(value):
        value.seek(0)
        try:
            with Image.open(value) as imagen:
                formato = imagen.format
                imagen.verify()
        except (OSError, SyntaxError, ValueError, Image.DecompressionBombError):
            return False
        return formato in ("JPEG", "PNG")


class RevisionPagoSerializer(serializers.Serializer):
    """Payload de revisar un pago: `{accion: confirmar|rechazar, motivo}`."""

    accion = serializers.ChoiceField(
        choices=("confirmar", "rechazar"),
        error_messages={"invalid_choice": "La acción debe ser confirmar o rechazar."},
    )
    motivo = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_motivo(self, value):
        valor = value.strip()
        if len(valor) > 255:
            raise serializers.ValidationError("El motivo no puede superar los 255 caracteres.")
        return valor

    def validate(self, attrs):
        if attrs["accion"] == "rechazar" and not attrs.get("motivo"):
            raise serializers.ValidationError({"motivo": "Indicá el motivo del rechazo."})
        return attrs


class VotoSerializer(serializers.Serializer):
    acepta = serializers.BooleanField()


class VotoEliminacionSerializer(serializers.ModelSerializer):
    usuario = UsuarioPublicoSerializer(read_only=True)

    class Meta:
        model = VotoEliminacion
        fields = ("usuario", "acepta")
        read_only_fields = fields


class SolicitudEliminacionSerializer(serializers.ModelSerializer):
    votos = VotoEliminacionSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    aceptaron = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudEliminacion
        fields = ("id", "estado", "votos", "total", "aceptaron")

    def get_total(self, obj):
        return obj.pool.memberships.count()

    def get_aceptaron(self, obj):
        return obj.votos.filter(acepta=True).count()


class EventoPoolSerializer(serializers.ModelSerializer):
    """Un evento del historial del pool. Contrato: {tipo, actor, datos, creado}.

    `actor` nulo es el sistema. `datos` solo trae lo que el texto del evento
    necesita: nunca PII del miembro (regla en los hooks que registran).
    """

    actor = UsuarioPublicoSerializer(read_only=True)

    class Meta:
        model = EventoPool
        fields = ("tipo", "actor", "datos", "creado")
        read_only_fields = fields


class ResenaSerializer(serializers.ModelSerializer):
    """Una reseña entre participantes. Contrato de lectura:
    {id, pool, pool_titulo, autor, destinatario, puntaje, comentario, rol, creado}.

    `rol` es el papel del destinatario en ese pool (administrador/participante).
    Para escribir se manda `{destinatario, puntaje, comentario}`; el pool y el
    autor los pone la vista. Las reglas de dominio (pool finalizado, ambos
    participantes, sin autocalificarse ni repetir) se validan acá.
    """

    autor = UsuarioPublicoSerializer(read_only=True)
    pool_titulo = serializers.CharField(source="pool.titulo", read_only=True)
    rol = serializers.SerializerMethodField()
    puntaje = serializers.IntegerField(
        min_value=1,
        max_value=5,
        error_messages={
            "required": "El puntaje es obligatorio.",
            "invalid": "El puntaje debe ser un número del 1 al 5.",
            "min_value": "El puntaje debe ser un número del 1 al 5.",
            "max_value": "El puntaje debe ser un número del 1 al 5.",
        },
    )
    comentario = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = Resena
        fields = (
            "id",
            "pool",
            "pool_titulo",
            "autor",
            "destinatario",
            "puntaje",
            "comentario",
            "rol",
            "creado",
        )
        read_only_fields = ("id", "pool", "pool_titulo", "autor", "rol", "creado")
        extra_kwargs = {
            "destinatario": {
                "error_messages": {
                    "required": "Elegí a quién calificar.",
                    "null": "Elegí a quién calificar.",
                    "does_not_exist": "La persona elegida no existe.",
                    "incorrect_type": "La persona elegida no es válida.",
                }
            }
        }

    def get_rol(self, obj):
        return "administrador" if obj.destinatario_id == obj.pool.creador_id else "participante"

    def validate_comentario(self, value):
        valor = value.strip()
        if len(valor) > 500:
            raise serializers.ValidationError("El comentario no puede superar los 500 caracteres.")
        return valor

    def validate(self, attrs):
        pool = self.context["pool"]
        autor = self.context["request"].user
        destinatario = attrs["destinatario"]
        if pool.estado != Pool.Estado.FINALIZADO:
            raise serializers.ValidationError(
                {"detail": "Solo se puede calificar cuando el pool finalizó."}
            )
        if destinatario.id == autor.id:
            raise serializers.ValidationError({"destinatario": "No podés calificarte a vos mismo."})
        if not pool.es_participante(destinatario):
            raise serializers.ValidationError(
                {"destinatario": "Solo podés calificar a participantes de este pool."}
            )
        if Resena.objects.filter(pool=pool, autor=autor, destinatario=destinatario).exists():
            raise serializers.ValidationError(
                {"destinatario": "Ya calificaste a esta persona en este pool."}
            )
        return attrs
