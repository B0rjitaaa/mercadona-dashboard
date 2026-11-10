import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env_list(name: str, default: str = "") -> list[str]:
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "corsheaders",
    # project
    "apps.core",
    "apps.receipts",
    "apps.gmail_sync",
    "apps.mercadona",
    "apps.products",
    "apps.analytics",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "mercadona"),
        "USER": os.environ.get("POSTGRES_USER", "mercadona"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "mercadona"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TIME_ZONE", "Europe/Madrid")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "COERCE_DECIMAL_TO_STRING": True,
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

# Celery
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ACKS_LATE = True

# Gmail
GMAIL_CREDENTIALS_FILE = os.environ.get("GMAIL_CREDENTIALS_FILE", "/app/secrets/credentials.json")
GMAIL_TOKEN_FILE = os.environ.get("GMAIL_TOKEN_FILE", "/app/secrets/token.json")
GMAIL_QUERY = os.environ.get("GMAIL_QUERY", "from:mercadona has:attachment filename:pdf")

# Mercadona API
MERCADONA_BASE_URL = "https://tienda.mercadona.es/api"
MERCADONA_POSTAL_CODE = os.environ.get("MERCADONA_POSTAL_CODE", "41008")
MERCADONA_WAREHOUSE = os.environ.get("MERCADONA_WAREHOUSE", "svq1")
