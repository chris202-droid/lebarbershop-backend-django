from rest_framework import serializers
from .models import Ticket, LigneTicket


class LigneTicketSerializer(serializers.ModelSerializer):
    soin_nom = serializers.CharField(source="soin.nom", read_only=True)
    employe_executant_nom = serializers.SerializerMethodField()
    ticket_salon = serializers.CharField(source="ticket.salon_id", read_only=True)

    class Meta:
        model = LigneTicket
        fields = ["id", "soin", "soin_nom", "employe_executant", "employe_executant_nom", "prix", "statut", "ticket_salon"]
        read_only_fields = ["id", "statut", "ticket_salon"]
        extra_kwargs = {"prix": {"required": False}}

    def get_employe_executant_nom(self, obj):
        u = obj.employe_executant.utilisateur
        return u.get_full_name() or u.username


class TicketSerializer(serializers.ModelSerializer):
    lignes = LigneTicketSerializer(many=True)
    client_nom = serializers.SerializerMethodField()
    employe_createur_nom = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id", "salon", "client", "client_nom", "nom_client_temporaire", "employe_createur",
            "employe_createur_nom", "caissiere_validatrice", "statut", "mode_paiement",
            "reduction_pourcentage", "montant_brut", "montant_net", "date_creation",
            "date_validation", "lignes",
        ]
        read_only_fields = [
            "id", "montant_brut", "montant_net", "date_creation", "date_validation",
            "caissiere_validatrice", "statut",
        ]

    def get_client_nom(self, obj):
        if obj.client:
            return obj.client.nom
        return obj.nom_client_temporaire

    def get_employe_createur_nom(self, obj):
        u = obj.employe_createur.utilisateur
        return u.get_full_name() or u.username

    def validate(self, attrs):
        if not attrs.get("lignes"):
            raise serializers.ValidationError("Le ticket doit contenir au moins un soin.")
        salon = attrs.get("salon")
        employe_createur = attrs.get("employe_createur")
        if salon and employe_createur and employe_createur.salon_id != salon.id:
            raise serializers.ValidationError({"employe_createur": "Cet employé n'appartient pas à ce salon."})
        for ligne in attrs["lignes"]:
            executant = ligne.get("employe_executant")
            if salon and executant and executant.salon_id != salon.id:
                raise serializers.ValidationError({"lignes": "Un employé assigné n'appartient pas à ce salon."})
        # Ni client existant ni nom temporaire : un nom par défaut du type
        # "Clt1.28.8.26" sera généré automatiquement à la création — voir
        # Ticket.generer_nom_client_defaut().
        return attrs

    def validate_employe_createur(self, employe):
        """
        Le créateur du ticket doit être un poste actif de l'utilisateur
        authentifié — empêche un employé d'ouvrir un ticket au nom d'un
        collègue (faille de contrôle d'accès sinon).
        """
        request = self.context.get("request")
        if request and employe.utilisateur_id != request.user.id:
            raise serializers.ValidationError("Vous ne pouvez créer un ticket qu'en votre propre nom.")
        if not employe.actif:
            raise serializers.ValidationError("Ce poste n'est plus actif.")
        est_proprietaire = employe.salon.proprietaire_id == employe.utilisateur_id
        if not est_proprietaire and not employe.peut_creer_ticket:
            raise serializers.ValidationError("Vous n'avez pas la permission de créer un ticket pour ce salon.")
        return employe

    def create(self, validated_data):
        lignes_data = validated_data.pop("lignes")
        ticket = Ticket(**validated_data)
        if not ticket.client_id and not ticket.nom_client_temporaire:
            ticket.nom_client_temporaire = ticket.generer_nom_client_defaut()
        ticket.save()
        for ligne_data in lignes_data:
            # Le prix du catalogue est la valeur par défaut, mais l'employé
            # qui enregistre le ticket peut le modifier à la main (point 3 —
            # ex. tarif négocié, promotion ponctuelle).
            prix = ligne_data.pop("prix", None) or ligne_data["soin"].prix
            LigneTicket.objects.create(ticket=ticket, prix=prix, **ligne_data)
        ticket.recalculer_montants()
        ticket.save()
        return ticket

    def update(self, instance, validated_data):
        """
        Modifie un ticket (client, réduction, liste des soins et prix) — les
        lignes fournies REMPLACENT entièrement les lignes existantes. La vue
        (TicketViewSet.perform_update) interdit déjà cet appel une fois le
        ticket validé ou annulé ; ce garde-fou est dupliqué ici par sécurité
        si le serializer était réutilisé ailleurs.
        """
        if instance.statut != Ticket.Statut.EN_ATTENTE:
            raise serializers.ValidationError(
                "Ce ticket ne peut plus être modifié (déjà validé ou annulé)."
            )
        lignes_data = validated_data.pop("lignes", None)
        for champ, valeur in validated_data.items():
            setattr(instance, champ, valeur)
        instance.save()

        if lignes_data is not None:
            instance.lignes.all().delete()
            for ligne_data in lignes_data:
                prix = ligne_data.pop("prix", None) or ligne_data["soin"].prix
                LigneTicket.objects.create(ticket=instance, prix=prix, **ligne_data)

        instance.recalculer_montants()
        instance.save()
        return instance


class TicketValidationSerializer(serializers.Serializer):
    """Utilisé par la caissière pour valider/encaisser un ticket."""
    mode_paiement = serializers.ChoiceField(choices=Ticket.ModePaiement.choices)
