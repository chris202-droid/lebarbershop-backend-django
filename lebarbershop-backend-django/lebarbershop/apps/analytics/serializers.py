from rest_framework import serializers
from .models import RendementEmployeJournalier, BilanJournalierSalon


class RendementEmployeJournalierSerializer(serializers.ModelSerializer):
    class Meta:
        model = RendementEmployeJournalier
        fields = "__all__"


class BilanJournalierSalonSerializer(serializers.ModelSerializer):
    class Meta:
        model = BilanJournalierSalon
        fields = "__all__"
