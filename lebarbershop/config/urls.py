from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.salons.urls")),
    path("api/v1/", include("apps.employes.urls")),
    path("api/v1/", include("apps.services.urls")),
    path("api/v1/", include("apps.clients.urls")),
    path("api/v1/", include("apps.tickets.urls")),
    path("api/v1/", include("apps.stocks.urls")),
    path("api/v1/", include("apps.avis.urls")),
    path("api/v1/", include("apps.geolocalisation.urls")),
    path("api/v1/", include("apps.analytics.urls")),
    path("api/v1/", include("apps.paiements.urls")),
    path("api/v1/", include("apps.contact.urls")),
]
