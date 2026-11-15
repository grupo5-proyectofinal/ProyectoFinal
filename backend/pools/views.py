from datetime import timedelta

from django.db import transaction
from django.db.models import Count, F, Prefetch, Q, Sum
from django.db.models.functions import Coalesce
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import (
    MethodNotAllowed,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (
    SAFE_METHODS,
    AllowAny,
    IsAdminUser,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from notificaciones.servicio import (
    confirmar_union,
    notificar_baja_resuelta,
    notificar_baja_solicitada,
    notificar_datos_cobro,
    notificar_devolucion,
    notificar_devolucion_por_cancelacion,
    notificar_estado,
    notificar_extension,
    notificar_mensaje,
    notificar_pago_enviado,
    notificar_pago_revisado,
    notificar_recepcion,
    notificar_union,
)

from .confianza import analizar_enlace, conteos_dominio, dominio_de
from .geocoding import geocodificar
from .models import (
    DIAS_RECONFIRMACION,
    AtributoCategoria,
    Category,
    EventoPool,
    Membership,
    Pool,
    PoolImage,
    SolicitudBaja,
    crear_devolucion,
    expirar_vencidos_perezoso,
    registrar_evento,
)
from .producto import MENSAJES_MOTIVO, imagen_de_url, leer_enlace
from .serializers import (
    AtributosCategoriaSerializer,
    CantidadSerializer,
    CategorySerializer,
    ComprobanteSerializer,
    EnlaceProductoSerializer,
    EventoPoolSerializer,
    ExtensionSerializer,
    MembershipSerializer,
    MensajeSerializer,
    PedidoBajaSerializer,
    PoolImageSerializer,
    PoolSerializer,
    ReconfirmacionSerializer,
    ResenaSerializer,
    ResolverBajaSerializer,
    RevisionPagoSerializer,
    SolicitudBajaSerializer,
    UnionSerializer,
)
from .variantes import (
    mismo_detalle,
    validar_cupo_variantes,
    validar_detalle,
    variantes_vigentes,
)

MAX_IMAGENES = 10

# Chat por polling: el cliente pide "lo nuevo" con `desde` = último id que vio.
MENSAJES_LIMITE = 50
MENSAJES_LIMITE_MAX = 200
# El chat nace en "listo" y se puede escribir hasta que el pool finaliza: después queda solo lectura.
ESTADOS_CON_CHAT = (Pool.Estado.LISTO, Pool.Estado.EN_CURSO)


def _entero(valor, default):
    """Entero de un query param, o `default` si falta o no es numérico."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        return default


# Con el pago enviado o confirmado la membresía queda fija: cambiar la cantidad
# (o irse) invalidaría el monto ya transferido.
PAGOS_EN_CURSO = (Membership.PagoEstado.ENVIADO, Membership.PagoEstado.CONFIRMADO)

# Acciones que devuelven un pool completo (no listados): habilitan exponer los
# datos PII del miembro al creador (regla en MembershipSerializer).
ACCIONES_DETALLE = {
    "retrieve",
    "confirmar",
    "finalizar",
    "cancelar",
    "mi_membresia",
    "extender",
    "reconfirmar",
}


class PrevisualizarEnlaceThrottle(UserRateThrottle):
    scope = "previsualizar_enlace"


class PoolFilter(filters.FilterSet):
    q = filters.CharFilter(method="filtrar_q")
    categoria = filters.NumberFilter(method="filtrar_categoria")
    precio_min = filters.NumberFilter(field_name="precio_unitario", lookup_expr="gte")
    precio_max = filters.NumberFilter(field_name="precio_unitario", lookup_expr="lte")
    ciudad = filters.CharFilter(field_name="ciudad", lookup_expr="icontains")
    estado = filters.CharFilter(field_name="estado")
    creador = filters.NumberFilter(field_name="creador_id")

    class Meta:
        model = Pool
        fields = ()

    def filtrar_categoria(self, queryset, name, value):
        # "Ropa" incluye Remera, Buzo, Pantalón…: los pools viven en la subcategoría.
        return queryset.filter(Q(categoria_id=value) | Q(categoria__padre_id=value))

    def filtrar_q(self, queryset, name, value):
        return queryset.filter(
            Q(titulo__icontains=value)
            | Q(nombre_producto__icontains=value)
            | Q(descripcion__icontains=value)
        )


class PoolViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = PoolSerializer
    filterset_class = PoolFilter
    filter_backends = (filters.DjangoFilterBackend, OrderingFilter)
    ordering_fields = (
        "fecha_caducidad",
        "precio_unitario",
        "vistas",
        "integrantes",
        "restante",
    )
    ordering = ("-creado",)

    def get_permissions(self):
        # El listado es público; el detalle de un pool pide sesión.
        if self.action == "retrieve":
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        expirar_vencidos_perezoso()
        return (
            Pool.objects.select_related("categoria", "categoria__padre", "creador")
            .prefetch_related(
                "imagenes",
                # `variantes` del serializer: atributos de la categoría y de su padre.
                "categoria__atributos",
                "categoria__padre__atributos",
                Prefetch(
                    "memberships",
                    queryset=Membership.objects.select_related("usuario", "pool"),
                ),
            )
            .annotate(
                integrantes=Count("memberships"),
                # Unidades que faltan para completar (equivale a `disponible`).
                # Ordenar por `restante` ascendente = "cerca de completarse":
                # `integrantes` cuenta personas e ignora cuánto reservó cada una.
                restante=(
                    F("cantidad_total")
                    - F("cantidad_creador")
                    - Coalesce(Sum("memberships__cantidad"), 0)
                ),
            )
            .order_by("-creado")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["exponer_datos_miembros"] = self.action in ACCIONES_DETALLE
        context["conteos_dominio"] = getattr(self, "_conteos_dominio", None)
        return context

    def paginate_queryset(self, queryset):
        """Anota el lote a serializar con los conteos de dominio del enlace.

        El análisis de cada pool necesita la cantidad de pools con el mismo
        dominio; calcularla acá la deja en una sola consulta por listado (sin
        N+1). En acciones de detalle no se llama: el serializer cuenta su único
        enlace.
        """
        page = super().paginate_queryset(queryset)
        objetos = page if page is not None else queryset
        self._conteos_dominio = conteos_dominio(pool.enlace for pool in objetos)
        return page

    def perform_create(self, serializer):
        pool = serializer.save(creador=self.request.user)
        self._refrescar_coords(pool)
        self._imagen_desde_enlace(pool)
        registrar_evento(pool, EventoPool.Tipo.CREADO, actor=self.request.user)
        if pool.actualizar_estado():
            self._guardar_estado(pool)

    # ponytail: sin lock acá; usar _bloqueado(pk) si hubiera uso concurrente real
    def perform_update(self, serializer):
        anterior = (serializer.instance.direccion, serializer.instance.ciudad)
        cambios = self._campos_cambiados(serializer)
        pool = serializer.save()
        self._refrescar_coords(pool, anterior)
        if cambios:
            registrar_evento(
                pool, EventoPool.Tipo.EDICION, actor=self.request.user, datos={"campos": cambios}
            )
        if set(cambios) & set(PoolSerializer.CAMPOS_COBRO):
            # Quien ya copió el alias viejo tiene que enterarse antes de transferir.
            notificar_datos_cobro(pool, actor=self.request.user)
        if pool.actualizar_estado():
            self._guardar_estado(pool)

    def _guardar_estado(self, pool):
        """Persiste el estado recalculado y avisa a los demás participantes."""
        pool.save(update_fields=["estado"])
        notificar_estado(pool, pool.estado, actor=self.request.user)

    @staticmethod
    def _campos_cambiados(serializer):
        """Campos que el update realmente cambia: editar sin cambios no deja evento."""
        return sorted(
            campo
            for campo, valor in serializer.validated_data.items()
            if getattr(serializer.instance, campo) != valor
        )

    def _imagen_desde_enlace(self, pool):
        """Guarda como portada la imagen que la vista previa del enlace encontró.

        El front manda `imagen_url` (la del producto, no se puede subir desde el
        navegador por CORS). Fail-soft: si no se puede bajar, el pool se crea igual.
        """
        url = self.request.data.get("imagen_url")
        if not isinstance(url, str) or not url.strip():
            return
        archivo = imagen_de_url(url.strip())
        if archivo is not None:
            PoolImage.objects.create(pool=pool, imagen=archivo, orden=0)

    def _refrescar_coords(self, pool, anterior=None):
        """Geocodifica y persiste coords si la dirección cambió o faltan coords."""
        cambio_direccion = anterior is None or anterior != (pool.direccion, pool.ciudad)
        if not cambio_direccion and pool.latitud is not None and pool.longitud is not None:
            return
        coords = geocodificar(pool.direccion, pool.ciudad)
        pool.latitud, pool.longitud = coords if coords else (None, None)
        pool.save(update_fields=["latitud", "longitud"])

    def _bloqueado(self, pk):
        # Sin annotate: FOR UPDATE no admite GROUP BY.
        return get_object_or_404(Pool.objects.select_for_update(of=("self",)), pk=pk)

    def retrieve(self, request, *args, **kwargs):
        pool = self.get_object()
        Pool.objects.filter(pk=pool.pk).update(vistas=F("vistas") + 1)
        pool.vistas += 1
        return Response(self.get_serializer(pool).data)

    def update(self, request, *args, **kwargs):
        # PATCH pasa por partial_update (que valida el estado) y llega acá con partial.
        if not kwargs.get("partial"):
            pool = self.get_object()
            self._solo_creador(pool)
            self._solo_abierto(pool)
        return super().update(request, *args, **kwargs)

    # Los datos de cobro se cargan cuando el pool se completa (para que transfieran),
    # así que se pueden editar fuera de "abierto" mientras haya pagos por hacer.
    def partial_update(self, request, *args, **kwargs):
        pool = self.get_object()
        self._solo_creador(pool)
        solo_cobro = bool(request.data) and set(request.data) <= set(PoolSerializer.CAMPOS_COBRO)
        if solo_cobro:
            if pool.estado not in (Pool.Estado.ABIERTO, Pool.Estado.LISTO):
                raise ValidationError("Los datos de cobro se editan hasta que se confirma el pedido.")
        else:
            self._solo_abierto(pool)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Los pools no se eliminan: el creador los cancela y queda el historial.
        raise MethodNotAllowed(request.method)

    def _solo_creador(self, pool):
        if pool.creador_id != self.request.user.id:
            raise PermissionDenied("Solo el creador puede hacer esto.")

    def _solo_abierto(self, pool):
        if pool.estado != Pool.Estado.ABIERTO:
            raise ValidationError("Solo se puede editar un pool abierto.")

    def _es_participante(self, pool, mensaje="Solo los integrantes pueden ver esto."):
        if pool.creador_id == self.request.user.id:
            return
        if not pool.memberships.filter(usuario=self.request.user).exists():
            raise PermissionDenied(mensaje)

    def _rechazar_vencido(self, pool):
        """Bajo lock: corta la acción si el pool venció (la cancelación es perezosa)."""
        if pool.vencio():
            raise ValidationError("El pool está vencido.")

    def _rechazar_con_pago(self, membership):
        if membership.pago_estado in PAGOS_EN_CURSO:
            raise ValidationError(
                "Ya enviaste el pago: no podés cambiar tu participación. "
                "Hablalo con el administrador del pool."
            )

    def _mi_membresia(self, pool):
        membership = pool.memberships.filter(usuario=self.request.user).first()
        if membership is None:
            raise PermissionDenied("Solo los integrantes pueden hacer esto.")
        return membership

    def _membresia_detalle(self, membership):
        context = {"request": self.request, "exponer_datos_miembros": True}
        return Response(MembershipSerializer(membership, context=context).data)

    def _disponible_conmigo(self, pool, membership):
        return pool.disponible + membership.cantidad

    def _validar_cantidad(self, pool, cantidad, disponible):
        if cantidad < pool.min_por_integrante:
            raise ValidationError(
                {"cantidad": f"El mínimo por integrante es {pool.min_por_integrante}."}
            )
        if cantidad > disponible:
            raise ValidationError({"cantidad": f"Solo quedan {disponible} disponibles."})

    def _paginar(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(
        detail=False,
        methods=("post",),
        url_path="previsualizar-enlace",
        permission_classes=(IsAuthenticated,),
        throttle_classes=(PrevisualizarEnlaceThrottle,),
    )
    def previsualizar_enlace(self, request):
        """Nombre, precio e imagen del producto que publica el enlace de la tienda."""
        serializer = EnlaceProductoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enlace = serializer.validated_data["enlace"]  # ya sin tracking (limpiar_enlace)
        # Las validaciones del sitio se muestran antes de publicar, aunque la tienda
        # no deje leer los datos del producto (Iteración 1: "análisis de URL").
        uso = conteos_dominio([enlace]).get(dominio_de(enlace), 0)
        analisis = analizar_enlace(enlace, uso=uso)
        lectura = leer_enlace(enlace)
        if lectura["datos"] is None:
            motivo = lectura["motivo"]
            return Response(
                {
                    "encontrado": False,
                    "motivo": motivo,
                    "detail": MENSAJES_MOTIVO.get(motivo, MENSAJES_MOTIVO["sin_datos"]),
                    "enlace": enlace,
                    "analisis": analisis,
                }
            )
        return Response(
            {
                "encontrado": True,
                **lectura["datos"],
                "aviso": lectura["aviso"],
                "enlace": enlace,
                "analisis": analisis,
            }
        )

    @action(detail=False, methods=("get",), permission_classes=(IsAuthenticated,))
    def mios(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return self._paginar(queryset.filter(creador=request.user))

    @action(detail=False, methods=("get",), permission_classes=(IsAuthenticated,))
    def unidos(self, request):
        # pk__in evita reusar el join de memberships al anotar integrantes.
        queryset = self.filter_queryset(self.get_queryset())
        return self._paginar(
            queryset.filter(
                pk__in=Membership.objects.filter(usuario=request.user).values("pool")
            )
        )

    @action(detail=True, methods=("post",))
    def unirse(self, request, pk=None):
        with transaction.atomic():
            pool = self._bloqueado(pk)
            self._rechazar_vencido(pool)
            if pool.estado != Pool.Estado.ABIERTO:
                raise ValidationError("El pool no está abierto.")
            if pool.creador_id == request.user.id:
                raise ValidationError("El creador ya participa del pool.")
            if pool.memberships.filter(usuario=request.user).exists():
                raise ValidationError("Ya estás en este pool.")
            serializer = UnionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            cantidad = serializer.validated_data["cantidad"]
            detalle = validar_detalle(
                variantes_vigentes(pool), serializer.validated_data.get("detalle"), cantidad
            )
            telefono = serializer.validated_data["telefono"]
            mensaje = serializer.validated_data.get("mensaje", "")
            disponible = pool.disponible
            self._validar_cantidad(pool, cantidad, disponible)
            validar_cupo_variantes(pool, detalle)
            membership = Membership.objects.create(
                pool=pool,
                usuario=request.user,
                cantidad=cantidad,
                detalle=detalle,
                telefono=telefono,
                mensaje=mensaje,
            )
            registrar_evento(
                pool, EventoPool.Tipo.UNION, actor=request.user, datos={"cantidad": cantidad}
            )
            notificar_union(pool, request.user, cantidad)
            confirmar_union(pool, request.user, cantidad)
            if pool.actualizar_estado(disponible - cantidad):
                self._guardar_estado(pool)
        return Response(
            MembershipSerializer(membership, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=("delete",))
    def salir(self, request, pk=None):
        with transaction.atomic():
            pool = self._bloqueado(pk)
            self._rechazar_vencido(pool)
            if pool.estado not in (Pool.Estado.ABIERTO, Pool.Estado.LISTO):
                raise ValidationError("No se puede salir en este estado.")
            membership = pool.memberships.filter(usuario=request.user).first()
            if membership is None:
                raise ValidationError("No estás en este pool.")
            self._rechazar_con_pago(membership)
            disponible = pool.disponible + membership.cantidad
            cantidad = membership.cantidad
            membership.delete()
            registrar_evento(
                pool, EventoPool.Tipo.SALIDA, actor=request.user, datos={"cantidad": cantidad}
            )
            if pool.actualizar_estado(disponible):
                self._guardar_estado(pool)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=("patch",), url_path="mi-membresia")
    def mi_membresia(self, request, pk=None):
        with transaction.atomic():
            pool = self._bloqueado(pk)
            self._rechazar_vencido(pool)
            if pool.estado not in (Pool.Estado.ABIERTO, Pool.Estado.LISTO):
                raise ValidationError("No se puede editar en este estado.")
            membership = pool.memberships.filter(usuario=request.user).first()
            if membership is None:
                raise ValidationError("No estás en este pool.")
            self._rechazar_con_pago(membership)
            serializer = CantidadSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            nueva = serializer.validated_data["cantidad"]
            disponible = self._disponible_conmigo(pool, membership)
            self._validar_cantidad(pool, nueva, disponible)
            detalle = validar_detalle(
                variantes_vigentes(pool), serializer.validated_data.get("detalle"), nueva
            )
            validar_cupo_variantes(pool, detalle, excluir=membership)
            if nueva != membership.cantidad:
                registrar_evento(
                    pool,
                    EventoPool.Tipo.CANTIDAD,
                    actor=request.user,
                    datos={"antes": membership.cantidad, "despues": nueva},
                )
            if nueva == membership.cantidad and not mismo_detalle(detalle, membership.detalle):
                # Mismo total con otras variantes (M·Negro → L·Negro): evento propio.
                registrar_evento(
                    pool, EventoPool.Tipo.CANTIDAD, actor=request.user,
                    datos={"antes": nueva, "despues": nueva, "variantes": True},
                )

            membership.cantidad = nueva
            membership.detalle = detalle
            membership.save(update_fields=["cantidad", "detalle"])
            if pool.actualizar_estado(disponible - nueva):
                self._guardar_estado(pool)
            actualizado = self.get_queryset().get(pk=pool.pk)
        return Response(self.get_serializer(actualizado).data)

    @action(detail=True, methods=("get",), permission_classes=(IsAuthenticated,))
    def historial(self, request, pk=None):
        pool = self.get_object()
        self._es_participante(pool)
        eventos = pool.eventos.select_related("actor")
        paginador = PageNumberPagination()
        pagina = paginador.paginate_queryset(eventos, request, view=self)
        return paginador.get_paginated_response(EventoPoolSerializer(pagina, many=True).data)

    @action(
        detail=True,
        methods=("get", "post"),
        url_path="mensajes",
        permission_classes=(IsAuthenticated,),
    )
    def mensajes(self, request, pk=None):
        pool = self.get_object()
        self._es_participante(pool, "Solo los integrantes pueden acceder al chat.")
        if request.method == "POST":
            return self._enviar_mensaje(request, pool)
        return self._listar_mensajes(request, pool)

    def _listar_mensajes(self, request, pool):
        """Lo nuevo después de `desde`, ascendente y acotado a `limit`.

        Pide `limit + 1` filas para saber si quedó algo sin contar.
        """
        desde = _entero(request.query_params.get("desde"), 0)
        limite = _entero(request.query_params.get("limit"), MENSAJES_LIMITE)
        limite = max(1, min(limite, MENSAJES_LIMITE_MAX))
        nuevos = pool.mensajes.select_related("autor").filter(id__gt=desde)
        lote = list(nuevos[: limite + 1])
        return Response(
            {
                "results": MensajeSerializer(lote[:limite], many=True).data,
                "hay_mas": len(lote) > limite,
            }
        )

    def _enviar_mensaje(self, request, pool):
        if pool.estado not in ESTADOS_CON_CHAT:
            raise ValidationError(
                f"No se pueden enviar mensajes en el estado '{pool.estado}'."
            )
        serializer = MensajeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mensaje = serializer.save(pool=pool, autor=request.user)
        notificar_mensaje(mensaje)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=("get", "post"),
        url_path="resenas",
        permission_classes=(IsAuthenticated,),
    )
    def resenas(self, request, pk=None):
        """GET: las reseñas que el usuario ya dejó en este pool. POST: califica a alguien."""
        pool = self.get_object()
        self._es_participante(pool, "Solo los integrantes pueden calificar.")
        if request.method == "GET":
            propias = pool.resenas.filter(autor=request.user).select_related("autor", "pool")
            return Response({"results": ResenaSerializer(propias, many=True).data})
        serializer = ResenaSerializer(data=request.data, context={"request": request, "pool": pool})
        serializer.is_valid(raise_exception=True)
        serializer.save(pool=pool, autor=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _transicion(self, pool, desde, hacia, validar=None, despues=None):
        """Cambia el estado con el pool bloqueado: un pago confirmado o una salida
        en paralelo no pueden colarse entre la validación y el cambio."""
        with transaction.atomic():
            pool = self._bloqueado(pool.pk)
            self._solo_creador(pool)
            if pool.estado not in desde:
                raise ValidationError(f"Transición inválida desde el estado '{pool.estado}'.")
            if validar is not None:
                validar(pool)
            pool.estado = hacia
            pool.save(update_fields=["estado"])
            registrar_evento(
                pool, EventoPool.Tipo.ESTADO, actor=self.request.user, datos={"estado": hacia}
            )
            notificar_estado(pool, hacia, actor=self.request.user)
            if despues is not None:
                despues(pool)
        return Response(self.get_serializer(self.get_object()).data)

    def _devoluciones_al_cancelar(self, pool):
        """Al cancelar, a quienes ya pagaron se les debe la devolución: se deja registrada para
        que no dependa de que alguien se acuerde. Los pedidos de baja pendientes se aprueban."""
        ahora = timezone.now()
        pendientes = list(pool.solicitudes_baja.filter(estado=SolicitudBaja.Estado.PENDIENTE))
        for solicitud in pendientes:
            solicitud.estado = SolicitudBaja.Estado.APROBADA
            solicitud.resuelto = ahora
            solicitud.save(update_fields=["estado", "resuelto"])
            notificar_devolucion_por_cancelacion(pool, solicitud)
        con_solicitud = set(
            pool.solicitudes_baja.exclude(estado=SolicitudBaja.Estado.RECHAZADA).values_list(
                "usuario_id", flat=True
            )
        )
        nuevas = 0
        for membership in pool.memberships.select_related("usuario"):
            if membership.pago_realizado and membership.usuario_id not in con_solicitud:
                solicitud = crear_devolucion(pool, membership, "El pool se canceló.")
                notificar_devolucion_por_cancelacion(pool, solicitud)
                nuevas += 1
        if pendientes or nuevas:
            registrar_evento(
                pool,
                EventoPool.Tipo.DEVOLUCION,
                actor=self.request.user,
                datos={"cancelacion": True, "cantidad": len(pendientes) + nuevas},
            )

    def _cerrar_bajas_al_finalizar(self, pool):
        """Un pedido de baja pendiente no puede quedar sin respuesta cuando el pool termina."""
        for solicitud in pool.solicitudes_baja.filter(estado=SolicitudBaja.Estado.PENDIENTE):
            solicitud.estado = SolicitudBaja.Estado.RECHAZADA
            solicitud.motivo_rechazo = "El pool finalizó."
            solicitud.resuelto = timezone.now()
            solicitud.save(update_fields=["estado", "motivo_rechazo", "resuelto"])
            notificar_baja_resuelta(pool, solicitud)

    @staticmethod
    def _sin_pagos_pendientes(pool):
        faltan = pool.pagos_pendientes().count()
        if faltan:
            raise ValidationError(f"Faltan confirmar {faltan} pago{'s' if faltan != 1 else ''}.")

    @staticmethod
    def _sin_recepciones_pendientes(pool):
        faltan = pool.recepciones_pendientes().count()
        if faltan:
            raise ValidationError(
                f"Faltan {faltan} participante{'s' if faltan != 1 else ''} "
                "por confirmar la recepción del producto."
            )

    @action(detail=True, methods=("post",))
    def confirmar(self, request, pk=None):
        return self._transicion(
            self.get_object(),
            (Pool.Estado.LISTO,),
            Pool.Estado.EN_CURSO,
            validar=self._sin_pagos_pendientes,
        )

    @action(detail=True, methods=("post",))
    def finalizar(self, request, pk=None):
        return self._transicion(
            self.get_object(),
            (Pool.Estado.EN_CURSO,),
            Pool.Estado.FINALIZADO,
            validar=self._sin_recepciones_pendientes,
            despues=self._cerrar_bajas_al_finalizar,
        )

    @action(
        detail=True,
        methods=("post",),
        url_path="comprobante",
        permission_classes=(IsAuthenticated,),
    )
    def comprobante(self, request, pk=None):
        """El miembro sube (o reemplaza) el comprobante de su parte."""
        with transaction.atomic():
            pool = self._bloqueado(pk)
            membership = self._mi_membresia(pool)
            if pool.estado != Pool.Estado.LISTO:
                raise ValidationError("Solo se puede enviar el comprobante con el pool listo.")
            if membership.pago_estado == Membership.PagoEstado.CONFIRMADO:
                raise ValidationError("Tu pago ya fue confirmado.")
            serializer = ComprobanteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            anterior = membership.comprobante.name if membership.comprobante else None
            membership.comprobante = serializer.validated_data["comprobante"]
            membership.pago_estado = Membership.PagoEstado.ENVIADO
            membership.pago_motivo_rechazo = ""
            membership.pago_enviado = timezone.now()
            membership.pago_revisado = None
            membership.save(
                update_fields=[
                    "comprobante",
                    "pago_estado",
                    "pago_motivo_rechazo",
                    "pago_enviado",
                    "pago_revisado",
                ]
            )
            if anterior:
                transaction.on_commit(lambda: membership.comprobante.storage.delete(anterior))
            registrar_evento(pool, EventoPool.Tipo.PAGO_ENVIADO, actor=request.user)
            notificar_pago_enviado(pool, request.user)
        return self._membresia_detalle(membership)

    @action(
        detail=True,
        methods=("get",),
        url_path=r"miembros/(?P<mid>\d+)/comprobante",
        permission_classes=(IsAuthenticated,),
    )
    def ver_comprobante(self, request, pk=None, mid=None):
        """Descarga del comprobante: solo el creador del pool o el propio miembro."""
        pool = self.get_object()
        membership = get_object_or_404(pool.memberships, pk=mid)
        if request.user.id not in (pool.creador_id, membership.usuario_id):
            raise PermissionDenied("No podés ver este comprobante.")
        if not membership.comprobante:
            raise NotFound("No hay comprobante.")
        nombre = membership.comprobante.name.rsplit("/", 1)[-1]
        return FileResponse(membership.comprobante.open("rb"), filename=nombre)

    @action(
        detail=True,
        methods=("post",),
        url_path=r"miembros/(?P<mid>\d+)/pago",
        permission_classes=(IsAuthenticated,),
    )
    def revisar_pago(self, request, pk=None, mid=None):
        """El creador confirma o rechaza (con motivo) el pago de un miembro."""
        with transaction.atomic():
            pool = self._bloqueado(pk)
            self._solo_creador(pool)
            membership = get_object_or_404(
                pool.memberships.select_related("usuario"), pk=mid
            )
            if pool.estado != Pool.Estado.LISTO:
                raise ValidationError("Solo se pueden revisar pagos con el pool listo.")
            if membership.pago_estado != Membership.PagoEstado.ENVIADO:
                raise ValidationError("No hay un comprobante pendiente de revisión.")
            serializer = RevisionPagoSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            confirma = serializer.validated_data["accion"] == "confirmar"
            if confirma:
                membership.pago_estado = Membership.PagoEstado.CONFIRMADO
                membership.pago_motivo_rechazo = ""
            else:
                membership.pago_estado = Membership.PagoEstado.RECHAZADO
                membership.pago_motivo_rechazo = serializer.validated_data["motivo"]
            membership.pago_revisado = timezone.now()
            membership.save(
                update_fields=["pago_estado", "pago_motivo_rechazo", "pago_revisado"]
            )
            registrar_evento(
                pool,
                EventoPool.Tipo.PAGO_CONFIRMADO if confirma else EventoPool.Tipo.PAGO_RECHAZADO,
                actor=request.user,
                datos={"usuario": membership.usuario.username},
            )
            notificar_pago_revisado(
                pool, membership, confirma, membership.pago_motivo_rechazo
            )
        return self._membresia_detalle(membership)

    @action(
        detail=True,
        methods=("post",),
        url_path="recepcion",
        permission_classes=(IsAuthenticated,),
    )
    def recepcion(self, request, pk=None):
        """El miembro confirma que recibió el producto."""
        with transaction.atomic():
            pool = self._bloqueado(pk)
            membership = self._mi_membresia(pool)
            if pool.estado != Pool.Estado.EN_CURSO:
                raise ValidationError(
                    "Solo se puede confirmar la recepción con el pedido en curso."
                )
            if membership.recepcion_confirmada is not None:
                raise ValidationError("Ya confirmaste la recepción.")
            membership.recepcion_confirmada = timezone.now()
            membership.save(update_fields=["recepcion_confirmada"])
            registrar_evento(pool, EventoPool.Tipo.RECEPCION, actor=request.user)
            notificar_recepcion(pool, request.user, pool.recepciones_pendientes().count())
        return self._membresia_detalle(membership)

    @action(
        detail=True,
        methods=("get", "post"),
        url_path="bajas",
        permission_classes=(IsAuthenticated,),
    )
    def bajas(self, request, pk=None):
        """Bajas con devolución. GET: todas (creador) o las propias. POST: pide la baja."""
        if request.method == "POST":
            return self._pedir_baja(request, pk)
        pool = self.get_object()
        solicitudes = pool.solicitudes_baja.select_related("usuario")
        if pool.creador_id != request.user.id:
            solicitudes = solicitudes.filter(usuario=request.user)
        return Response({"results": SolicitudBajaSerializer(solicitudes, many=True).data})

    def _pedir_baja(self, request, pk):
        serializer = PedidoBajaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            pool = self._bloqueado(pk)
            membership = self._mi_membresia(pool)
            if pool.estado not in (Pool.Estado.ABIERTO, Pool.Estado.LISTO, Pool.Estado.EN_CURSO):
                raise ValidationError(
                    "Solo se puede pedir la baja con el pool abierto, listo o en curso."
                )
            if membership.pago_estado not in PAGOS_EN_CURSO:
                raise ValidationError(
                    "Todavía no enviaste tu pago: podés salir del pool directamente."
                )
            if pool.solicitudes_baja.filter(
                usuario=request.user, estado=SolicitudBaja.Estado.PENDIENTE
            ).exists():
                raise ValidationError("Ya tenés un pedido de baja pendiente.")
            solicitud = SolicitudBaja.objects.create(
                pool=pool,
                usuario=request.user,
                cantidad=membership.cantidad,
                monto=pool.precio_unitario * membership.cantidad,
                motivo=serializer.validated_data["motivo"],
            )
            registrar_evento(pool, EventoPool.Tipo.BAJA_SOLICITADA, actor=request.user)
            notificar_baja_solicitada(pool, solicitud)
        return Response(SolicitudBajaSerializer(solicitud).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=("post",),
        url_path=r"bajas/(?P<bid>\d+)/resolver",
        permission_classes=(IsAuthenticated,),
    )
    def resolver_baja(self, request, pk=None, bid=None):
        """El creador aprueba (el integrante sale) o rechaza (con motivo) una baja."""
        serializer = ResolverBajaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        aprueba = serializer.validated_data["accion"] == "aprobar"
        with transaction.atomic():
            pool = self._bloqueado(pk)
            self._solo_creador(pool)
            solicitud = get_object_or_404(
                pool.solicitudes_baja.select_related("usuario"), pk=bid
            )
            if solicitud.estado != SolicitudBaja.Estado.PENDIENTE:
                raise ValidationError("Esta solicitud ya fue resuelta.")
            if pool.estado not in (Pool.Estado.ABIERTO, Pool.Estado.LISTO, Pool.Estado.EN_CURSO):
                raise ValidationError("El pool ya no admite bajas.")
            solicitud.resuelto = timezone.now()
            if aprueba:
                membership = pool.memberships.filter(usuario=solicitud.usuario).first()
                if membership is None:
                    raise ValidationError("El integrante ya no está en el pool.")
                disponible = pool.disponible + membership.cantidad
                membership.delete()
                solicitud.estado = SolicitudBaja.Estado.APROBADA
                registrar_evento(
                    pool,
                    EventoPool.Tipo.SALIDA,
                    actor=solicitud.usuario,
                    datos={"cantidad": solicitud.cantidad, "motivo": "baja"},
                )
                registrar_evento(
                    pool,
                    EventoPool.Tipo.BAJA_APROBADA,
                    actor=request.user,
                    datos={"usuario": solicitud.usuario.username},
                )
                if pool.actualizar_estado(disponible):
                    self._guardar_estado(pool)
            else:
                solicitud.estado = SolicitudBaja.Estado.RECHAZADA
                solicitud.motivo_rechazo = serializer.validated_data["motivo"]
                registrar_evento(
                    pool,
                    EventoPool.Tipo.BAJA_RECHAZADA,
                    actor=request.user,
                    datos={"usuario": solicitud.usuario.username},
                )
            solicitud.save()
            notificar_baja_resuelta(pool, solicitud)
        return Response(SolicitudBajaSerializer(solicitud).data)

    @action(
        detail=True,
        methods=("post",),
        url_path=r"bajas/(?P<bid>\d+)/devolucion",
        permission_classes=(IsAuthenticated,),
    )
    def devolucion_baja(self, request, pk=None, bid=None):
        """Creador: marca la devolución como hecha. Integrante: confirma que la recibió."""
        with transaction.atomic():
            pool = self._bloqueado(pk)
            solicitud = get_object_or_404(
                pool.solicitudes_baja.select_related("usuario"), pk=bid
            )
            if request.user.id == pool.creador_id:
                if solicitud.estado != SolicitudBaja.Estado.APROBADA:
                    raise ValidationError("No hay una devolución pendiente de hacer.")
                solicitud.estado = SolicitudBaja.Estado.DEVUELTA
                solicitud.devuelto = timezone.now()
                realizada = True
            elif request.user.id == solicitud.usuario_id:
                if solicitud.estado != SolicitudBaja.Estado.DEVUELTA:
                    raise ValidationError("El administrador todavía no marcó la devolución.")
                solicitud.estado = SolicitudBaja.Estado.CONFIRMADA
                solicitud.confirmado = timezone.now()
                realizada = False
            else:
                raise PermissionDenied("Solo el administrador o quien pidió la baja.")
            solicitud.save()
            registrar_evento(
                pool,
                EventoPool.Tipo.DEVOLUCION,
                actor=request.user,
                datos={"usuario": solicitud.usuario.username, "realizada": realizada},
            )
            notificar_devolucion(pool, solicitud, realizada)
        return Response(SolicitudBajaSerializer(solicitud).data)

    @action(detail=True, methods=("post",))
    def cancelar(self, request, pk=None):
        return self._transicion(
            self.get_object(),
            (
                Pool.Estado.ABIERTO,
                Pool.Estado.CADUCADO,
                Pool.Estado.RECONFIRMACION,
                Pool.Estado.LISTO,
                Pool.Estado.EN_CURSO,
            ),
            Pool.Estado.CANCELADO,
            despues=self._devoluciones_al_cancelar,
        )

    @action(detail=True, methods=("post",))
    def extender(self, request, pk=None):
        """El creador extiende el plazo de un pool caducado: los participantes reconfirman."""
        serializer = ExtensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            pool = self._bloqueado(pk)
            self._solo_creador(pool)
            if pool.estado != Pool.Estado.CADUCADO:
                raise ValidationError(
                    "Solo se puede extender el plazo de un pool caducado."
                )
            fecha = serializer.validated_data["fecha_caducidad"]
            pool.fecha_caducidad = fecha
            pool.estado = Pool.Estado.RECONFIRMACION
            pool.reconfirmacion_hasta = timezone.now() + timedelta(
                days=DIAS_RECONFIRMACION
            )
            pool.save(
                update_fields=["fecha_caducidad", "estado", "reconfirmacion_hasta"]
            )
            pool.memberships.update(reconfirmado=None)
            registrar_evento(
                pool,
                EventoPool.Tipo.EXTENDIDO,
                actor=request.user,
                datos={"fecha": fecha.isoformat()},
            )
            notificar_extension(pool, request.user)
            pool.resolver_reconfirmacion()
        return Response(self.get_serializer(self.get_object()).data)

    @action(
        detail=True,
        methods=("post",),
        url_path="reconfirmar",
        permission_classes=(IsAuthenticated,),
    )
    def reconfirmar(self, request, pk=None):
        """Un participante confirma que sigue (o sale) tras la extensión del plazo."""
        serializer = ReconfirmacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        seguir = serializer.validated_data["seguir"]
        with transaction.atomic():
            pool = self._bloqueado(pk)
            if pool.estado != Pool.Estado.RECONFIRMACION:
                raise ValidationError("El pool no está esperando confirmaciones.")
            membership = self._mi_membresia(pool)
            if membership.reconfirmado is not None:
                raise ValidationError("Ya respondiste.")
            if seguir:
                membership.reconfirmado = timezone.now()
                membership.save(update_fields=["reconfirmado"])
            else:
                cantidad = membership.cantidad
                debe_devolucion = membership.pago_realizado
                if debe_devolucion:
                    solicitud = crear_devolucion(pool, membership, "Salió al reconfirmar.")
                membership.delete()
                registrar_evento(
                    pool,
                    EventoPool.Tipo.SALIDA,
                    actor=request.user,
                    datos={"cantidad": cantidad},
                )
                if debe_devolucion:
                    notificar_baja_resuelta(pool, solicitud)
            registrar_evento(
                pool,
                EventoPool.Tipo.RECONFIRMACION,
                actor=request.user,
                datos={"seguir": seguir},
            )
            pool.resolver_reconfirmacion()
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=("post",), url_path="imagenes")
    def subir_imagen(self, request, pk=None):
        pool = self.get_object()
        self._solo_creador(pool)
        if pool.imagenes.count() >= MAX_IMAGENES:
            raise ValidationError(f"Máximo {MAX_IMAGENES} imágenes por pool.")
        serializer = PoolImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(pool=pool)
        registrar_evento(
            pool, EventoPool.Tipo.IMAGEN, actor=request.user, datos={"accion": "agregada"}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=("delete",), url_path=r"imagenes/(?P<img_id>\d+)")
    def borrar_imagen(self, request, pk=None, img_id=None):
        pool = self.get_object()
        self._solo_creador(pool)
        imagen = get_object_or_404(pool.imagenes, pk=img_id)
        imagen.delete()
        registrar_evento(
            pool, EventoPool.Tipo.IMAGEN, actor=request.user, datos={"accion": "eliminada"}
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryViewSet(viewsets.ModelViewSet):
    """Categorías y subcategorías: lectura pública; el staff las administra
    (alta, nombre, padre, baja si nadie las usa y atributos propios)."""

    queryset = Category.objects.select_related("padre").prefetch_related(
        "atributos", "padre__atributos"
    )
    serializer_class = CategorySerializer
    # Sin paginar: son pocas y el select de "Crear pool" las necesita todas
    # (con PAGE_SIZE=12 se perdían las que pasaran de la primera página).
    pagination_class = None
    http_method_names = ("get", "post", "patch", "put", "delete", "head", "options")

    def get_permissions(self):
        return [AllowAny()] if self.request.method in SAFE_METHODS else [IsAdminUser()]

    def destroy(self, request, *args, **kwargs):
        categoria = self.get_object()
        if categoria.pools.exists() or categoria.subcategorias.exists():
            raise ValidationError(
                "No se puede borrar: tiene pools o subcategorías. Reasignalos primero."
            )
        categoria.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=("put",))
    def atributos(self, request, pk=None):
        """Reemplaza los atributos propios. Los pools que ofrecían una opción que
        ya no existe dejan de ofrecerla (variantes_vigentes)."""
        categoria = self.get_object()
        serializer = AtributosCategoriaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nuevos = serializer.validated_data["atributos"]
        with transaction.atomic():
            categoria.atributos.exclude(nombre__in=[a["nombre"] for a in nuevos]).delete()
            for orden, atributo in enumerate(nuevos):
                AtributoCategoria.objects.update_or_create(
                    categoria=categoria,
                    nombre=atributo["nombre"],
                    defaults={"opciones": atributo["opciones"], "orden": orden},
                )
        return Response(self.get_serializer(self.get_queryset().get(pk=categoria.pk)).data)
