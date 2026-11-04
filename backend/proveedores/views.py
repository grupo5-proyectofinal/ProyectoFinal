from django.db.models import Q
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
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

from .models import Proveedor
from .serializers import ProveedorDetalleSerializer, ProveedorSerializer

POOLS_ACTIVOS_MAX = 6


class SugerirProveedorThrottle(UserRateThrottle):
    scope = "sugerir_proveedor"


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
