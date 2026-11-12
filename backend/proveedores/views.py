from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeout
from decimal import Decimal

from django.db.models import Count, F, Prefetch, Q, Window
from django.db.models.functions import RowNumber
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import (
    SAFE_METHODS,
    AllowAny,
    IsAdminUser,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from pools.confianza import dominio_de
from pools.models import Pool
from pools.producto import leer_enlace

from .importacion import importar_archivo
from .models import Comparacion, Oferta, ParametroCosto, PrecioHistorico, Proveedor
from .serializers import (
    PUNTOS_HISTORIAL,
    ComparacionSerializer,
    OfertaSerializer,
    ParametroCostoSerializer,
    ProveedorDetalleSerializer,
    ProveedorSerializer,
    parametros_vigentes,
    registrar_precio,
)

POOLS_ACTIVOS_MAX = 6
LECTURAS_EN_PARALELO = 5
TIEMPO_MAXIMO_LECTURAS = 20  # segundos, por debajo del timeout de gunicorn (30)


class SugerirProveedorThrottle(UserRateThrottle):
    scope = "sugerir_proveedor"


class ActualizarPreciosThrottle(UserRateThrottle):
    scope = "actualizar_precios"


class ProveedorFilter(filters.FilterSet):
    q = filters.CharFilter(method="filtrar_q")
    rubro = filters.NumberFilter(method="filtrar_rubro")
    provincia = filters.CharFilter(field_name="provincia", lookup_expr="iexact")
    verificado = filters.BooleanFilter(field_name="verificado")
    estado = filters.CharFilter(field_name="estado")

    class Meta:
        model = Proveedor
        fields = ()

    def filtrar_q(self, queryset, name, value):
        return queryset.filter(
            Q(nombre__icontains=value) | Q(dominio__icontains=value) | Q(descripcion__icontains=value)
        )

    def filtrar_rubro(self, queryset, name, value):
        # Un rubro principal ("Ropa") incluye a los que cargaron una subcategoría.
        return queryset.filter(Q(rubros__id=value) | Q(rubros__padre_id=value)).distinct()


class ProveedorViewSet(viewsets.ModelViewSet):
    # Directorio curado (decenas, no miles) y la UI no pagina: lista completa.
    """Directorio de mayoristas.

    Público: solo los aprobados. Con sesión se puede sugerir uno (queda pendiente).
    El staff ve todos, edita, aprueba o rechaza.
    """

    filterset_class = ProveedorFilter
    pagination_class = None

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        if self.action == "create":
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def get_throttles(self):
        if self.action == "create" and not self.request.user.is_staff:
            return [SugerirProveedorThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        queryset = Proveedor.objects.prefetch_related("rubros")
        if not self.request.user.is_staff:
            queryset = queryset.filter(estado=Proveedor.Estado.APROBADO)
        return queryset

    def get_serializer_class(self):
        return ProveedorDetalleSerializer if self.action == "retrieve" else ProveedorSerializer

    def retrieve(self, request, *args, **kwargs):
        proveedor = self.get_object()
        usan = self._pools_del_dominio(proveedor.dominio)
        activos = sorted(
            (p for p in usan if p.estado == Pool.Estado.ABIERTO), key=lambda p: p.fecha_caducidad
        )[:POOLS_ACTIVOS_MAX]
        contexto = {
            **self.get_serializer_context(),
            "pools_total": len(usan),
            "pools_activos": [
                {"id": p.id, "titulo": p.titulo, "precio_unitario": str(p.precio_unitario)}
                for p in activos
            ],
        }
        return Response(ProveedorDetalleSerializer(proveedor, context=contexto).data)

    @staticmethod
    def _pools_del_dominio(dominio):
        """Pools cuyo enlace es de este sitio (dominio exacto, con o sin www).

        El `icontains` es un prefiltro: `tienda.com.ar.evil.com` no cuenta.
        """
        if not dominio:
            return []
        candidatos = Pool.objects.filter(enlace__icontains=dominio).only(
            "id", "titulo", "precio_unitario", "estado", "fecha_caducidad", "enlace"
        )
        return [p for p in candidatos if (dominio_de(p.enlace) or "").removeprefix("www.") == dominio]

    def perform_create(self, serializer):
        if self.request.user.is_staff:
            serializer.save(estado=Proveedor.Estado.APROBADO, sugerido_por=self.request.user)
        else:
            # Sugerencia: queda pendiente y sin el sello de verificado.
            serializer.save(
                estado=Proveedor.Estado.PENDIENTE, verificado=False, sugerido_por=self.request.user
            )

    @action(
        detail=False,
        methods=("post",),
        url_path="importar",
        parser_classes=(MultiPartParser, FormParser),
    )
    def importar(self, request):
        """Carga masiva desde un CSV (staff). Reusa la lógica del comando."""
        archivo = request.FILES.get("archivo")
        if archivo is None:
            return Response(
                {"detail": "Adjuntá un archivo CSV en el campo archivo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if archivo.size > 2 * 1024 * 1024:
            return Response(
                {"detail": "El CSV no puede superar los 2 MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            resultado = importar_archivo(archivo)
        except ValueError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(resultado)

    @action(detail=True, methods=("post",))
    def aprobar(self, request, pk=None):
        return self._estado(Proveedor.Estado.APROBADO)

    @action(detail=True, methods=("post",))
    def rechazar(self, request, pk=None):
        return self._estado(Proveedor.Estado.RECHAZADO)

    def _estado(self, estado):
        proveedor = self.get_object()
        proveedor.estado = estado
        proveedor.save(update_fields=["estado", "actualizado"])
        return Response(ProveedorSerializer(proveedor).data)


class ParametroCostoViewSet(
    mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """Tipo de cambio y alícuotas de referencia: lectura pública, edición staff."""

    queryset = ParametroCosto.objects.all()
    serializer_class = ParametroCostoSerializer
    lookup_field = "clave"
    pagination_class = None
    http_method_names = ("get", "patch", "head", "options")

    def get_permissions(self):
        return [AllowAny()] if self.request.method in SAFE_METHODS else [IsAdminUser()]


class ComparacionViewSet(viewsets.ModelViewSet):
    """Comparaciones de costo final.

    Las sueltas son de quien las crea. Las de un pool las ven también sus
    integrantes (es un argumento de confianza), pero solo el creador las edita.
    """

    serializer_class = ComparacionSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = None  # las de un usuario; /comparar las lista todas

    def get_queryset(self):
        usuario = self.request.user
        if self.action == "list":
            # El listado solo muestra cuántas ofertas tiene: nada de historial.
            return (
                Comparacion.objects.filter(creador=usuario, pool__isnull=True)
                .select_related("creador")
                .annotate(total_ofertas=Count("ofertas"))
            )
        # Solo los últimos puntos de cada oferta: numerados por oferta en SQL (ventana).
        historial = PrecioHistorico.objects.annotate(
            posicion=Window(
                RowNumber(), partition_by=F("oferta_id"), order_by=(F("fecha").desc(), F("id").desc())
            )
        ).filter(posicion__lte=PUNTOS_HISTORIAL)
        base = Comparacion.objects.select_related("creador", "pool").prefetch_related(
            Prefetch(
                "ofertas",
                queryset=Oferta.objects.select_related("proveedor").prefetch_related(
                    Prefetch("historial", queryset=historial)
                ),
            )
        )
        return base.filter(
            Q(creador=usuario) | Q(pool__creador=usuario) | Q(pool__memberships__usuario=usuario)
        ).distinct()

    def get_serializer_context(self):
        contexto = super().get_serializer_context()
        contexto["con_ofertas"] = self.action != "list"
        contexto["parametros"] = parametros_vigentes()
        return contexto

    def _solo_creador(self, comparacion):
        if comparacion.creador_id != self.request.user.id:
            raise PermissionDenied("Solo quien creó la comparación puede editarla.")

    def perform_create(self, serializer):
        serializer.save(creador=self.request.user)

    def perform_update(self, serializer):
        self._solo_creador(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._solo_creador(instance)
        instance.delete()

    @action(detail=False, methods=("get",), url_path=r"de-pool/(?P<pool_id>\d+)")
    def de_pool(self, request, pool_id=None):
        comparacion = get_object_or_404(self.get_queryset(), pool_id=pool_id)
        return Response(self.get_serializer(comparacion).data)

    @action(
        detail=True,
        methods=("post",),
        url_path="actualizar-precios",
        throttle_classes=(ActualizarPreciosThrottle,),
    )
    def actualizar_precios(self, request, pk=None):
        """Vuelve a leer el precio de cada oferta con enlace y guarda los cambios.

        Las tiendas se consultan en paralelo con un tope total de tiempo, para no
        pasar el timeout del servidor con varias tiendas lentas o que bloquean.
        """
        comparacion = self.get_object()
        self._solo_creador(comparacion)
        con_enlace = [o for o in comparacion.ofertas.all() if o.url]
        lecturas, fallidas = {}, []
        with ThreadPoolExecutor(max_workers=LECTURAS_EN_PARALELO) as ejecutor:
            futuros = {ejecutor.submit(leer_enlace, o.url): o for o in con_enlace}
            try:
                for futuro in as_completed(futuros, timeout=TIEMPO_MAXIMO_LECTURAS):
                    lecturas[futuros[futuro].pk] = futuro.result()
            except FuturesTimeout:
                pass  # las que no llegaron cuentan como no leídas
        actualizadas = sin_cambios = 0
        for oferta in con_enlace:
            datos = (lecturas.get(oferta.pk) or {}).get("datos") or {}
            moneda = datos.get("moneda") or "ARS"
            precio = datos.get("precio_unitario") or datos.get("precio_moneda")
            if not precio or moneda != oferta.moneda:
                fallidas.append(oferta.tienda)
                continue
            if Decimal(precio) == oferta.precio_unitario:
                sin_cambios += 1
                continue
            oferta.precio_unitario = Decimal(precio)
            oferta.save(update_fields=["precio_unitario", "actualizado"])
            registrar_precio(oferta)
            actualizadas += 1
        comparacion = self.get_queryset().get(pk=comparacion.pk)
        return Response(
            {
                "actualizadas": actualizadas,
                "sin_cambios": sin_cambios,
                "fallidas": fallidas,
                "comparacion": self.get_serializer(comparacion).data,
            }
        )


class OfertaViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OfertaSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ("post", "patch", "delete", "head", "options")

    def get_queryset(self):
        return Oferta.objects.filter(comparacion__creador=self.request.user)

    def perform_create(self, serializer):
        oferta = serializer.save()
        registrar_precio(oferta)

    def perform_update(self, serializer):
        anterior = (serializer.instance.precio_unitario, serializer.instance.moneda)
        oferta = serializer.save()
        if (oferta.precio_unitario, oferta.moneda) != anterior:
            registrar_precio(oferta)

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

