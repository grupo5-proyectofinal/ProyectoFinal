from django.db import transaction
from django.db.models import Count, F, Prefetch, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from notificaciones.servicio import notificar_estado, notificar_mensaje, notificar_union

from .confianza import conteos_dominio
from .geocoding import geocodificar
from .models import (
    Category,
    EventoPool,
    Membership,
    Pool,
    PoolImage,
    SolicitudEliminacion,
    expirar_vencidos,
    registrar_evento,
)
from .producto import datos_de_enlace, imagen_de_url
from .serializers import (
    CantidadSerializer,
    CategorySerializer,
    EnlaceProductoSerializer,
    EventoPoolSerializer,
    MembershipSerializer,
    MensajeSerializer,
    PoolImageSerializer,
    PoolSerializer,
    ResenaSerializer,
    SolicitudEliminacionSerializer,
    UnionSerializer,
    VotoSerializer,
)

MAX_IMAGENES = 10

# Chat por polling: el cliente pide "lo nuevo" con `desde` = último id que vio.
MENSAJES_LIMITE = 50
MENSAJES_LIMITE_MAX = 200
# ERS 2.3: el chat nace en "listo" y la escritura sigue habilitada hasta "finalizado".
ESTADOS_CON_CHAT = (Pool.Estado.LISTO, Pool.Estado.EN_CURSO, Pool.Estado.FINALIZADO)


