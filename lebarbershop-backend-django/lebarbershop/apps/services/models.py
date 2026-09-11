import uuid
from django.db import models
from apps.salons.models import Salon


class Soin(models.Model):
    """Un soin/service proposé par un salon (coupe, coiffure, maquillage, etc.)."""

    class Categorie(models.TextChoices):
        COIFFURE_HOMME = "coiffure_homme", "Coiffure homme"
        COIFFURE_FEMME = "coiffure_femme", "Coiffure femme"
        ESTHETIQUE = "esthetique", "Esthétique"
        PEDICURE = "pedicure", "Pédicure"
        MANUCURE = "manucure", "Manucure"
        AUTRE = "autre", "Autre"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="soins")
    nom = models.CharField(max_length=150)
    categorie = models.CharField(max_length=30, choices=Categorie.choices)
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    duree_estimee_minutes = models.PositiveIntegerField(default=30)
    actif = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nom} ({self.salon.nom}) - {self.prix}"
