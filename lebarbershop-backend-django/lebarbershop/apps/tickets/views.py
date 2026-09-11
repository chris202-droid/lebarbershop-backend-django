from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Ticket, LigneTicket
from .serializers import TicketSerializer, TicketValidationSerializer, LigneTicketSerializer
from apps.employes.models import Employe
from apps.salons.models import Salon
from apps.clients.models import FideliteClientSalon
from apps.analytics.models import RendementEmployeJournalier, BilanJournalierSalon


def _employe_autorise(user, salon, droit):
    """
    Détermine si `user` peut effectuer une action de type `droit`
    ("peut_valider_ticket" ou "peut_confirmer_ticket") sur un ticket de
    `salon`, et retourne le poste (Employe) à utiliser pour l'audit trail.

    Autorisé pour : le propriétaire du salon (toujours, jamais restreint),
    un co-manager ("gestionnaire") ayant le droit accordé, une caissière
    ayant le droit accordé (pour peut_valider_ticket), ou un administrateur
    SAAS. Retourne (poste_ou_None, reponse_erreur_ou_None).
    """
    if user.est_admin_principal or user.est_admin_secondaire:
        return None, None
    if salon.proprietaire_id == user.id:
        poste = Employe.objects.filter(utilisateur=user, salon=salon, actif=True).first()
        return poste, None

    poste = Employe.objects.filter(
        utilisateur=user, salon=salon, actif=True, role__in=[Employe.Role.GESTIONNAIRE, Employe.Role.CAISSIERE]
    ).first()
    if poste and getattr(poste, droit):
        return poste, None
    return None, Response(
        {"detail": "Vous n'avez pas la permission d'effectuer cette action sur ce salon."},
        status=status.HTTP_403_FORBIDDEN,
    )


def _mettre_a_jour_agregats(ticket):
    """Met à jour fidélité client, rendement employé et bilan salon après validation d'un ticket."""
    if ticket.client:
        fidelite, _ = FideliteClientSalon.objects.get_or_create(client=ticket.client, salon=ticket.salon)
        fidelite.nombre_visites += 1
        fidelite.derniere_visite = ticket.date_validation
        fidelite.save()

    aujourd_hui = ticket.date_validation.date()
    lignes_valides = ticket.lignes.exclude(statut=LigneTicket.Statut.ANNULE)
    for ligne in lignes_valides:
        rendement, _ = RendementEmployeJournalier.objects.get_or_create(
            employe=ligne.employe_executant, date=aujourd_hui
        )
        rendement.nombre_soins += 1
        rendement.montant_total += ligne.prix
        rendement.save()

    bilan, _ = BilanJournalierSalon.objects.get_or_create(salon=ticket.salon, date=aujourd_hui)
    bilan.entrees_total += ticket.montant_net
    champ_categorie = {
        "coiffure_homme": "entrees_coiffure_homme",
        "coiffure_femme": "entrees_coiffure_femme",
        "esthetique": "entrees_esthetique",
        "pedicure": "entrees_pedicure",
        "manucure": "entrees_manucure",
    }
    for ligne in lignes_valides:
        champ = champ_categorie.get(ligne.soin.categorie, "entrees_autre")
        setattr(bilan, champ, getattr(bilan, champ) + ligne.prix)
    bilan.save()


