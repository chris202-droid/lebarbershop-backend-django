from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import RendementEmployeViewSet, BilanJournalierViewSet, statistiques_secteur, bilan_financier, bilan_salon

router = DefaultRouter(trailing_slash='/?')
router.register("rendements-employes", RendementEmployeViewSet, basename="rendement-employe")
router.register("bilans-journaliers", BilanJournalierViewSet, basename="bilan-journalier")

urlpatterns = router.urls + [
    path("statistiques-secteurs/", statistiques_secteur, name="statistiques-secteurs"),
    path("bilan-financier/", bilan_financier, name="bilan-financier"),
    path("bilan-salon/", bilan_salon, name="bilan-salon"),
]
