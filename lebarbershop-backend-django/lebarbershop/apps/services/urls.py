from rest_framework.routers import DefaultRouter
from .views import SoinViewSet

router = DefaultRouter(trailing_slash='/?')
router.register("soins", SoinViewSet, basename="soin")
urlpatterns = router.urls
