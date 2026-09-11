from rest_framework import serializers
from .models import SecteurGeographique


class SecteurGeographiqueSerializer(serializers.ModelSerializer):
    nombre_salons = serializers.ReadOnlyField()

    class Meta:
        model = SecteurGeographique
        fields = ["id", "nom", "ville", "pays", "nombre_salons"]
