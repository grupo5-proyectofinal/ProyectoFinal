from rest_framework.routers import DefaultRouter

from .views import (
    ComparacionViewSet,
    OfertaViewSet,
    ParametroCostoViewSet,
    ProveedorViewSet,
)

router = DefaultRouter()
router.register("proveedores", ProveedorViewSet, basename="proveedor")
router.register("parametros-costo", ParametroCostoViewSet, basename="parametro-costo")
router.register("comparaciones", ComparacionViewSet, basename="comparacion")
router.register("ofertas", OfertaViewSet, basename="oferta")

urlpatterns = router.urls
