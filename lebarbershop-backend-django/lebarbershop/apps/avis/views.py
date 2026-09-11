from rest_framework import viewsets, permissions
from django.db.models import Avg
from .models import Avis
from .serializers import AvisSerializer


class AvisViewSet(viewsets.ModelViewSet):
    serializer_class = AvisSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Avis.objects.select_related("salon", "client")
        salon_id = self.request.query_params.get("salon")
        if salon_id:
            qs = qs.filter(salon_id=salon_id)
        return qs