class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Ticket.objects.select_related("salon", "client", "employe_createur").prefetch_related("lignes")
        if not (user.est_admin_principal or user.est_admin_secondaire):
            # Un ticket n'est visible que par : le propriétaire du salon, un
            # employé actif de ce salon (peu importe son rôle), ou l'employé
            # assigné à l'une de ses lignes (pour voir "ses" soins à confirmer).
            qs = qs.filter(
                Q(salon__proprietaire=user)
                | Q(salon__employes__utilisateur=user, salon__employes__actif=True)
                | Q(lignes__employe_executant__utilisateur=user)
            ).distinct()
        salon_id = self.request.query_params.get("salon")
        if salon_id:
            qs = qs.filter(salon_id=salon_id)
        statut = self.request.query_params.get("statut")
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    def _peut_modifier_ou_supprimer(self, request, ticket):
        """
        Un ticket ne peut être modifié, supprimé ou annulé que tant qu'il
        est encore "en attente" (point 3), et seulement par : son créateur,
        le propriétaire du salon, un co-manager habilité (peut_creer_ticket),
        ou un administrateur SAAS.
        """
        if ticket.statut != Ticket.Statut.EN_ATTENTE:
            return False, Response(
                {"detail": "Ce ticket a déjà été validé ou annulé et ne peut plus être modifié."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user
        if user.est_admin_principal or user.est_admin_secondaire:
            return True, None
        if ticket.employe_createur.utilisateur_id == user.id:
            return True, None
        if ticket.salon.proprietaire_id == user.id:
            return True, None
        _, erreur = _employe_autorise(user, ticket.salon, "peut_creer_ticket")
        if erreur is None:
            return True, None
        return False, Response(
            {"detail": "Vous n'êtes pas autorisé à modifier ce ticket."}, status=status.HTTP_403_FORBIDDEN
        )

    def update(self, request, *args, **kwargs):
        ticket = self.get_object()
        autorise, erreur = self._peut_modifier_ou_supprimer(request, ticket)
        if not autorise:
            return erreur
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        ticket = self.get_object()
        autorise, erreur = self._peut_modifier_ou_supprimer(request, ticket)
        if not autorise:
            return erreur
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="annuler")
    def annuler(self, request, pk=None):
        """
        POST /api/v1/tickets/{id}/annuler/ — annule le ticket entier (le
        client est reparti sans qu'aucun soin ne soit finalisé) plutôt que de
        le supprimer, pour conserver une trace. Un ticket annulé disparaît de
        la file de la caissière (point 4 : elle ne filtre que sur
        statut=en_attente).
        """
        ticket = self.get_object()
        autorise, erreur = self._peut_modifier_ou_supprimer(request, ticket)
        if not autorise:
            return erreur
        ticket.lignes.update(statut=LigneTicket.Statut.ANNULE)
        ticket.statut = Ticket.Statut.ANNULE
        ticket.save(update_fields=["statut"])
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=["post"], url_path="valider")
    def valider(self, request, pk=None):
        """
        Encaisse et valide le ticket : statut -> validé, mise à jour de la
        fidélité client et des agrégats de performance.
        Autorisé pour : une caissière du salon, le propriétaire du salon, un
        co-manager ayant le droit peut_valider_ticket, ou un administrateur
        SAAS. Les lignes encore "en attente" sont considérées confirmées au
        moment du paiement (le client était bien présent pour tous les soins
        listés).
        """
        ticket = self.get_object()
        if ticket.statut != Ticket.Statut.EN_ATTENTE:
            return Response({"detail": "Ce ticket a déjà été traité."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = TicketValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validateur, erreur = _employe_autorise(request.user, ticket.salon, "peut_valider_ticket")
        if erreur:
            return erreur
        # Le poste utilisé pour l'audit trail : celui d'une caissière si
        # disponible, sinon le poste (propriétaire/gestionnaire) qui a validé.
        caissiere = Employe.objects.filter(
            utilisateur=request.user, salon=ticket.salon, role=Employe.Role.CAISSIERE
        ).first() or validateur

        ticket.lignes.filter(statut=LigneTicket.Statut.EN_ATTENTE).update(statut=LigneTicket.Statut.CONFIRME)
        ticket.recalculer_montants()
        ticket.statut = Ticket.Statut.VALIDE
        ticket.mode_paiement = serializer.validated_data["mode_paiement"]
        ticket.caissiere_validatrice = caissiere
        ticket.date_validation = timezone.now()
        ticket.save()

        _mettre_a_jour_agregats(ticket)

        return Response(TicketSerializer(ticket).data)


class LigneTicketViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Permet à un employé de confirmer ("le client a fait le soin") ou
    d'annuler ("le client a annulé") le soin qui lui est assigné dans un
    ticket, avant que la caissière ne finalise le paiement (point 5).
    """
    serializer_class = LigneTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = LigneTicket.objects.select_related("ticket", "soin", "employe_executant")
        if user.est_admin_principal or user.est_admin_secondaire:
            return qs
        # Un manager (propriétaire ou co-manager) voit toutes les lignes de
        # son/ses salon(s), en plus de ses propres lignes assignées — pour
        # pouvoir superviser/confirmer les soins de toute son équipe.
        salons_geres = Salon.objects.filter(
            Q(proprietaire=user) | Q(employes__utilisateur=user, employes__role="gestionnaire", employes__actif=True)
        ).values_list("id", flat=True).distinct()
        return qs.filter(Q(employe_executant__utilisateur=user) | Q(ticket__salon_id__in=salons_geres)).distinct()

    def _changer_statut(self, request, pk, nouveau_statut):
        ligne = self.get_object()
        user = request.user
        est_admin = user.est_admin_principal or user.est_admin_secondaire
        est_executant = ligne.employe_executant.utilisateur_id == user.id
        autorise = est_admin or est_executant
        if not autorise:
            # Un manager (propriétaire ou co-manager habilité) peut aussi
            # confirmer/annuler n'importe quelle ligne de son salon, pour
            # garder un droit de regard sur le déroulement des soins
            # (point 1 : le manager peut confirmer un ticket).
            _, erreur = _employe_autorise(user, ligne.ticket.salon, "peut_confirmer_ticket")
            autorise = erreur is None
        if not autorise:
            return Response({"detail": "Vous n'êtes pas autorisé à confirmer ou annuler ce soin."},
                             status=status.HTTP_403_FORBIDDEN)
        if ligne.ticket.statut != Ticket.Statut.EN_ATTENTE:
            return Response({"detail": "Ce ticket a déjà été validé."}, status=status.HTTP_400_BAD_REQUEST)
        ligne.statut = nouveau_statut
        ligne.save(update_fields=["statut"])
        ligne.ticket.recalculer_montants()

        # Point 4 : si TOUTES les lignes du ticket finissent annulées (plus
        # aucun soin retenu), le ticket entier est automatiquement annulé et
        # disparaît donc de la file de la caissière, sans action manuelle
        # supplémentaire de sa part.
        lignes_ticket = ligne.ticket.lignes.all()
        if lignes_ticket.exists() and all(l.statut == LigneTicket.Statut.ANNULE for l in lignes_ticket):
            ligne.ticket.statut = Ticket.Statut.ANNULE
        ligne.ticket.save(update_fields=["montant_brut", "montant_net", "statut"])
        return Response(LigneTicketSerializer(ligne).data)

    @action(detail=True, methods=["post"])
    def confirmer(self, request, pk=None):
        """POST /api/v1/lignes-ticket/{id}/confirmer/ — le client a fait le soin."""
        return self._changer_statut(request, pk, LigneTicket.Statut.CONFIRME)

    @action(detail=True, methods=["post"])
    def annuler(self, request, pk=None):
        """POST /api/v1/lignes-ticket/{id}/annuler/ — le client a annulé le soin."""
        return self._changer_statut(request, pk, LigneTicket.Statut.ANNULE)
