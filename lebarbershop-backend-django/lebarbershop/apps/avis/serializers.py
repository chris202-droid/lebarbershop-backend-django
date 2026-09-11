from rest_framework import serializers
from .models import Avis


class AvisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avis
        fields = "__all__"
        read_only_fields = ["id", "date_creation"]
