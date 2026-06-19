"""
Django settings for the SmartCV Builder project.

This is the "core build" phase: real auth, real CV builder, real PDF
export. AI features, payment gateways, social login, Celery/Redis are
NOT wired up here - see README.md "Roadmap" for what's stubbed and why.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_local_env(env_path: Path) -> None:
    """Load simple KEY=VALUE pairs from .env without overriding real env vars."""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


load_local_env(BASE_DIR / ".env")

# --------------------------------------------------------------------------
# Core / security
# --------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-change-me-before-deploying",
)
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if h]

# --------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "widget_tweaks",
    "accounts",
    "resumes",
    "ai",
    "payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "smartcv.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "smartcv.wsgi.application"

# --------------------------------------------------------------------------
# Database
#
# Defaults to SQLite so the project runs out of the box with zero setup.
# Set DJANGO_DB_ENGINE=postgres (plus the env vars below) to use Postgres
# as the spec requires for production.
# --------------------------------------------------------------------------
if os.environ.get("DJANGO_DB_ENGINE") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "smartcv"),
            "USER": os.environ.get("POSTGRES_USER", "smartcv"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --------------------------------------------------------------------------
# Passwords
# --------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------
# i18n
# --------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Static / media
# --------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------
# Auth flow
# --------------------------------------------------------------------------
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "resumes:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# --------------------------------------------------------------------------
# Uploads - secure file upload basics (size cap; type is validated in forms)
# --------------------------------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# --------------------------------------------------------------------------
# Email - prints to console in dev so password reset / verification links
# are visible without a real SMTP provider. Swap EMAIL_BACKEND for SMTP
# (and set the env vars below) once you have real credentials.
# --------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@smartcv.local")

MESSAGE_TAGS = {
    10: "info",
    20: "info",
    25: "success",
    30: "warning",
    40: "danger",
}

# --------------------------------------------------------------------------
# AI Provider (OpenAI, GitHub, or ZAI) for AI features: resume writer,
# analyzer, career suggestions.
# Set `AI_PROVIDER` to 'openai', 'github', or 'zai' (default: 'openai')
# --------------------------------------------------------------------------
AI_PROVIDER = os.environ.get("AI_PROVIDER", "openai").lower()

# OpenAI configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# GitHub AI configuration (for models.github.com or Azure OpenAI)
GITHUB_API_KEY = os.environ.get("GITHUB_API_KEY", "")
GITHUB_AI_MODEL = os.environ.get("GITHUB_AI_MODEL", "gpt-4o")
GITHUB_AI_ENDPOINT = os.environ.get("GITHUB_AI_ENDPOINT", "https://models.inference.ai.azure.com")

# ZAI provider configuration
# Set AI_PROVIDER=zai to use this provider.
ZAI_API_KEY = os.environ.get("ZAI_API_KEY", "")
ZAI_AI_MODEL = os.environ.get("ZAI_AI_MODEL", "glm-5.2")
ZAI_AI_ENDPOINT = os.environ.get("ZAI_AI_ENDPOINT", "https://api.z.ai/api/paas/v4/chat/completions")

# --------------------------------------------------------------------------
# Stripe (payment integration)
# Use sk_test_… / pk_test_… keys for dev/staging; live keys for production.
# STRIPE_WEBHOOK_SECRET is the whsec_… from `stripe listen` in dev or the
# Stripe dashboard webhook endpoint configuration in production.
# STRIPE_PREMIUM_PRICE_ID is the Price ID (price_…) for the Premium
# subscription product you created in your Stripe dashboard.
# --------------------------------------------------------------------------
STRIPE_SECRET_KEY       = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY  = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET   = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PREMIUM_PRICE_ID = os.environ.get("STRIPE_PREMIUM_PRICE_ID", "")
