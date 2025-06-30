# create_admin.py
import os
import django
import sys # Importez sys pour les messages d'erreur et de succès
from django.contrib.auth import get_user_model
from django.db import IntegrityError, ProgrammingError # Ajout de ProgrammingError pour les problèmes de DB non prête

# Configure Django settings module
# Assurez-vous que 'school_project.settings' correspond au chemin de votre fichier settings.py
# Exemple: si votre settings.py est dans mon_app/settings.py, ce serait 'my_app.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except Exception as e:
    # Capturer les exceptions si Django ne peut pas être initialisé (ex: base de données non prête)
    print(f"Error setting up Django: {e}", file=sys.stderr)
    sys.exit(1) # Quitte le script avec un code d'erreur

User = get_user_model()

# Récupérez les informations de l'administrateur depuis les variables d'environnement
ADMIN_USERNAME = os.environ.get('DJANGO_ADMIN_USERNAME')
ADMIN_EMAIL = os.environ.get('DJANGO_ADMIN_EMAIL', '') # Email peut être vide
ADMIN_PASSWORD = os.environ.get('DJANGO_ADMIN_PASSWORD')

# Vérification que les variables essentielles sont définies
if not all([ADMIN_USERNAME, ADMIN_PASSWORD]):
    print("Error: DJANGO_ADMIN_USERNAME and DJANGO_ADMIN_PASSWORD environment variables must be set.", file=sys.stderr)
    sys.exit(1)

try:
    # Vérifie si l'utilisateur existe déjà
    if not User.objects.filter(username=ADMIN_USERNAME).exists():
        print(f"Attempting to create superuser '{ADMIN_USERNAME}'...", flush=True)
        User.objects.create_superuser(ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD)
        print(f"Superuser '{ADMIN_USERNAME}' created successfully.", flush=True)
    else:
        print(f"Superuser '{ADMIN_USERNAME}' already exists. Skipping creation.", flush=True)
except IntegrityError:
    # Gère le cas où l'utilisateur a été créé par un processus concurrent
    print(f"Error: Superuser '{ADMIN_USERNAME}' could not be created due to an integrity conflict (username already exists).", file=sys.stderr)
    sys.exit(1)
except ProgrammingError as pe:
    # Gère le cas où la base de données n'est pas complètement migrée
    print(f"Error creating superuser: Database tables might not be ready. Ensure migrations are applied. Details: {pe}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    # Gère toute autre erreur inattendue
    print(f"An unexpected error occurred during superuser creation: {e}", file=sys.stderr)
    sys.exit(1)