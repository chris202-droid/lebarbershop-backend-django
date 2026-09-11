from rest_framework.routers import DefaultRouter
from .views import ProduitViewSet, MouvementStockViewSet

router = DefaultRouter(trailing_slash='/?')
router.register("produits", ProduitViewSet, basename="produit")
router.register("mouvements-stock", MouvementStockViewSet, basename="mouvement-stock")
urlpatterns = router.urls