def _entero(valor, default):
    """Entero de un query param, o `default` si falta o no es numérico."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        return default


# Acciones que devuelven un pool completo (no listados): habilitan exponer los
# datos PII del miembro al creador (regla en MembershipSerializer).
ACCIONES_DETALLE = {
    "retrieve",
    "confirmar",
    "finalizar",
    "cancelar",
    "mi_membresia",
}


class PrevisualizarEnlaceThrottle(UserRateThrottle):
    scope = "previsualizar_enlace"


class PoolFilter(filters.FilterSet):
    q = filters.CharFilter(method="filtrar_q")
    categoria = filters.NumberFilter(field_name="categoria_id")
    precio_min = filters.NumberFilter(field_name="precio_unitario", lookup_expr="gte")
    precio_max = filters.NumberFilter(field_name="precio_unitario", lookup_expr="lte")
    ciudad = filters.CharFilter(field_name="ciudad", lookup_expr="icontains")
    estado = filters.CharFilter(field_name="estado")
    creador = filters.NumberFilter(field_name="creador_id")

    class Meta:
        model = Pool
        fields = ()

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

    def get_queryset(self):
        expirar_vencidos()
        return (
            Pool.objects.select_related("categoria", "creador")
            .prefetch_related(
                "imagenes",
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
        pool = self.get_object()
        self._solo_creador(pool)
        self._solo_abierto(pool)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        pool = self.get_object()
        self._solo_creador(pool)
        self._solo_abierto(pool)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        pool = self.get_object()
        self._solo_creador(pool)
        self._solo_abierto(pool)
        return super().destroy(request, *args, **kwargs)

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

    def _rechazar_solicitud_pendiente(self, pool):
        if pool.solicitud_pendiente() is not None:
            raise ValidationError("Hay una solicitud de eliminación pendiente.")

    def _cerrar_solicitud_pendiente(self, pool):
        pool.solicitudes_eliminacion.filter(
            estado=SolicitudEliminacion.Estado.PENDIENTE
        ).update(estado=SolicitudEliminacion.Estado.CANCELADA)

    def _es_unanimidad(self, solicitud):
        total = solicitud.pool.memberships.count()
        aceptaron = solicitud.votos.filter(acepta=True).count()
        return total > 0 and aceptaron == total

    def _rechazar_vencido(self, pool):
        """Bajo lock: corta la acción si el pool venció (la cancelación es perezosa)."""
        if pool.vencio():
            raise ValidationError("El pool está vencido.")

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
        datos = datos_de_enlace(serializer.validated_data["enlace"])
        if datos is None or not any(datos.values()):
            return Response(
                {
                    "encontrado": False,
                    "detail": "No pudimos leer los datos de ese enlace. Completalos a mano.",
                }
            )
        return Response({"encontrado": True, **datos})

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
            self._rechazar_solicitud_pendiente(pool)
            if pool.estado != Pool.Estado.ABIERTO:
                raise ValidationError("El pool no está abierto.")
            if pool.creador_id == request.user.id:
                raise ValidationError("El creador ya participa del pool.")
            if pool.memberships.filter(usuario=request.user).exists():
                raise ValidationError("Ya estás en este pool.")
            serializer = UnionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            cantidad = serializer.validated_data["cantidad"]
            telefono = serializer.validated_data["telefono"]
            mensaje = serializer.validated_data.get("mensaje", "")
            disponible = pool.disponible
            self._validar_cantidad(pool, cantidad, disponible)
            membership = Membership.objects.create(
                pool=pool,
                usuario=request.user,
                cantidad=cantidad,
                telefono=telefono,
                mensaje=mensaje,
            )
            registrar_evento(
                pool, EventoPool.Tipo.UNION, actor=request.user, datos={"cantidad": cantidad}
            )
            notificar_union(pool, request.user, cantidad)
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
            self._rechazar_solicitud_pendiente(pool)
            if pool.estado not in (Pool.Estado.ABIERTO, Pool.Estado.LISTO):
                raise ValidationError("No se puede salir en este estado.")
            membership = pool.memberships.filter(usuario=request.user).first()
            if membership is None:
                raise ValidationError("No estás en este pool.")
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
            self._rechazar_solicitud_pendiente(pool)
            if pool.estado not in (Pool.Estado.ABIERTO, Pool.Estado.LISTO):
                raise ValidationError("No se puede editar en este estado.")
            membership = pool.memberships.filter(usuario=request.user).first()
            if membership is None:
                raise ValidationError("No estás en este pool.")
            serializer = CantidadSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            nueva = serializer.validated_data["cantidad"]
            disponible = self._disponible_conmigo(pool, membership)
            self._validar_cantidad(pool, nueva, disponible)
            if nueva != membership.cantidad:
                registrar_evento(
                    pool,
                    EventoPool.Tipo.CANTIDAD,
                    actor=request.user,
                    datos={"antes": membership.cantidad, "despues": nueva},
                )
            membership.cantidad = nueva
            membership.save(update_fields=["cantidad"])
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

    # ponytail: sin lock acá; usar _bloqueado(pk) si hubiera uso concurrente real
    def _transicion(self, pool, desde, hacia):
        self._solo_creador(pool)
        if pool.estado not in desde:
            raise ValidationError(f"Transición inválida desde el estado '{pool.estado}'.")
        pool.estado = hacia
        pool.save(update_fields=["estado"])
        registrar_evento(
            pool, EventoPool.Tipo.ESTADO, actor=self.request.user, datos={"estado": hacia}
        )
        notificar_estado(pool, hacia, actor=self.request.user)
        if hacia not in (Pool.Estado.LISTO, Pool.Estado.EN_CURSO):
            self._cerrar_solicitud_pendiente(pool)
        return Response(self.get_serializer(pool).data)

    @action(detail=True, methods=("post",))
    def confirmar(self, request, pk=None):
        return self._transicion(self.get_object(), (Pool.Estado.LISTO,), Pool.Estado.EN_CURSO)

    @action(detail=True, methods=("post",))
    def finalizar(self, request, pk=None):
        return self._transicion(self.get_object(), (Pool.Estado.EN_CURSO,), Pool.Estado.FINALIZADO)

    @action(detail=True, methods=("post",))
    def cancelar(self, request, pk=None):
        return self._transicion(
            self.get_object(), (Pool.Estado.ABIERTO, Pool.Estado.LISTO), Pool.Estado.CANCELADO
        )

    @action(
        detail=True,
        methods=("get", "post"),
        url_path="eliminacion",
        permission_classes=(IsAuthenticated,),
    )
    def eliminacion(self, request, pk=None):
        if request.method == "POST":
            return self._solicitar_eliminacion(request, pk)
        return self._detalle_eliminacion(request, pk)

    def _solicitar_eliminacion(self, request, pk):
        with transaction.atomic():
            pool = self._bloqueado(pk)
            self._solo_creador(pool)
            if pool.estado not in (Pool.Estado.LISTO, Pool.Estado.EN_CURSO):
                raise ValidationError(
                    "Solo se puede solicitar la eliminación en un pool listo o en curso."
                )
            if pool.solicitud_pendiente() is not None:
                raise ValidationError("Ya hay una solicitud de eliminación pendiente.")
            solicitud = SolicitudEliminacion.objects.create(pool=pool)
            if pool.memberships.count() == 0:
                pool.delete()
                return Response({"estado": "aprobada"})
            registrar_evento(pool, EventoPool.Tipo.SOLICITUD_ELIMINACION, actor=request.user)
            return Response(
                {"id": solicitud.id, "estado": "pendiente"}, status=status.HTTP_201_CREATED
            )

    def _detalle_eliminacion(self, request, pk):
        pool = self.get_object()
        self._es_participante(pool)
        solicitud = pool.solicitudes_eliminacion.order_by("-creado").first()
        if solicitud is None:
            raise NotFound("No hay una solicitud de eliminación.")
        return Response(SolicitudEliminacionSerializer(solicitud).data)

    @action(detail=True, methods=("post",), url_path="eliminacion/voto")
    def eliminacion_voto(self, request, pk=None):
        with transaction.atomic():
            pool = self._bloqueado(pk)
            if pool.creador_id == request.user.id:
                raise ValidationError("El creador no puede votar.")
            if not pool.memberships.filter(usuario=request.user).exists():
                raise PermissionDenied("Solo los integrantes pueden votar.")
            solicitud = pool.solicitud_pendiente()
            if solicitud is None:
                raise ValidationError("No hay una solicitud de eliminación pendiente.")
            if pool.estado not in (Pool.Estado.LISTO, Pool.Estado.EN_CURSO):
                self._cerrar_solicitud_pendiente(pool)
                raise ValidationError("La solicitud de eliminación ya no está vigente.")
            serializer = VotoSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            if solicitud.votos.filter(usuario=request.user).exists():
                raise ValidationError("Ya votaste esta solicitud.")
            acepta = serializer.validated_data["acepta"]
            solicitud.votos.create(usuario=request.user, acepta=acepta)
            registrar_evento(
                pool,
                EventoPool.Tipo.VOTO_ELIMINACION,
                actor=request.user,
                datos={"acepta": acepta},
            )
            if not acepta:
                solicitud.estado = SolicitudEliminacion.Estado.RECHAZADA
                solicitud.save(update_fields=["estado"])
                return Response({"estado": "rechazada"})
            if self._es_unanimidad(solicitud):
                pool.delete()
                return Response({"estado": "aprobada"})
            return Response({"estado": "pendiente"})

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


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
