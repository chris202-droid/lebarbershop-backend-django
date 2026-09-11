from rest_framework import serializers
from .models import Salon, Abonnement, CodeReduction, CodeSponsoring, AbonnementAnalyseSectorielle, Forfait


class SalonSerializer(serializers.ModelSerializer):
    abonnement_actif_id = serializers.SerializerMethodField()

    class Meta:
        model = Salon
        fields = [
            "id", "nom", "proprietaire", "nombre_employes_max", "adresse", "ville",
            "pays", "secteur_geographique", "latitude", "longitude",
            "telephone_contact", "email_contact", "statut", "nom_modifiable",
            "photo_url", "date_creation", "abonnement_actif_id",
        ]
        read_only_fields = ["id", "statut", "date_creation", "proprietaire", "nom_modifiable"]

    def get_abonnement_actif_id(self, obj):
        actif = obj.abonnement_actif
        return actif.id if actif else None


class AbonnementSerializer(serializers.ModelSerializer):
    duree_mois = serializers.IntegerField(required=True)
    salon_nom = serializers.CharField(source="salon.nom", read_only=True)
    # Point 1 : un seul champ texte, public, où saisir SOIT un code de
    # réduction SOIT un code de sponsoring/parrainage — la résolution vers
    # le bon type se fait ici plutôt que d'exiger que l'appelant connaisse
    # l'UUID interne du code (`code_reduction`/`code_sponsoring` restent
    # utilisables directement par l'admin, mais `code_promo` est le champ
    # destiné au formulaire de paiement du gestionnaire).
    code_promo = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Abonnement
        fields = "__all__"
        read_only_fields = ["id", "montant_total", "date_creation", "est_essai"]

    def validate_duree_mois(self, value):
        if value < Abonnement.DUREE_MINIMALE_MOIS:
            raise serializers.ValidationError(
                f"La durée minimale d'abonnement est de {Abonnement.DUREE_MINIMALE_MOIS} mois."
            )
        return value

    def _valider_code_reduction(self, code):
        from django.utils import timezone
        if not code.actif:
            raise serializers.ValidationError({"code_promo": "Ce code n'est plus actif."})
        if code.date_expiration and code.date_expiration < timezone.now():
            raise serializers.ValidationError({"code_promo": "Ce code a expiré."})
        if code.nombre_utilisations_max is not None and code.nombre_utilisations >= code.nombre_utilisations_max:
            raise serializers.ValidationError({"code_promo": "Ce code a atteint son nombre maximal d'utilisations."})

    def validate_code_reduction(self, code):
        if code is not None:
            self._valider_code_reduction(code)
        return code

    def validate(self, attrs):
        code_promo = attrs.pop("code_promo", None)
        self._code_reduction_resolu = attrs.get("code_reduction")
        self._code_sponsoring_resolu = attrs.get("code_sponsoring")

        if code_promo:
            reduction = CodeReduction.objects.filter(code=code_promo).first()
            if reduction:
                self._valider_code_reduction(reduction)
                self._code_reduction_resolu = reduction
            else:
                sponsoring = CodeSponsoring.objects.filter(code=code_promo, actif=True, statut=CodeSponsoring.Statut.ACTIF).first()
                if not sponsoring:
                    raise serializers.ValidationError({"code_promo": "Ce code n'existe pas ou n'est plus valide."})
                self._code_sponsoring_resolu = sponsoring
        return attrs

    def create(self, validated_data):
        est_premier = validated_data.get("est_premier_abonnement", False)
        prix_mensuel = (
            Abonnement.PRIX_PREMIER_ABONNEMENT_MENSUEL if est_premier
            else Abonnement.PRIX_RENOUVELLEMENT_MENSUEL
        )
        validated_data["prix_mensuel"] = prix_mensuel
        montant = prix_mensuel * validated_data["duree_mois"]

        # Points 1 et 2 : la remise (réduction ou sponsoring, résolue depuis
        # `code_promo` ou fournie directement via `code_reduction`/
        # `code_sponsoring`) est un MONTANT FIXE déduit du total, pas un
        # pourcentage.
        code_reduction = self._code_reduction_resolu
        code_sponsoring = self._code_sponsoring_resolu
        validated_data["code_reduction"] = code_reduction
        validated_data["code_sponsoring"] = code_sponsoring

        if code_reduction:
            montant = max(montant - code_reduction.montant_reduction * validated_data["duree_mois"], 0)
        if code_sponsoring and code_sponsoring.montant_reduction_utilisateur:
            montant = max(montant - code_sponsoring.montant_reduction_utilisateur * validated_data["duree_mois"], 0)

        validated_data["montant_total"] = montant
        abonnement = super().create(validated_data)

        if code_reduction:
            code_reduction.nombre_utilisations += 1
            code_reduction.save(update_fields=["nombre_utilisations"])

        # Programme partenaire (points 16/18) : chaque souscription utilisant
        # un code de sponsoring actif crédite son propriétaire de la
        # commission fixe (200 FCFA par défaut) et incrémente son compteur
        # d'utilisations affiché dans son tableau de bord.
        if code_sponsoring and code_sponsoring.statut == CodeSponsoring.Statut.ACTIF:
            code_sponsoring.nombre_utilisations += 1
            code_sponsoring.save(update_fields=["nombre_utilisations"])

        return abonnement


