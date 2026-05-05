import environ
from .base import *  # noqa: F401, F403

env = environ.Env()

DEBUG = False

DATABASES = {
    "default": env.db("DATABASE_URL")
}

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
