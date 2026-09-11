from rest_framework import serializers
from .models import Client, FideliteClientSalon


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"
        read_only_fields = ["id", "date_creation"]


class FideliteClientSalonSerializer(serializers.ModelSerializer):
    class Meta:
        model = FideliteClientSalon
        fields = "__all__"
