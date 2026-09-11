from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils.dateparse import parse_date
from .models import RendementEmployeJournalier, BilanJournalierSalon
from .serializers import RendementEmployeJournalierSerializer, BilanJournalierSalonSerializer
from apps.salons.permissions import EstAdminSaaS


class RendementEmployeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RendementEmployeJournalierSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = RendementEmployeJournalier.objects.select_related("employe")
        employe_id = self.request.query_params.get("employe")
        if employe_id:
            qs = qs.filter(employe_id=employe_id)
        debut, fin = self.request.query_params.get("debut"), self.request.query_params.get("fin")
        if debut:
            qs = qs.filter(date__gte=parse_date(debut))
        if fin:
            qs = qs.filter(date__lte=parse_date(fin))
        return qs.order_by("date")


class BilanJournalierViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BilanJournalierSalonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = BilanJournalierSalon.objects.select_related("salon")
        salon_id = self.request.query_params.get("salon")
        if salon_id:
            qs = qs.filter(salon_id=salon_id)
        debut, fin = self.request.query_params.get("debut"), self.request.query_params.get("fin")
        if debut:
            qs = qs.filter(date__gte=parse_date(debut))
        if fin:
            qs = qs.filter(date__lte=parse_date(fin))
        return qs.order_by("date")


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def statistiques_secteur(request):
    """
    Statistiques par secteur géographique et par rentabilité (utilisé pour les
    abonnements 'analyse sectorielle' à 20000/25000 et pour l'admin principal).
    """
    from django.db.models import Sum, Count
    from apps.salons.models import Salon

    data = (
        Salon.objects.values("secteur_geographique", "ville")
        .annotate(nombre_salons=Count("id"))
        .order_by("-nombre_salons")
    )
    return Response(list(data))


def _cle_et_libelle_periode(date_obj, periode):
    """Calcule une clé de regroupement (triable) et un libellé lisible pour une date donnée."""
    annee, mois = date_obj.year, date_obj.month
    if periode == "semaine":
        annee_iso, semaine_iso, _ = date_obj.isocalendar()
        return (annee_iso, semaine_iso), f"Semaine {semaine_iso} - {annee_iso}"
    if periode == "mois":
        return (annee, mois), f"{date_obj.strftime('%B %Y')}"
    if periode == "trimestre":
        trimestre = (mois - 1) // 3 + 1
        return (annee, trimestre), f"T{trimestre} {annee}"
    if periode == "semestre":
        semestre = 1 if mois <= 6 else 2
        return (annee, semestre), f"S{semestre} {annee}"
    # annee
    return (annee,), f"{annee}"


PERIODES_VALIDES = ("semaine", "mois", "trimestre", "semestre", "annee")


