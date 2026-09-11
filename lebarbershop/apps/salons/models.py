import uuid
from django.db import models
from django.core.validators import MinValueValidator
from apps.accounts.models import Utilisateur


class Salon(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=150)
    proprietaire = models.ForeignKey(
        Utilisateur, on_delete=models.PROTECT, related_name="salons_possedes"
    )
    nombre_employes_max = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    # Localisation
    adresse = models.CharField(max_length=255)
    ville = models.CharField(max_length=100)
    pays = models.CharField(max_length=100, default="Cameroun")
    secteur_geographique = models.CharField(
        max_length=100,
        help_text="Quartier / secteur utilisé pour les statistiques par zone."
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    telephone_contact = models.CharField(max_length=20)
    email_contact = models.EmailField(blank=True, null=True)

    class Statut(models.TextChoices):
        ACTIF = "actif", "Actif"
        SUSPENDU = "suspendu", "Suspendu"
        EN_ATTENTE = "en_attente", "En attente de paiement"

    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)

    nom_modifiable = models.BooleanField(
        default=True,
        help_text="Devient faux dès que le propriétaire a renommé le salon une fois après sa "
                   "création — le nom n'est alors plus modifiable via l'API."
    )
    photo_url = models.TextField(
        blank=True, null=True,
        help_text="Photo du salon : soit une URL externe, soit une image encodée en base64 "
                   "(data:image/...;base64,...) envoyée directement depuis le formulaire d'upload "
                   "du frontend. Un TextField plutôt qu'un URLField pour accepter les deux cas — "
                   "voir README pour un branchement vers un vrai stockage objet (S3/Cloudinary) "
                   "en production à grande échelle."
    )

    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom

    @property
    def abonnement_actif(self):
        return self.abonnements.filter(statut=Abonnement.Statut.ACTIF).order_by("-date_fin").first()


class Abonnement(models.Model):
    """
    Abonnement mensuel du salon au SAAS.
    Premier abonnement payant : 1500/mois (4500 pour 3 mois). Ensuite 1800/mois. Minimum 3 mois.
    Un essai gratuit de 14 jours (sans moyen de paiement) est possible une seule
    fois par salon — voir `est_essai` et `DUREE_ESSAI_JOURS`.
    """
    PRIX_PREMIER_ABONNEMENT_MENSUEL = 1500
    PRIX_RENOUVELLEMENT_MENSUEL = 1800
    DUREE_MINIMALE_MOIS = 1
    DUREE_ESSAI_JOURS = 30

    class Statut(models.TextChoices):
        ACTIF = "actif", "Actif"
        EXPIRE = "expire", "Expiré"
        ANNULE = "annule", "Annulé"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="abonnements")
    est_premier_abonnement = models.BooleanField(default=False)
    est_essai = models.BooleanField(
        default=False,
        help_text="Essai gratuit de 15 jours, sans paiement ni carte bancaire, limité à un par salon."
    )
    duree_mois = models.PositiveSmallIntegerField(null=True, blank=True)
    prix_mensuel = models.DecimalField(max_digits=10, decimal_places=2)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)

    code_reduction = models.ForeignKey(
        "salons.CodeReduction", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="abonnements"
    )
    code_sponsoring = models.ForeignKey(
        "salons.CodeSponsoring", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="abonnements"
    )

    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.ACTIF)

    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Abonnement {self.salon.nom} ({self.date_debut:%d/%m/%Y} - {self.date_fin:%d/%m/%Y})"


