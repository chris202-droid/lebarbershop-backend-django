from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    SalonViewSet, AbonnementViewSet, AbonnementEssaiView, CodeReductionViewSet,
    CodeSponsoringViewSet, AbonnementAnalyseSectorielleViewSet, ForfaitViewSet,
)

router = DefaultRouter(trailing_slash='/?')
router.register("salons", SalonViewSet, basename="salon")
router.register("abonnements", AbonnementViewSet, basename="abonnement")
router.register("codes-reduction", CodeReductionViewSet, basename="code-reduction")
router.register("codes-sponsoring", CodeSponsoringViewSet, basename="code-sponsoring")
router.register("analyses-sectorielles", AbonnementAnalyseSectorielleViewSet, basename="analyse-sectorielle")
router.register("forfaits", ForfaitViewSet, basename="forfait")

urlpatterns = [
    # Déclarée avant le routeur pour ne pas être interceptée par abonnements/{pk}/
    path("abonnements/essai", AbonnementEssaiView.as_view(), name="abonnement-essai"),
] + router.urls
