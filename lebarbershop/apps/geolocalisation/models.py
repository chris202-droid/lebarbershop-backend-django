from django.db import models
from apps.salons.models import Salon


class SecteurGeographique(models.Model):
    """
    Regroupe les salons par secteur pour les statistiques de rentabilité
    et pour l'analyse des secteurs occupés/non occupés (abonnement 20000).
    """
    nom = models.CharField(max_length=100, unique=True)
    ville = models.CharField(max_length=100)
    pays = models.CharField(max_length=100, default="Cameroun")

    def __str__(self):
        return f"{self.nom}, {self.ville}"

    @property
    def salons(self):
        return Salon.objects.filter(secteur_geographique=self.nom, ville=self.ville)

    @property
    def nombre_salons(self):
        return self.salons.count()