def _utilisateur_autorise_pour_salon(user, salon):
    """Propriétaire, gestionnaire, caissière du salon, ou administrateur SAAS."""
    if user.est_admin_principal or user.est_admin_secondaire:
        return True
    if salon.proprietaire_id == user.id:
        return True
    from apps.employes.models import Employe
    return Employe.objects.filter(
        utilisateur=user, salon=salon, actif=True,
        role__in=[Employe.Role.GESTIONNAIRE, Employe.Role.CAISSIERE],
    ).exists()


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def bilan_salon(request):
    """
    GET /api/v1/analytics/bilan-salon/?salon=<id>&periode=semaine|mois|trimestre|semestre|annee
    Réservé au gestionnaire et à la caissière du salon concerné (point 14) :
    - `lignes` : chiffre d'affaires du salon regroupé par période, pour le graphique ;
    - `par_employe` : nombre de soins et montant total généré par chaque
      employé du salon (cumul complet, indépendant de `periode`) ;
    - `totaux` : chiffre d'affaires cumulé et nombre de tickets validés.
    """
    from apps.salons.models import Salon
    from .models import BilanJournalierSalon, RendementEmployeJournalier

    salon_id = request.query_params.get("salon")
    if not salon_id:
        return Response({"detail": "Le paramètre 'salon' est requis."}, status=400)
    try:
        salon = Salon.objects.get(id=salon_id)
    except Salon.DoesNotExist:
        return Response({"detail": "Salon introuvable."}, status=404)
    if not _utilisateur_autorise_pour_salon(request.user, salon):
        return Response({"detail": "Vous n'avez pas accès au bilan de ce salon."}, status=403)

    periode = request.query_params.get("periode", "mois")
    if periode not in PERIODES_VALIDES:
        return Response({"detail": f"periode doit être l'une de {PERIODES_VALIDES}."}, status=400)

    groupes = {}
    for b in BilanJournalierSalon.objects.filter(salon=salon):
        cle, libelle = _cle_et_libelle_periode(b.date, periode)
        g = groupes.setdefault(cle, {"periode": libelle, "revenu": 0, "nombre_tickets": 0})
        g["revenu"] += float(b.entrees_total)
    lignes = [groupes[cle] for cle in sorted(groupes.keys())]

    par_employe = []
    from django.db.models import Sum
    agregats = (
        RendementEmployeJournalier.objects
        .filter(employe__salon=salon)
        .values("employe_id", "employe__utilisateur__first_name", "employe__utilisateur__username", "employe__role")
        .annotate(nombre_soins=Sum("nombre_soins"), montant_total=Sum("montant_total"))
        .order_by("-montant_total")
    )
    for a in agregats:
        par_employe.append({
            "employe_id": a["employe_id"],
            "nom": a["employe__utilisateur__first_name"] or a["employe__utilisateur__username"],
            "role": a["employe__role"],
            "nombre_soins": a["nombre_soins"] or 0,
            "montant_total": float(a["montant_total"] or 0),
        })

    totaux = {
        "revenu_total": sum(l["revenu"] for l in lignes),
        "nombre_tickets_total": sum(e["nombre_soins"] for e in par_employe),
    }

    return Response({"periode": periode, "lignes": lignes, "par_employe": par_employe, "totaux": totaux})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, EstAdminSaaS])
def bilan_financier(request):
    """
    GET /api/v1/analytics/bilan-financier/?periode=mois|trimestre|semestre|annee
    Réservé à l'administrateur principal. Regroupe, pour chaque période :
    - `revenu_abonnements` : les paiements d'abonnement SAAS réussis
      (le revenu de LeBarberShop lui-même) ;
    - `chiffre_affaires_salons` : la somme des entrées journalières de tous
      les salons (le volume d'affaires généré par la plateforme).
    Renvoie aussi les totaux globaux (toutes périodes confondues).
    """
    from apps.paiements.models import PaiementAbonnement
    from .models import BilanJournalierSalon

    periode = request.query_params.get("periode", "mois")
    if periode not in ("mois", "trimestre", "semestre", "annee"):
        return Response({"detail": "periode doit être 'mois', 'trimestre', 'semestre' ou 'annee'."}, status=400)

    groupes = {}

    paiements = PaiementAbonnement.objects.filter(statut="reussi").exclude(date_confirmation=None)
    for p in paiements:
        cle, libelle = _cle_et_libelle_periode(p.date_confirmation, periode)
        g = groupes.setdefault(cle, {"periode": libelle, "revenu_abonnements": 0, "chiffre_affaires_salons": 0, "nombre_paiements": 0})
        g["revenu_abonnements"] += float(p.montant)
        g["nombre_paiements"] += 1

    for b in BilanJournalierSalon.objects.all():
        cle, libelle = _cle_et_libelle_periode(b.date, periode)
        g = groupes.setdefault(cle, {"periode": libelle, "revenu_abonnements": 0, "chiffre_affaires_salons": 0, "nombre_paiements": 0})
        g["chiffre_affaires_salons"] += float(b.entrees_total)

    lignes = [groupes[cle] for cle in sorted(groupes.keys())]
    totaux = {
        "revenu_abonnements": sum(l["revenu_abonnements"] for l in lignes),
        "chiffre_affaires_salons": sum(l["chiffre_affaires_salons"] for l in lignes),
        "nombre_paiements": sum(l["nombre_paiements"] for l in lignes),
    }
    return Response({"periode": periode, "lignes": lignes, "totaux": totaux})
