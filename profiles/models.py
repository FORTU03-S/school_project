# school_project/profiles/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
import string
import random

from school.models import School, Classe

# --- Définition des rôles d'utilisateur ---
class UserRole(models.TextChoices):
    STUDENT = 'STUDENT', 'Élève'
    PARENT = 'PARENT', 'Parent'
    TEACHER = 'TEACHER', 'Enseignant'
    DIRECTION = 'DIRECTION', 'Direction'
    ACCOUNTANT = 'ACCOUNTANT', 'Comptable'
    ADMIN = 'ADMIN', 'ADMIN'
    STAFF = 'STAFF', 'Personnel Administratif'

# --- Manager personnalisé pour CustomUser (pour utiliser l'email comme identifiant) ---
class CustomUserManager(BaseUserManager):
    """
    Manager de modèle personnalisé où l'email est l'identifiant unique
    pour l'authentification au lieu des noms d'utilisateur.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('L\'adresse email doit être définie'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Crée et enregistre un superutilisateur avec l'email et le mot de passe donnés.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', UserRole.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Le superutilisateur doit avoir is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Le superutilisateur doit avoir is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


# --- Modèle CustomUser (Utilisateur personnalisé) ---
class CustomUser(AbstractUser):
    """
    Modèle d'utilisateur personnalisé étendant AbstractUser.
    Utilise l'email comme champ d'authentification principal.
    Ajoute un champ 'user_type' pour catégoriser les utilisateurs.
    """
    username = None # Supprime le champ username par défaut d'AbstractUser
    email = models.EmailField(_('adresse email'), unique=True)
    user_type = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STAFF,
        verbose_name="Type d'utilisateur"
    )
    first_name = models.CharField(_("prénom"), max_length=150, blank=False)
    last_name = models.CharField(_("nom de famille"), max_length=150, blank=False)
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Numéro de Téléphone")
    address = models.TextField(blank=True, null=True, verbose_name="Adresse")
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True, verbose_name="Photo de profil")
    date_of_birth = models.DateField(blank=True, null=True, verbose_name="Date de naissance")

    is_approved = models.BooleanField(default=False, verbose_name="Approuvé")

    school = models.ForeignKey(
        'school.School', # Référence par chaîne si School est dans une autre app
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='custom_users',
        verbose_name="École Affiliée"
    )

    USERNAME_FIELD = 'email' # Définit l'email comme champ d'authentification
    REQUIRED_FIELDS = ['user_type', 'first_name', 'last_name'] # Champs obligatoires à la création de superuser

    objects = CustomUserManager() # Utilise le manager personnalisé

    # CORRECTION : _str_ doit avoir deux underscores de chaque côté
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user_type})" if self.first_name and self.last_name else self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    class Meta:
        verbose_name = "Utilisateur Personnalisé"
        verbose_name_plural = "Utilisateurs Personnalisés"
        ordering = ['last_name', 'first_name', 'email']


# --- Modèle Student (Élève) ---
class Student(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Prénom de l'élève")
    last_name = models.CharField(max_length=100, verbose_name="Nom de l'élève")
    middle_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Post-nom")
    date_of_birth = models.DateField(verbose_name="Date de naissance", null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Homme'), ('Female', 'Femme'), ('Other', 'Autre')], blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Numéro de Téléphone")
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='student_profiles/', null=True, blank=True)
    student_id_code = models.CharField(max_length=50, unique=True, verbose_name="Code d'identification élève", blank=True, null=True)

    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name="École"
    )
    current_classe = models.ForeignKey(
        Classe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students_in_class',
        verbose_name="Classe Actuelle"
    )
    parents = models.ManyToManyField(
        # ⭐ CORRECTION ICI : Utilisez settings.AUTH_USER_MODEL pour CustomUser ⭐
        settings.AUTH_USER_MODEL,
        related_name='children',
        # ⭐ CORRECTION ICI : Accédez au UserRole via settings.AUTH_USER_MODEL ⭐
        limit_choices_to={
            'user_type': 'PARENT' # Le plus simple est de mettre la chaîne directe
            # Si vous tenez à utiliser l'enum, il faut importer le CustomUser model lui-même
            # et y accéder via CustomUser.UserRole.PARENT
        },
        blank=True,
        verbose_name="Parents légaux"
    )

    is_active = models.BooleanField(default=True, verbose_name="Actif")
    enrollment_date = models.DateField(default=timezone.now, verbose_name="Date d'inscription")

    def _str(self): # ⭐ CORRECTION: double underscore pour __str_ ⭐
        classe_info = self.current_classe.name if self.current_classe else 'Non assignée'
        return f"{self.first_name} {self.last_name} ({classe_info})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    # ⭐ IMPORTANTE MODIFICATION : LA LOGIQUE D'INSCRIPTION AUX COURS EST SUPPRIMÉE D'ICI ⭐
    # Elle sera gérée dans la vue (ou un signal post_save) pour éviter des exécutions répétées.
    def save(self, *args, **kwargs):
        if not self.student_id_code: # Si le code n'est pas déjà défini
            # Méthode préférée : Basé sur le temps et une chaîne aléatoire (très faible risque de collision)
            timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            generated_code = f"STU-{timestamp}-{random_suffix}"

            # Assurez-vous de l'unicité
            while Student.objects.filter(student_id_code=generated_code).exists():
                random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                generated_code = f"STU-{timestamp}-{random_suffix}"
            self.student_id_code = generated_code

        super().save(*args, **kwargs) # Appeler la méthode save originale du modèle

    class Meta:
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"
        ordering = ['school__name', 'last_name', 'first_name']
# --- Modèle Parent (Parent d'élève) ---
class Parent(models.Model):
    """
    Informations spécifiques aux parents, distinctes de leur compte utilisateur.
    """
    user_account = models.OneToOneField(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parent_profile',
        limit_choices_to={'user_type': UserRole.PARENT},
        verbose_name="Compte Utilisateur Parent"
    )
    first_name = models.CharField(max_length=100, verbose_name="Prénom du parent")
    last_name = models.CharField(max_length=100, verbose_name="Nom du parent")

    school = models.ForeignKey(
        'school.School',
        on_delete=models.CASCADE,
        related_name='parents_at_school',
        verbose_name="École Affiliée"
    )

    is_approved = models.BooleanField(default=False, verbose_name="Approuvé")

    # CORRECTION : _str_ doit avoir deux underscores de chaque côté
    def __str__(self):
        return f"{self.first_name} {self.last_name} (Approuvé: {self.is_approved})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    class Meta:
        verbose_name = "Parent"
        verbose_name_plural = "Parents"
        ordering = ['school__name', 'last_name', 'first_name']


# --- Signaux pour lier les comptes CustomUser aux profils Student et Parent ---
@receiver(post_save, sender=CustomUser)
def create_or_update_profile_for_custom_user(sender, instance, created, **kwargs):
    if instance.user_type == UserRole.STUDENT:
        # CORRECTION : Utiliser un logger au lieu d'un simple print pour les messages d'erreur/avertissement
        # import logging
        # logger = logging.getLogger(_name_)
        if not instance.email or not instance.first_name or not instance.last_name:
            # logger.warning(f"ATTENTION: CustomUser {instance.email} de type STUDENT n'a pas les informations complètes pour créer un profil Student.")
            print(f"ATTENTION: CustomUser {instance.email} de type STUDENT n'a pas les informations complètes pour créer un profil Student.")
            return

        defaults = {
            'first_name': instance.first_name,
            'last_name': instance.last_name,
            'date_of_birth': instance.date_of_birth,
            'school': instance.school,
            'student_id_code': f"STU-{instance.pk}-{timezone.now().year}"
        }
        if instance.school:
            defaults['school'] = instance.school

        student_profile, created = Student.objects.get_or_create(user_account=instance, defaults=defaults)

        if not created:
            student_profile.first_name = instance.first_name
            student_profile.last_name = instance.last_name
            student_profile.date_of_birth = instance.date_of_birth or student_profile.date_of_birth
            student_profile.school = instance.school or student_profile.school
            student_profile.save()

    elif instance.user_type == UserRole.PARENT:
        if not instance.email or not instance.first_name or not instance.last_name:
            # logger.warning(f"ATTENTION: CustomUser {instance.email} de type PARENT n'a pas les informations complètes pour créer un profil Parent.")
            print(f"ATTENTION: CustomUser {instance.email} de type PARENT n'a pas les informations complètes pour créer un profil Parent.")
            return

        defaults = {
            'first_name': instance.first_name,
            'last_name': instance.last_name,
            'is_approved': instance.is_approved
        }
        if instance.school:
            defaults['school'] = instance.school

        parent_profile, created = Parent.objects.get_or_create(user_account=instance, defaults=defaults)

        if not created:
            parent_profile.first_name = instance.first_name
            parent_profile.last_name = instance.last_name
            parent_profile.school = instance.school or parent_profile.school
            parent_profile.is_approved = instance.is_approved
            parent_profile.save()

# --- Modèle Notification (Votre Notification en bas de models.py) ---
class Notification(models.Model):
    recipient = models.ForeignKey('profiles.CustomUser', on_delete=models.CASCADE, related_name='notifications', verbose_name="Destinataire")
    sender = models.ForeignKey('profiles.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications', verbose_name="Expéditeur")
    subject = models.CharField(max_length=255, verbose_name="Sujet" , blank=True, null=True)
    message = models.TextField(verbose_name="Message")
    notification_type_choices = [
        ('ABSENCE', 'Absence Enfant'),
        ('EVALUATION', 'Évaluation à venir'),
        ('HOMEWORK', 'Devoir à faire'),
        ('QUIZ', 'Interrogation / Quiz'), # Ajouté pour correspondre à GradeForm
        ('MESSAGE_TEACHER', 'Message de l\'enseignant'),
        ('PAYMENT', 'Statut de Paiement'),
        ('REPORT_CARD', 'Bulletin Scolaire'),
        ('GENERAL', 'Général'),
    ]
    notification_type = models.CharField(max_length=50, choices=notification_type_choices, verbose_name="Type de notification")
    is_read = models.BooleanField(default=False, verbose_name="Lu")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Date/Heure")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Lu à")