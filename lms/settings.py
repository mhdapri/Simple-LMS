"""
Django settings untuk Simple LMS - Lab 05: Optimasi Database

Melanjutkan dari Modul 04 (Django ORM) dengan tambahan:
- Database PostgreSQL (bukan SQLite)
- Django Silk untuk query profiling
- Media files untuk ImageField dan FileField
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: jangan gunakan key ini di production!
SECRET_KEY = "django-insecure-lab05-db-optimization-simple-lms-key-2025"

# SECURITY WARNING: matikan DEBUG di production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# =============================================================================
# Aplikasi yang terdaftar
# =============================================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "silk",
    "django_celery_results",
    "django_celery_beat",
    "courses",
]


# =============================================================================
# Middleware
# =============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "silk.middleware.SilkyMiddleware",  # Silk harus di posisi awal (setelah Security)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "lms.urls"

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

WSGI_APPLICATION = "lms.wsgi.application"


# =============================================================================
# Database - PostgreSQL atau SQLite fallback untuk pengembangan lokal
# =============================================================================

USE_SQLITE = os.getenv("USE_SQLITE", "1") == "1"

if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "lms_db"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
            "HOST": os.getenv("DB_HOST", "database"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }


# =============================================================================
# Django Silk - Konfigurasi Profiling
# Akses dashboard di: http://localhost:8000/silk/
# =============================================================================

SILKY_PYTHON_PROFILER = True   # Aktifkan function-level profiling
SILKY_META = True              # Track query Silk sendiri (untuk transparansi)


# =============================================================================
# Password validation
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# =============================================================================
# Internationalization
# =============================================================================

LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True


# =============================================================================
# Static dan Media files
# =============================================================================

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
MONGO_DB = os.getenv("MONGO_DB", "lms_logs")
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_BEAT_SCHEDULE = {
    "update-course-statistics": {
        "task": "courses.tasks.update_course_statistics",
        "schedule": 60 * 60,
    }
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"