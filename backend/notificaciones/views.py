from django_filters import rest_framework as filters
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notificacion
from .serializers import NotificacionSerializer


class NotificacionFilter(filters.FilterSet):
    leida = filters.BooleanFilter(field_name="leida")

    class Meta:
        model = Notificacion
        fields = ()


class NotificacionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Bandeja del usuario logueado: solo ve las propias."""

    permission_classes = (IsAuthenticated,)
    serializer_class = NotificacionSerializer
    filterset_class = NotificacionFilter

    def get_queryset(self):
        return Notificacion.objects.filter(usuario=self.request.user).select_related("pool")

    @action(detail=False, methods=("get",))
    def resumen(self, request):
        return Response({"no_leidas": self.get_queryset().filter(leida=False).count()})

    @action(detail=True, methods=("post",))
    def leer(self, request, pk=None):
        notificacion = self.get_object()
        if not notificacion.leida:
            notificacion.leida = True
            notificacion.save(update_fields=["leida"])
        return Response(self.get_serializer(notificacion).data)

    @action(detail=False, methods=("post",), url_path="leer-todas")
    def leer_todas(self, request):
        marcadas = self.get_queryset().filter(leida=False).update(leida=True)
        return Response({"marcadas": marcadas})
