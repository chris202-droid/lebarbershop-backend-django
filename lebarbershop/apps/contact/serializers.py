from rest_framework import serializers
from .models import DemandeContact, DemandePartenariat, DemandeCodePromo


class DemandeContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandeContact
        fields = ["id", "nom", "email", "motif", "message", "date_creation"]
        read_only_fields = ["id", "date_creation"]


class DemandePartenariatSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandePartenariat
        fields = ["id", "nom", "structure", "contact", "date_creation"]
        read_only_fields = ["id", "date_creation"]


class DemandeCodePromoInSerializer(serializers.Serializer):
    email = serializers.EmailField()


class DemandeCodePromoOutSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="code.code", read_only=True)
    montant_reduction = serializers.DecimalField(source="code.montant_reduction", max_digits=10, decimal_places=2, read_only=True)
    date_expiration = serializers.DateTimeField(source="code.date_expiration", read_only=True)

    class Meta:
        model = DemandeCodePromo
        fields = ["id", "email", "code", "montant_reduction", "date_expiration", "date_creation"]
        read_only_fields = fields


# --- Vues administrateur : ajoutent/permettent la modification de `traite` ---

class DemandeContactAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandeContact
        fields = ["id", "nom", "email", "motif", "message", "traite", "date_creation"]
        read_only_fields = ["id", "nom", "email", "motif", "message", "date_creation"]


class DemandePartenariatAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandePartenariat
        fields = ["id", "nom", "structure", "contact", "traite", "code_sponsoring_attribue", "date_creation"]
        read_only_fields = ["id", "nom", "structure", "contact", "date_creation"]


class DemandeCodePromoAdminSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="code.code", read_only=True)
    code_actif = serializers.BooleanField(source="code.actif", read_only=True)

    class Meta:
        model = DemandeCodePromo
        fields = ["id", "email", "code", "code_actif", "date_creation"]
        read_only_fields = fields
