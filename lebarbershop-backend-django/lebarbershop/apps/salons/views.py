from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from django.utils import timezone
from .models import Salon, Abonnement, CodeReduction, CodeSponsoring, AbonnementAnalyseSectorielle, Forfait
from .serializers import (
    SalonSerializer, SalonAdminSerializer, AbonnementSerializer, CodeReductionSerializer,
    CodeSponsoringSerializer, AbonnementAnalyseSectorielleSerializer, ForfaitSerializer,
)
from .permissions import EstProprietaireOuAdmin, EstAdminPrincipal, EstAdminSaaS


class SalonViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, EstProprietaireOuAdmin]
    pagination_class = None  # le super admin doit voir TOUS les salons sans pagination

    def get_serializer_class(self):
        user = self.request.user
        if user.is_authenticated and (user.est_admin_principal or user.est_admin_secondaire):
            return SalonAdminSerializer
        return SalonSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Salon.objects.select_related("proprietaire").prefetch_related("abonnements")
        if user.est_admin_principal or user.est_admin_secondaire:
            statut = self.request.query_params.get("statut")
            return qs.filter(statut=statut) if statut else qs
        # Un salon est visible par son propriétaire ET par tout employé actif
        # (coiffeur, caissière, gestionnaire...) qui y travaille — sans quoi
        # un employé connecté ne verrait jamais le nom de son propre salon.
        from django.db.models import Q
        return qs.filter(
            Q(proprietaire=user) | Q(employes__utilisateur=user, employes__actif=True)
        ).distinct()

    def perform_create(self, serializer):
        salon = serializer.save(proprietaire=self.request.user, statut=Salon.Statut.EN_ATTENTE)
        # Le propriétaire est automatiquement gestionnaire de son propre salon
        # dès la création : il peut immédiatement ajouter des employés, voir
        # les stocks, les statistiques, etc. sans étape supplémentaire.
        from apps.employes.models import Employe
        Employe.objects.get_or_create(
            utilisateur=self.request.user, salon=salon,
            defaults={"role": Employe.Role.GESTIONNAIRE, "actif": True},
        )
        # Catalogue de soins et produits par défaut (points 12/13 du scénario
        # socle) : le gestionnaire peut immédiatement créer des tickets et
        # voir un stock réaliste, sans tout ressaisir à la main.
        from .catalogue_par_defaut import appliquer_catalogue_par_defaut
        appliquer_catalogue_par_defaut(salon)

    def perform_update(self, serializer):
        instance = self.get_object()
        user = self.request.user
        est_admin = user.est_admin_principal or user.est_admin_secondaire

        nouveau_nom = serializer.validated_data.get("nom")
        # La restriction "une seule modification" ne s'applique qu'au
        # propriétaire ; l'administrateur peut renommer librement un salon
        # (ex. correction d'une faute, changement d'enseigne officiel).
        if not est_admin and nouveau_nom is not None and nouveau_nom != instance.nom:
            if not instance.nom_modifiable:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({
                    "nom": "Le nom du salon ne peut être modifié qu'une seule fois après sa création."
                })
            serializer.save(nom_modifiable=False)
        else:
            serializer.save()

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, EstAdminSaaS])
    def activer(self, request, pk=None):
        """POST /api/v1/salons/{id}/activer/ — réservé à l'administrateur."""
        salon = self.get_object()
        salon.statut = Salon.Statut.ACTIF
        salon.save(update_fields=["statut"])
        return Response(SalonAdminSerializer(salon).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, EstAdminSaaS])
    def suspendre(self, request, pk=None):
        """
        POST /api/v1/salons/{id}/suspendre/ — réservé à l'administrateur.
        Blocage administratif (ex. litige, non-respect des règles) :
        distinct d'une simple désactivation, le salon reste marqué comme
        volontairement bloqué plutôt que simplement en attente.
        """
        salon = self.get_object()
        salon.statut = Salon.Statut.SUSPENDU
        salon.save(update_fields=["statut"])
        return Response(SalonAdminSerializer(salon).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, EstAdminSaaS])
    def desactiver(self, request, pk=None):
        """
        POST /api/v1/salons/{id}/desactiver/ — réservé à l'administrateur.
        Désactivation "douce" : remet le salon en attente (ex. abonnement à
        renouveler), sans connotation disciplinaire contrairement à /suspendre/.
        """
        salon = self.get_object()
        salon.statut = Salon.Statut.EN_ATTENTE
        salon.save(update_fields=["statut"])
        return Response(SalonAdminSerializer(salon).data)


