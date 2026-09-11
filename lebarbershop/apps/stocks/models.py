import uuid
from django.db import models
from apps.salons.models import Salon
from apps.tickets.models import Ticket


class Produit(models.Model):
    """Produit acheté et utilisé par le salon (consommables coiffure/esthétique)."""

    class Categorie(models.TextChoices):
        MATERIEL = "materiel", "Matériel"
        PRODUIT_HOMME = "produit_homme", "Produit homme"
        PRODUIT_FEMME = "produit_femme", "Produit femme"
        ESTHETIQUE = "esthetique", "Esthétique"
        AUTRE = "autre", "Autre"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="produits")
    nom = models.CharField(max_length=150)
    categorie = models.CharField(max_length=20, choices=Categorie.choices, default=Categorie.AUTRE)
    quantite_stock = models.PositiveIntegerField(default=0)
    seuil_alerte = models.PositiveIntegerField(
        default=5, help_text="En dessous de ce seuil, une alerte de rupture est envoyée."
    )
    prix_unitaire_achat = models.DecimalField(max_digits=10, decimal_places=2)
    date_dernier_achat = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.nom} ({self.salon.nom})"

    @property
    def en_alerte_stock(self):
        return self.quantite_stock <= self.seuil_alerte


class MouvementStock(models.Model):
    """Historique des mouvements de stock (achat ou consommation liée à un ticket)."""

    class TypeMouvement(models.TextChoices):
        ACHAT = "achat", "Achat / réapprovisionnement"
        CONSOMMATION = "consommation", "Consommation (soin exécuté)"
        AJUSTEMENT = "ajustement", "Ajustement manuel"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="mouvements")
    type_mouvement = models.CharField(max_length=20, choices=TypeMouvement.choices)
    quantite = models.IntegerField(help_text="Positif pour un achat, négatif pour une consommation.")
    ticket_associe = models.ForeignKey(
        Ticket, on_delete=models.SET_NULL, null=True, blank=True, related_name="mouvements_stock"
    )
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.produit.nom} : {self.quantite} ({self.get_type_mouvement_display()})"
