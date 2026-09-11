import uuid
import secrets
from django.db import models
from apps.accounts.models import Utilisateur
from apps.salons.models import CodeReduction


class DemandeContact(models.Model):
    """Message envoyé depuis le formulaire 'Nous contacter' de la landing page."""

    class Motif(models.TextChoices):
        PARTENARIAT = "partenariat", "Devenir partenaire"
        OUVERTURE_SALON = "ouverture_salon", "Ouvrir un salon"
        INFORMATION = "information", "Prise d'information"
        AUTRE = "autre", "Autre"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=150)
    email = models.EmailField()
    motif = models.CharField(max_length=30, choices=Motif.choices, default=Motif.INFORMATION)
    message = models.TextField()
    traite = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nom} <{self.email}> — {self.get_motif_display()}"


class DemandePartenariat(models.Model):
    """Demande envoyée depuis le formulaire 'Devenir partenaire' (agents / gérants de salon)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=150)
    structure = models.CharField(max_length=150, blank=True, null=True)
    contact = models.CharField(max_length=150, help_text="Email ou téléphone du demandeur.")
    traite = models.BooleanField(default=False)
    code_sponsoring_attribue = models.ForeignKey(
        "salons.CodeSponsoring", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="demande_origine"
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nom} ({self.contact})"


class DemandeCodePromo(models.Model):
    """
    Demande envoyée depuis le formulaire 'Obtenir un code promo'.
    Un CodeReduction est généré automatiquement et renvoyé immédiatement dans
    la réponse de l'API (pas d'envoi d'email configuré à ce stade).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    code = models.ForeignKey(CodeReduction, on_delete=models.CASCADE, related_name="demande_origine")
    date_creation = models.DateTimeField(auto_now_add=True)

    MONTANT_PAR_DEFAUT = 500  # FCFA, montant fixe (et non un pourcentage)
    VALIDITE_JOURS = 30

    def __str__(self):
        return f"{self.email} -> {self.code.code}"

    @staticmethod
    def generer_code_unique():
        """Génère un code lisible et unique, ex. BIENVENUE-4F92A1."""
        from django.utils import timezone
        while True:
            suffixe = secrets.token_hex(3).upper()
            code = f"BIENVENUE-{suffixe}"
            if not CodeReduction.objects.filter(code=code).exists():
                return code

    @classmethod
    def creer_pour_email(cls, email):
        from django.utils import timezone
        code_reduction = CodeReduction.objects.create(
            code=cls.generer_code_unique(),
            montant_reduction=cls.MONTANT_PAR_DEFAUT,
            date_expiration=timezone.now() + timezone.timedelta(days=cls.VALIDITE_JOURS),
            nombre_utilisations_max=1,
        )
        return cls.objects.create(email=email, code=code_reduction)