class AbonnementViewSet(viewsets.ModelViewSet):
    serializer_class = AbonnementSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # le super admin doit voir TOUS les abonnements sans pagination

    def get_queryset(self):
        user = self.request.user
        if user.est_admin_principal or user.est_admin_secondaire:
            return Abonnement.objects.all()
        return Abonnement.objects.filter(salon__proprietaire=user)

    def perform_create(self, serializer):
        salon = serializer.validated_data["salon"]
        est_premier = not salon.abonnements.exists()
        date_debut = timezone.now()
        duree = serializer.validated_data["duree_mois"]
        date_fin = date_debut + timezone.timedelta(days=30 * duree)
        abonnement = serializer.save(
            est_premier_abonnement=est_premier,
            date_debut=date_debut,
            date_fin=date_fin,
        )
        salon.statut = Salon.Statut.ACTIF
        salon.save(update_fields=["statut"])

        # Comptabilise l'utilisation d'un code de sponsoring (programme
        # partenaire employé notamment) pour calculer ses gains cumulés.
        if abonnement.code_sponsoring_id:
            code = abonnement.code_sponsoring
            code.nombre_utilisations += 1
            code.save(update_fields=["nombre_utilisations"])

    @action(detail=False, methods=["post"], url_path="apercu")
    def apercu(self, request):
        """
        POST /api/v1/abonnements/apercu/
        body : { salon, duree_mois, code_promo? }

        Calcule INSTANTANÉMENT le prix normal, la réduction et le prix final
        — sans créer d'abonnement ni consommer une utilisation de code —
        pour un affichage en direct côté frontend pendant que le
        gestionnaire choisit la durée et saisit un code promo. La réduction
        d'un code (fixe, en FCFA) est multipliée par le nombre de mois de
        l'abonnement, exactement comme au moment de la création réelle
        (voir AbonnementSerializer.create).
        """
        salon_id = request.data.get("salon")
        code_promo = (request.data.get("code_promo") or "").strip()

        try:
            duree_mois = int(request.data.get("duree_mois"))
        except (TypeError, ValueError):
            return Response({"detail": "duree_mois est requis."}, status=status.HTTP_400_BAD_REQUEST)
        if duree_mois < Abonnement.DUREE_MINIMALE_MOIS:
            return Response(
                {"detail": f"La durée minimale d'abonnement est de {Abonnement.DUREE_MINIMALE_MOIS} mois."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        salon = Salon.objects.filter(id=salon_id).first()
        if not salon:
            return Response({"detail": "Salon introuvable."}, status=status.HTTP_404_NOT_FOUND)
        user = request.user
        if not (user.est_admin_principal or user.est_admin_secondaire or salon.proprietaire_id == user.id):
            return Response({"detail": "Vous n'êtes pas autorisé à voir le tarif de ce salon."},
                             status=status.HTTP_403_FORBIDDEN)

        est_premier = not salon.abonnements.exists()
        prix_mensuel = Abonnement.PRIX_PREMIER_ABONNEMENT_MENSUEL if est_premier else Abonnement.PRIX_RENOUVELLEMENT_MENSUEL
        prix_normal = prix_mensuel * duree_mois

        reduction = 0
        code_valide = False
        erreur_code = None

        if code_promo:
            code_reduction = CodeReduction.objects.filter(code=code_promo).first()
            if code_reduction:
                if not code_reduction.actif:
                    erreur_code = "Ce code n'est plus actif."
                elif code_reduction.date_expiration and code_reduction.date_expiration < timezone.now():
                    erreur_code = "Ce code a expiré."
                elif (code_reduction.nombre_utilisations_max is not None
                      and code_reduction.nombre_utilisations >= code_reduction.nombre_utilisations_max):
                    erreur_code = "Ce code a atteint son nombre maximal d'utilisations."
                else:
                    reduction = code_reduction.montant_reduction * duree_mois
                    code_valide = True
            else:
                code_sponsoring = CodeSponsoring.objects.filter(
                    code=code_promo, actif=True, statut=CodeSponsoring.Statut.ACTIF
                ).first()
                if code_sponsoring:
                    reduction = code_sponsoring.montant_reduction_utilisateur * duree_mois
                    code_valide = True
                else:
                    erreur_code = "Ce code n'existe pas ou n'est plus valide."

        prix_final = max(prix_normal - reduction, 0)

        return Response({
            "est_premier_abonnement": est_premier,
            "prix_mensuel": prix_mensuel,
            "duree_mois": duree_mois,
            "prix_normal": prix_normal,
            "reduction": reduction,
            "prix_final": prix_final,
            "code_valide": code_valide,
            "erreur_code": erreur_code,
        })

@method_decorator(csrf_exempt, name='dispatch')
class AbonnementEssaiView(APIView):
    """
    POST /api/v1/abonnements/essai/  body: {"salon": "<id>"}
    Démarre un essai gratuit de 14 jours pour un salon, sans moyen de paiement
    ni information de carte bancaire.

    Limité à UN essai par utilisateur, pas par salon : un gestionnaire peut
    créer autant de salons qu'il le souhaite (en les payant), mais seul le
    tout premier salon qu'il a créé peut bénéficier de l'essai gratuit.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        salon_id = request.data.get("salon")
        if not salon_id:
            return Response({"detail": "Le champ 'salon' est requis."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            salon = Salon.objects.get(pk=salon_id)
        except Salon.DoesNotExist:
            return Response({"detail": "Salon introuvable."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if salon.proprietaire_id != user.id and not (user.est_admin_principal or user.est_admin_secondaire):
            return Response({"detail": "Seul le propriétaire du salon peut démarrer l'essai gratuit."},
                             status=status.HTTP_403_FORBIDDEN)

        if salon.abonnements.exists():
            return Response(
                {"detail": "Ce salon a déjà un abonnement ou un essai en cours."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.a_utilise_essai_gratuit:
            return Response(
                {"detail": "Vous avez déjà utilisé votre essai gratuit sur un précédent salon. "
                           "Ce nouveau salon doit être souscrit avec un abonnement payant."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        date_debut = timezone.now()
        date_fin = date_debut + timezone.timedelta(days=Abonnement.DUREE_ESSAI_JOURS)
        abonnement = Abonnement.objects.create(
            salon=salon,
            est_premier_abonnement=True,
            est_essai=True,
            duree_mois=1,
            prix_mensuel=0,
            montant_total=0,
            date_debut=date_debut,
            date_fin=date_fin,
            statut=Abonnement.Statut.ACTIF,
        )
        salon.statut = Salon.Statut.ACTIF
        salon.save(update_fields=["statut"])
        user.a_utilise_essai_gratuit = True
        user.save(update_fields=["a_utilise_essai_gratuit"])

        return Response(AbonnementSerializer(abonnement).data, status=status.HTTP_201_CREATED)


class CodeReductionViewSet(viewsets.ModelViewSet):
    serializer_class = CodeReductionSerializer
    permission_classes = [permissions.IsAuthenticated, EstAdminSaaS]
    pagination_class = None
    queryset = CodeReduction.objects.all()

    def perform_create(self, serializer):
        serializer.save(cree_par=self.request.user)


class CodeSponsoringViewSet(viewsets.ModelViewSet):
    serializer_class = CodeSponsoringSerializer
    pagination_class = None

    def get_permissions(self):
        # La création "classique" (codes agents/partenaires salon) reste
        # réservée à l'admin ; la lecture est ouverte à tout utilisateur
        # authentifié (filtrée à ses propres codes s'il n'est pas admin).
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), EstAdminSaaS()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = CodeSponsoring.objects.all()
        if user.est_admin_principal or user.est_admin_secondaire:
            return qs
        # Un utilisateur non-admin (ex. employé partenaire) ne voit que ses
        # propres codes achetés via le programme partenaire.
        return qs.filter(beneficiaire_utilisateur=user)

    def perform_create(self, serializer):
        serializer.save(cree_par=self.request.user)

    @action(detail=False, methods=["post"], url_path="acheter")
    def demander_achat(self, request):
        """
        POST /api/v1/codes-sponsoring/acheter/
        Programme partenaire employé (points 7, 17, 18) : n'importe quel
        utilisateur connecté peut demander un code de sponsoring personnel à
        CodeSponsoring.PRIX_ACHAT_PARTENAIRE (500 FCFA). Il peut proposer le
        nom de son code (`code` dans le corps de la requête) ; à défaut, un
        code est généré automatiquement.

        Le code est créé avec le statut "en_attente_paiement" et n'est PAS
        utilisable : l'attribution finale n'a lieu qu'après confirmation du
        paiement via .confirmer_paiement (Orange Money, MTN MoMo ou carte
        bancaire — voir mode_paiement dans le corps de la requête).
        """
        user = request.user
        existant = CodeSponsoring.objects.filter(
            beneficiaire_utilisateur=user, statut=CodeSponsoring.Statut.ACTIF
        ).first()
        if existant:
            return Response(CodeSponsoringSerializer(existant).data, status=status.HTTP_200_OK)

        mode_paiement = request.data.get("mode_paiement")
        if mode_paiement not in CodeSponsoring.ModePaiement.values:
            return Response(
                {"mode_paiement": "Choisissez un mode de paiement valide (orange_money, mtn_momo, carte_bancaire)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code_propose = (request.data.get("code") or "").strip().upper()
        if code_propose:
            if CodeSponsoring.objects.filter(code=code_propose).exists():
                return Response({"code": "Ce nom de code est déjà utilisé, choisissez-en un autre."},
                                 status=status.HTTP_400_BAD_REQUEST)
            code_final = code_propose
        else:
            code_final = CodeSponsoring.generer_code_partenaire(user)

        code = CodeSponsoring.objects.create(
            code=code_final,
            beneficiaire_nom=user.get_full_name() or user.username,
            beneficiaire_contact=user.telephone or user.email,
            beneficiaire_utilisateur=user,
            est_partenaire_employe=True,
            prix_achat=CodeSponsoring.PRIX_ACHAT_PARTENAIRE,
            commission_fixe_par_utilisation=CodeSponsoring.COMMISSION_PAR_UTILISATION,
            montant_reduction_utilisateur=CodeSponsoring.REDUCTION_UTILISATEUR_PAR_DEFAUT,
            cree_par=user,
            actif=False,
            statut=CodeSponsoring.Statut.EN_ATTENTE_PAIEMENT,
            mode_paiement=mode_paiement,
        )
        return Response(CodeSponsoringSerializer(code).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="confirmer-paiement")
    def confirmer_paiement(self, request, pk=None):
        """
        POST /api/v1/codes-sponsoring/{id}/confirmer-paiement/
        Finalise l'attribution du code après paiement (point 18). En
        production, cette action serait déclenchée par le webhook de la
        passerelle Orange Money / MTN MoMo / carte plutôt qu'appelée
        directement par le frontend.
        """
        code = self.get_object()
        if code.beneficiaire_utilisateur_id != request.user.id and not (
            request.user.est_admin_principal or request.user.est_admin_secondaire
        ):
            return Response({"detail": "Ce code ne vous appartient pas."}, status=status.HTTP_403_FORBIDDEN)
        if code.statut == CodeSponsoring.Statut.ACTIF:
            return Response(CodeSponsoringSerializer(code).data)

        code.statut = CodeSponsoring.Statut.ACTIF
        code.actif = True
        code.date_paiement_confirme = timezone.now()
        code.save(update_fields=["statut", "actif", "date_paiement_confirme"])
        return Response(CodeSponsoringSerializer(code).data)


class AbonnementAnalyseSectorielleViewSet(viewsets.ModelViewSet):
    """Abonnements payants (20000 / 25000) pour les utilisateurs lambda."""
    serializer_class = AbonnementAnalyseSectorielleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AbonnementAnalyseSectorielle.objects.filter(utilisateur=self.request.user)

    def perform_create(self, serializer):
        duree = timezone.timedelta(days=30)
        serializer.save(
            utilisateur=self.request.user,
            date_debut=timezone.now(),
            date_fin=timezone.now() + duree,
        )


class ForfaitViewSet(viewsets.ModelViewSet):
    """
    Forfaits configurables par l'administrateur principal.
    Lecture publique (landing page, `?actif=true` pour n'afficher que les
    forfaits proposés au public) ; écriture réservée à l'administrateur.
    """
    serializer_class = ForfaitSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), EstAdminSaaS()]

    def get_queryset(self):
        qs = Forfait.objects.all()
        actif = self.request.query_params.get("actif")
        if actif is not None:
            qs = qs.filter(actif=(actif.lower() == "true"))
        return qs

    def perform_create(self, serializer):
        serializer.save(cree_par=self.request.user)
