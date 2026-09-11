from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from .models import Utilisateur, DroitAdministrateur
from .serializers import (
    UtilisateurSerializer, InscriptionSerializer, ChangerMotDePasseSerializer,
    AdministrateurSecondaireSerializer, NommerAdministrateurSerializer,
    ReinitialiserIdentifiantsSerializer, DroitAdministrateurSerializer,
)
from apps.salons.permissions import EstAdminPrincipal, EstAdminSaaS, PeutAjouterAdministrateur


class InscriptionView(generics.CreateAPIView):
    """Inscription publique (propriétaire de salon ou utilisateur lambda)."""
    queryset = Utilisateur.objects.all()
    serializer_class = InscriptionSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "utilisateur": UtilisateurSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=status.HTTP_201_CREATED)


class ProfilView(generics.RetrieveUpdateAPIView):
    serializer_class = UtilisateurSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangerMotDePasseView(APIView):
    """
    POST /api/v1/auth/changer-mot-de-passe/
    Utilisé (1) par un employé à sa première connexion pour remplacer le mot
    de passe temporaire fixé par son gestionnaire, et (2) par tout utilisateur
    souhaitant changer son mot de passe depuis son profil.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangerMotDePasseSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Mot de passe mis à jour."})


# --- Administration : gestion des administrateurs secondaires ---

class AdministrateurSecondaireListeView(generics.ListAPIView):
    """
    GET /api/v1/auth/administrateurs/ — visible par tout administrateur du
    SAAS (principal ou secondaire) : chacun doit pouvoir voir qui sont les
    autres administrateurs et leurs droits. Seules la création, la
    modification des droits et la révocation restent réservées au seul
    administrateur principal (voir les vues ci-dessous).
    """
    queryset = Utilisateur.objects.filter(est_admin_secondaire=True).select_related("droits")
    serializer_class = AdministrateurSecondaireSerializer
    permission_classes = [permissions.IsAuthenticated, EstAdminSaaS]
    pagination_class = None


class NommerAdministrateurView(APIView):
    """
    POST /api/v1/auth/administrateurs/
    Désigne un utilisateur existant comme administrateur secondaire et lui
    attribue des droits granulaires. Autorisé pour l'administrateur
    principal, ou tout administrateur secondaire ayant reçu le droit
    peut_ajouter_administrateur.
    """
    permission_classes = [permissions.IsAuthenticated, PeutAjouterAdministrateur]

    def post(self, request):
        serializer = NommerAdministrateurSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilisateur = serializer.save(attribue_par=request.user)
        return Response(AdministrateurSecondaireSerializer(utilisateur).data, status=status.HTTP_201_CREATED)


class ModifierAdministrateurView(APIView):
    """
    PATCH /api/v1/auth/administrateurs/{id}/ — met à jour les droits d'un administrateur secondaire.
    DELETE /api/v1/auth/administrateurs/{id}/ — révoque son statut d'administrateur.
    Autorisé pour l'administrateur principal, ou tout administrateur
    secondaire ayant reçu le droit peut_ajouter_administrateur.
    """
    permission_classes = [permissions.IsAuthenticated, PeutAjouterAdministrateur]

    def patch(self, request, utilisateur_id):
        utilisateur = get_object_or_404(Utilisateur, pk=utilisateur_id, est_admin_secondaire=True)
        droits, _ = DroitAdministrateur.objects.get_or_create(administrateur=utilisateur)
        serializer_droits = DroitAdministrateurSerializer(droits, data=request.data, partial=True)
        serializer_droits.is_valid(raise_exception=True)
        serializer_droits.save()
        return Response(AdministrateurSecondaireSerializer(utilisateur).data)

    def delete(self, request, utilisateur_id):
        utilisateur = get_object_or_404(Utilisateur, pk=utilisateur_id, est_admin_secondaire=True)
        utilisateur.est_admin_secondaire = False
        utilisateur.save(update_fields=["est_admin_secondaire"])
        DroitAdministrateur.objects.filter(administrateur=utilisateur).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReinitialiserIdentifiantsView(APIView):
    """
    POST /api/v1/auth/utilisateurs/{id}/reinitialiser/
    Permet à l'administrateur de modifier le nom d'utilisateur et/ou de
    réinitialiser le mot de passe de n'importe quel compte — notamment celui
    d'un gestionnaire de salon (point 8 du cahier des charges de l'espace
    super administrateur).
    """
    permission_classes = [permissions.IsAuthenticated, EstAdminPrincipal]

    def post(self, request, utilisateur_id):
        utilisateur = get_object_or_404(Utilisateur, pk=utilisateur_id)
        serializer = ReinitialiserIdentifiantsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(utilisateur=utilisateur)
        return Response(UtilisateurSerializer(utilisateur).data)