class CodeReductionSerializer(serializers.ModelSerializer):
    # Saisie plus simple pour l'administrateur qu'une date d'expiration
    # absolue : indiquer une durée de validité en jours à partir de
    # aujourd'hui. Ignoré si `date_expiration` est fourni explicitement.
    duree_jours = serializers.IntegerField(write_only=True, required=False, min_value=1)

    class Meta:
        model = CodeReduction
        fields = "__all__"
        read_only_fields = ["id", "cree_par", "date_creation", "nombre_utilisations"]

    def create(self, validated_data):
        duree_jours = validated_data.pop("duree_jours", None)
        if duree_jours and not validated_data.get("date_expiration"):
            from django.utils import timezone
            validated_data["date_expiration"] = timezone.now() + timezone.timedelta(days=duree_jours)
        return super().create(validated_data)


class CodeSponsoringSerializer(serializers.ModelSerializer):
    gains_cumules = serializers.ReadOnlyField()

    class Meta:
        model = CodeSponsoring
        fields = "__all__"
        read_only_fields = [
            "id", "cree_par", "date_creation", "code", "beneficiaire_utilisateur",
            "est_partenaire_employe", "prix_achat", "commission_fixe_par_utilisation",
            "nombre_utilisations", "gains_cumules",
        ]


class AbonnementAnalyseSectorielleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbonnementAnalyseSectorielle
        fields = "__all__"
        read_only_fields = ["id", "utilisateur", "montant_paye"]

    def create(self, validated_data):
        type_abo = validated_data["type_abonnement"]
        validated_data["montant_paye"] = AbonnementAnalyseSectorielle.PRIX[type_abo]
        return super().create(validated_data)


class ForfaitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forfait
        fields = [
            "id", "nom", "type_forfait", "description", "prix", "duree_mois",
            "avantages", "ordre_affichage", "actif", "date_creation", "date_modification",
        ]
        read_only_fields = ["id", "date_creation", "date_modification"]


class SalonAdminSerializer(serializers.ModelSerializer):
    """
    Vue étendue d'un salon pour l'administrateur : expose des informations
    sur le propriétaire (non exposées via SalonSerializer côté gestionnaire),
    les détails complets de l'abonnement en cours (et pas seulement son id,
    pour retrouver côté React tout ce qui est visible dans le Django admin :
    statut, essai gratuit, dates, montant), et autorise la modification du
    nom sans la restriction "une seule fois" qui s'applique uniquement au
    propriétaire.
    """
    proprietaire_username = serializers.CharField(source="proprietaire.username", read_only=True)
    proprietaire_email = serializers.EmailField(source="proprietaire.email", read_only=True)
    proprietaire_telephone = serializers.CharField(source="proprietaire.telephone", read_only=True)
    abonnement_actif_id = serializers.SerializerMethodField()
    abonnement_actif = serializers.SerializerMethodField()

    class Meta:
        model = Salon
        fields = [
            "id", "nom", "proprietaire", "proprietaire_username", "proprietaire_email",
            "proprietaire_telephone", "nombre_employes_max", "adresse", "ville", "pays",
            "secteur_geographique", "latitude", "longitude", "telephone_contact",
            "email_contact", "statut", "photo_url", "date_creation",
            "abonnement_actif_id", "abonnement_actif",
        ]
        read_only_fields = ["id", "proprietaire", "date_creation"]

    def get_abonnement_actif_id(self, obj):
        actif = obj.abonnement_actif
        return actif.id if actif else None

    def get_abonnement_actif(self, obj):
        actif = obj.abonnement_actif
        if not actif:
            return None
        return {
            "id": actif.id,
            "statut": actif.statut,
            "est_essai": actif.est_essai,
            "date_debut": actif.date_debut,
            "date_fin": actif.date_fin,
            "duree_mois": actif.duree_mois,
            "montant_total": actif.montant_total,
        }
