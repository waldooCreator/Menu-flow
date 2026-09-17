"""
Configuración de Django. Todo lo que cambia entre instancias (una por
restaurante, SPEC-009) viene de variables de entorno, nunca escrito aquí.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga el .env de la raíz del proyecto (un nivel arriba de backend/)
load_dotenv(BASE_DIR.parent / ".env")


def _bool_env(nombre, por_defecto="False"):
    return os.environ.get(nombre, por_defecto).strip().lower() in ("1", "true", "sí", "si")


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "clave-insegura-solo-para-desarrollo")
DEBUG = _bool_env("DJANGO_DEBUG", "True")
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

# En desarrollo se acepta cualquier host: el PC se abre desde el celular por
# la IP de la red local, que cambia cada vez que se cambia de red o de
# hotspot. Fijarla a mano seria una molestia constante.
# En produccion NUNCA se llega aqui, porque DEBUG es False.
if DEBUG:
    ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Lookups de PostgreSQL: `unaccent` para buscar en el libro sin tildes (SPEC-024).
    "django.contrib.postgres",
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "corsheaders",
    "configuracion",
    "menu",
    "estaciones",
    "pedidos",
    "ventas",
    "clientes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "nucleo.urls"

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

WSGI_APPLICATION = "nucleo.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "terra"),
        "USER": os.environ.get("DB_USER", "terra"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5433"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Español, tal como manda la regla de idioma del proyecto (CLAUDE.md)
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Rutas relativas configurables (SPEC-009 / ADR de despliegue multi-instancia):
# cada instancia en el VPS define su propia carpeta de medios.
MEDIA_URL = os.environ.get("MEDIA_URL", "/media/")
MEDIA_ROOT = BASE_DIR / os.environ.get("MEDIA_ROOT", "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- API (DRF) ------------------------------------------------------------
# Django es solo API y permisos (decisión del autor, ADR-006): ninguna vista
# renderiza HTML. Todo el frontend —cliente, mesero/estación y admin— es Vue
# y consume esta API.

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    # Por defecto cerrado (solo autenticados). Cada vista pública (menú,
    # configuración) declara explícitamente AllowAny — nunca al revés, para
    # que un endpoint nuevo no quede abierto por olvido.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}

# --- CORS -------------------------------------------------------------
# Orígenes de Vue permitidos. En el VPS, cada instancia define el suyo
# (mismo patrón que puerto/DB/medios por instancia — ADR-006).
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if o.strip()
]
