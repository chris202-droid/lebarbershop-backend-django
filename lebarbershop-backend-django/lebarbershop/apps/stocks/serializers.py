from rest_framework import serializers
from .models import Produit, MouvementStock


class ProduitSerializer(serializers.ModelSerializer):
    en_alerte_stock = serializers.ReadOnlyField()

    class Meta:
        model = Produit
        fields = "__all__"
        read_only_fields = ["id"]


class MouvementStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = MouvementStock
        fields = "__all__"
        read_only_fields = ["id", "date"]

    def create(self, validated_data):
        mouvement = super().create(validated_data)
        produit = mouvement.produit
        produit.quantite_stock += mouvement.quantite
        if mouvement.type_mouvement == MouvementStock.TypeMouvement.ACHAT:
            from django.utils import timezone
            produit.date_dernier_achat = timezone.now().date()
        produit.save()
        return mouvement
