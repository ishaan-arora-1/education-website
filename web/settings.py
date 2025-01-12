import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-5kyff0s@l_##j3jawec5@b%!^^e(j7v)ouj4b7q6kru#o#a)o3"


env = environ.Env()

env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

if os.path.exists(env_file):
    print(f"Using env file: {env_file}")
    environ.Env.read_env(env_file)
else:
    print("No .env file found.")


# Debug settings
DEBUG = env.bool("DJANGO_DEBUG", default=False)

PA_USER = "alphaonelabs99282llkb"
PA_HOST = PA_USER + ".pythonanywhere.com"
PA_WSGI = "/var/www/" + PA_USER + "_pythonanywhere_com_wsgi.py"
PA_SOURCE_DIR = "/home/" + PA_USER + "/web"

# Production settings
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

ALLOWED_HOSTS = [
    "alphaonelabs99282llkb.pythonanywhere.com",
    "127.0.0.1",
    "localhost",
    "alphaonelabs.com",
    "www.alphaonelabs.com",
]
CSRF_TRUSTED_ORIGINS = ["https://alphaonelabs.com", "https://www.alphaonelabs.com"]

# Error handling
handler404 = "web.views.custom_404"
handler500 = "web.views.custom_500"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "web",
    "captcha",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "web.middleware.GlobalExceptionMiddleware",
]

ROOT_URLCONF = "web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates", BASE_DIR / "web/templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "web.context_processors.last_modified",
            ],
        },
    },
]

CAPTCHA_FONT_SIZE = 28
CAPTCHA_IMAGE_SIZE = (150, 40)
CAPTCHA_LETTER_ROTATION = (-20, 20)
CAPTCHA_BACKGROUND_COLOR = "#f0f8ff"
CAPTCHA_FOREGROUND_COLOR = "#2f4f4f"
CAPTCHA_NOISE_FUNCTIONS = ("captcha.helpers.noise_arcs", "captcha.helpers.noise_dots")
CAPTCHA_FILTER_FUNCTIONS = ("captcha.helpers.post_smooth",)
CAPTCHA_2X_IMAGE = True
CAPTCHA_TEST_MODE = False

WSGI_APPLICATION = "web.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

SITE_ID = 1
SITE_NAME = "AlphaOne Labs"
SITE_DOMAIN = "alphaonelabs.com"

# Allauth settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USERNAME_MIN_LENGTH = None
ACCOUNT_RATE_LIMITS = {
    "login_attempt": "5/5m",  # 5 attempts per 5 minutes
    "login_failed": "3/5m",  # 3 failed attempts per 5 minutes
    "signup": "5/h",  # 5 signups per hour
    "send_email": "5/5m",  # 5 emails per 5 minutes
    "change_email": "3/h",  # 3 email changes per hour
}
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_SESSION_REMEMBER = True

# Override allauth forms
ACCOUNT_FORMS = {
    "signup": "web.forms.UserRegistrationForm",
}

LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "index"


LANGUAGE_CODE = "en"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MEDIA_ROOT = "/home/alphaonelabs99282llkb/web/media"
MEDIA_URL = "/media/"
# STATIC_ROOT = "/home/alphaonelabs99282llkb/web/static"
STATIC_URL = "/static/"


STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Email settings
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    print("Using console email backend for development")
    DEFAULT_FROM_EMAIL = "noreply@example.com"  # Default for development
    SENDGRID_API_KEY = None  # Not needed in development
else:
    # Production email settings
    EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"
    SENDGRID_API_KEY = env.str("SENDGRID_API_KEY", default=env.str("SENDGRID_PASSWORD", default=""))
    EMAIL_HOST = "smtp.sendgrid.net"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = "apikey"
    EMAIL_HOST_PASSWORD = env.str("SENDGRID_PASSWORD", default="")
    DEFAULT_FROM_EMAIL = env.str("EMAIL_FROM", default="noreply@alphaonelabs.com")

STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")

LANGUAGES = [
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("zh-hans", "Simplified Chinese"),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

USE_L10N = True

if os.environ.get("DATABASE_URL"):
    DEBUG = False
    DATABASES = {"default": env.db()}

    # Only add MySQL-specific options if using MySQL
    if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
        DATABASES["default"]["OPTIONS"] = {
            "sql_mode": (
                "STRICT_TRANS_TABLES,"
                "NO_ZERO_IN_DATE,"
                "NO_ZERO_DATE,"
                "ERROR_FOR_DIVISION_BY_ZERO,"
                "NO_ENGINE_SUBSTITUTION"
            ),
        }

    # Google Cloud Storage settings for media files in production
    if os.environ.get("GS_BUCKET_NAME"):
        GS_BUCKET_NAME = os.environ.get("GS_BUCKET_NAME")
        GS_DEFAULT_ACL = None
        GS_QUERYSTRING_AUTH = False
        GS_LOCATION = "media"  # Store files in a media directory in the bucket

        # Use default Google Cloud Storage backend
        DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"

    SENDGRID_API_KEY = os.getenv("SENDGRID_PASSWORD", "blank")
    EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"
    EMAIL_FROM = os.getenv("EMAIL_FROM")
