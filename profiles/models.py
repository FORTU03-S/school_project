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
import logging

logger = logging.getLogger(__name__)

# --- Définition des rôles d'utilisateur ---
class UserRole(models.TextChoices):
    STUDENT = 'STUDENT', 'Élève'
    PARENT = 'PARENT', 'Parent'
    TEACHER = 'TEACHER', 'Enseignant'
    DIRECTION = 'DIRECTION', 'Direction'
    ACCOUNTANT = 'ACCOUNTANT', 'Comptable'
    ADMIN = 'ADMIN', 'ADMIN'
    STAFF = 'STAFF', 'Personnel Administratif'

# --- Manager personnalisé pour CustomUser ---
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
    username = None  # Supprime le champ username par défaut d'AbstractUser
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
        'school.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='custom_users',
        verbose_name="École Affiliée"
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['user_type', 'first_name', 'last_name']

    objects = CustomUserManager()

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
    user_account = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile',
        limit_choices_to={'user_type': UserRole.STUDENT},
        verbose_name="Compte Utilisateur Élève"
    )
    
    first_name = models.CharField(max_length=100, verbose_name="Prénom de l'élève")
    last_name = models.CharField(max_length=100, verbose_name="Nom de l'élève")
    middle_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Post-nom")
    date_of_birth = models.DateField(verbose_name="Date de naissance", null=True, blank=True)
    gender = models.CharField(
        max_length=10, 
        choices=[('Male', 'Homme'), ('Female', 'Femme'), ('Other', 'Autre')], 
        blank=True, 
        null=True
    )
    address = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Numéro de Téléphone")
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='student_profiles/', null=True, blank=True)
    student_id_code = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Code d'identification élève", 
        blank=True, 
        null=True
    )

    school = models.ForeignKey(
        'school.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name="École"
    )
    current_classe = models.ForeignKey(
        'school.Classe',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students_in_class',
        verbose_name="Classe Actuelle"
    )
    parents = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='children',
        limit_choices_to={'user_type': UserRole.PARENT},
        blank=True,
        verbose_name="Parents légaux"
    )

    is_active = models.BooleanField(default=True, verbose_name="Actif")
    enrollment_date = models.DateField(default=timezone.now, verbose_name="Date d'inscription")

    def __str__(self):
        classe_info = self.current_classe.name if self.current_classe else 'Non assignée'
        return f"{self.first_name} {self.last_name} ({classe_info})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        if not self.student_id_code:
            timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            generated_code = f"STU-{timestamp}-{random_suffix}"

            while Student.objects.filter(student_id_code=generated_code).exists():
                random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                generated_code = f"STU-{timestamp}-{random_suffix}"
            self.student_id_code = generated_code

        super().save(*args, **kwargs)

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
        settings.AUTH_USER_MODEL,
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
    """
    Signal pour créer ou mettre à jour automatiquement les profils Student et Parent
    lors de la création/modification d'un CustomUser.
    """
    if instance.user_type == UserRole.STUDENT:
        if not instance.email or not instance.first_name or not instance.last_name:
            logger.warning(f"ATTENTION: CustomUser {instance.email} de type STUDENT n'a pas les informations complètes pour créer un profil Student.")
            return

        defaults = {
            'first_name': instance.first_name,
            'last_name': instance.last_name,
            'date_of_birth': instance.date_of_birth,
            'school': instance.school,
            'email': instance.email,
        }

        if not hasattr(instance, 'student_profile') or not instance.student_profile:
            timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            defaults['student_id_code'] = f"STU-{instance.pk}-{timestamp}-{random_suffix}"

        student_profile, created = Student.objects.get_or_create(
            user_account=instance, 
            defaults=defaults
        )

        if not created:
            student_profile.first_name = instance.first_name
            student_profile.last_name = instance.last_name
            student_profile.date_of_birth = instance.date_of_birth or student_profile.date_of_birth
            student_profile.school = instance.school or student_profile.school
            student_profile.email = instance.email
            student_profile.save()

    elif instance.user_type == UserRole.PARENT:
        if not instance.email or not instance.first_name or not instance.last_name:
            logger.warning(f"ATTENTION: CustomUser {instance.email} de type PARENT n'a pas les informations complètes pour créer un profil Parent.")
            return

        if not instance.school:
            logger.warning(f"ATTENTION: CustomUser {instance.email} de type PARENT n'a pas d'école assignée.")
            return

        defaults = {
            'first_name': instance.first_name,
            'last_name': instance.last_name,
            'school': instance.school,
            'is_approved': instance.is_approved
        }

        parent_profile, created = Parent.objects.get_or_create(
            user_account=instance, 
            defaults=defaults
        )

        if not created:
            parent_profile.first_name = instance.first_name
            parent_profile.last_name = instance.last_name
            parent_profile.school = instance.school or parent_profile.school
            parent_profile.is_approved = instance.is_approved
            parent_profile.save()


# --- Modèle Notification ---
class Notification(models.Model):
    """
    Système de notifications pour les utilisateurs de l'application.
    """
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, 
        related_name='notifications', 
        verbose_name="Destinataire"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='sent_notifications', 
        verbose_name="Expéditeur"
    )
    subject = models.CharField(max_length=255, verbose_name="Sujet", blank=True, null=True)
    message = models.TextField(verbose_name="Message")
    
    NOTIFICATION_TYPE_CHOICES = [
        ('ABSENCE', 'Absence Enfant'),
        ('EVALUATION', 'Évaluation à venir'),
        ('HOMEWORK', 'Devoir à faire'),
        ('QUIZ', 'Interrogation / Quiz'),
        ('MESSAGE_TEACHER', 'Message de l\'enseignant'),
        ('PAYMENT', 'Statut de Paiement'),
        ('REPORT_CARD', 'Bulletin Scolaire'),
        ('GENERAL', 'Général'),
    ]
    
    notification_type = models.CharField(
        max_length=50, 
        choices=NOTIFICATION_TYPE_CHOICES, 
        verbose_name="Type de notification"
    )
    is_read = models.BooleanField(default=False, verbose_name="Lu")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Date/Heure")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Lu à")

    def __str__(self):
        return f"{self.subject or 'Sans sujet'} - {self.recipient.full_name}"

    def mark_as_read(self):
        """Marque la notification comme lue."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-timestamp']