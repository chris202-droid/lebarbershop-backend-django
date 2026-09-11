import uuid
from django.db import models
from apps.salons.models import Abonnement


class PaiementAbonnement(models.Model):
    """Trace chaque paiement effectué pour un abonnement de salon au SAAS."""

    class ModePaiement(models.TextChoices):
        ORANGE_MONEY = "orange_money", "Orange Money"
        MTN_MOMO = "mtn_momo", "MTN Mobile Money"
        CARTE_BANCAIRE = "carte_bancaire", "Carte bancaire (Visa/Mastercard)"

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        REUSSI = "reussi", "Réussi"
        ECHOUE = "echoue", "Échoué"
        REMBOURSE = "rembourse", "Remboursé"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    abonnement = models.ForeignKey(Abonnement, on_delete=models.CASCADE, related_name="paiements")
    mode_paiement = models.CharField(max_length=20, choices=ModePaiement.choices)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    reference_transaction = models.CharField(max_length=100, unique=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_confirmation = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_mode_paiement_display()} - {self.montant} ({self.statut})"
