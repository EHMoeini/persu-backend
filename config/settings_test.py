"""Settings used only by the pytest suite.

The production settings remain in ``config.settings``. These overrides keep the
API tests fast and deterministic without changing runtime behavior.
"""

from .settings import *  # noqa: F401,F403


DEBUG = False

# The test client uses http://testserver; do not redirect it to HTTPS.
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Argon2 is intentionally slow; password hashing is not what these API tests
# measure. Use MD5 only in the test settings.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Explicit local-memory cache so throttle tests cannot leak across processes.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "persu-api-tests",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
