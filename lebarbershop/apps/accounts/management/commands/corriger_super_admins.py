from django.core.management.base import BaseCommand
from apps.accounts.models import Utilisateur


class Command(BaseCommand):
    help = (
        "Corrige les comptes existants rendus super-utilisateurs Django "
        "(is_superuser=True, via `createsuperuser` ou le Django admin) mais "
        "dont le champ métier `est_admin_principal` n'a jamais été mis à "
        "jour en conséquence — ces comptes voient le Django admin mais pas "
        "les données de l'API (salons, codes promo, administrateurs...). "
        "Cette commande n'est nécessaire qu'une seule fois pour les comptes "
        "déjà existants : tout nouveau compte est désormais synchronisé "
        "automatiquement à chaque sauvegarde (voir Utilisateur.save())."
    )

    def handle(self, *args, **options):
        a_corriger = Utilisateur.objects.filter(is_superuser=True, est_admin_principal=False)
        total = a_corriger.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("Aucun compte à corriger — tout est déjà synchronisé."))
            return
        for utilisateur in a_corriger:
            utilisateur.est_admin_principal = True
            utilisateur.save(update_fields=["est_admin_principal"])
            self.stdout.write(f"  corrigé : {utilisateur.username}")
        self.stdout.write(self.style.SUCCESS(f"{total} compte(s) super-utilisateur corrigé(s)."))