class CodeReduction(models.Model):
    """Codes de réduction créés par l'administrateur principal (ou secondaire habilité)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)
    montant_reduction = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Montant fixe (en FCFA) déduit du montant total, et non un pourcentage.",
    )
    # Propriétaire du code (point demandé explicitement) : la personne à qui
    # ce code est destiné/attribué et son moyen de contact — distinct de
    # `cree_par`, qui est l'administrateur ayant créé le code.
    proprietaire_nom = models.CharField(max_length=150, blank=True, null=True)
    proprietaire_contact = models.CharField(
        max_length=150, blank=True, null=True,
        help_text="Email ou téléphone du propriétaire du code."
    )
    cree_par = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateTimeField(null=True, blank=True)
    actif = models.BooleanField(default=True)
    nombre_utilisations_max = models.PositiveIntegerField(null=True, blank=True)
    nombre_utilisations = models.PositiveIntegerField(
        default=0, help_text="Compteur incrémenté à chaque abonnement souscrit avec ce code."
    )

    def __str__(self):
        return self.code


class CodeSponsoring(models.Model):
    """
    Codes distribués à des tiers (autres gérants de salon, agents marketing)
    OU achetés par un employé du SAAS via le programme partenaire (point 7
    du cahier des charges "espace employé") : un employé achète un code à
    PRIX_ACHAT_PARTENAIRE, le revend/partage, et gagne COMMISSION_PAR_UTILISATION
    à chaque fois qu'un nouveau salon souscrit un abonnement avec ce code.

    Pour le programme partenaire employé, le code n'est définitivement
    attribué (actif) qu'après confirmation du paiement (Orange Money, MTN
    MoMo ou carte bancaire) — voir CodeSponsoringViewSet.demander_achat et
    .confirmer_paiement.
    """
    PRIX_ACHAT_PARTENAIRE = 500
    COMMISSION_PAR_UTILISATION = 250
    REDUCTION_UTILISATEUR_PAR_DEFAUT = 250  # FCFA accordés à qui utilise le code, distinct de la commission

    class Statut(models.TextChoices):
        ACTIF = "actif", "Actif"
        EN_ATTENTE_PAIEMENT = "en_attente_paiement", "En attente de paiement"

    class ModePaiement(models.TextChoices):
        ORANGE_MONEY = "orange_money", "Orange Money"
        MTN_MOMO = "mtn_momo", "MTN Mobile Money"
        CARTE_BANCAIRE = "carte_bancaire", "Carte bancaire"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)
    beneficiaire_nom = models.CharField(max_length=150)
    beneficiaire_contact = models.CharField(max_length=100, blank=True, null=True)
    beneficiaire_utilisateur = models.ForeignKey(
        Utilisateur, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="codes_sponsoring_achetes",
        help_text="Renseigné uniquement pour les codes achetés via le programme partenaire employé.",
    )
    commission_pourcentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    montant_reduction_utilisateur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Montant fixe (en FCFA) déduit du montant total de l'abonnement pour la "
                   "personne qui utilise ce code à la souscription/au renouvellement — "
                   "distinct de la commission versée au propriétaire du code.",
    )
    est_partenaire_employe = models.BooleanField(default=False)
    prix_achat = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission_fixe_par_utilisation = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    nombre_utilisations = models.PositiveIntegerField(default=0)
    cree_par = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, related_name="codes_sponsoring_crees")
    date_creation = models.DateTimeField(auto_now_add=True)
    actif = models.BooleanField(default=True)
    statut = models.CharField(max_length=25, choices=Statut.choices, default=Statut.ACTIF)
    mode_paiement = models.CharField(max_length=20, choices=ModePaiement.choices, blank=True, null=True)
    date_paiement_confirme = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} -> {self.beneficiaire_nom}"

    @property
    def gains_cumules(self):
        return self.nombre_utilisations * self.commission_fixe_par_utilisation

    @staticmethod
    def generer_code_partenaire(utilisateur):
        import secrets
        base = (utilisateur.first_name or utilisateur.username)[:10].upper().replace(" ", "")
        while True:
            code = f"PART-{base}-{secrets.token_hex(2).upper()}"
            if not CodeSponsoring.objects.filter(code=code).exists():
                return code


class AbonnementAnalyseSectorielle(models.Model):
    """
    Abonnement payant pour utilisateurs lambda :
    - 20000 : accès aux statistiques de secteurs rentables / non occupés.
    - 25000 : accès complet (standards, matériel, salaires, rendements).
    """
    class Type(models.TextChoices):
        SECTEURS_RENTABLES = "secteurs_rentables", "Analyse des secteurs rentables (20000)"
        GESTION_COMPLETE = "gestion_complete", "Analyse de gestion complète (25000)"

    PRIX = {
        Type.SECTEURS_RENTABLES: 20000,
        Type.GESTION_COMPLETE: 25000,
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(
        Utilisateur, on_delete=models.CASCADE, related_name="abonnements_analyse"
    )
    type_abonnement = models.CharField(max_length=30, choices=Type.choices)
    montant_paye = models.DecimalField(max_digits=10, decimal_places=2)
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    actif = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.utilisateur} - {self.get_type_abonnement_display()}"


class Forfait(models.Model):
    """
    Forfait configurable par l'administrateur principal, affiché sur la
    landing page (section « Nos forfaits ») et utilisable comme référence de
    prix lors de la souscription. Découple les prix affichés au public des
    valeurs actuellement codées en dur dans Abonnement / AbonnementAnalyseSectorielle,
    pour permettre à l'admin de faire évoluer la grille tarifaire sans déploiement.
    """

    class Type(models.TextChoices):
        ABONNEMENT_SALON = "abonnement_salon", "Abonnement salon"
        ANALYSE_SECTORIELLE = "analyse_sectorielle", "Analyse sectorielle"
        AUTRE = "autre", "Autre"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    type_forfait = models.CharField(max_length=30, choices=Type.choices)
    description = models.CharField(max_length=255, blank=True, null=True)
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    duree_mois = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Laisser vide si le forfait n'est pas périodique (ex. analyse sectorielle)."
    )
    avantages = models.JSONField(
        default=list, blank=True,
        help_text="Liste de courtes phrases affichées comme avantages sur la landing page."
    )
    ordre_affichage = models.PositiveSmallIntegerField(default=0)
    actif = models.BooleanField(default=True)
    cree_par = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, related_name="forfaits_crees")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["ordre_affichage", "prix"]

    def __str__(self):
        return f"{self.nom} — {self.prix} FCFA"
