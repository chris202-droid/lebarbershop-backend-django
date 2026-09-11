import uuid
from django.db import models
from apps.salons.models import Salon


class Client(models.Model):
    """
    Client d'un ou plusieurs salons. Peut être créé à la volée par un coiffeur
    lorsqu'il n'existe pas encore en base.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=150)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom


class FideliteClientSalon(models.Model):
    """
    Compteur de visites d'un client dans un salon précis, utilisé pour
    accorder des réductions de fidélité.
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="fidelites")
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="fidelites_clients")
    nombre_visites = models.PositiveIntegerField(default=0)
    derniere_visite = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("client", "salon")

    def __str__(self):
        return f"{self.client.nom} @ {self.salon.nom} : {self.nombre_visites} visites"
