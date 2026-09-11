import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.salons.models import Salon
from apps.clients.models import Client


class Avis(models.Model):
    """Note + commentaire laissés par un client sur un salon."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="avis")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="avis_laisses")
    note = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    commentaire = models.TextField(blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.note}/5 - {self.salon.nom}"
