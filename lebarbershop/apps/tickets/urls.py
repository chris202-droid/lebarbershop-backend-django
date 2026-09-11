from rest_framework.routers import DefaultRouter
from .views import TicketViewSet, LigneTicketViewSet

router = DefaultRouter(trailing_slash='/?')
router.register("tickets", TicketViewSet, basename="ticket")
router.register("lignes-ticket", LigneTicketViewSet, basename="ligne-ticket")
urlpatterns = router.urls
