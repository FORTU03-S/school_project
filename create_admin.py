# create_admin.py
import os
import django
import sys
from django.contrib.auth import get_user_model
from django.db import IntegrityError, ProgrammingError

# --- DIAGNOSTIC PRINTS (gardez-les pour le prochain déploiement de test) ---
print(f"--- DIAGNOSTIC INFO ---", flush=True)
print(f"Current working directory (os.getcwd()): {os.getcwd()}", flush=True)
print(f"Python sys.path (où Python cherche les modules):", flush=True)
for p in sys.path:
    print(f"  - {p}", flush=True)
print(f"DJANGO_SETTINGS_MODULE will be set to: config.settings", flush=True)
print(f"--- END DIAGNOSTIC INFO ---", flush=True)

# Configure Django settings module (Confirmé comme 'config.settings')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except Exception as e:
    print(f"ERROR: Failed to setup Django: {e}", file=sys.stderr, flush=True)
    sys.exit(1)

User = get_user_model()

# Récupérez les informations de l'administrateur depuis les variables d'environnement
# Pour CustomUser avec email comme USERNAME_FIELD, DJANGO_ADMIN_EMAIL est l'identifiant principal.
ADMIN_EMAIL_IDENTIFIER = os.environ.get('DJANGO_ADMIN_EMAIL') # Utiliser l'email comme identifiant principal
ADMIN_PASSWORD = os.environ.get('DJANGO_ADMIN_PASSWORD')
# Les champs requis (first_name, last_name, user_type) doivent aussi venir des variables d'environnement
# ou être des valeurs par défaut pour l'admin.
# Pour simplifier, nous allons les définir ici pour le superutilisateur.
# Vous pouvez les ajouter comme variables d'environnement si vous voulez plus de flexibilité.
ADMIN_FIRST_NAME = os.environ.get('DJANGO_ADMIN_FIRST_NAME', 'Super')
ADMIN_LAST_NAME = os.environ.get('DJANGO_ADMIN_LAST_NAME', 'Admin')
ADMIN_USER_TYPE = os.environ.get('DJANGO_ADMIN_USER_TYPE', 'admin') # S'assurer que 'admin' est une valeur valide dans UserRole

# Vérification que les variables essentielles sont définies
if not all([ADMIN_EMAIL_IDENTIFIER, ADMIN_PASSWORD]):
    print("ERROR: DJANGO_ADMIN_EMAIL and DJANGO_ADMIN_PASSWORD environment variables must be set.", file=sys.stderr, flush=True)
    sys.exit(1)

# Vérification des champs requis supplémentaires
if not all([ADMIN_FIRST_NAME, ADMIN_LAST_NAME]):
    print("ERROR: DJANGO_ADMIN_FIRST_NAME and DJANGO_ADMIN_LAST_NAME environment variables (or default values) must be set for superuser creation.", file=sys.stderr, flush=True)
    sys.exit(1)


try:
    # CORRECTION ICI : Filtrer par le champ USERNAME_FIELD (qui est 'email' dans votre CustomUser)
    if not User.objects.filter(email=ADMIN_EMAIL_IDENTIFIER).exists():
        print(f"Attempting to create superuser with email '{ADMIN_EMAIL_IDENTIFIER}'...", flush=True)
        # CORRECTION ICI : Passer les arguments à create_superuser selon la signature de votre CustomUser
        # create_superuser prend les arguments de USERNAME_FIELD et password,
        # puis les REQUIRED_FIELDS comme arguments nommés.
        User.objects.create_superuser(
            email=ADMIN_EMAIL_IDENTIFIER, # Ceci est le USERNAME_FIELD
            password=ADMIN_PASSWORD,
            # Les champs définis dans REQUIRED_FIELDS de votre CustomUser doivent être passés ici
            user_type=ADMIN_USER_TYPE,
            first_name=ADMIN_FIRST_NAME,
            last_name=ADMIN_LAST_NAME,
            # Vous pouvez ajouter d'autres champs si nécessaire, mais seulement les REQUIRED_FIELDS sont obligatoires
            # Par exemple: phone_number="1234567890", address="123 Admin St"
        )
        print(f"Superuser with email '{ADMIN_EMAIL_IDENTIFIER}' created successfully.", flush=True)
    else:
        print(f"Superuser with email '{ADMIN_EMAIL_IDENTIFIER}' already exists. Skipping creation.", flush=True)
except IntegrityError:
    print(f"ERROR: Superuser with email '{ADMIN_EMAIL_IDENTIFIER}' could not be created due to an integrity conflict (email already exists).", file=sys.stderr, flush=True)
    sys.exit(1)
except ProgrammingError as pe:
    print(f"ERROR: Database tables might not be ready. Ensure migrations are applied. Details: {pe}", file=sys.stderr, flush=True)
    sys.exit(1)
except Exception as e:
    print(f"ERROR: An unexpected error occurred during superuser creation: {e}", file=sys.stderr, flush=True)
    sys.exit(1)