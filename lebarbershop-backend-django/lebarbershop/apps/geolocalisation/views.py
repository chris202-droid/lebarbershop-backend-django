from rest_framework import viewsets, permissions
from .models import SecteurGeographique
from .serializers import SecteurGeographiqueSerializer


class SecteurGeographiqueViewSet(viewsets.ModelViewSet):
    queryset = SecteurGeographique.objects.all()
    serializer_class = SecteurGeographiqueSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
