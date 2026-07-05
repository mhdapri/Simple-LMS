"""
Settings override untuk testing lokal dengan SQLite.
Gunakan dengan: DJANGO_SETTINGS_MODULE=lms.settings_test python manage.py ...
Atau: python manage.py --settings=lms.settings_test ...
"""

from .settings import *  # noqa: F401, F403

# Override database ke SQLite untuk testing lokal (tanpa Docker/PostgreSQL)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_test.sqlite3",
    }
}
