from rest_framework import serializers
from .models import PaiementAbonnement


class PaiementAbonnementSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaiementAbonnement
        fields = "__all__"
        read_only_fields = ["id", "statut", "date_creation", "date_confirmation"]
