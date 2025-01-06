from pathlib import Path
import os
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-5kyff0s@l_##j3jawec5@b%!^^e(j7v)ouj4b7q6kru#o#a)o3"


env = environ.Env()

# Define the path to the .env file
env_file = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
)

# Check if the .env file exists
if os.path.exists(env_file):
    print(f"Using env file: {env_file}")
    environ.Env.read_env(env_file)
else:
    print("No .env file found.")


# print out the env file used
print(f"Using env file: {env.path}")

DEBUG = True
PA_USER = "alphaonelabs99282llkb"
PA_HOST = PA_USER + ".pythonanywhere.com"
PA_WSGI = "/var/www/" + PA_USER + "_pythonanywhere_com_wsgi.py"
PA_SOURCE_DIR = "/home/" + PA_USER + "/web"

ALLOWED_HOSTS = ["alphaonelabs99282llkb.pythonanywhere.com", "127.0.0.1"]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "web",
    "captcha",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "web.middleware.GlobalExceptionMiddleware",  # Add this line
]

ROOT_URLCONF = "web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates", BASE_DIR],
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

WSGI_APPLICATION = "web.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


if os.environ.get("DATABASE_URL"):
    DEBUG = False
    DATABASES = {"default": env.db()}

    EMAIL_HOST = "smtp.sendgrid.net"
    EMAIL_HOST_USER = os.environ.get("SENDGRID_USERNAME", "apikey")
    EMAIL_HOST_PASSWORD = os.environ.get("SENDGRID_PASSWORD", "blank")
    SENDGRID_API_KEY = os.environ.get("SENDGRID_PASSWORD", "blank")
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"
    EMAIL_FROM = os.environ.get("EMAIL_FROM")

    # import sentry_sdk

    # sentry_sdk.init(
    #     dsn=os.environ.get("SENTRY_DSN"),
    # )


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


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MEDIA_ROOT = "/home/alphaonelabs99282llkb/web/media"
MEDIA_URL = "/media/"
STATIC_ROOT = "/home/alphaonelabs99282llkb/web/static"
STATIC_URL = "/static/"
