from rest_framework.routers import DefaultRouter
from .views import AvisViewSet

router = DefaultRouter(trailing_slash='/?')
router.register("avis", AvisViewSet, basename="avis")
urlpatterns = router.urls
