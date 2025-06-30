# school_project/profiles/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
# Importez explicitement les ModelAdmin des modèles de 'school'
# dont vous avez besoin pour autocomplete_fields.
# En les important, vous assurez que Django les enregistre AVANT de les utiliser ici.
# Assurez-vous que school.admin est importé pour que ces ModelAdmin soient reconnus.
from school.admin import SchoolAdmin, ClasseAdmin, AcademicPeriodAdmin # <-- NOUVELLES IMPORTATIONS CLÉS
from school.models import School, Classe # Modèles School et Classe sont nécessaires pour les FK/M2M

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser, Student, UserRole, Parent, Notification # Notification est définie ici

# IMPORTANT : Pour que autocomplete_fields fonctionne, les modèles référencés doivent avoir
# leur ModelAdmin enregistré. Si School, Classe, AcademicPeriod, etc. sont enregistrés
# dans school/admin.py, l'importation de leurs classes Admin ici assure qu'ils sont connus.

# 1. CustomUserAdmin
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            return self.add_form
        return super().get_form(request, obj, **kwargs)

    list_display = (
        'email',
        'full_name',
        'user_type',
        'school',
        'is_staff',
        'is_active',
        'is_approved'
    )
    search_fields = (
        'email',
        'first_name',
        'last_name',
        'school__name',
    )
    list_filter = (
        'user_type',
        'school',
        'is_staff',
        'is_active',
        'is_approved'
    )
    ordering = ('last_name', 'first_name', 'email',)
    autocomplete_fields = ('school',) # SchoolAdmin est importé et enregistré

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': (
            'first_name',
            'last_name',
            'user_type',
            'phone_number',
            'address',
            'profile_picture',
            'date_of_birth',
            'school',
            'is_approved',
        )}),
        (_('Permissions'), {'fields': (
            'is_active',
            'is_staff',
            'is_superuser',
            'groups',
            'user_permissions',
        )}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (_('Adresse Email et Mot de Passe'), {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
        (_('Informations personnelles'), {'fields': (
            'first_name',
            'last_name',
            'user_type',
            'phone_number',
            'address',
            'profile_picture',
            'date_of_birth',
            'school',
            'is_approved',
        )}),
        (_('Permissions'), {'fields': (
            'is_staff',
            'is_superuser',
            'is_active',
            'groups',
            'user_permissions'
        )}),
    )

# 2. StudentAdmin
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'first_name',
        'last_name',
        'middle_name',
        'student_id_code',
        'school',
        'current_classe',
        'is_active',
        'enrollment_date',
        
    )
    search_fields = (
        'first_name',
        'last_name',
        'middle_name',
        'student_id_code',
        'school__name',
        'current_classe__name',
    )
    list_filter = (
        'school',
        'current_classe__name',
        'is_active',
        'enrollment_date',
        'parents',
    )
    # Tous les modèles dans autocomplete_fields sont enregistrés
    autocomplete_fields = (
        # CustomUserAdmin est défini dans ce fichier
        'school',       # SchoolAdmin est importé et enregistré
        'current_classe', # ClasseAdmin est importé et enregistré
        'parents',      # ParentAdmin est défini dans ce fichier
    )
    fieldsets = (
        (None, {'fields': ( 'school', 'current_classe')}),
        (_('Informations personnelles'), {'fields': ('first_name', 'last_name', 'middle_name', 'date_of_birth', 'student_id_code')}),
        (_('Statut'), {'fields': ('is_active', 'enrollment_date', 'parents')}),
    )

# 3. ParentAdmin
@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = (
        'first_name',
        'last_name',
        'school',
        'is_approved',
        
    )
    search_fields = (
        'first_name',
        'last_name',
        
        
        
        'school__name',
    )
    list_filter = (
        'school',
        'is_approved',
    )
    # Tous les modèles dans autocomplete_fields sont enregistrés
    autocomplete_fields = ('school',) # CustomUserAdmin et SchoolAdmin sont enregistrés

# 4. NotificationAdmin
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'sender', 'notification_type', 'is_read', 'timestamp')
    search_fields = (
        'recipient_email', 'recipientfirst_name', 'recipient_last_name',
        'sender_email', 'senderfirst_name', 'sender_last_name',
        'message',
    )
    list_filter = ('notification_type', 'is_read', 'timestamp')
    autocomplete_fields = ('recipient', 'sender') # CustomUserAdmin est enregistré