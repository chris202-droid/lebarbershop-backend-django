from rest_framework import viewsets, permissions, filters
from .models import Soin
from .serializers import SoinSerializer


class SoinViewSet(viewsets.ModelViewSet):
    serializer_class = SoinSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["nom", "categorie"]

    def get_queryset(self):
        qs = Soin.objects.select_related("salon")
        salon_id = self.request.query_params.get("salon")
        if salon_id:
            qs = qs.filter(salon_id=salon_id)
        return qs
