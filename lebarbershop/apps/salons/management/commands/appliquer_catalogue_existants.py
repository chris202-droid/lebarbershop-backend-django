from django.core.management.base import BaseCommand
from apps.salons.models import Salon
from apps.salons.catalogue_par_defaut import appliquer_catalogue_par_defaut


class Command(BaseCommand):
    help = (
        "Applique (ou complète) le catalogue par défaut de soins et produits "
        "sur TOUS les salons déjà existants en base — point 5 : toute "
        "évolution de ce catalogue (nouveaux soins/produits ajoutés au fil "
        "du temps) doit pouvoir être rattrapée sur les salons créés avant "
        "cette évolution, pas seulement sur les nouveaux salons. "
        "Sans danger à relancer plusieurs fois : seuls les éléments "
        "manquants (par nom) sont ajoutés, aucun doublon n'est créé."
    )

    def handle(self, *args, **options):
        salons = Salon.objects.all()
        total = salons.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("Aucun salon en base."))
            return
        for salon in salons:
            avant_soins = salon.soins.count()
            avant_produits = salon.produits.count()
            appliquer_catalogue_par_defaut(salon)
            apres_soins = salon.soins.count()
            apres_produits = salon.produits.count()
            ajoutes = (apres_soins - avant_soins) + (apres_produits - avant_produits)
            if ajoutes:
                self.stdout.write(
                    f"  {salon.nom} : +{apres_soins - avant_soins} soin(s), +{apres_produits - avant_produits} produit(s)"
                )
        self.stdout.write(self.style.SUCCESS(f"Catalogue vérifié/complété sur {total} salon(s)."))
