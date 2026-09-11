# LEBARBERSHOP — Backend Django REST Framework

SaaS de gestion de salons de coiffure et d'esthétique au Cameroun.

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Variables d'environnement (voir config/settings.py) :
# DJANGO_SECRET_KEY, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Structure des apps

| App              | Rôle |
|-------------------|------|
| `accounts`        | Utilisateurs (admin principal/secondaire, propriétaires, employés), droits d'admin |
| `salons`           | Salons, abonnements SAAS, codes réduction/sponsoring, abonnements d'analyse sectorielle |
| `employes`         | Employés d'un salon et leurs rôles |
| `services`         | Soins/services proposés (avec prix et catégorie) |
| `clients`          | Clients et fidélité par salon |
| `tickets`          | Tickets de soins, lignes de ticket, validation/encaissement |
| `stocks`           | Produits et mouvements de stock (alertes de rupture) |
| `avis`             | Notes et commentaires clients sur les salons |
| `geolocalisation`  | Secteurs géographiques (statistiques par zone) |
| `analytics`        | Bilans journaliers, rendement des employés, statistiques sectorielles |
| `paiements`        | Paiements d'abonnement (Orange Money, MTN MoMo, carte bancaire) |
| `contact`          | Formulaires publics de la landing page : contact, demande de partenariat, demande de code promo |

## Points clés d'implémentation

- **Abonnement SAAS** : 1500 FCFA/mois pour le 1er abonnement (min 3 mois = 4500), 1800 FCFA/mois ensuite (`apps/salons/models.py::Abonnement`). Calcul automatique dans `AbonnementSerializer.create`.
- **Workflow ticket** : un coiffeur/coiffeuse crée le ticket (`POST /api/v1/tickets/`) avec ses lignes de soins (chacune associée à l'employé qui l'exécute) ; la caissière le valide et encaisse (`POST /api/v1/tickets/{id}/valider/`), ce qui met à jour automatiquement la fidélité client et les agrégats de performance/bilan.
- **Analyse sectorielle payante** (20000 / 25000 FCFA) : `apps/salons/models.py::AbonnementAnalyseSectorielle`.
- **Sécurité** : JWT (SimpleJWT), CSRF activé, cookies HttpOnly/SameSite/Secure, X-Frame-Options DENY (clickjacking), throttling DRF, `SECURE_*` settings pour HSTS/SSL en production — voir `config/settings.py`.
- **Internationalisation** : `LANGUAGES = [fr, en]`, `langue_preferee` sur l'utilisateur ; la détection de zone géographique est à brancher côté frontend/IP pour définir la langue par défaut.
- **Formulaires publics (landing page)** : `apps/contact/` expose 3 endpoints `AllowAny` (throttlés) consommés par `Accueil.jsx` côté frontend :
  - `POST /api/v1/contact/demandes/` — formulaire « Nous contacter » (`nom`, `email`, `motif`, `message`). `motif` ∈ `partenariat`, `ouverture_salon`, `information`, `autre`. Déclenche l'envoi d'un email de notification vers `CONTACT_EMAIL_DESTINATAIRE` (par défaut `information@kalarai.com`, configurable via variable d'environnement) — voir `apps/contact/emails.py`. En développement sans SMTP configuré, l'email s'affiche simplement dans la console (`EMAIL_BACKEND` console par défaut si `DEBUG=True`).
  - `POST /api/v1/contact/partenariats/` — formulaire « Devenir partenaire » (`nom`, `structure`, `contact`) ; déclenche aussi une notification email ; à traiter manuellement dans le Django admin puis convertir en `CodeSponsoring` réel via `apps/salons`.
  - `POST /api/v1/contact/code-promo/` — formulaire « Obtenir un code promo » (`email`) : génère et renvoie immédiatement un `CodeReduction` de 10 %, valable 30 jours, usage unique (pas d'envoi d'email configuré — le code est affiché directement côté frontend). Une nouvelle demande avec le même email renvoie le code déjà généré tant qu'il est actif.
  - Variables d'environnement email à définir en production : `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`, `CONTACT_EMAIL_DESTINATAIRE`.
- **Essai gratuit de 14 jours** : `POST /api/v1/abonnements/essai/` (`apps/salons/views.py::AbonnementEssaiView`) — crée un `Abonnement` avec `est_essai=True`, `prix_mensuel=0`, `montant_total=0`, valable `Abonnement.DUREE_ESSAI_JOURS` (14 jours), sans passer par `PaiementAbonnement` ni exiger de moyen de paiement. Réservé au propriétaire du salon (ou à un administrateur), et limité à un essai par salon (refusé si le salon a déjà un abonnement, quel qu'il soit). Le salon passe directement en statut `actif`.

## Prochaines étapes suggérées

1. `python manage.py makemigrations && migrate` une fois PostgreSQL configuré.
2. Brancher les passerelles Orange Money / MTN MoMo / carte bancaire dans `apps/paiements/views.py::confirmer`.
3. Ajouter les tâches planifiées (Celery) pour : expiration des abonnements, alertes de rupture de stock, agrégation nocturne des bilans.
4. Déploiement : Vercel (serverless, via `vercel.json` + WSGI adapter) ou cPanel classique (voir `requirements.txt`, `gunicorn`).
