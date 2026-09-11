from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import PaiementAbonnement
from .serializers import PaiementAbonnementSerializer


class PaiementAbonnementViewSet(viewsets.ModelViewSet):
    """
    Initie et suit les paiements d'abonnement (Orange Money, MTN MoMo, carte bancaire).
    L'intégration effective avec les passerelles de paiement (webhooks, signatures)
    est à brancher ici, dans confirmer().
    """
    serializer_class = PaiementAbonnementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PaiementAbonnement.objects.filter(abonnement__salon__proprietaire=self.request.user)

    @action(detail=True, methods=["post"], url_path="confirmer")
    def confirmer(self, request, pk=None):
        """Webhook / callback de confirmation venant de la passerelle de paiement."""
        paiement = self.get_object()
        paiement.statut = PaiementAbonnement.Statut.REUSSI
        paiement.date_confirmation = timezone.now()
        paiement.save()
        return Response(PaiementAbonnementSerializer(paiement).data)
