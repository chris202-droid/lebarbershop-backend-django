from rest_framework import viewsets, permissions
from .models import Employe
from .serializers import EmployeSerializer, EmployeCreationSerializer
from .permissions import EstGestionnaireDuSalon


class EmployeViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, EstGestionnaireDuSalon]

    def get_serializer_class(self):
        return EmployeCreationSerializer if self.action == "create" else EmployeSerializer

    def get_salon_cible(self, request):
        """Utilisé par EstGestionnaireDuSalon pour vérifier les droits à la création."""
        from apps.salons.models import Salon
        salon_id = request.data.get("salon")
        return Salon.objects.filter(pk=salon_id).first() if salon_id else None

    def get_queryset(self):
        user = self.request.user
        qs = Employe.objects.select_related("utilisateur", "salon")
        if user.est_admin_principal or user.est_admin_secondaire:
            base = qs
        # ?moi=true : un utilisateur récupère uniquement SES propres postes
        # (utilisé au login pour savoir dans quel(s) salon(s) il travaille et
        # avec quel rôle, sans mélanger avec la liste du personnel qu'il gère).
        elif self.request.query_params.get("moi") == "true":
            base = qs.filter(utilisateur=user, actif=True)
        else:
            # Voient la liste complète du personnel : le propriétaire du
            # salon et tout co-manager (rôle "gestionnaire") qui y travaille.
            # Un employé "simple" ne voit que sa propre fiche.
            from django.db.models import Q
            base = qs.filter(
                Q(salon__proprietaire=user)
                | Q(salon__employes__utilisateur=user, salon__employes__role="gestionnaire", salon__employes__actif=True)
                | Q(utilisateur=user)
            ).distinct()

        salon_id = self.request.query_params.get("salon")
        return base.filter(salon_id=salon_id) if salon_id else base
