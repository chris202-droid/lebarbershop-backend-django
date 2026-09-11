from django.contrib import admin
from .models import Salon, Abonnement, CodeReduction, CodeSponsoring, AbonnementAnalyseSectorielle, Forfait


@admin.register(Salon)
class SalonAdmin(admin.ModelAdmin):
    list_display = ("nom", "proprietaire", "ville", "secteur_geographique", "statut", "date_creation")
    list_filter = ("statut", "ville")
    search_fields = ("nom", "proprietaire__username", "proprietaire__email")


@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ("salon", "statut", "est_essai", "date_debut", "date_fin", "montant_total")
    list_filter = ("statut", "est_essai")


@admin.register(CodeReduction)
class CodeReductionAdmin(admin.ModelAdmin):
    list_display = ("code", "montant_reduction", "actif", "date_expiration")
    list_filter = ("actif",)


@admin.register(CodeSponsoring)
class CodeSponsoringAdmin(admin.ModelAdmin):
    list_display = ("code", "beneficiaire_nom", "actif")
    list_filter = ("actif",)


@admin.register(AbonnementAnalyseSectorielle)
class AbonnementAnalyseSectorielleAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "type_abonnement", "montant_paye", "actif")


@admin.register(Forfait)
class ForfaitAdmin(admin.ModelAdmin):
    list_display = ("nom", "type_forfait", "prix", "duree_mois", "actif", "ordre_affichage")
    list_filter = ("type_forfait", "actif")
    ordering = ("ordre_affichage",)
