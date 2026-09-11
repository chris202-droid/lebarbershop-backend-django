import uuid
from django.db import models
from apps.salons.models import Salon
from apps.clients.models import Client
from apps.employes.models import Employe
from apps.services.models import Soin


class Ticket(models.Model):
    """
    Ticket de soins ouvert par un employé (coiffeur, coiffeuse, etc.),
    présenté à la caissière pour paiement/validation.
    Peut contenir plusieurs soins exécutés par des employés différents.
    """

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente de paiement"
        VALIDE = "valide", "Validé / payé"
        ANNULE = "annule", "Annulé"

    class ModePaiement(models.TextChoices):
        ESPECES = "especes", "Espèces"
        ORANGE_MONEY = "orange_money", "Orange Money"
        MTN_MOMO = "mtn_momo", "MTN Mobile Money"
        CARTE_BANCAIRE = "carte_bancaire", "Carte bancaire"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="tickets")
    client = models.ForeignKey(
        Client, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets"
    )
    nom_client_temporaire = models.CharField(
        max_length=150, blank=True, null=True,
        help_text="Utilisé si le client n'existe pas encore en base."
    )
    employe_createur = models.ForeignKey(
        Employe, on_delete=models.PROTECT, related_name="tickets_crees"
    )
    caissiere_validatrice = models.ForeignKey(
        Employe, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tickets_valides"
    )

    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    mode_paiement = models.CharField(max_length=20, choices=ModePaiement.choices, blank=True, null=True)

    reduction_pourcentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    montant_brut = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    montant_net = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Ticket #{str(self.id)[:8]} - {self.salon.nom}"

    def recalculer_montants(self):
        # Les lignes annulées par l'employé assigné (client ne s'est pas
        # présenté / a annulé le soin) ne comptent pas dans le total.
        total = sum(l.prix for l in self.lignes.exclude(statut=LigneTicket.Statut.ANNULE))
        self.montant_brut = total
        self.montant_net = total * (1 - self.reduction_pourcentage / 100)

    def generer_nom_client_defaut(self):
        """
        Génère un nom de client par défaut du type "Clt1.28.8.26" (client
        n°1 de la journée, 28 août 2026) lorsque ni client existant ni nom
        temporaire ne sont fournis à la création du ticket.
        """
        from django.utils import timezone
        aujourd_hui = timezone.now().date()
        rang = Ticket.objects.filter(salon=self.salon, date_creation__date=aujourd_hui).count() + 1
        return f"Clt{rang}.{aujourd_hui.day}.{aujourd_hui.month}.{aujourd_hui.strftime('%y')}"


class LigneTicket(models.Model):
    """Un soin précis dans un ticket, exécuté par un employé précis."""

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        CONFIRME = "confirme", "Confirmé (soin réalisé)"
        ANNULE = "annule", "Annulé (client absent/annulation)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="lignes")
    soin = models.ForeignKey(Soin, on_delete=models.PROTECT, related_name="lignes_ticket")
    employe_executant = models.ForeignKey(
        Employe, on_delete=models.PROTECT, related_name="soins_a_executer"
    )
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)

    def __str__(self):
        return f"{self.soin.nom} par {self.employe_executant}"
