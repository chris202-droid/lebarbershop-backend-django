from django.contrib import admin
from .models import DemandeContact, DemandePartenariat, DemandeCodePromo


@admin.register(DemandeContact)
class DemandeContactAdmin(admin.ModelAdmin):
    list_display = ("nom", "email", "motif", "traite", "date_creation")
    list_filter = ("motif", "traite")
    search_fields = ("nom", "email", "message")


@admin.register(DemandePartenariat)
class DemandePartenariatAdmin(admin.ModelAdmin):
    list_display = ("nom", "contact", "structure", "traite", "date_creation")
    list_filter = ("traite",)
    search_fields = ("nom", "contact", "structure")


@admin.register(DemandeCodePromo)
class DemandeCodePromoAdmin(admin.ModelAdmin):
    list_display = ("email", "code", "date_creation")
    search_fields = ("email",)
