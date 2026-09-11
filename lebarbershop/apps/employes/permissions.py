from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


def est_gestionnaire_effectif(user, salon):
    """
    Vrai si `user` peut administrer le personnel de `salon` : soit il en est
    le propriétaire, soit il y occupe un poste actif de gestionnaire (un
    co-manager désigné — point 2/4 : plusieurs managers peuvent coexister).
    """
    if salon.proprietaire_id == user.id:
        return True
    return salon.employes.filter(utilisateur=user, role="gestionnaire", actif=True).exists()


class EstGestionnaireDuSalon(permissions.BasePermission):
    """
    Le propriétaire du salon ou un co-manager (rôle "gestionnaire") peut
    ajouter, modifier ou retirer des employés. Un employé peut lire sa
    propre fiche (déjà filtré au niveau du queryset de la vue) mais ne peut
    pas gérer les autres employés du salon.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.est_admin_principal or request.user.est_admin_secondaire:
            return True
        if view.action == "create":
            salon = view.get_salon_cible(request)
            return bool(salon) and est_gestionnaire_effectif(request.user, salon)
        return True  # affiné par has_object_permission pour update/delete

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if user.est_admin_principal or user.est_admin_secondaire:
            return True
        if not est_gestionnaire_effectif(user, obj.salon):
            return False
        # Protège le propriétaire réel du salon : un co-manager ne peut ni le
        # rétrograder, ni le retirer du personnel (seul lui-même ou un admin
        # SAAS le pourrait, ce qui n'est de toute façon jamais exposé côté UI).
        if obj.utilisateur_id == obj.salon.proprietaire_id and user.id != obj.utilisateur_id:
            raise PermissionDenied("Le propriétaire du salon ne peut pas être modifié ou retiré par un autre manager.")
        return True
