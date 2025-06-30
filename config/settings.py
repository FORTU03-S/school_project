

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-votresecretkeyici!genereznouvelle' # REMPLACEZ CECI PAR UNE VRAIE CLÉ EN PROD !

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True # Mettez à False en production

ALLOWED_HOSTS = [] # Laissez vide pour le développement, ajoutez les noms de domaine en production (ex: ['mon-site.com', 'www.mon-site.com'])


# Application definition

INSTALLED_APPS = [
    # Applications Django par défaut
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',    # Pour CustomUser et UserProfile
    'school',
    'profiles',   
    'crispy_forms', # Pour les formulaires Bootstrap (si vous l'utilisez)
    'crispy_bootstrap5', # Pour le thème Bootstrap 5 avec Crispy Forms
    'widget_tweaks', # Pour les widgets améliorés (si vous l'utilisez)
]

# MIDDLEWARE est une liste de classes de middleware à utiliser.
# Les middleware sont des "hooks" de bas niveau qui peuvent modifier les requêtes et les réponses.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'debug_toolbar.middleware.DebugToolbarMiddleware', # Décommenter si Debug Toolbar est activé
]

# Définissez le modèle d'utilisateur personnalisé que Django doit utiliser.
# C'est CRUCIAL pour que Django reconnaisse votre CustomUser.
AUTH_USER_MODEL = 'profiles.CustomUser' # S'assurer que le chemin est correct

ROOT_URLCONF = 'config.urls' # Le chemin vers votre fichier urls.py principal

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], # Ajoutez un dossier 'templates' global pour vos templates communs
        'APP_DIRS': True, # Cherche des templates dans les dossiers 'templates' de chaque application
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3', # Utilisation de SQLite par défaut, facile pour le développement
    }
}

# Pour une base de données PostgreSQL (recommandé pour la production) :
#DATABASES = {
#     'default': {
 #        'ENGINE': 'django.db.backends.mysql',
 #        'NAME': 'school_project_db',
 #        'USER': 'root',
 #""        'PASSWORD': 'fortu@2002MK',
 #        'HOST': 'localhost', # Ou l'adresse IP de votre serveur de base de données
 #        'PORT': '3306', # Port par défaut 
  #""       'OPTIONS': {
  #           'init_command':"SET sql_mode='STRICT_TRANS_TABLES'"
 #        }
 #    }
 #}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]




# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'fr-fr' # Langue par défaut de votre projet

TIME_ZONE = 'Africa/Lubumbashi' # Fuseau horaire pour la RDC (ou 'Africa/Kinshasa', 'Africa/Goma')

USE_I18N = True # Active le système de traduction

USE_TZ = True # Active la prise en charge des fuseaux horaires (recommandé)


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/' # URL de base pour les fichiers statiques (CSS, JS, images)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') # Où Django collectera les fichiers statiques en production
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'), # Où vous stockerez vos fichiers statiques dans le développement
]

# Media files (uploaded by users - e.g., profile pictures)
# https://docs.djangoproject.com/en/5.0/topics/files/

MEDIA_URL = '/media/' # URL de base pour les fichiers médias (téléchargés par les utilisateurs)
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') # Où les fichiers médias seront stockés physiquement

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configurations supplémentaires utiles

# Redirections après connexion/déconnexion
LOGIN_REDIRECT_URL = 'home' # URL vers laquelle rediriger après une connexion réussie
LOGOUT_REDIRECT_URL = '/' # URL vers laquelle rediriger après une déconnexion réussie
LOGIN_URL = 'profiles:login' # Nom de l'URL pour la page de connexion (si vous en avez une)

# Pour les messages de Django (ex: après un formulaire validé)
MESSAGE_TAGS = {
    # Permet de styliser les messages différemment avec Bootstrap ou autre framework CSS
    # 10: 'debug', 20: 'info', 25: 'success', 30: 'warning', 40: 'error'
    # 'debug': 'alert-secondary',
    # 'info': 'alert-info',
    # 'success': 'alert-success',
    # 'warning': 'alert-warning',
    # 'error': 'alert-danger',
}

# Email Backend (pour l'envoi d'emails - ex: réinitialisation de mot de passe)
# En développement, il est courant d'utiliser la console ou un serveur de test
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' # Affiche les emails dans la console

# Pour la production, vous utiliserez un backend réel (ex: SMTP)
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.example.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your_email@example.com'
# EMAIL_HOST_PASSWORD = 'your_email_password'


# Pour Django Debug Toolbar (si vous l'utilisez)
# INTERNAL_IPS = [
#     "127.0.0.1",
# ]
# URL vers laquelle rediriger après une connexion réussie
LOGIN_REDIRECT_URL = 'dashboard_parent' # Nous allons créer cette URL et cette vue
# URL vers laquelle rediriger après une déconnexion réussie
LOGOUT_REDIRECT_URL = 'home' # Redirige vers la page d'accueil après déconnexion

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstra5"
CRISPY_TEMPLATE_PACK = "bootstrap5"  # Utilise Bootstrap 5 pour les formulaires avec Crispy Forms