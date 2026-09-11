from rest_framework.routers import DefaultRouter
from .views import PaiementAbonnementViewSet

router = DefaultRouter(trailing_slash='/?')
router.register("paiements", PaiementAbonnementViewSet, basename="paiement")
urlpatterns = router.urls
