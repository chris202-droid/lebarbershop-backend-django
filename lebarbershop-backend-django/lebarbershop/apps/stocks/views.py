from rest_framework import viewsets, permissions
from .models import Produit, MouvementStock
from .serializers import ProduitSerializer, MouvementStockSerializer


class ProduitViewSet(viewsets.ModelViewSet):
    serializer_class = ProduitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Produit.objects.select_related("salon")
        salon_id = self.request.query_params.get("salon")
        if salon_id:
            qs = qs.filter(salon_id=salon_id)
        categorie = self.request.query_params.get("categorie")
        if categorie:
            qs = qs.filter(categorie=categorie)
        en_alerte = self.request.query_params.get("en_alerte")
        if en_alerte == "true":
            from django.db.models import F
            qs = qs.filter(quantite_stock__lte=F("seuil_alerte"))
        return qs


class MouvementStockViewSet(viewsets.ModelViewSet):
    queryset = MouvementStock.objects.select_related("produit")
    serializer_class = MouvementStockSerializer
    permission_classes = [permissions.IsAuthenticated]
