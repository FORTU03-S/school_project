# school/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate

class SchoolConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'school'

    def ready(self):
        # Importer le signal ici pour éviter les dépendances circulaires
        post_migrate.connect(create_default_fee_type, sender=self)

# Fonction pour créer un FeeType par défaut
def create_default_fee_type(sender, **kwargs):
    from .models import FeeType # Importez FeeType ici pour éviter les dépendances
    if FeeType.objects.count() == 0:
        FeeType.objects.create(name="Frais de Scolarité Standard", description="Frais de scolarité par défaut", is_active=True)
        print("Type de frais par défaut 'Frais de Scolarité Standard' créé.")
