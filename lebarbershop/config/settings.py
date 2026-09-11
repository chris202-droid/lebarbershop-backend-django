"""
Configuration Django pour LEBARBERSHOP.
"""
from pathlib import Path
from datetime import timedelta
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "changez-moi-en-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"
# En production (Vercel) : DJANGO_ALLOWED_HOSTS peut rester tel quel si vous
# gardez exactement ce nom de domaine backend ; sinon, remplacez-le dans les
# variables d'environnement du projet Vercel (Settings → Environment Variables).
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "lebarbershopback.vercel.app,localhost,127.0.0.1"
).split(",")

#supprimer
GDAL_LIBRARY_PATH = r'D:\kalarai\vkalarai\Lib\site-packages\osgeo\gdal304.dll'
GEOS_LIBRARY_PATH = r'D:\kalarai\vkalarai\Lib\site-packages\osgeo\geos_c.dll'
#FIN


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",

    "apps.accounts",
    "apps.salons",
    "apps.employes",
    "apps.services",
    "apps.clients",
    "apps.tickets",
    "apps.stocks",
    "apps.avis",
    "apps.geolocalisation",
    "apps.analytics",
    "apps.paiements",
    "apps.contact",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.NormaliserSlashFinalMiddleware",  # avant CommonMiddleware/APPEND_SLASH — voir config/middleware.py
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",          # protection CSRF
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",  # protection clickjacking
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# 2. Découpage manuel de l'URL avec les outils natifs de Python
db_url = os.environ.get('POSTGRES_URL')
if db_url:
    url = urlparse(db_url)
    DATABASES = {
        'default': {
                'ENGINE': 'django.contrib.gis.db.backends.postgis',
                'NAME': url.path[1:],
                'USER': url.username,
                'PASSWORD':  url.password,
                'HOST': url.hostname,
                'PORT': url.port or 543,
                'OPTIONS':{
                    'charset':'utf8',
                    'init_command':"SET sql_mode = 'STRICT_TRANS_TABLES' ",
                    'sslmode':'require'
                },
            }
    }
else:
    DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.mysql',
        'NAME': 'lebarbershop',
        'USER': 'root',
        'PASSWORD':  '',
        'HOST': 'localhost',
        'PORT': 3308,
        'OPTIONS':{
            'charset':'utf8',
            'init_command':"SET sql_mode = 'STRICT_TRANS_TABLES' ",
        },
    }
}

AUTH_USER_MODEL = "accounts.Utilisateur"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalisation (français / anglais, détection par zone géographique)
LANGUAGE_CODE = "fr"
LANGUAGES = [("fr", "Français"), ("en", "English")]
TIME_ZONE = "Africa/Douala"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django REST Framework ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {"user": "1000/day", "anon": "100/day"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# --- Sécurité (OWASP) ---
SECURE_BROWSER_XSS_FILTER = True          # protection XSS additionnelle navigateurs anciens
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"                  # anti clickjacking
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG          # cookies uniquement en HTTPS en prod (anti session hijacking)
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
# Vercel termine le HTTPS en amont (proxy) : sans cette ligne, Django voit une
# requête HTTP "interne" et SECURE_SSL_REDIRECT déclenche une boucle infinie
# de redirection. Cette ligne indique à Django de faire confiance à l'en-tête
# X-Forwarded-Proto envoyé par le proxy Vercel pour savoir si la requête
# d'origine était bien en HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG

# Requis par Django (4+) pour accepter les requêtes POST du Django admin
# (connexion, formulaires) lorsque le site est servi en HTTPS derrière un
# proxy comme celui de Vercel — sans ça, la connexion à /admin/ échoue avec
# une erreur "CSRF verification failed" même en visitant le bon domaine.
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS", "https://lebarbershopback.vercel.app"
).split(",")

# En production : définir CORS_ALLOWED_ORIGINS avec le(s) domaine(s) exact(s)
# du frontend (schéma https:// obligatoire, sans slash final) si celui-ci
# diffère de la valeur par défaut ci-dessous — voir Vercel → Settings →
# Environment Variables du projet backend.
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "https://lebarbershop.org,https://www.lebarbershop.org,http://localhost:8000,http://localhost:5173",
).split(",")
CORS_ALLOW_CREDENTIALS = True

# --- Email (notifications des formulaires publics : contact, partenariat) ---
# En développement (aucune variable EMAIL_HOST définie), les emails sont
# affichés dans la console au lieu d'être réellement envoyés.
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@lebarbershop.org")

# Boîte de réception des formulaires publics (contact, partenariat)
CONTACT_EMAIL_DESTINATAIRE = os.environ.get("CONTACT_EMAIL_DESTINATAIRE", "information@kalarai.com")
