from rest_framework import permissions


class EstProprietaireOuAdmin(permissions.BasePermission):
    """Seuls le propriétaire du salon ou un administrateur du SAAS peuvent modifier."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if user.est_admin_principal or user.est_admin_secondaire:
            return True
        return obj.proprietaire_id == user.id


class EstAdminPrincipal(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.est_admin_principal)


class EstAdminSaaS(permissions.BasePermission):
    """
    Vrai pour tout administrateur du SAAS — principal OU secondaire.

    Utilisée pour l'ensemble des informations et actions du tableau de bord
    super administrateur (salons, codes promo/sponsoring, forfaits, demandes,
    bilan financier, liste des administrateurs) : tous les administrateurs
    voient et opèrent sur les mêmes données globales. Seules la création et
    la révocation d'un AUTRE administrateur, ainsi que la réinitialisation
    des identifiants d'un compte, restent réservées au seul administrateur
    principal (voir EstAdminPrincipal) — des actions sensibles qui touchent
    directement à la sécurité des accès.
    """
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.est_admin_principal or user.est_admin_secondaire))


class EstAdminAvecDroit(permissions.BasePermission):
    """Vérifie un droit précis attribué à un administrateur secondaire."""
    droit_requis = None

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.est_admin_principal:
            return True
        if user.est_admin_secondaire and hasattr(user, "droits"):
            return getattr(user.droits, self.droit_requis, False)
        return False


class PeutAjouterAdministrateur(EstAdminAvecDroit):
    """
    Autorise l'administrateur principal, ou tout administrateur secondaire
    ayant explicitement reçu le droit `peut_ajouter_administrateur` — sans
    quoi cette gestion reste réservée au seul principal, même quand ce droit
    lui a été accordé (point demandé : tous les administrateurs habilités
    doivent pouvoir accéder à ces informations/actions, pas seulement le
    principal).
    """
    droit_requis = "peut_ajouter_administrateur"
