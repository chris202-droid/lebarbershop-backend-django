from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from apps.accounts.models import Utilisateur
from .models import Employe


class EmployeSerializer(serializers.ModelSerializer):
    nom_complet = serializers.SerializerMethodField()
    salon_nom = serializers.CharField(source="salon.nom", read_only=True)
    role_affiche = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = Employe
        fields = [
            "id", "utilisateur", "nom_complet", "salon", "salon_nom", "role", "role_affiche",
            "role_autre_precision", "actif", "date_embauche",
            "peut_creer_ticket", "peut_confirmer_ticket", "peut_valider_ticket",
        ]
        read_only_fields = ["id", "utilisateur", "salon", "date_embauche"]

    def get_nom_complet(self, obj):
        return obj.utilisateur.get_full_name() or obj.utilisateur.username

    def validate(self, attrs):
        salon = getattr(self.instance, "salon", None)
        if salon and salon.employes.filter(actif=True).exclude(pk=getattr(self.instance, "pk", None)).count() >= salon.nombre_employes_max:
            raise serializers.ValidationError("Le nombre maximal d'employés pour ce salon est atteint.")
        return attrs


class EmployeCreationSerializer(serializers.ModelSerializer):
    """
    Création d'un employé PAR le gestionnaire du salon : celui-ci définit
    lui-même les identifiants (nom d'utilisateur + mot de passe provisoire)
    de l'employé plutôt que de faire référence à un compte déjà existant.
    Le compte Utilisateur et la fiche Employe sont créés dans la même
    transaction. `mot_de_passe_temporaire=True` force l'employé à changer ce
    mot de passe à sa première connexion (voir apps/accounts/views.py).
    """
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(write_only=True, required=False, allow_null=True)
    telephone = serializers.CharField(write_only=True, required=False, allow_null=True)

    nom_complet = serializers.SerializerMethodField()

    class Meta:
        model = Employe
        fields = [
            "id", "salon", "role", "role_autre_precision", "actif",
            "username", "password", "first_name", "last_name", "email", "telephone",
            "utilisateur", "nom_complet", "date_embauche",
        ]
        read_only_fields = ["id", "utilisateur", "nom_complet", "date_embauche"]

    def get_nom_complet(self, obj):
        return obj.utilisateur.get_full_name() or obj.utilisateur.username

    def validate(self, attrs):
        salon = attrs.get("salon")
        if salon and salon.employes.filter(actif=True).count() >= salon.nombre_employes_max:
            raise serializers.ValidationError("Le nombre maximal d'employés pour ce salon est atteint.")
        if Utilisateur.objects.filter(username=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "Ce nom d'utilisateur existe déjà."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        compte = Utilisateur.objects.create(
            username=validated_data.pop("username"),
            first_name=validated_data.pop("first_name", "") or "",
            last_name=validated_data.pop("last_name", "") or "",
            email=validated_data.pop("email", None) or None,
            telephone=validated_data.pop("telephone", None) or None,
            mot_de_passe_temporaire=True,
        )
        compte.set_password(validated_data.pop("password"))
        compte.save()
        return Employe.objects.create(utilisateur=compte, **validated_data)
