from rest_framework.routers import DefaultRouter
from .views import SecteurGeographiqueViewSet

router = DefaultRouter(trailing_slash='/?')
router.register("secteurs", SecteurGeographiqueViewSet, basename="secteur")
urlpatterns = router.urls
