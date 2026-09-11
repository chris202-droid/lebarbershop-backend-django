from rest_framework import generics, permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from .models import DemandeContact, DemandePartenariat, DemandeCodePromo
from .serializers import (
    DemandeContactSerializer, DemandePartenariatSerializer,
    DemandeCodePromoInSerializer, DemandeCodePromoOutSerializer,
    DemandeContactAdminSerializer, DemandePartenariatAdminSerializer, DemandeCodePromoAdminSerializer,
)
from .emails import notifier_demande_contact, notifier_demande_partenariat
from apps.salons.permissions import EstAdminSaaS


class DemandeContactCreateView(generics.CreateAPIView):
    """POST /api/v1/contact/demandes/ — formulaire 'Nous contacter' de la landing page."""
    queryset = DemandeContact.objects.all()
    serializer_class = DemandeContactSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def perform_create(self, serializer):
        demande = serializer.save()
        notifier_demande_contact(demande)  # -> information@kalarai.com


class DemandePartenariatCreateView(generics.CreateAPIView):
    """POST /api/v1/contact/partenariats/ — formulaire 'Devenir partenaire'."""
    queryset = DemandePartenariat.objects.all()
    serializer_class = DemandePartenariatSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def perform_create(self, serializer):
        demande = serializer.save()
        notifier_demande_partenariat(demande)  # -> information@kalarai.com


class DemandeCodePromoView(APIView):
    """
    POST /api/v1/contact/code-promo/ — formulaire 'Obtenir un code promo'.
    Génère immédiatement un CodeReduction (10%, valable 30 jours, usage unique)
    et le renvoie dans la réponse. Aucun envoi d'email n'est configuré à ce
    stade : le code est affiché directement côté frontend.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        entree = DemandeCodePromoInSerializer(data=request.data)
        entree.is_valid(raise_exception=True)

        demande_existante = DemandeCodePromo.objects.filter(
            email=entree.validated_data["email"]
        ).order_by("-date_creation").first()
        if demande_existante and demande_existante.code.actif:
            sortie = DemandeCodePromoOutSerializer(demande_existante)
            return Response(sortie.data, status=status.HTTP_200_OK)

        demande = DemandeCodePromo.creer_pour_email(entree.validated_data["email"])
        sortie = DemandeCodePromoOutSerializer(demande)
        return Response(sortie.data, status=status.HTTP_201_CREATED)


# --- Administration : consultation et traitement des demandes ---

class DemandeContactAdminViewSet(viewsets.ModelViewSet):
    """Réservé à l'administrateur : liste et marque les demandes de contact comme traitées."""
    queryset = DemandeContact.objects.all().order_by("-date_creation")
    serializer_class = DemandeContactAdminSerializer
    permission_classes = [permissions.IsAuthenticated, EstAdminSaaS]
    pagination_class = None
    http_method_names = ["get", "patch", "head", "options"]


class DemandePartenariatAdminViewSet(viewsets.ModelViewSet):
    """Réservé à l'administrateur : liste et traite les demandes de partenariat."""
    queryset = DemandePartenariat.objects.all().order_by("-date_creation")
    serializer_class = DemandePartenariatAdminSerializer
    permission_classes = [permissions.IsAuthenticated, EstAdminSaaS]
    pagination_class = None
    http_method_names = ["get", "patch", "head", "options"]


class DemandeCodePromoAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """Réservé à l'administrateur : consultation des codes promo distribués via la landing page."""
    queryset = DemandeCodePromo.objects.select_related("code").order_by("-date_creation")
    serializer_class = DemandeCodePromoAdminSerializer
    permission_classes = [permissions.IsAuthenticated, EstAdminSaaS]
    pagination_class = None


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, EstAdminSaaS])
def demandes_toutes(request):
    """
    GET /api/v1/contact/demandes-toutes/
    Vue unifiée de TOUTES les demandes reçues sur le site (contact,
    partenariat, code promo), peu importe leur nature, triées par date
    décroissante — utilisée par le tableau de bord du super administrateur.
    """
    demandes = []
    for d in DemandeContact.objects.all():
        demandes.append({
            "id": str(d.id), "type": "contact", "type_label": "Contact",
            "titre": d.nom, "sous_titre": f"{d.get_motif_display()} — {d.email}",
            "detail": d.message, "traite": d.traite, "date_creation": d.date_creation,
        })
    for d in DemandePartenariat.objects.all():
        demandes.append({
            "id": str(d.id), "type": "partenariat", "type_label": "Partenariat",
            "titre": d.nom, "sous_titre": d.structure or d.contact,
            "detail": d.contact, "traite": d.traite, "date_creation": d.date_creation,
        })
    for d in DemandeCodePromo.objects.select_related("code").all():
        demandes.append({
            "id": str(d.id), "type": "code_promo", "type_label": "Code promo",
            "titre": d.email, "sous_titre": d.code.code,
            "detail": f"Code {'actif' if d.code.actif else 'désactivé'}",
            "traite": True, "date_creation": d.date_creation,
        })
    demandes.sort(key=lambda d: d["date_creation"], reverse=True)
    return Response(demandes)
