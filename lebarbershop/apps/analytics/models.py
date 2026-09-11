from django.db import models
from apps.salons.models import Salon
from apps.employes.models import Employe


class RendementEmployeJournalier(models.Model):
    """
    Snapshot journalier du rendement d'un employé, calculé/agrégé à partir des
    LigneTicket. Permet des requêtes rapides pour les courbes de performance
    (jour, semaine, mois, plusieurs mois) sans recalculer sur les tickets bruts.
    """
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name="rendements_journaliers")
    date = models.DateField()
    nombre_soins = models.PositiveIntegerField(default=0)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ("employe", "date")

    def __str__(self):
        return f"{self.employe} - {self.date} : {self.montant_total}"


class BilanJournalierSalon(models.Model):
    """Bilan agrégé par salon et par jour : dépenses et entrées, globales et par catégorie."""
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="bilans_journaliers")
    date = models.DateField()

    entrees_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    entrees_coiffure_homme = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    entrees_coiffure_femme = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    entrees_esthetique = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    entrees_pedicure = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    entrees_manucure = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    entrees_autre = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    depenses_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ("salon", "date")

    def __str__(self):
        return f"{self.salon.nom} - {self.date}"
