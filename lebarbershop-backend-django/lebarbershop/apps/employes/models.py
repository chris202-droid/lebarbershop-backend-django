import uuid
from django.db import models
from apps.accounts.models import Utilisateur
from apps.salons.models import Salon


class Employe(models.Model):
    class Role(models.TextChoices):
        COIFFEUR_HOMME = "coiffeur_homme", "Coiffeur homme"
        COIFFEUSE_FEMME = "coiffeuse_femme", "Coiffeuse femme"
        CAISSIERE = "caissiere", "Caissière"
        MAQUILLEUSE = "maquilleuse", "Maquilleuse"
        ESTHETICIENNE = "estheticienne", "Esthéticienne"
        GESTIONNAIRE = "gestionnaire", "Gestionnaire du salon"
        AUTRE = "autre", "Autre"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(
        Utilisateur, on_delete=models.CASCADE, related_name="postes_employe"
    )
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="employes")
    role = models.CharField(max_length=30, choices=Role.choices)
    role_autre_precision = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Précision du rôle si 'Autre' est sélectionné."
    )
    actif = models.BooleanField(default=True)
    date_embauche = models.DateField(auto_now_add=True)

    # Permissions granulaires sur le cycle de vie des tickets (point 4) :
    # un manager peut désigner un autre manager (co-gestionnaire) et lui
    # retirer certaines capacités, plutôt que de tout lui accorder par
    # défaut. Ces champs s'appliquent à tous les rôles pour rester simples,
    # mais ne sont exposés à l'édition côté frontend que pour les employés
    # ayant le rôle "gestionnaire" — le propriétaire réel du salon n'est lui
    # jamais restreint par ces indicateurs (voir apps/tickets/views.py).
    peut_creer_ticket = models.BooleanField(default=True)
    peut_confirmer_ticket = models.BooleanField(default=True)
    peut_valider_ticket = models.BooleanField(default=True)

    class Meta:
        unique_together = ("utilisateur", "salon")

    def __str__(self):
        return f"{self.utilisateur} - {self.get_role_display()} @ {self.salon.nom}"

    def clean(self):
        # Le nombre d'employés actifs ne doit pas dépasser nombre_employes_max du salon
        from django.core.exceptions import ValidationError
        if self.salon.employes.filter(actif=True).exclude(pk=self.pk).count() >= self.salon.nombre_employes_max:
            raise ValidationError("Le nombre maximal d'employés pour ce salon est atteint.")
