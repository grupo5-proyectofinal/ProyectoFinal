from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from .models import Category, Membership, Pool
from .serializers import (
    CantidadSerializer,
    CategorySerializer,
    MembershipSerializer,
    PoolImageSerializer,
    PoolSerializer,
)

MAX_IMAGENES = 10


class PoolFilter(filters.FilterSet):
    q = filters.CharFilter(method="filtrar_q")
    categoria = filters.NumberFilter(field_name="categoria_id")
    precio_min = filters.NumberFilter(field_name="precio_unitario", lookup_expr="gte")
    precio_max = filters.NumberFilter(field_name="precio_unitario", lookup_expr="lte")
    ciudad = filters.CharFilter(field_name="ciudad", lookup_expr="icontains")
    estado = filters.CharFilter(field_name="estado")

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
    ordering_fields = ("fecha_caducidad", "precio_unitario", "vistas")
    ordering = ("-creado",)

    def get_queryset(self):
        return Pool.objects.select_related("categoria", "creador").prefetch_related(
            "imagenes", "memberships__usuario"
        )

    def perform_create(self, serializer):
        pool = serializer.save(creador=self.request.user)
        if pool.actualizar_estado():
            pool.save(update_fields=["estado"])

    # ponytail: sin lock acá; usar _bloqueado(pk) si hubiera uso concurrente real
    def perform_update(self, serializer):
        pool = serializer.save()
        if pool.actualizar_estado():
            pool.save(update_fields=["estado"])

    def _bloqueado(self, pk):
        return get_object_or_404(self.get_queryset().select_for_update(of=("self",)), pk=pk)

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

    @action(detail=False, methods=("get",), permission_classes=(IsAuthenticated,))
    def mios(self, request):
        return self._paginar(self.get_queryset().filter(creador=request.user))

    @action(detail=False, methods=("get",), permission_classes=(IsAuthenticated,))
    def unidos(self, request):
        return self._paginar(self.get_queryset().filter(memberships__usuario=request.user))

    @action(detail=True, methods=("post",))
    def unirse(self, request, pk=None):
        with transaction.atomic():
            pool = self._bloqueado(pk)
            if pool.estado != Pool.Estado.ABIERTO:
                raise ValidationError("El pool no está abierto.")
            if pool.creador_id == request.user.id:
                raise ValidationError("El creador ya participa del pool.")
            if pool.memberships.filter(usuario=request.user).exists():
                raise ValidationError("Ya estás en este pool.")
            serializer = CantidadSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            cantidad = serializer.validated_data["cantidad"]
            disponible = pool.disponible
            self._validar_cantidad(pool, cantidad, disponible)
            membership = Membership.objects.create(
                pool=pool, usuario=request.user, cantidad=cantidad
            )
            if pool.actualizar_estado(disponible - cantidad):
                pool.save(update_fields=["estado"])
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=("delete",))
    def salir(self, request, pk=None):
        with transaction.atomic():
            pool = self._bloqueado(pk)
            if pool.estado not in (Pool.Estado.ABIERTO, Pool.Estado.LISTO):
                raise ValidationError("No se puede salir en este estado.")
            membership = pool.memberships.filter(usuario=request.user).first()
            if membership is None:
                raise ValidationError("No estás en este pool.")
            disponible = pool.disponible + membership.cantidad
            membership.delete()
            if pool.actualizar_estado(disponible):
                pool.save(update_fields=["estado"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=("patch",), url_path="mi-membresia")
    def mi_membresia(self, request, pk=None):
        with transaction.atomic():
            pool = self._bloqueado(pk)
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
            membership.cantidad = nueva
            membership.save(update_fields=["cantidad"])
            if pool.actualizar_estado(disponible - nueva):
                pool.save(update_fields=["estado"])
            actualizado = self.get_queryset().get(pk=pool.pk)
        return Response(self.get_serializer(actualizado).data)

    # ponytail: sin lock acá; usar _bloqueado(pk) si hubiera uso concurrente real
    def _transicion(self, pool, desde, hacia):
        self._solo_creador(pool)
        if pool.estado not in desde:
            raise ValidationError(f"Transición inválida desde el estado '{pool.estado}'.")
        pool.estado = hacia
        pool.save(update_fields=["estado"])
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

    @action(detail=True, methods=("post",), url_path="imagenes")
    def subir_imagen(self, request, pk=None):
        pool = self.get_object()
        self._solo_creador(pool)
        if pool.imagenes.count() >= MAX_IMAGENES:
            raise ValidationError(f"Máximo {MAX_IMAGENES} imágenes por pool.")
        serializer = PoolImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(pool=pool)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=("delete",), url_path=r"imagenes/(?P<img_id>\d+)")
    def borrar_imagen(self, request, pk=None, img_id=None):
        pool = self.get_object()
        self._solo_creador(pool)
        imagen = get_object_or_404(pool.imagenes, pk=img_id)
        imagen.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
