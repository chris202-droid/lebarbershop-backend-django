from rest_framework import serializers
from .models import Soin


class SoinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Soin
        fields = "__all__"
        read_only_fields = ["id"]
