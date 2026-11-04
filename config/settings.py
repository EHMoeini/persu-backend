"""Django settings for the Persu backend."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be an integer.") from exc


def env_list(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


# Render sets this automatically for every web service.
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()


# ---------------------------------------------------------------------------
# Test deployment defaults
# ---------------------------------------------------------------------------
# These values make the repository runnable as a production-like test stack
# without an .env file. They are intentionally NOT production secrets. Override
# them with environment variables for any shared or public deployment. See
# .env.production.example for the full override list.
DEBUG = env_bool("DJANGO_DEBUG", False)

_TEST_DEPLOYMENT_SECRET_KEY = (
    "G2JbZTRyHp8woT3u55MvzXeobq-4iX69FWtGEvUjYkuSZ0PRnaI0QLOkmf2pf6l9"
)
_TEST_DEPLOYMENT_AUTH_JWT_SECRET = (
    "NxIVFqDbxSw40CVuy2Q7A1coh2AM6VN1TeKov-ViCMGRknFNCllYsDaoeER1CTTv"
)

_DJANGO_SECRET_FROM_ENV = os.getenv("DJANGO_SECRET_KEY", "").strip()
_AUTH_JWT_SECRET_FROM_ENV = os.getenv("AUTH_JWT_SECRET", "").strip()

if bool(_DJANGO_SECRET_FROM_ENV) != bool(_AUTH_JWT_SECRET_FROM_ENV):
    raise ImproperlyConfigured(
        "Set both DJANGO_SECRET_KEY and AUTH_JWT_SECRET, or neither to use the "
        "test deployment defaults."
    )

SECRET_KEY = _DJANGO_SECRET_FROM_ENV or _TEST_DEPLOYMENT_SECRET_KEY
AUTH_JWT_SECRET = _AUTH_JWT_SECRET_FROM_ENV or _TEST_DEPLOYMENT_AUTH_JWT_SECRET

if not DEBUG and len(SECRET_KEY) < 32:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be at least 32 characters when DJANGO_DEBUG is false."
    )

if len(AUTH_JWT_SECRET) < 32:
    raise ImproperlyConfigured(
        "AUTH_JWT_SECRET must be at least 32 characters for HS256."
    )

if SECRET_KEY == AUTH_JWT_SECRET:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY and AUTH_JWT_SECRET must differ.")

_default_allowed_hosts = "localhost,127.0.0.1,testserver"
if RENDER_EXTERNAL_HOSTNAME:
    _default_allowed_hosts = f"{_default_allowed_hosts},{RENDER_EXTERNAL_HOSTNAME}"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", _default_allowed_hosts)

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "apps.common",
    "apps.accounts",
    "apps.resources",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").strip().lower()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Test-only PostgreSQL credentials; docker-compose.yml uses the same defaults.
# Override DB_PASSWORD (and the other DB_* variables) for any shared deployment.
_TEST_DEPLOYMENT_DB_PASSWORD = "fd2Sb_yRNfAqMD3dVYK-lHSNr51Ged2b"

if DATABASE_URL:
    # Render (and most hosts) provide a single PostgreSQL connection string.
    _db_url = urlparse(DATABASE_URL)
    if _db_url.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured(
            "DATABASE_URL must be a PostgreSQL connection string."
        )

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(_db_url.path.lstrip("/")),
            "USER": unquote(_db_url.username or ""),
            "PASSWORD": unquote(_db_url.password or ""),
            "HOST": _db_url.hostname or "",
            "PORT": str(_db_url.port or "5432"),
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {
                key: values[-1]
                for key, values in parse_qs(_db_url.query).items()
            },
        }
    }
elif DB_ENGINE in {"postgres", "postgresql"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "persu"),
            "USER": os.getenv("DB_USER", "persu"),
            "PASSWORD": os.getenv("DB_PASSWORD", _TEST_DEPLOYMENT_DB_PASSWORD),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
            "CONN_HEALTH_CHECKS": True,
        }
    }
elif DB_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
            "OPTIONS": {"timeout": 20},
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    raise ImproperlyConfigured(
        "DB_ENGINE must be 'sqlite' or 'postgresql'."
    )

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Cache (Redis is recommended for multi-worker production deployments)
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "").strip()

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "persu-local",
        }
    }

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

# Argon2id for new passwords; PBKDF2 verifies legacy hashes.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.BearerAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "apps.accounts.permissions.IsAuthenticatedUser",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_THROTTLE_RATES": {
        "auth_check": "10/min",
        "auth_login": "5/min",
        "auth_register": "5/min",
        "auth_refresh": "20/min",
        "auth_logout": "30/min",
        "auth_otp_send": "5/min",
        "auth_otp_verify": "10/min",
    },
}

# Access JWT settings.
AUTH_JWT = {
    "ALGORITHM": "HS256",
    "SECRET": AUTH_JWT_SECRET,
    "ISSUER": os.getenv("AUTH_JWT_ISSUER", "http://localhost:8000"),
    "AUDIENCE": os.getenv("AUTH_JWT_AUDIENCE", "http://localhost:3000"),
    "ACCESS_TOKEN_TTL_SECONDS": env_int("AUTH_ACCESS_TOKEN_TTL_SECONDS", 15 * 60),
}
AUTH_REFRESH_TOKEN_TTL_SECONDS = env_int(
    "AUTH_REFRESH_TOKEN_TTL_SECONDS", 30 * 24 * 60 * 60
)

if AUTH_JWT["ACCESS_TOKEN_TTL_SECONDS"] <= 0:
    raise ImproperlyConfigured("AUTH_ACCESS_TOKEN_TTL_SECONDS must be positive.")
if AUTH_REFRESH_TOKEN_TTL_SECONDS <= 0:
    raise ImproperlyConfigured("AUTH_REFRESH_TOKEN_TTL_SECONDS must be positive.")

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# Browser CORS applies only to /api/*.
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
CORS_ALLOW_CREDENTIALS = False
CORS_ALLOW_HEADERS = [
    "authorization",
    "content-type",
]
CORS_ALLOW_METHODS = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
]
CORS_URLS_REGEX = r"^/api/"

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
# The test deployment runs over plain HTTP on localhost. Enable the HTTPS
# settings below (or set the matching environment variables) once TLS is
# terminated by a trusted proxy or load balancer.
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
# Allow internal load-balancer health checks without an HTTPS redirect.
SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", SECURE_SSL_REDIRECT)
CSRF_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", SECURE_SSL_REDIRECT)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG and SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = not DEBUG and SECURE_HSTS_SECONDS > 0

if env_bool("DJANGO_BEHIND_PROXY", bool(RENDER_EXTERNAL_HOSTNAME)):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True

_default_csrf_origins = "http://localhost:8000,http://127.0.0.1:8000"
if RENDER_EXTERNAL_HOSTNAME:
    _default_csrf_origins = (
        f"{_default_csrf_origins},https://{RENDER_EXTERNAL_HOSTNAME}"
    )

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", _default_csrf_origins)

# ---------------------------------------------------------------------------
# Internationalization / static files
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}
WHITENOISE_MAX_AGE = 0 if DEBUG else 31536000

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}
