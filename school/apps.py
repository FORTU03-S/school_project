# school_project/school/apps.py

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class SchoolConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'school' # <-- Le nom de l'application doit être 'school' ici
    verbose_name = _("Gestion Scolaire") # Optionnel, pour un nom plus sympa dans l'admin
