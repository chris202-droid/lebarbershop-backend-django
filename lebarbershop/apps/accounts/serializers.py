from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Utilisateur, DroitAdministrateur


class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = [
            "id", "username", "first_name", "last_name", "email", "telephone",
            "langue_preferee", "zone_geographique", "est_admin_principal",
            "est_admin_secondaire", "is_superuser", "mot_de_passe_temporaire", "photo_url",
            "date_creation",
        ]
        read_only_fields = ["id", "est_admin_principal", "is_superuser", "mot_de_passe_temporaire", "date_creation"]


class InscriptionSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Utilisateur
        fields = ["username", "first_name", "last_name", "email", "telephone", "password", "langue_preferee"]

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("telephone"):
            raise serializers.ValidationError("Un email ou un numéro de téléphone est requis.")
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = Utilisateur(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ChangerMotDePasseSerializer(serializers.Serializer):
    """
    Changement de mot de passe. `ancien_mot_de_passe` n'est exigé que si le
    compte n'est PAS en mot de passe temporaire (cas d'un employé qui doit
    changer son mot de passe imposé par le gestionnaire à sa première
    connexion : il n'a pas besoin de connaître "l'ancien").
    """
    ancien_mot_de_passe = serializers.CharField(write_only=True, required=False, allow_blank=True)
    nouveau_mot_de_passe = serializers.CharField(write_only=True, validators=[validate_password])

    def validate(self, attrs):
        utilisateur = self.context["request"].user
        if not utilisateur.mot_de_passe_temporaire:
            if not attrs.get("ancien_mot_de_passe") or not utilisateur.check_password(attrs["ancien_mot_de_passe"]):
                raise serializers.ValidationError({"ancien_mot_de_passe": "Mot de passe actuel incorrect."})
        return attrs

    def save(self, **kwargs):
        utilisateur = self.context["request"].user
        utilisateur.set_password(self.validated_data["nouveau_mot_de_passe"])
        utilisateur.mot_de_passe_temporaire = False
        utilisateur.save(update_fields=["password", "mot_de_passe_temporaire"])
        return utilisateur


class DroitAdministrateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = DroitAdministrateur
        fields = "__all__"
        read_only_fields = ["attribue_par", "date_attribution"]


class AdministrateurSecondaireSerializer(serializers.ModelSerializer):
    """
    Vue combinée utilisateur + droits, utilisée par le super administrateur
    pour lister et configurer les administrateurs secondaires.
    """
    droits = serializers.SerializerMethodField()

    class Meta:
        model = Utilisateur
        fields = [
            "id", "username", "first_name", "last_name", "email", "telephone",
            "est_admin_secondaire", "droits", "date_creation",
        ]
        read_only_fields = fields

    def get_droits(self, obj):
        # `getattr` (plutôt qu'un accès direct `obj.droits`) évite un crash
        # HTTP 500 si le compte a été promu administrateur secondaire sans
        # ligne DroitAdministrateur associée — par exemple un compte modifié
        # à la main via le Django admin plutôt que via le flux normal de
        # nomination. Un administrateur sans droits explicites en a alors
        # simplement aucun (tout à False), plutôt que de faire planter la liste.
        droits = getattr(obj, "droits", None)
        if droits is None:
            return None
        return DroitAdministrateurSerializer(droits).data


class NommerAdministrateurSerializer(serializers.Serializer):
    """
    Désigne un administrateur secondaire et lui attribue des droits
    granulaires.

    Deux cas de figure :
    - `username` correspond à un compte déjà inscrit : il est promu tel
      quel (aucun mot de passe requis).
    - `username` est inédit : un nouveau compte est créé directement avec
      son identité complète — nom, prénom, email, contact téléphonique et
      identifiants (nom d'utilisateur + mot de passe) — sans passer par le
      formulaire d'inscription public.
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True, label="Prénom")
    last_name = serializers.CharField(required=False, allow_blank=True, label="Nom")
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    telephone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    peut_modifier_salon = serializers.BooleanField(default=False)
    peut_ajouter_administrateur = serializers.BooleanField(default=False)
    peut_creer_codes_reduction = serializers.BooleanField(default=False)
    peut_creer_codes_sponsoring = serializers.BooleanField(default=False)
    peut_voir_abonnements = serializers.BooleanField(default=False)
    peut_consulter_rendement_employes = serializers.BooleanField(default=False)
    peut_consulter_depenses = serializers.BooleanField(default=False)

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value

    def validate(self, attrs):
        self._utilisateur_existant = Utilisateur.objects.filter(username=attrs["username"]).first()

        if self._utilisateur_existant:
            if self._utilisateur_existant.est_admin_principal:
                raise serializers.ValidationError({"username": "Cet utilisateur est déjà administrateur principal."})
        else:
            # Nouveau compte : identifiants complets exigés (point demandé
            # explicitement : nom, prénom, email, contact téléphonique, identifiants).
            if not attrs.get("password"):
                raise serializers.ValidationError(
                    {"password": "Un mot de passe est requis pour créer ce nouvel administrateur."}
                )
            if not attrs.get("last_name"):
                raise serializers.ValidationError({"last_name": "Le nom est requis pour créer ce nouvel administrateur."})
            if not attrs.get("first_name"):
                raise serializers.ValidationError({"first_name": "Le prénom est requis pour créer ce nouvel administrateur."})
            if not attrs.get("email") and not attrs.get("telephone"):
                raise serializers.ValidationError("Un email ou un contact téléphonique est requis pour créer ce compte.")
        return attrs

    def save(self, attribue_par):
        champs_identite = {"username", "password", "first_name", "last_name", "email", "telephone"}
        droits_champs = {k: v for k, v in self.validated_data.items() if k not in champs_identite}

        if self._utilisateur_existant:
            utilisateur = self._utilisateur_existant
        else:
            utilisateur = Utilisateur(
                username=self.validated_data["username"],
                first_name=self.validated_data.get("first_name", ""),
                last_name=self.validated_data.get("last_name", ""),
                email=self.validated_data.get("email") or None,
                telephone=self.validated_data.get("telephone") or None,
            )
            utilisateur.set_password(self.validated_data["password"])

        utilisateur.est_admin_secondaire = True
        utilisateur.save()

        droits, _ = DroitAdministrateur.objects.update_or_create(
            administrateur=utilisateur,
            defaults={**droits_champs, "attribue_par": attribue_par},
        )
        return utilisateur


class ReinitialiserIdentifiantsSerializer(serializers.Serializer):
    """
    Utilisée par l'administrateur pour modifier le nom d'utilisateur et/ou
    réinitialiser le mot de passe de n'importe quel compte (ex. le
    gestionnaire d'un salon qui a perdu l'accès à son compte).
    """
    username = serializers.CharField(required=False)
    nouveau_mot_de_passe = serializers.CharField(required=False, validators=[validate_password])

    def validate(self, attrs):
        if not attrs.get("username") and not attrs.get("nouveau_mot_de_passe"):
            raise serializers.ValidationError("Renseignez au moins un nouveau nom d'utilisateur ou un nouveau mot de passe.")
        return attrs

    def save(self, utilisateur):
        if self.validated_data.get("username"):
            utilisateur.username = self.validated_data["username"]
        if self.validated_data.get("nouveau_mot_de_passe"):
            utilisateur.set_password(self.validated_data["nouveau_mot_de_passe"])
            utilisateur.mot_de_passe_temporaire = True  # doit en choisir un nouveau à la prochaine connexion
        utilisateur.save()
        return utilisateur
