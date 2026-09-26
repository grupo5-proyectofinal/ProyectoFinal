from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, PoolViewSet

router = DefaultRouter()
router.register("pools", PoolViewSet, basename="pool")
router.register("categories", CategoryViewSet, basename="category")

urlpatterns = router.urls
