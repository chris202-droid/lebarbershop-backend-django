from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    DemandeContactCreateView, DemandePartenariatCreateView, DemandeCodePromoView,
    DemandeContactAdminViewSet, DemandePartenariatAdminViewSet, DemandeCodePromoAdminViewSet,
    demandes_toutes,
)

router = DefaultRouter(trailing_slash='/?')
router.register("contact/admin/demandes-contact", DemandeContactAdminViewSet, basename="admin-demande-contact")
router.register("contact/admin/demandes-partenariat", DemandePartenariatAdminViewSet, basename="admin-demande-partenariat")
router.register("contact/admin/demandes-code-promo", DemandeCodePromoAdminViewSet, basename="admin-demande-code-promo")

urlpatterns = [
    # Formulaires publics (landing page)
    path("contact/demandes/", DemandeContactCreateView.as_view(), name="demande-contact"),
    path("contact/partenariats/", DemandePartenariatCreateView.as_view(), name="demande-partenariat"),
    path("contact/code-promo/", DemandeCodePromoView.as_view(), name="demande-code-promo"),
    # Administration
    path("contact/admin/demandes-toutes/", demandes_toutes, name="admin-demandes-toutes"),
] + router.urls
