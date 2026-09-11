from rest_framework import viewsets, permissions, filters
from .models import Client, FideliteClientSalon
from .serializers import ClientSerializer, FideliteClientSalonSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["nom", "telephone", "email"]


class FideliteClientSalonViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FideliteClientSalon.objects.select_related("client", "salon")
    serializer_class = FideliteClientSalonSerializer
    permission_classes = [permissions.IsAuthenticated]
