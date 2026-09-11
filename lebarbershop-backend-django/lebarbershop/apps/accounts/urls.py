from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    InscriptionView, ProfilView, ChangerMotDePasseView,
    AdministrateurSecondaireListeView, NommerAdministrateurView, ModifierAdministrateurView,
    ReinitialiserIdentifiantsView,
)

urlpatterns = [
    path("inscription/", InscriptionView.as_view(), name="inscription"),
    path("connexion/", TokenObtainPairView.as_view(), name="connexion"),
    path("connexion/rafraichir/", TokenRefreshView.as_view(), name="connexion-refresh"),
    path("profil/", ProfilView.as_view(), name="profil"),
    path("changer-mot-de-passe/", ChangerMotDePasseView.as_view(), name="changer-mot-de-passe"),

    # Administration (super admin)
    path("administrateurs/", AdministrateurSecondaireListeView.as_view(), name="administrateurs-liste"),
    path("administrateurs/nommer/", NommerAdministrateurView.as_view(), name="administrateurs-nommer"),
    path("administrateurs/<uuid:utilisateur_id>/", ModifierAdministrateurView.as_view(), name="administrateurs-modifier"),
    path("utilisateurs/<uuid:utilisateur_id>/reinitialiser/", ReinitialiserIdentifiantsView.as_view(), name="utilisateur-reinitialiser"),
]
