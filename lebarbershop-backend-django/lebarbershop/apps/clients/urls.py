from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, FideliteClientSalonViewSet

router = DefaultRouter(trailing_slash='/?')
router.register("clients", ClientViewSet, basename="client")
router.register("fidelite", FideliteClientSalonViewSet, basename="fidelite")
urlpatterns = router.urls
