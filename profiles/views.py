# profiles/views.py
from django.db import models, IntegrityError
import logging 
from django.views.generic import TemplateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, F, Q
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.files.base import ContentFile
import base64 # Pour l'encodage du PDF si on l'envoie directement
import uuid # Pour le numéro de reçu unique
import random
from decimal import Decimal
import string
import os # Pour les chemins de fichiers
from django.conf import settings
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.http import HttpResponse, Http404

# Imports pour le PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib import colors
logger = logging.getLogger(__name__)
from .chart_generator import ChartGenerator
from datetime import datetime
#from profiles.chart_generator import ChartGenerator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Count, Sum, F, ExpressionWrapper, DecimalField, Sum, Avg
from django.db import transaction
from django.utils import timezone # Assurez-vous que timezone est importé
from school.models import Enrollment, Evaluation, Grade, AcademicPeriod, EvaluationType, Course, ClassAssignment, Classe, Attendance, DisciplinaryRecord, Payment, AcademicPeriod # Assurez-vous que tous sont importés
from django.forms import formset_factory, ModelForm, DateInput, CheckboxSelectMultiple
from profiles.models import CustomUser, UserRole, Student # Assurez-vous que CustomUser et UserRole sont importés
from  profiles.forms import Notification
from school.models import School, TuitionFee
from .models import CustomUser as User
from django import forms
from school.forms import EnrollmentForm, PaymentForm, FeeTypeForm, TuitionFeeForm

# Importez tous les formulaires nécessaires
from .forms import (
    ParentCreationForm,
    TeacherRegistrationForm,
    CustomAuthenticationForm,
    DirectionUserApprovalForm,
    ClassAssignmentForm,
    NotificationForm,
    StudentForm,
    DisciplinaryRecordForm,# Ajouté pour la vue teacher_student_detail_view si besoin 
    CourseForm,
    AcademicPeriodForm,
    TeacherCreationForm,
    ExistingParentForm
    
)
from profiles.forms import ClasseForm
from .models import UserRole, Notification
# Importez tous les modèles nécessaires (certains sont déjà importés ci-dessus)
# from .models import CustomUser, UserRole, Student
# from school.models import ClassAssignment, Classe, AcademicPeriod, Grade, Payment, Course, Enrollment, DisciplinaryRecord


# --- Fonctions utilitaires ---
def is_staff_or_direction(user):
    """Vérifie si l'utilisateur est un ADMIN, DIRECTION ou TEACHER (pour des permissions plus larges)."""
    return user.is_authenticated and (
        user.user_type == UserRole.ADMIN or
        user.user_type == UserRole.DIRECTION or
        user.user_type == UserRole.TEACHER
    )

def is_direction(user):
    """Vérifie si l'utilisateur est un ADMIN ou DIRECTION."""
    return user.is_authenticated and (
        user.user_type == UserRole.ADMIN or
        user.user_type == UserRole.DIRECTION
    )

def is_parent(user):
    return user.is_authenticated and user.user_type == UserRole.PARENT

def is_teacher(user):
    return user.is_authenticated and user.user_type == UserRole.TEACHER

# Fonction utilitaire pour vérifier si un enseignant est assigné à la classe d'un élève
def is_teacher_assigned_to_student_class(user, student):
    if not student.current_classe:
        return False
    # Assurez-vous que 'classe' est le bon champ dans ClassAssignment et Student
    return ClassAssignment.objects.filter(teacher=user, classe=student.current_classe).exists()

def is_commune_admin(user):
    # Exemple: si la "commune" est représentée par un superutilisateur
    return user.is_authenticated and user.is_superuser
    # Ou si vous avez un rôle spécifique pour la commune :
    # return user.is_authenticated and user.role == 'commune_admin'
    
#def is_accountant(user):
#    return user.is_authenticated and user.user_type == UserRole.ACCOUNTANT 

# ... (votre code existant) ...

def login_view(request):
    # Logique pour les utilisateurs déjà connectés (GET request si déjà authentifié)
    if request.user.is_authenticated:
        if request.user.user_type == UserRole.DIRECTION or request.user.user_type == UserRole.ADMIN:
            return redirect('profiles:direction_dashboard') # <-- AJOUTEZ PROFILES:
        elif request.user.user_type == UserRole.TEACHER:
            return redirect('profiles:teacher_dashboard') # <-- AJOUTEZ PROFILES:
        elif request.user.user_type == UserRole.PARENT:
            return redirect('profiles:parent_my_children') # <-- AJOUTEZ PROFILES:
        elif request.user.user_type == UserRole.ACCOUNTANT:
            return redirect('profiles:accounting_dashboard') # <-- AJOUTEZ PROFILES:
        else:
            return redirect('profiles:home') # <-- AJOUTEZ PROFILES:

    # Logique pour gérer la soumission du formulaire de connexion (POST request)
    if request.method == 'POST':
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)

            if user is not None:
                if not user.is_approved:
                    messages.error(request, "Votre compte est en attente d'approbation par l'administration.")
                    return render(request, 'profiles/login.html', {'form': form, 'title': 'Connexion'})

                if user.user_type == UserRole.TEACHER:
                    if not ClassAssignment.objects.filter(teacher=user).exists():
                        messages.error(request, "Vous n'êtes pas encore assigné(e) à une classe. Veuillez contacter la direction.")
                        return render(request, 'profiles/login.html', {'form': form, 'title': 'Connexion'})

                login(request, user)
                messages.success(request, f"Bienvenue, {user.full_name}!")

                # Redirection après connexion réussie (POST request)
                if user.user_type == UserRole.DIRECTION or user.user_type == UserRole.ADMIN:
                    return redirect('profiles:direction_dashboard') # <-- AJOUTEZ PROFILES:
                elif user.user_type == UserRole.TEACHER:
                    return redirect('profiles:teacher_dashboard') # <-- AJOUTEZ PROFILES:
                elif user.user_type == UserRole.PARENT:
                    return redirect('profiles:parent_my_children') # <-- AJOUTEZ PROFILES:
                elif user.user_type == UserRole.ACCOUNTANT:
                    return redirect('profiles:accounting_dashboard') # <-- AJOUTEZ PROFILES:
                else:
                    return redirect('profiles:home') # <-- AJOUTEZ PROFILES:
            else:
                messages.error(request, "Email ou mot de passe invalide.")
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = CustomAuthenticationForm()

    return render(request, 'profiles/login.html', {'form': form, 'title': 'Connexion'})

# ... (le reste de vos vues) ...

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, "Vous avez été déconnecté(e) avec succès.")
        return redirect('profiles:login') # Redirige vers la page de connexion
    else:
        messages.error(request, "La déconnexion doit être effectuée via un formulaire sécurisé.")
        return redirect('profiles/home') # Ou une autre page appropriée comme 'login'

def register_view(request):
    return render(request, 'profiles/register_choice.html', {'title': 'S\'inscrire'})




def register_teacher_view(request):
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Votre inscription a été envoyée pour approbation. Vous serez notifié(e) une fois approuvé(e).")
            return redirect('profiles:login')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = TeacherRegistrationForm()
    return render(request, 'profiles/register_teacher.html', {'form': form, 'title': 'Inscription Enseignant'})

# profiles/views.py (ou le fichier où se trouve votre home_view)

# ... (vos imports existants) ...

def home_view(request):
    # Pour le message initial si besoin, sinon on peut l'enlever
    # message = request.session.pop('welcome_message', None)
    context = {
        'title': 'Bienvenue sur SYBEMAcademia',
        # 'message': message, # Décommentez si vous utilisez un message de session
    }
    return render(request, 'home.html', context) # Assurez-vous que 'home.html' est le bon chemin



@login_required
@user_passes_test(is_parent, login_url='/login/')
def parent_child_detail_view(request, child_id):
    child = get_object_or_404(Student, id=child_id)

    # CORRECTION: Vérification de sécurité: S'assurer que cet enfant appartient bien au parent connecté
    if not child.parents.filter(id=request.user.id).exists():
        messages.error(request, "Vous n'êtes pas autorisé à consulter le profil de cet enfant.")
        return redirect('profiles:parent_my_children_list.html')

    # 1. Informations pour les "Notes et Bulletins"
    grades = Grade.objects.filter(enrollment__student=child).select_related(
        'evaluation', 'enrollment__course'
    ).order_by('enrollment__course__name', 'evaluation__date') # Correction: ajout de __ pour traverser les relations

    # 2. Informations pour les "Absences et Présences"
    attendances = Attendance.objects.filter(enrollment__student=child).order_by('-date')

    # 3. Informations pour les "Actions Disciplinaires"
    disciplinary_records = DisciplinaryRecord.objects.filter(student=child).order_by('-created_at')

    # 4. Informations pour les "Paiements"
    payments = Payment.objects.filter(student=child).order_by('-payment_date')

    # 5. Informations pour les "Notifications" (Adapté pour être "concernant l'enfant")
    q_objects = Q(recipient=request.user) # Notifications envoyées directement au parent

    if hasattr(child, 'user_account') and child.user_account: # Assurez-vous que l'élève a un champ user_account pointant vers CustomUser
        q_objects |= Q(recipient=child.user_account) # Notifications envoyées directement au compte utilisateur de l'enfant

    notifications = Notification.objects.filter(q_objects).distinct().order_by('-timestamp')

    # CONTEXTE DE LA VUE
    context = {
        'child': child,
        'grades': grades,
        'attendances': attendances,
        'disciplinary_records': disciplinary_records,
        'payments': payments,
        'notifications': notifications,
        'title': f"Profil de {child.full_name}"
    }
    return render(request, 'profiles/child_detail.html', context)

def teacher_dashboard_view(request):
    teacher_user = request.user

    # Assurez-vous que ces lignes sont toujours atteintes et que les variables sont toujours définies
    courses_taught = Course.objects.filter(
        teachers=teacher_user,
        school=teacher_user.school
    ).prefetch_related('classes', 'subjects').order_by('classes__name', 'name').distinct()

    courses_info = []
    for course in courses_taught:
        student_count = Enrollment.objects.filter(course=course).count()
        class_names = ", ".join([c.name for c in course.classes.all()]) or "Aucune classe assignée"
        courses_info.append({
            'course': course,
            'student_count': student_count,
            'class_names': class_names
        })

    unread_notifications = Notification.objects.filter(
        recipient=teacher_user,
        is_read=False
    ).order_by('-timestamp')[:5]

    context = { # S'assurer que 'context' est toujours défini
        'title': 'Tableau de Bord Enseignant',
        'teacher': teacher_user,
        'courses_info': courses_info,
        'unread_notifications': unread_notifications,
    }

    return render(request, 'profiles/teacher_dashboard.html', context)

def is_accounting_or_admin_or_direction(user):
    return user.is_authenticated and user.user_type in ['ADMIN', 'ACCOUNTANT', 'DIRECTION']

def generate_receipt_pdf(payment_obj):
    # Chemin où le PDF sera sauvegardé temporairement
    # Assurez-vous que MEDIA_ROOT est configuré dans settings.py
    # et que le dossier 'receipts' existe dans MEDIA_ROOT
    pdf_filename = f"receipt_{payment_obj.receipt_number}.pdf"
    pdf_path = os.path.join(settings.MEDIA_ROOT, 'receipts', pdf_filename)
    
    # Créer le dossier 'receipts' si il n'existe pas
    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'receipts'), exist_ok=True)

    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Styles personnalisés
    header_style = ParagraphStyle(
        'Header',
        parent=styles['h1'],
        fontSize=20,
        alignment=TA_CENTER,
        spaceAfter=14
    )
    subheader_style = ParagraphStyle(
        'SubHeader',
        parent=styles['h2'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        spaceBefore=6,
        spaceAfter=6
    )
    right_align_style = ParagraphStyle(
        'RightAlign',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_RIGHT
    )
    center_align_style = ParagraphStyle(
        'CenterAlign',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER
    )

    elements = []

    # En-tête
    elements.append(Paragraph("Reçu de Paiement", header_style))
    elements.append(Paragraph(f"École: {payment_obj.student.school.name if payment_obj.student and payment_obj.student.school else 'N/A'}", subheader_style))
    elements.append(Spacer(1, 0.2 * 10))

    # Informations sur le reçu
    data = [
        ["Numéro de Reçu:", payment_obj.receipt_number],
        ["Date de Paiement:", payment_obj.payment_date.strftime("%d %B %Y")],
        ["Période Académique:", payment_obj.academic_period.name if payment_obj.academic_period else 'N/A'],
        ["Enregistré par:", payment_obj.recorded_by.full_name if payment_obj.recorded_by else 'N/A']
    ]
    table = Table(data, colWidths=[150, 300])
    table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.4 * 10))

    # Informations sur l'élève
    elements.append(Paragraph("Détails de l'Élève:", styles['h3']))
    elements.append(Paragraph(f"Nom Complet: {payment_obj.student.full_name}", body_style))
    elements.append(Paragraph(f"Code Élève: {payment_obj.student.student_id_code}", body_style))
    elements.append(Paragraph(f"Classe: {payment_obj.student.current_classe.name if payment_obj.student.current_classe else 'N/A'}", body_style))
    elements.append(Spacer(1, 0.2 * 10))

    # Détails du paiement
    elements.append(Paragraph("Détails du Paiement:", styles['h3']))
    payment_details_data = [
        ["Intitulé du Frais:", payment_obj.fee_type.name if payment_obj.fee_type else 'N/A'],
        ["Montant Payé:", f"{payment_obj.amount_paid:.2f} $"],
        ["Statut du Paiement:", payment_obj.get_payment_status_display()],
        ["ID Transaction:", payment_obj.transaction_id if payment_obj.transaction_id else 'N/A']
    ]
    payment_details_table = Table(payment_details_data, colWidths=[150, 300])
    payment_details_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(payment_details_table)
    elements.append(Spacer(1, 0.5 * 10))

    elements.append(Paragraph("Merci pour votre paiement.", center_align_style))
    elements.append(Spacer(1, 0.5 * 10))
    elements.append(Paragraph("Signature de l'administration: _______________________", right_align_style))

    doc.build(elements)
    
    return pdf_path




        #return redirect(reverse_lazy('profiles:accounting_dashboard'))
# Formulaire pour créer un nouveau type de frais (intitulé)
def is_direction(user):
    return user.is_authenticated and user.user_type == UserRole.DIRECTION


@login_required
@user_passes_test(is_direction, login_url='/login/')
def add_student_view(request):
    user_school = request.user.school
    
    # Rediriger si l'utilisateur n'est pas affilié à une école
    if not user_school:
        messages.error(request, "Votre compte n'est affilié à aucune école. Veuillez contacter un administrateur.")
        return redirect('some_error_page') # Remplacez par une URL appropriée

    student_form = StudentForm(user_school=user_school)
    parent_form = ParentCreationForm() # Pour le cas où le parent n'existe pas

    # Un nouveau formulaire pour lier un élève à un parent existant
    # Ceci est une suggestion si vous voulez un flow séparé pour lier
    # For now, we'll keep the creation logic within the main view.

    if request.method == 'POST':
        student_form = StudentForm(request.POST, request.FILES, user_school=user_school)
        parent_form = ParentCreationForm(request.POST) # Pour les informations du parent potentiel

        # Validez les deux formulaires (le parent_form sera validé même si on réutilise un parent existant)
        if student_form.is_valid() and parent_form.is_valid():
            parent_email = parent_form.cleaned_data.get('email') # L'email saisi dans le formulaire du parent

            try:
                with transaction.atomic():
                    # --- GESTION DU PARENT ---
                    # 1. Tenter de trouver un CustomUser existant avec cet email et le type 'PARENT'
                    try:
                        # Assurez-vous que l'email est unique pour CustomUser
                        # et que CustomUser.user_type est bien filtré
                        existing_parent_user = CustomUser.objects.get(
                            email=parent_email, 
                            user_type=UserRole.PARENT,
                            school=user_school # Optionnel: filtrer aussi par école si un parent ne peut être que dans 1 école
                        )
                        # Si trouvé, on utilise ce parent existant
                        parent_to_link = existing_parent_user
                        messages.info(request, f"Parent existant ({parent_to_link.full_name}) trouvé et réutilisé.")

                    except CustomUser.DoesNotExist:
                        # Si aucun CustomUser existant avec cet email/type n'est trouvé, créer un nouveau parent
                        parent_user = parent_form.save(commit=False)
                        parent_user.school = user_school # Le parent est lié à la même école
                        parent_user.user_type = UserRole.PARENT # Assurez-vous que le type est correctement défini par le formulaire ou ici
                        parent_user.save()
                        
                        # Si votre modèle Parent a un champ 'user_account' qui est OneToOneField
                        # Il est généralement créé automatiquement si user_account est primary_key=True
                        # Sinon, vous devez le créer explicitement.
                        # Ex: Parent.objects.create(user_account=parent_user, ...)
                        # Votre Parent modèle a user_account comme OneToOneField, donc ça devrait être bon.

                        parent_to_link = parent_user # Le nouveau CustomUser parent

                        messages.success(request, f"Nouveau parent ({parent_to_link.full_name}) créé.")
                    
                    # --- CRÉATION DE L'ÉLÈVE ---
                    # 2. Création de l'élève (instance du modèle Student)
                    student = student_form.save(commit=False)
                    student.school = user_school # L'élève est lié à la même école
                    
                    # Créez le CustomUser pour l'élève ici si chaque élève doit avoir un compte utilisateur.
                    # Actuellement, votre Student a un user_account qui est OneToOneField,
                    # mais votre StudentForm ne gère pas la création de ce CustomUser
                    # et votre vue ne le fait pas non plus.
                    # Si chaque élève DOIT avoir un compte, la logique doit être ajoutée ici.
                    # Pour l'instant, je me base sur votre code qui ne le crée pas explicitement dans cette vue.
                    # Si vous voulez créer un user_account pour l'élève:
                    # student_user = CustomUser.objects.create_user(
                    #     username=generate_unique_username(student.first_name, student.last_name), # Fonction à créer pour un nom d'utilisateur unique
                    #     email=student_form.cleaned_data.get('email'), # Si l'email est dans student_form
                    #     first_name=student.first_name,
                    #     last_name=student.last_name,
                    #     user_type=UserRole.STUDENT,
                    #     school=user_school,
                    #     password=generate_temporary_password() # Mot de passe temporaire
                    # )
                    # student.user_account = student_user

                    student.save() # Sauvegarde l'instance Student. student_id_code est auto-généré ici.

                    # --- LIEN PARENT-ENFANT ---
                    # 3. Lier le parent (CustomUser) à l'élève (Student)
                    # Votre modèle Student a un ManyToManyField parents vers CustomUser.
                    student.parents.add(parent_to_link) 
                    # Note : La relation ManyToMany sur parents est de CustomUser vers Student.
                    # Donc parent_to_link est un CustomUser, et student.parents.add() est correct.

                    messages.success(request, f"L'élève {student.full_name} a été ajouté avec succès et lié au parent {parent_to_link.full_name}.")
                    return redirect('profiles:list_students') # Redirigez vers la liste des élèves ou autre

            except Exception as e:
                # Ceci inclura les erreurs de validation d'unicité de l'email si elles sont levées avant
                messages.error(request, f"Une erreur s'est produite lors de l'ajout de l'élève et du parent : {e}")
                # logger.error(f"Erreur à l'ajout élève/parent: {e}")
        else:
            # Si un des formulaires n'est pas valide, les erreurs seront affichées automatiquement dans le template
            messages.error(request, "Veuillez corriger les erreurs dans les formulaires.")

    context = {
        'student_form': student_form,
        'parent_form': parent_form,
        'title': "Ajouter un Nouvel Élève et son Parent",
    }
    return render(request, 'profiles/add_student.html', context)

@login_required
@user_passes_test(is_direction, login_url='/login/')
def list_students_view(request):
    classes = Classe.objects.all().order_by('name')
    
    students = Student.objects.all()

    selected_class_id = request.GET.get('class_filter')
    if selected_class_id and selected_class_id != 'all':
        try:
            students = students.filter(current_classe__id=selected_class_id)
        except ValueError:
            messages.error(request, "ID de classe invalide fourni.")
            selected_class_id = 'all'

    students = students.order_by('last_name', 'first_name')

    context = {
        'students': students,
        'classes': classes,
        'selected_class_id': selected_class_id,
        'title': "Liste des Élèves"
    }
    return render(request, 'profiles/list_students.html', context)


@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/')
def direction_manage_users(request):
    """
    Vue pour la direction pour gérer les utilisateurs, avec options de filtrage.
    """
    user = request.user
    users = CustomUser.objects.filter(school=user.school).order_by('first_name', 'last_name') # Filtre par l'école de la direction

    # --- Logique de filtrage ---
    user_type_filter = request.GET.get('user_type')
    is_approved_filter = request.GET.get('is_approved') # 'true', 'false', ou ''
    search_query = request.GET.get('q')

    if user_type_filter:
        users = users.filter(user_type=user_type_filter)

    if is_approved_filter:
        if is_approved_filter == 'true':
            users = users.filter(is_approved=True)
        elif is_approved_filter == 'false':
            users = users.filter(is_approved=False)

    if search_query:
        # Recherche insensible à la casse sur username, first_name, last_name
        users = users.filter( 
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    # --- Fin Logique de filtrage ---

    context = {
        'title': 'Gestion des Utilisateurs',
        'users': users,
        'user_type_choices': UserRole.choices, # Passez les choix de types d'utilisateur au template
    }
    return render(request, 'profiles/direction_manage_users.html', context)

@login_required
@user_passes_test(is_direction, login_url='/login/')
def direction_approve_user(request, user_id):
    user_to_approve = get_object_or_404(CustomUser, id=user_id)
    if user_to_approve.is_superuser or user_to_approve.is_staff:
        messages.error(request, "Vous ne pouvez pas modifier ce type de compte directement ici.")
        return redirect('direction_manage_users')

    if request.method == 'POST':
        form = DirectionUserApprovalForm(request.POST, instance=user_to_approve)
        if form.is_valid():
            form.save()
            messages.success(request, f"Le compte de {user_to_approve.full_name} a été mis à jour avec succès.")
            return redirect('profiles:direction_manage_users')
        else:
            messages.error(request, "Erreur lors de la mise à jour du compte. Veuillez vérifier les champs.")
    else:
        form = DirectionUserApprovalForm(instance=user_to_approve)

    context = {
        'form': form,
        'user_to_approve': user_to_approve,
        'title': f'Modifier {user_to_approve.full_name}',
    }
    return render(request, 'profiles/direction_approve_user.html', context)

# --- Vues de gestion des assignations de classes pour la Direction ---
# profiles/views.py

# ... (le reste de votre code)


def is_direction(user):
    return user.is_authenticated and user.user_type == 'DIRECTION'

CustomUser = get_user_model()

def is_direction(user):
    return user.is_authenticated and user.user_type == 'DIRECTION'

@login_required
@user_passes_test(is_direction, login_url='/login/')
def direction_manage_class_assignments(request):
    user_school = request.user.school

    if not user_school:
        messages.error(request, "Votre compte n'est pas lié à une école. Impossible de gérer les assignations.")
        return redirect('profiles:direction_dashboard')

    active_academic_period = AcademicPeriod.objects.filter(
        school=user_school,
        is_current=True
    ).first()

    if not active_academic_period:
        messages.warning(request, "Aucune période académique active n'est définie pour votre école. Certaines opérations d'assignation pourraient être limitées.")

    if request.method == 'POST':
        # Instanciez le formulaire avec les données POST et le contexte user_school
        form = ClassAssignmentForm(request.POST, user_school=user_school)

        if form.is_valid():
            # Vérifiez l'assignation unique avant de sauvegarder
            teacher_instance = form.cleaned_data['teacher']
            classe_instance = form.cleaned_data['classe']
            academic_period_instance = form.cleaned_data['academic_period']

            # Utilisez get_or_create pour éviter les doublons et simplifier la logique
            assignment, created = ClassAssignment.objects.get_or_create(
                school=user_school,
                teacher=teacher_instance,
                classe=classe_instance,
                academic_period=academic_period_instance
            )
            if created:
                messages.success(request, f"L'enseignant {teacher_instance.get_full_name()} a été assigné à la classe '{classe_instance.name}' pour la période '{academic_period_instance.name}'.")
            else:
                messages.info(request, f"L'assignation de {teacher_instance.get_full_name()} à la classe '{classe_instance.name}' pour cette période existe déjà.")

            # IMPORTANT : Après une soumission de formulaire réussie, redirigez
            return redirect('profiles:direction_manage_class_assignments')
        else:
            # Le formulaire n'est pas valide, les messages d'erreur doivent être gérés par le template
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire d'assignation.")
            # Pour le débogage, vous pouvez imprimer form.errors ici :
            # print(form.errors)

        # Gérer les autres actions POST si elles sont séparées du ClassAssignmentForm
        # Exemple : si vous avez toujours la partie d'assignation des élèves
        # if request.POST.get('action_type') == 'assign_student_to_class':
        #     # ... votre logique d'assignation d'élève existante ...
        #     pass


    else: # Requête GET
        # Instanciez un formulaire vide pour l'affichage initial
        form = ClassAssignmentForm(user_school=user_school)

    # Récupérer les assignations de classe existantes pour le tableau
    assignments = ClassAssignment.objects.filter(
        school=user_school,
        academic_period=active_academic_period # Filtrer par la période académique active
    ).order_by('teacher__last_name', 'teacher__first_name')


    context = {
        'title': "Gérer les Assignations de Classe",
        'form': form, # Passer l'instance du formulaire au template
        'assignments': assignments, # Passer les assignations existantes au template
        'active_academic_period': active_academic_period,
        # Vous n'avez plus besoin de 'classes', 'students', 'teachers', 'courses' directement
        # dans le contexte pour les listes déroulantes du formulaire, car le formulaire les gère.
        # Gardez-les si d'autres parties de votre template les utilisent à des fins différentes.
    }
    return render(request, 'profiles/direction_manage_class_assignments.html', context)   


@login_required
@user_passes_test(is_direction, login_url='/login/')
def direction_delete_class_assignment(request, assignment_id):
    assignment = get_object_or_404(ClassAssignment, id=assignment_id)
    if request.method == 'POST':
        assignment.delete()
        messages.success(request, "Assignation de classe supprimée avec succès.")
        return redirect('profiles:direction_manage_class_assignments.html')
    context = {
        'assignment': assignment,
        'title': 'Confirmer la suppression d\'assignation',
    }
    return render(request, 'profiles/confirm_delete_assignment.html', context)


@login_required
@user_passes_test(lambda u: u.is_approved and u.user_type == UserRole.TEACHER)
def teacher_list_students_view(request):
    teacher = request.user
 
    assigned_class_ids = ClassAssignment.objects.filter(teacher=teacher).values_list('classe__id', flat=True)

    # CORRECTION: La syntaxe correcte est current_classe__id__in pour filtrer par les IDs d'une ForeignKey
    students = Student.objects.filter(current_classe__id__in=assigned_class_ids).order_by('last_name', 'first_name')

    context = {
        'students': students,
        'title': 'Mes Élèves (Enseignant)',
    }
    return render(request, 'profiles/teacher_list_students.html', context)

@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.TEACHER, UserRole.DIRECTION, UserRole.ACCOUNTANT, UserRole.ADMIN], login_url='/login/')
def send_notification_view(request, recipient_role=None, student_id=None):
    sender_user = request.user
    # Déterminez le type de destinataire par défaut
    if recipient_role is None:
        if request.user.user_type == UserRole.TEACHER:
            recipient_role = UserRole.PARENT
        elif request.user.user_type == UserRole.DIRECTION:
            recipient_role = UserRole.PARENT
        elif request.user.user_type == UserRole.ACCOUNTANT:
            recipient_role = UserRole.PARENT
        else: # Admin ou autre
            recipient_role = UserRole.PARENT

    students_involved = None
    if student_id:
        student = get_object_or_404(Student, id=student_id)
        students_involved = [student]

    initial_data = {}
    if students_involved and len(students_involved) == 1 and students_involved[0].parents.count() == 1:
        # CORRECTION: Assurez-vous que le champ 'user_account' existe sur votre modèle Parent ou CustomUser
        # Si CustomUser est directement le parent, utilisez `id`
        # Sinon, si un modèle ParentProfile existe avec un OneToOneField 'user' vers CustomUser, utilisez `parent.user.id`
        # Pour l'instant, je suppose que Student.parents est une ManyToManyField vers CustomUser
        initial_data['recipient'] = students_involved[0].parents.first().id 


    if request.method == 'POST':
        form = NotificationForm(
            request.POST
        )
        if form.is_valid():
            notification = form.save(commit=False)
            notification.sender = sender_user
            notification.save()
            messages.success(request, f"La notification a été envoyée avec succès à {notification.recipient.full_name}.")
            if request.user.user_type == UserRole.TEACHER:
                return redirect('profiles:teacher_dashboard')
            elif request.user.user_type == UserRole.DIRECTION:
                return redirect('profiles:direction_dashboard')
            elif request.user.user_type == UserRole.ACCOUNTANT:
                return redirect('profiles:accounting_dashboard')
            else:
                return redirect('profiles:home_view')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = NotificationForm()
        
    
    title = f"Envoyer une Notification en tant que {request.user.get_user_type_display()}"
    if recipient_role == UserRole.PARENT:
        title += " (aux Parents)"
    elif recipient_role == UserRole.TEACHER:
        title += " (aux Enseignants)"

    context = {
        'title': title,
        'form': form,
        'recipient_role': recipient_role,
        'student_id': student_id
    }
    return render(request, 'profiles/direction_send_notification_choice.html', context)

@login_required
@user_passes_test(is_parent, login_url='/login/')
def parent_mark_notification_read(request, notification_id):
    """
    Marque une notification spécifique comme lue pour le parent connecté.
    """
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save()
    messages.success(request, "Notification marquée comme lue.")
    return redirect('profiles:parent_notifications')

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.PARENT, login_url='/login/')
def parent_child_payments_view(request, student_id):
    try:
        child = request.user.children.get(id=student_id)
    except Student.DoesNotExist:
        messages.error(request, "Cet enfant ne fait pas partie de votre famille ou n'existe pas.")
        return redirect('profiles:parent_dashboard')

    payments = Payment.objects.filter(student=child).order_by('-payment_date')

    total_paid = payments.aggregate(sum_paid=models.Sum('amount_paid'))['sum_paid'] or 0

    context = {
        'title': f"Situation des Paiements de {child.full_name}",
        'child': child,
        'payments': payments,
        'total_paid': total_paid,
    }
    return render(request, 'profiles/parent_child_payments.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.TEACHER, login_url='/login/')
def teacher_attendance_view(request):
    teacher_user = request.user
    teacher_courses = Course.objects.filter(teachers=teacher_user).order_by('classes__name', 'name')

    selected_course_id = request.GET.get('course_id')
    selected_date_str = request.GET.get('attendance_date', timezone.now().strftime('%Y-%m-%d'))
    selected_date = timezone.datetime.strptime(selected_date_str, '%Y-%m-%d').date()

    students_in_course = []
    course_name = "Sélectionnez un cours"

    selected_course = None
    if selected_course_id:
        try:
            selected_course_id_int = int(selected_course_id)
            selected_course = teacher_courses.get(id=selected_course_id_int)
            course_name = selected_course.name

            enrollments = Enrollment.objects.filter(
                course=selected_course
            ).select_related('student').order_by('student__last_name', 'student__first_name')

            all_attendances_for_date = Attendance.objects.filter(
                enrollment__in=enrollments,
                date=selected_date
            ).select_related('enrollment__student')

            attendances_dict = {
                attendance.enrollment_id: attendance
                for attendance in all_attendances_for_date
            }

            for enrollment in enrollments:
                student = enrollment.student
                current_attendance = attendances_dict.get(enrollment.id)

                students_in_course.append({
                    'student': student,
                    'enrollment_id': enrollment.id,
                    'is_present_today': current_attendance.is_present if current_attendance else None,
                    'reason_for_absence': current_attendance.reason_for_absence if current_attendance and not current_attendance.is_present else None,
                    'attendance_id': current_attendance.id if current_attendance else None
                })

        except (Course.DoesNotExist, ValueError):
            messages.error(request, "Cours non trouvé ou sélection invalide.")
            return redirect('profiles:teacher_attendance_view')
        except Exception as e:
            messages.error(request, f"Une erreur inattendue s'est produite lors du chargement des élèves : {e}")
            return redirect('profiles:teacher_attendance_view')

    if request.method == 'POST':
        enrollment_id = request.POST.get('enrollment_id')
        action = request.POST.get('action')
        reason = request.POST.get('reason_for_absence', '')

        if not enrollment_id or not action:
            messages.error(request, "Données de soumission invalides.")
            return redirect(request.META.get('HTTP_REFERER', 'manage_attendance'))

        try:
            enrollment = Enrollment.objects.get(id=enrollment_id)
            if not enrollment.course in teacher_courses:
                 messages.error(request, "Vous n'êtes pas autorisé à modifier la présence pour cet élève dans ce cours.")
                 return redirect(request.META.get('HTTP_REFERER', 'manage_attendance'))

            is_present = (action == 'present')

            attendance, created = Attendance.objects.get_or_create(
                enrollment=enrollment,
                date=selected_date,
                defaults={
                    'is_present': is_present,
                    'marked_by': teacher_user,
                    'reason_for_absence': reason if not is_present else None
                }
            )

            if not created:
                attendance.is_present = is_present
                attendance.reason_for_absence = reason if not is_present else None
                attendance.marked_by = teacher_user
                attendance.save()

            if not is_present:
                parents = enrollment.student.parents.all()
                if parents.exists():
                    message_subject = f"Absence de votre enfant {enrollment.student.full_name} le {selected_date}"
                    message_body = (
                        f"Cher parent,\n\n"
                        f"Nous vous informons que votre enfant, {enrollment.student.full_name}, "
                        f"est absent du cours de {enrollment.course.name} ce {selected_date.strftime('%d/%m/%Y')}."
                    )
                    if reason:
                        message_body += f"\nRaison fournie : {reason}"
                    message_body += "\n\nCordialement,\nVotre école."

                    for parent_user in parents:
                        Notification.objects.create(
                            recipient=parent_user,
                            sender=teacher_user,
                            subject=message_subject, # Correction: 'Subject' -> 'subject'
                            message=message_body,
                            notification_type='ABSENCE'
                        )
                else:
                    messages.warning(request, f"L'élève {enrollment.student.full_name} est absent mais n'a pas de parents liés pour la notification.")
            elif is_present and not created:
                pass # No action for now on changing absent to present

            messages.success(request, f"Présence/absence de {enrollment.student.full_name} enregistrée avec succès.")
            return redirect(f"{request.path}?course_id={selected_course_id}&attendance_date={selected_date_str}")

        except Enrollment.DoesNotExist:
            messages.error(request, "Inscription d'élève non trouvée.")
        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement : {e}")

    context = {
        'title': 'Gérer les Absences & Présences',
        'teacher_courses': teacher_courses,
        'selected_course_id': int(selected_course_id) if selected_course_id else None,
        'selected_date_str': selected_date_str,
        'course_name': course_name,
        'students_in_course': students_in_course,
    }
    return render(request, 'profiles/teacher_attendance.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.TEACHER, login_url='/login/')
def teacher_grades_view(request):
    messages.info(request, "La gestion des notes sera bientôt disponible ici !")
    return render(request, 'profiles:teacher_enter_grades.html', {'title': 'Gestion des Notes'})

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.TEACHER, login_url='/login/')
def teacher_message_view(request):
    messages.info(request, "La messagerie enseignant sera bientôt disponible ici !")
    return render(request, 'profiles:coming_soon.html', {'title': 'Messagerie Enseignant'})

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.TEACHER, login_url='/login/')
def teacher_manage_evaluations(request):
    teacher_user = request.user
    if not teacher_user.school:
        messages.error(request, "Votre compte enseignant n'est pas lié à une école. Veuillez contacter l'administrateur.")
        return redirect('profiles:teacher_dashboard')

    teacher_courses = Course.objects.filter(teachers=teacher_user, school=teacher_user.school).order_by('name')

    selected_course_id = request.GET.get('course_id')
    evaluations = []
    selected_course = None

    if selected_course_id:
        try:
            selected_course_id_int = int(selected_course_id)
            selected_course = teacher_courses.get(id=selected_course_id_int)
            evaluations = Evaluation.objects.filter(course=selected_course).order_by('-date')
        except Course.DoesNotExist:
            messages.error(request, "Cours non trouvé ou accès non autorisé.")
            return redirect('profiles:teacher_manage_evaluations')

    context = {
        'title': 'Gérer les Évaluations',
        'teacher_courses': teacher_courses,
        'selected_course_id': selected_course_id_int if selected_course_id else None,
        'selected_course': selected_course,
        'evaluations': evaluations,
    }
    return render(request, 'profiles/teacher_manage_evaluations.html', context)


@login_required
@user_passes_test(lambda u: u.user_type == UserRole.TEACHER, login_url='/login/')
def teacher_add_evaluation(request):
    teacher_user = request.user
    if not teacher_user.school:
        messages.error(request, "Votre compte enseignant n'est pas lié à une école.")
        return redirect('profiles:teacher_dashboard')

    teacher_courses = Course.objects.filter(teachers=teacher_user, school=teacher_user.school).order_by('name')
    academic_periods = AcademicPeriod.objects.filter(school=teacher_user.school).order_by('-start_date')


    if request.method == 'POST':
        name = request.POST.get('name')
        course_id = request.POST.get('course')
        evaluation_type = request.POST.get('evaluation_type')
        date_str = request.POST.get('date')
        max_score = request.POST.get('max_score')
        description = request.POST.get('description')
        academic_period_id = request.POST.get('academic_period')

        try:
            course = teacher_courses.get(id=course_id)
            academic_period = academic_periods.get(id=academic_period_id)
            date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
            max_score = float(max_score)

            Evaluation.objects.create(
                name=name,
                course=course,
                evaluation_type=evaluation_type,
                date=date,
                max_score=max_score,
                description=description,
                created_by=teacher_user,
                academic_period=academic_period
            )
            messages.success(request, "Évaluation ajoutée avec succès.")
            return redirect('profiles:teacher_manage_evaluations')
        except Course.DoesNotExist:
            messages.error(request, "Cours non trouvé.")
        except AcademicPeriod.DoesNotExist:
            messages.error(request, "Période académique non trouvée.")
        except ValueError:
            messages.error(request, "Erreur de format de date ou de score maximum.")
        except Exception as e:
            messages.error(request, f"Erreur lors de l'ajout de l'évaluation : {e}")

    context = {
        'title': 'Ajouter une Nouvelle Évaluation',
        'teacher_courses': teacher_courses,
        'evaluation_types': EvaluationType.choices,
        'academic_periods': academic_periods
    }
    return render(request, 'profiles/teacher_add_evaluation.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.TEACHER, login_url='/login/')
def teacher_enter_grades(request, evaluation_id):
    teacher_user = request.user
    if not teacher_user.school:
        messages.error(request, "Votre compte enseignant n'est pas lié à une école.")
        return redirect('profiles:teacher_dashboard') # Assuming a dashboard view for teachers

    # Ensure the evaluation exists and belongs to a course taught by this teacher in their school
    # Using 'taught_courses' as per our previous discussion for CustomUser's reverse relationship to Course
    evaluation = get_object_or_404(
        Evaluation,
        id=evaluation_id,
        course__teachers=teacher_user,         # Ensure evaluation's course is taught by this teacher
        course__school=teacher_user.school     # Ensure evaluation's course is in this teacher's school
    )

    # Get enrollments for students in this specific evaluation's course
    # Use select_related for efficiency when accessing student details
    enrollments_qs = Enrollment.objects.filter(
        course=evaluation.course,
        course__school=teacher_user.school # Redundant with evaluation filter, but good for clarity/safety
    ).select_related('student').order_by('student__last_name', 'student__first_name')

    # Get existing grades for this evaluation and these enrollments
    existing_grades_qs = Grade.objects.filter(evaluation=evaluation, enrollment__in=enrollments_qs)
    grades_dict = {grade.enrollment_id: grade for grade in existing_grades_qs}

    # Prepare data for rendering the form (GET request)
    students_grades_for_template = []
    for enrollment in enrollments_qs:
        grade = grades_dict.get(enrollment.id)
        students_grades_for_template.append({
            'student': enrollment.student,
            'enrollment': enrollment, # Pass the enrollment object directly for later use
            'grade_obj': grade,
            'score': grade.score if grade else '',
            'remarks': grade.remarks if grade else ''
        })

    if request.method == 'POST':
        grades_saved_count = 0
        grades_deleted_count = 0
        grades_skipped_count = 0 # To count grades not processed due to errors/warnings
        
        try:
            with transaction.atomic():
                # Iterate through the enrollments that were initially displayed to the user.
                # This ensures we process only the students relevant to this evaluation.
                for enrollment in enrollments_qs: # Use the original queryset for iteration
                    score_key = f'score_{enrollment.id}'
                    remarks_key = f'remarks_{enrollment.id}'

                    # Check if the score input field was actually submitted.
                    # This prevents processing students not rendered in the form if any.
                    if score_key not in request.POST:
                        grades_skipped_count += 1
                        continue # Skip if this student's input wasn't even in POST data

                    score_str = request.POST.get(score_key)
                    remarks = request.POST.get(remarks_key, '').strip() # .strip() to remove leading/trailing whitespace

                    # Retrieve existing grade for this specific enrollment and evaluation
                    existing_grade = grades_dict.get(enrollment.id) # Use the pre-fetched dict for efficiency

                    # Logic for saving/updating/deleting grades
                    if score_str:# If a score string is provided (not empty)
                        score_str = score_str.replace(',', '.') # Handle comma as decimal separator
                        try:
                            score = float(score_str)
                            # Validate score against max_score
                            if not (0 <= score <= float(evaluation.max_score)):
                                messages.warning(request, f"Note invalide pour {enrollment.student.full_name}: {score} est hors limites (0-{evaluation.max_score}).")
                                grades_skipped_count += 1
                                continue # Skip this grade, don't save/update

                            if existing_grade:
                                # Update existing grade only if values have changed
                                if existing_grade.score != score or existing_grade.remarks != remarks:
                                    existing_grade.score = score
                                    existing_grade.remarks = remarks
                                    existing_grade.graded_by = teacher_user
                                    existing_grade.save()
                                    grades_saved_count += 1
                                # else: no change, do nothing
                            else:
                                # Create new grade
                                Grade.objects.create(
                                    enrollment=enrollment,
                                    evaluation=evaluation,
                                    score=score,
                                    remarks=remarks,
                                    graded_by=teacher_user
                                )
                                grades_saved_count += 1
                        except ValueError:
                            messages.error(request, f"Note invalide pour {enrollment.student.full_name}: '{score_str}' n'est pas un nombre valide.")
                            grades_skipped_count += 1
                    else: # If score_str is empty (user cleared it or didn't input anything)
                        if existing_grade:
                            # Delete existing grade if the field is empty
                            existing_grade.delete()
                            grades_deleted_count += 1
                            # messages.info(request, f"La note existante pour {enrollment.student.full_name} a été supprimée.") # Moved to summary

            # Consolidated success/info/error messages after the loop and transaction
            if grades_saved_count > 0:
                messages.success(request, f"{grades_saved_count} note(s) enregistrée(s) ou mise(s) à jour avec succès.")
            if grades_deleted_count > 0:
                messages.info(request, f"{grades_deleted_count} note(s) supprimée(s).")
            if grades_skipped_count > 0:
                messages.warning(request, f"{grades_skipped_count} note(s) ignorée(s) en raison d'erreurs ou de validation.")
            if grades_saved_count == 0 and grades_deleted_count == 0 and grades_skipped_count == 0:
                messages.info(request, "Aucune modification de note à enregistrer.")

        except Exception as e:
            # Catch any unexpected errors during the transaction, ensures rollback and user feedback
            messages.error(request, f"Une erreur inattendue est survenue lors de l'enregistrement des notes. Veuillez réessayer. Détails techniques: {e}")
            print(f"Transaction rollback error in teacher_enter_grades: {e}") # For server-side debugging

        return redirect('profiles:teacher_enter_grades', evaluation_id=evaluation.id) # Redirect after POST

    context = {
        'title': f'Saisir les Notes pour {evaluation.name}',
        'evaluation': evaluation,
        'students_grades_list': students_grades_for_template, # Use the new name
    }
    return render(request, 'profiles/teacher_enter_grades.html', context)

@login_required
@user_passes_test(lambda u: u.is_approved and u.user_type == UserRole.TEACHER)
def teacher_student_list(request):
    teacher = request.user

    assigned_classes = Classe.objects.filter(classassignment__teacher=teacher).distinct().order_by('name')

    selected_class_id = request.GET.get('class_filter')
    students_in_teacher_classes = Student.objects.none()

    if assigned_classes.exists():
        if selected_class_id and selected_class_id != 'all':
            try:
                selected_class = assigned_classes.get(id=int(selected_class_id))
                students_in_teacher_classes = Student.objects.filter(current_classe=selected_class).order_by('last_name', 'first_name')
            except Classe.DoesNotExist:
                messages.error(request, "Classe non trouvée ou non assignée à votre profil.")
                selected_class_id = None
            except ValueError:
                messages.error(request, "ID de classe invalide.")
                selected_class_id = None
        else:
            students_in_teacher_classes = Student.objects.filter(current_classe__in=assigned_classes).order_by('last_name', 'first_name')
            selected_class_id = 'all'

    context = {
        'title': 'Ma Liste d\'Élèves',
        'students': students_in_teacher_classes,
        'assigned_classes': assigned_classes,
        'selected_class_id': selected_class_id,
    }
    return render(request, 'profiles/teacher_student_list.html', context)

@login_required
@user_passes_test(lambda u: u.is_approved and u.user_type == UserRole.TEACHER)
def teacher_add_remove_students_to_class(request, class_id):
    teacher_user = request.user
    classe = get_object_or_404(Classe, id=class_id)

    if not ClassAssignment.objects.filter(teacher=teacher_user, classe=classe).exists():
        messages.error(request, "Vous n'êtes pas assigné à cette classe.")
        return redirect('profiles:teacher_student_list')

    students_in_class = Student.objects.filter(current_classe=classe).order_by('last_name', 'first_name')
    students_not_in_class = Student.objects.filter(
        Q(school=teacher_user.school) | Q(school__isnull=True)
    ).exclude(
        id__in=students_in_class.values_list('id', flat=True)
    ).order_by('last_name', 'first_name')

    if request.method == 'POST':
        action = request.POST.get('action')
        student_ids = request.POST.getlist('student_ids')

        if action == 'add':
            for student_id in student_ids:
                student = get_object_or_404(Student, id=student_id)
                if not student.current_classe:
                    student.current_classe = classe
                    student.save()
                    messages.success(request, f"L'élève {student.full_name} a été ajouté à {classe.name}.")
                else:
                    messages.warning(request, f"L'élève {student.full_name} est déjà assigné à {student.current_classe.name}.")
        elif action == 'remove':
            for student_id in student_ids:
                student = get_object_or_404(Student, id=student_id)
                if student.current_classe == classe:
                    student.current_classe = None
                    student.save()
                    messages.info(request, f"L'élève {student.full_name} a été retiré de {classe.name}.")
                else:
                    messages.warning(request, f"L'élève {student.full_name} n'était pas dans {classe.name}.")
        return redirect('profiles:teacher_add_remove_students_to_class', class_id=class_id)

    context = {
        'title': f'Gérer les élèves de {classe.name}',
        'classe': classe,
        'students_in_class': students_in_class,
        'students_not_in_class': students_not_in_class,
    }
    return render(request, 'profiles/teacher_add_remove_students_to_class.html', context)
def is_teacher_assigned_to_student_class(teacher_user: CustomUser, student: Student) -> bool:
    """
    Fonction utilitaire pour vérifier si un enseignant est assigné à la classe d'un élève.
    Utilise le related_name 'taught_courses' défini dans le modèle Course.
    """
    if not student.current_classe:
        return False
    # CORRECTION : Utilise 'taught_courses' qui est le related_name de Course.teachers
    return teacher_user.taught_courses.filter(classe=student.current_classe, school=teacher_user.school).exists()


 

@login_required
@user_passes_test(lambda u: u.is_approved and u.user_type == UserRole.TEACHER)
def teacher_send_message_to_parents(request, student_id):
    teacher = request.user
    student = get_object_or_404(Student, id=student_id)

    # Vous pouvez décommenter et utiliser la fonction is_teacher_assigned_to_student_class si elle est pertinente ici
    # if not is_teacher_assigned_to_student_class(teacher, student):
    # messages.error(request, "Vous n'êtes pas autorisé à envoyer des messages pour cet élève.")
    # return redirect('teacher_student_list_view')

    parents_of_student = student.parents.all()

    if request.method == 'POST':
        subject = request.POST.get('subject')
        content = request.POST.get('content')

        if not subject or not content:
            messages.error(request, "Le sujet et le contenu du message sont requis.")
        else:
            for parent in parents_of_student:
                Notification.objects.create(
                    sender=teacher,
                    recipient=parent, # Le parent est un CustomUser
                    subject=subject,
                    message=content,
                    notification_type='MESSAGE' # Ou un autre type de notification pertinent
                )
            messages.success(request, f"Message envoyé aux parents de {student.full_name}.")
            return redirect('profiles:teacher_student_detail', student_id=student.id)

    context = {
        'title': f"Envoyer un message aux parents de {student.full_name}",
        'student': student,
        'parents_of_student': parents_of_student,
        # 'form': MessageForm() # Si vous utilisez un formulaire dédié
    }
    return render(request, 'profiles/teacher_send_message_to_parents.html', context)

@login_required
def parent_evaluations_view(request):
    if request.user.user_type != UserRole.PARENT: # Correction: utiliser UserRole.PARENT
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette page.")
        return redirect('profiles:home')

    context = {
        'user': request.user,
    }
    return render(request, 'profiles/parent_evaluations.html', context)

@login_required
def parent_attendance_view(request):
    if request.user.user_type != UserRole.PARENT: # Correction: utiliser UserRole.PARENT
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette page.")
        return redirect('profiles:home')

    context = {
        'user': request.user,
    }
    return render(request, 'profiles/parent_attendance.html', context)

@login_required
def parent_my_children_list_view(request):
    if request.user.user_type != UserRole.PARENT: # Correction: utiliser UserRole.PARENT
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette page.")
        return redirect('profiles:home')

    my_children = Student.objects.filter(parents=request.user).order_by('first_name', 'last_name')

    context = {
        'my_children': my_children,
        'user': request.user,
    }
    return render(request, 'profiles/parent_my_children_list.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.TEACHER, login_url='/login/')
def teacher_delete_evaluation(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)

    if not evaluation.course.teachers.filter(id=request.user.id).exists():
        messages.error(request, "Vous n'êtes pas autorisé à supprimer cette évaluation.")
        return redirect('profiles:teacher_manage_evaluations')

    if request.method == 'POST':
        evaluation.delete()
        messages.success(request, f"L'évaluation '{evaluation.name}' a été supprimée avec succès.")
        return redirect('profiles:teacher_manage_evaluations')

    context = {
        'title': f'Confirmer la suppression de {evaluation.name}',
        'evaluation': evaluation,
    }
    return render(request, 'profiles/confirm_delete_evaluation.html', context)

@login_required
@user_passes_test(is_parent, login_url='/login/')
def parent_notifications_view(request):
    # Log 1: Quand un parent accède à la vue
    logger.info(f"Le parent {request.user.email} (ID: {request.user.id}) accède à ses notifications.")

    # Récupération des notifications
    # Votre approche actuelle (Approche 1) est la plus simple et la plus directe.
    # Si toutes les notifications destinées au parent (directes ou via enfant) ont le parent comme 'recipient',
    # alors cette ligne est correcte.
    all_notifications = Notification.objects.filter(recipient=request.user).order_by('-timestamp')

    # Log 2: Nombre de notifications récupérées
    logger.info(f"Le parent {request.user.email} a récupéré {all_notifications.count()} notifications depuis la base de données.")

    # Log 3: Inspectez les détails des premières notifications récupérées
    # Utilisez logger.debug pour des informations très détaillées, elles n'apparaîtront que si le niveau de log est DEBUG
    for i, n in enumerate(all_notifications[:5]): # Limitez à 5 pour ne pas surcharger les logs
        sender_info = n.sender.email if n.sender else 'None'
        recipient_info = n.recipient.email if n.recipient else 'None'
        logger.debug(f"Notification {i+1}: ID={n.id}, Sujet='{n.subject[:30]}', Expéditeur={sender_info}, Destinataire={recipient_info}, Lue={n.is_read}")

    context = {
        'notifications': all_notifications,
        'title': "Vos Notifications"
    }
    return render(request, 'profiles/parent_notifications.html', context) # Assurez-vous que le nom du template est correct



@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/')
def classe_create(request):
    """
    Vue pour créer une nouvelle classe.
    """
    user = request.user
    if user.user_type != UserRole.DIRECTION:
        messages.error(request, "Vous n'êtes pas autorisé à créer une classe.")
        return redirect('profiles:home')

    # Assurez-vous que la direction est associée à une école
    if not user.school:
        messages.warning(request, "Votre compte n'est pas associé à une école. Impossible de créer une classe.")
        return redirect('profiles:home')

    if request.method == 'POST':
        # Passez l'instance de l'école au formulaire pour filtrer les querysets
        form = ClasseForm(request.POST, school=user.school)
        if form.is_valid():
            classe = form.save(commit=False)
            classe.school = user.school # Associez la classe à l'école de l'utilisateur
            classe.save()
            messages.success(request, f"La classe '{classe.name}' a été créée avec succès.")
            return redirect('profiles:class_list') # Redirigez vers la liste des classes
        else:
            messages.error(request, "Erreur lors de la création de la classe. Veuillez vérifier les informations.")
    else:
        # Passez l'instance de l'école au formulaire pour filtrer les querysets
        form = ClasseForm(initial={'shool': user.school}, request=request)

    context = {
        'title': 'Créer une Nouvelle Classe',
        'form': form,
    }
    # Nous allons réutiliser le template de formulaire pour la création et la modification
    return render(request, 'profiles/classe_form.html', context)

@login_required
def course_list(request, class_id=None):
    """
    Vue pour lister les cours, soit tous, soit filtrés par une classe spécifique.
    """
    classe = None
    if class_id:
        classe = get_object_or_404(Classe, pk=class_id)
        # --- C'EST LA LOGIQUE CLÉ POUR FILTRER LES COURS PAR CLASSE ---
        # Cette partie dépend FORTEMENT de la relation entre vos modèles Classe et Course.
        # Choisissez l'option qui correspond à vos modèles :

        # Option 1: Si Course a un ManyToManyField 'classes' vers Classe
        # courses = classe.course_set.all().order_by('name') # 'course_set' est le related_name par défaut
        # OU si vous avez défini 'related_name' sur le ManyToManyField sur Course, ex: related_name='courses_in_class'
        courses = classe.courses.all().order_by('name') # Si votre ManyToManyField s'appelle 'classes' sur Course

        # Option 2: Si vous utilisez un modèle intermédiaire ClassAssignment
        # Supposons que ClassAssignment a une ForeignKey vers Classe et une ForeignKey vers Course
        course_ids = ClassAssignment.objects.filter(classe=classe).values_list('course__id', flat=True).distinct()
        courses = Course.objects.filter(id__in=course_ids).order_by('name')

        # Option 3: Si un Course a une ForeignKey directe vers une seule Classe (moins probable pour "différents cours")
        # courses = Course.objects.filter(assigned_class=classe).order_by('name') # Remplacez 'assigned_class' par le nom de votre ForeignKey

        # Pour cet exemple, je vais réutiliser l'option 2 (via ClassAssignment) qui est la plus flexible pour N:N
        # Assurez-vous que vos modèles sont bien configurés pour cela.
        
    else:
        # Si aucun class_id n'est fourni, listez tous les cours
        courses = Course.objects.all().order_by('name')

    context = {
        'courses': courses,
        'classe': classe, # Passe l'objet Classe au template si un filtre est appliqué
        'all_classes': Classe.objects.all().order_by('name') # Pour le sélecteur dans le template course_list
    }
    return render(request, 'profiles/course_list.html', context) # Utilise le template de liste de cours existant
# ... (vos autres vues) ..

@login_required
@user_passes_test(is_direction, login_url='/login/')
def classe_create(request):
    user = request.user # L'utilisateur connecté
    
    # Assurez-vous que l'utilisateur est lié à une école
    if not user.school:
        messages.error(request, "Votre compte n'est pas lié à une école. Impossible d'ajouter une classe.")
        return redirect('profiles:direction_dashboard') # Redirige vers un tableau de bord

    if request.method == 'POST':
        # Passez request.POST ET request=request (et school=user.school si nécessaire)
        form = ClasseForm(request.POST, request=request, school=user.school) # <-- CORRECTION ICI
        if form.is_valid():
            classe = form.save(commit=False) # Sauvegarde l'instance mais ne la commit pas encore
            classe.school = user.school # Assigne l'école de l'utilisateur à la classe
            classe.save() # Sauvegarde la classe dans la base de données
            messages.success(request, "La classe a été ajoutée avec succès.")
            return redirect('profiles:classe_list') # Redirigez vers la liste des classes
        else:
            messages.error(request, "Erreur lors de l'ajout de la classe. Veuillez vérifier les informations.")
    else:
        # Pour les requêtes GET, instanciez un formulaire vide.
        # Passez request=request (et school=user.school si nécessaire)
        # Note: 'initial' est pour pré-remplir les champs du formulaire, pas pour les kwargs personnalisés.
        # Vous avez utilisé 'shool' au lieu de 'school' dans 'initial', corrigez aussi cela si vous le gardez.
        form = ClasseForm(request=request, school=user.school) # <-- CORRECTION ICI

    context = {
        'form': form,
        'title': "Ajouter une nouvelle Classe"
    }
    return render(request, 'profiles/classe_form.html', context) # Assurez-vous que le template est correct

@login_required
# Vous pouvez ajouter @permission_required si seulement certains rôles peuvent voir les classes
def class_list(request):
    """
    Vue pour lister toutes les classes de l'école de l'utilisateur connecté.
    """
    # Filtrer les classes par l'école de l'utilisateur si c'est pertinent
    # Ex: si votre modèle Classe a une ForeignKey vers School et que votre User a une ForeignKey vers School
    # classes = Classe.objects.filter(school=request.user.school).order_by('name')
    classes = Classe.objects.all().order_by('name') # Liste toutes les classes pour l'exemple

    context = {
        'classes': classes
    }
    return render(request, 'profiles/class_list.html', context) # Nous allons créer ce template

# --- Ajustement de la vue course_list (comme discuté précédemment) ---
def is_direction_or_teacher(user):
    return user.is_authenticated and (user.user_type == 'DIRECTION' or user.user_type == 'TEACHER')
@login_required
@user_passes_test(is_direction_or_teacher, login_url='/login/')
def course_list(request, classe_id):
    # Retrieve the Classe object
    classe = get_object_or_404(Classe, id=classe_id)

    # Filter courses by the current active academic period for the school
    active_academic_period = AcademicPeriod.objects.filter(
        school=classe.school, # Filter by the school associated with the classe
        is_current=True
    ).first()

    courses = [] # Initialize as empty list

    if active_academic_period:
        # ⭐ CORRECTION MAJEURE ICI ⭐
        # On filtre les Cours qui ont la 'classe' spécifiée dans leur ManyToManyField 'classes'
        # Et on s'assure qu'ils sont pour la bonne période académique et la bonne école.
        courses = Course.objects.filter(
            classes=classe, # <--- C'EST LE NOM DU CHAMP DANS LE MODÈLE COURSE (ManyToManyField vers Classe)
            academic_period=active_academic_period,
            school=classe.school 
        ).distinct().order_by('name') # .distinct() est important pour ManyToMany si un cours peut être lié à une classe via plusieurs chemins.
    else:
        # Handle case where no active academic period is found
        messages.warning(request, "Aucune période académique active trouvée pour cette école. Les cours ne peuvent pas être affichés.")

    context = {
        'classe': classe,
        'courses': courses,
        'title': f"Cours pour la {classe.name}",
        'active_academic_period': active_academic_period,
    }
    return render(request, 'profiles/course_list.html', context)

def is_direction(user):
    return user.is_authenticated and (user.user_type == UserRole.DIRECTION or user.user_type == UserRole.ADMIN)

def is_teacher(user):
    return user.is_authenticated and user.user_type == UserRole.TEACHER

def is_parent(user):
    return user.is_authenticated and user.user_type == UserRole.PARENT

# --- Nouvelle vue d'envoi de notification (point d'entrée principal) ---
@login_required
@user_passes_test(is_direction)
def direction_send_notification_view(request):
    classes = Classe.objects.all().order_by('name')
    context = {
        'classes': classes,
        'title': 'Envoyer une Notification'
    }
    return render(request, 'profiles/direction_send_notification_choice.html', context)


# --- Vue pour envoyer un message à un parent spécifique (via l'ID de l'élève) ---
@login_required
@user_passes_test(is_direction)
def direction_send_message_to_single_parent(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    parent_user = student.parent # Assurez-vous que votre modèle Student a un champ 'parent' qui est une ForeignKey vers CustomUser
    
    if not parent_user or parent_user.user_type != UserRole.PARENT:
        messages.error(request, "L'élève sélectionné n'a pas de parent associé ou le parent n'est pas de type PARENT.")
        return redirect('profiles:direction_send_notification') # Redirige vers la page de choix

    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.sender = request.user
            notification.recipient = parent_user # Destinataire spécifique
            notification.recipient_role = UserRole.PARENT # Rôle du destinataire
            notification.save()
            messages.success(request, f"Message envoyé à {parent_user.full_name} (Parent de {student.full_name}).")
            return redirect('profiles:direction_send_notification') # Redirige après envoi
    else:
        form = NotificationForm()
    
    context = {
        'form': form,
        'student': student,
        'parent_user': parent_user,
        'title': f'Envoyer un message à {parent_user.full_name}'
    }
    return render(request, 'profiles/direction_send_message_form.html', context)


# --- Vue pour envoyer un message aux parents de toutes les classes ---

@login_required
@user_passes_test(is_direction)
def direction_send_message_to_all_parents(request):
    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            # C'est ici que vous placez la première ligne de log
            logger.info(f"Formulaire valide. Utilisateur Direction : {request.user.email} (ID: {request.user.id})")

            # Récupérer tous les utilisateurs de type PARENT
            all_parents = CustomUser.objects.filter(user_type=UserRole.PARENT)
            
            if not all_parents.exists():
                messages.warning(request, "Aucun parent trouvé dans le système.")
                logger.warning("Aucun parent trouvé dans le système pour l'envoi de notification.") # Ajoutez aussi un log ici
                return redirect('profiles:direction_send_notification')

            for parent_user in all_parents:
                notification = form.save(commit=False) 
                notification.sender = request.user
                notification.recipient = parent_user # Envoie à chaque parent individuellement
                notification.recipient_role = UserRole.PARENT
                
                # C'est ici que vous placez la deuxième ligne de log, juste avant la sauvegarde
                logger.info(f"Préparation de la notification pour le parent : {parent_user.email} (ID: {parent_user.id}). Expéditeur : {request.user.email} (ID: {request.user.id}). Sujet : {notification.subject[:50]}...")
                
                try:
                    notification.save()
                    logger.info(f"Notification sauvegardée avec succès (ID: {notification.id}) pour {parent_user.email}.")
                except Exception as e:
                    logger.error(f"ÉCHEC DE SAUVEGARDE de la notification pour {parent_user.email} : {e}", exc_info=True)
            
            messages.success(request, "Message envoyé à tous les parents.")
            logger.info("Processus d'envoi de message terminé pour tous les parents.") # Et un log de fin de processus
            return redirect('profiles:direction_send_notification')
        else:
            logger.warning(f"Le formulaire de notification est invalide. Erreurs : {form.errors.as_json()}") # Log si le formulaire est invalide
    else:
        form = NotificationForm()

    context = {
        'form': form,
        'target_audience': 'tous les parents',
        'title': 'Envoyer un message à tous les parents'
    }
    return render(request, 'profiles/direction_send_message_form.html', context)


# --- Vue pour envoyer un message aux parents d'une classe spécifique ---
@login_required
@user_passes_test(is_direction)
def direction_send_message_to_class_parents(request, classe_id):
    classe = get_object_or_404(Classe, pk=classe_id)

    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            # Récupérer tous les élèves de cette classe
            # Assurez-vous que Student a une ForeignKey vers Classe
            students_in_class = Student.objects.filter(current_class=classe).exclude(parent__isnull=True) # Exclure les élèves sans parent
            
            if not students_in_class.exists():
                messages.warning(request, f"Aucun élève avec un parent trouvé dans la classe {classe.name}.")
                return redirect('profiles:direction_send_notification')

            # Collecter les parents uniques pour éviter les doublons si un parent a plusieurs enfants dans la même classe
            unique_parents = CustomUser.objects.filter(
                id_in=students_in_class.values_list('parent_id', flat=True).distinct()
            )

            if not unique_parents.exists():
                 messages.warning(request, f"Aucun parent associé aux élèves de la classe {classe.name}.")
                 return redirect('profiles:direction_send_notification')

            for parent_user in unique_parents:
                notification = form.save(commit=False)
                notification.sender = request.user
                notification.recipient = parent_user # Envoie à chaque parent individuellement
                notification.recipient_role = UserRole.PARENT
                notification.recipient_class = classe # Associe la notification à la classe
                notification.save()
            
            messages.success(request, f"Message envoyé aux parents de la classe {classe.name}.")
            return redirect('profiles:direction_send_notification')
    else:
        form = NotificationForm()

    context = {
        'form': form,
        'classe': classe,
        'target_audience': f'les parents de la classe {classe.name}',
        'title': f'Envoyer un message aux parents de {classe.name}'
    }
    return render(request, 'profiles/direction_send_message_form.html', context)

def academic_period_create(request):
    if request.method == 'POST':
        form = AcademicPeriodForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                academic_period = form.save(commit=False)
                # Si l'école n'est pas automatiquement définie par le formulaire
                # et que l'utilisateur est lié à une école, vous pouvez la définir ici.
                # Exemple: if hasattr(request.user, 'school') and request.user.school:
                #              academic_period.school = request.user.school
                academic_period.save()
                messages.success(request, "Période académique ajoutée avec succès.")
                return redirect('profiles:academic_period_list')
            except IntegrityError:
                messages.error(request, "Une période académique avec ce nom existe déjà pour cette école. Veuillez choisir un nom différent.")
                # Si l'erreur se produit, nous ne redirigeons pas, nous passons à 'else' pour afficher le formulaire avec les messages.
            except Exception as e:
                messages.error(request, f"Une erreur inattendue s'est produite: {e}")
                # Capture d'autres erreurs potentielles
        else:
            # Si le formulaire n'est pas valide (par exemple, champs manquants ou erreurs de validation)
            # crispy_forms se chargera d'afficher les erreurs sous les champs.
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = AcademicPeriodForm(user=request.user)

    context = {
        'form': form,
        'title': 'Ajouter une Nouvelle Période Académique'
    }
    return render(request, 'profiles/academic_period_form.html', context)

@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER], login_url='/login/')
def student_profile_view(request, student_id):
    """
    Vue pour afficher le profil détaillé d'un élève.
    Accessible par la direction et les enseignants (qui peuvent voir leurs élèves).
    """
    user = request.user

    # Récupérer l'élève ou retourner une 404
    # Assurez-vous que l'élève appartient à la même école que l'utilisateur connecté
    student = get_object_or_404(Student, id=student_id, school=user.school)

    # Logique pour les enseignants : ils ne peuvent voir que les profils des élèves de leur école
    if user.user_type == UserRole.TEACHER:
        # Vous pouvez ajouter des restrictions supplémentaires ici si un enseignant
        # ne doit voir que les élèves de SES classes/cours.
        # Pour l'instant, c'est juste par école.
        pass # Pas de filtre supplémentaire par défaut pour l'enseignant pour les profils

    context = {
        'title': f"Profil de {student.first_name} {student.last_name}",
        'student': student,
        # Vous pouvez ajouter d'autres données ici (notes, absences, cours, etc.)
        # Par exemple:
        # 'courses_enrolled': student.enrollments.all(),
        # 'recent_grades': Grade.objects.filter(student=student).order_by('-date_given')[:5],
    }
    return render(request, 'profiles/student_profile.html', context)

def course_update(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Cours mis à jour avec succès.")
            return redirect('profiles:course_list') # Redirige vers la liste des cours
    else:
        form = CourseForm(instance=course)
    return render(request, 'profiles/course_form.html', {'form': form, 'course': course, 'title': 'Modifier un cours'})

def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST': # La suppression doit idéalement se faire via POST pour la sécurité
        course.delete()
        messages.success(request, f"Le cours '{course.name}' a été supprimé avec succès.")
        return redirect('profiles:course_list') # Redirige vers la liste des cours après suppression

    # Pour une confirmation avant suppression (optionnel)
    # Vous pourriez rendre un template de confirmation ici au lieu de supprimer directement
    return render(request, 'profiles/course_confirm_delete.html', {'course': course})

def academic_period_list(request):
    academic_periods = AcademicPeriod.objects.all().order_by('-start_date')
    context = {
        'academic_periods': academic_periods,
        'title': 'Liste des Périodes Académiques'
    }
    return render(request, 'profiles/academic_period_list.html', context)

# profiles/views.py

# ... (Vos importations) ...

# --- AJOUTEZ CES CLASSES DE FORMULAIRE CI-DESSOUS ---


@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION or u.user_type == UserRole.ADMIN, login_url='/login/')
def direction_dashboard_view(request):
    direction_user = request.user
    
    # Pour s'assurer que les statistiques sont spécifiques à l'école de l'administrateur
    user_school = direction_user.school 

    # Statistiques générales
    total_students = Student.objects.filter(school=user_school).count()
    total_teachers = User.objects.filter(user_type=UserRole.TEACHER.value, school=user_school).count()
    total_parents = User.objects.filter(user_type=UserRole.PARENT.value, school=user_school).count()
    total_classes = Classe.objects.filter(school=user_school).count()
    total_courses = Course.objects.filter(school=user_school).count()
    total_unapproved_users = User.objects.filter(is_approved=False, school=user_school).count()

    # Répartition des utilisateurs par rôle (si vous voulez une vision plus granulaire)
    user_counts_by_role = User.objects.filter(school=user_school).values('user_type').annotate(count=Count('user_type'))
    # Convertir en dictionnaire pour un accès plus facile dans le template
    user_counts_dict = {item['user_type']: item['count'] for item in user_counts_by_role}

    # Récupérer les 5 dernières notifications non lues pour la direction
    unread_notifications = Notification.objects.filter(
        recipient=direction_user,
        is_read=False
    ).order_by('-timestamp')[:5]

    # Récupérer les 5 dernières demandes d'approbation d'utilisateurs
    latest_unapproved_users = User.objects.filter(
        is_approved=False, 
        school=user_school
    ).order_by('-date_joined')[:5]

    context = {
        'title': 'Tableau de Bord de la Direction',
        'direction_user': direction_user,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_parents': total_parents,
        'total_classes': total_classes,
        'total_courses': total_courses,
        'total_unapproved_users': total_unapproved_users,
        'user_counts_dict': user_counts_dict,
        'unread_notifications': unread_notifications,
        'latest_unapproved_users': latest_unapproved_users,
    }
    return render(request, 'profiles/direction_dashboard.html', context)

def is_direction_or_teacher(user):
    return user.is_authenticated and (user.user_type == 'DIRECTION' or user.user_type == 'TEACHER')

# Votre vue existante pour les cours d'une classe spécifique
@login_required
@user_passes_test(is_direction_or_teacher, login_url='/login/')
def course_list(request, classe_id):
    classe = get_object_or_404(Classe, id=classe_id)
    user_school = request.user.school # Obtenez l'école de l'utilisateur connecté

    active_academic_period = AcademicPeriod.objects.filter(
        school=user_school, # Utilisez l'école de l'utilisateur pour filtrer
        is_current=True
    ).first()

    courses = []

    if active_academic_period:
        courses = Course.objects.filter(
            classes=classe,
            academic_period=active_academic_period,
            school=user_school # Filtrez aussi par l'école de l'utilisateur
        ).distinct().order_by('name')
    else:
        messages.warning(request, "Aucune période académique active trouvée pour cette école. Les cours ne peuvent pas être affichés.")

    context = {
        'classe': classe,
        'courses': courses,
        'title': f"Cours pour la {classe.name}",
        'active_academic_period': active_academic_period,
    } 
    return render(request, 'profiles/course_list.html', context)

# ⭐ NOUVELLE VUE : Pour lister TOUS les cours (pas seulement ceux d'une classe spécifique) ⭐
@login_required
@user_passes_test(is_direction_or_teacher, login_url='/login/')
def all_courses_view(request):
    user_school = request.user.school # Obtenez l'école de l'utilisateur connecté

    active_academic_period = AcademicPeriod.objects.filter(
        school=user_school,
        is_current=True
    ).first()

    courses = []

    if active_academic_period:
        courses = Course.objects.filter(
            school=user_school, # Filtrez par l'école de l'utilisateur
            academic_period=active_academic_period
        ).order_by('name')
    else:
        messages.warning(request, "Aucune période académique active trouvée pour votre école. Les cours ne peuvent pas être affichés.")

    context = {
        'courses': courses,
        'title': "Tous les Cours",
        'active_academic_period': active_academic_period,
        'classe': None, # Important pour indiquer que ce n'est pas pour une classe spécifique
    }
    return render(request, 'profiles/course_list.html', context)

@login_required
@user_passes_test(is_direction, login_url='/login/') # Seule la direction peut gérer les élèves
def create_or_update_student(request, student_id=None):
    user_school = request.user.school
    student = None
    if student_id:
        student = get_object_or_404(Student, id=student_id, school=user_school) # S'assurer que l'élève appartient à l'école

    if not user_school:
        messages.error(request, "Votre compte n'est pas lié à une école. Impossible de gérer les élèves.")
        return redirect('profiles:direction_dashboard')

    # Obtenir la période académique active
    active_academic_period = AcademicPeriod.objects.filter(
        school=user_school,
        is_current=True
    ).first()

    if not active_academic_period and not student_id: # Avertir seulement à la création si pas de période active
        messages.warning(request, "Attention : Aucune période académique active n'est définie pour votre école. L'inscription automatique de l'élève aux cours pourrait être affectée.")

    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student) # Utilisez request.FILES si vous avez un champ fichier
        if form.is_valid():
            # Récupérer l'ancienne classe avant de sauvegarder, si c'est une mise à jour
            old_classe = student.current_classe if student else None
            
            student_instance = form.save(commit=False)
            student_instance.school = user_school # Assigner l'école
            student_instance.save() # Sauvegarder l'élève

            form.save_m2m() # Sauvegarder les relations ManyToMany (comme parents)

            new_classe = student_instance.current_classe

            # --- LOGIQUE D'INSCRIPTION AUTOMATIQUE ---
            # Si la classe de l'élève a changé OU si c'est un nouvel élève assigné à une classe
            if new_classe and (not old_classe or new_classe != old_classe):
                if active_academic_period:
                    # Supprimer les anciennes inscriptions si la classe a changé
                    if old_classe:
                        Enrollment.objects.filter(
                            student=student_instance,
                            academic_period=active_academic_period,
                            school=user_school,
                            course__in=old_classe.courses_taught.filter(academic_period=active_academic_period)
                        ).delete()
                        messages.info(request, f"Anciennes inscriptions pour {student_instance.full_name} supprimées.")


                    # Inscrire l'élève à tous les cours de la nouvelle classe
                    courses_in_new_classe = new_classe.courses_taught.filter(academic_period=active_academic_period)
                    for course in courses_in_new_classe:
                        Enrollment.objects.get_or_create(
                            student=student_instance,
                            course=course,
                            academic_period=active_academic_period,
                            school=user_school # Toujours lier l'inscription à l'école
                        )
                    messages.success(request, f"L'élève {student_instance.full_name} a été inscrit automatiquement à la classe et à tous les cours de '{new_classe.name}'.")
                else:
                    messages.warning(request, "Impossible d'inscrire automatiquement l'élève aux cours : aucune période académique active n'est définie.")
            elif not new_classe:
                messages.warning(request, "La classe de l'élève n'est pas définie. Il ne sera pas inscrit aux cours.")
            
            messages.success(request, f"L'élève {student_instance.full_name} a été {'mis à jour' if student_id else 'créé'} avec succès.")
            return redirect('profiles:teacher_list_students_view') # Ou une liste d'élèves
        else:
            messages.error(request, "Erreur lors de la sauvegarde de l'élève. Veuillez corriger les erreurs.")
    else:
        form = StudentForm(instance=student) # Initialise le formulaire pour GET

    context = {
        'form': form,
        'title': f"{'Modifier' if student_id else 'Ajouter'} un Élève",
        'student': student,
        'active_academic_period': active_academic_period,
    }
    return render(request, 'profiles/create_or_update_student.html', context) # Assurez-vous d'avoir ce template

# Fonction pour vérifier si l'utilisateur est un administrateur d'école ou un directeur
#def is_school_admin_or_director(user):
 #   return user.is_authenticated and (user.user_type == 'SCHOOL_ADMIN' or user.user_type == 'DIRECTOR')


#@login_required
#@user_passes_test(is_school_admin_or_director) # Seuls les admins/directeurs peuvent voir le tableau de bord

#def is_school_admin_or_director(user):
 #   return user.is_authenticated and (user.user_type == 'SCHOOL_ADMIN' or user.user_type == 'DIRECTOR')
#@login_required
#@user_passes_test(is_school_admin_or_director)
def direction_create_teacher(request): # C'est cette fonction qui est pointée par l'erreur
    user_school = request.user.school

    if request.method == 'POST':
        # Supprimez school_instance ici si elle était présente
        form = TeacherRegistrationForm(request.POST) # Ou TeacherCreationForm si c'est le nom que vous utilisez ici
        if form.is_valid():
            teacher = form.save(school=user_school)
            messages.success(request, f"L'enseignant {teacher.first_name} {teacher.last_name} a été créé avec succès.")
            return redirect('profiles:direction_manage_users')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        # Supprimez school_instance ici si elle était présente
        form = TeacherRegistrationForm() # Ou TeacherCreationForm si c'est le nom que vous utilisez ici

    context = {
        'form': form,
        'school_name': user_school.name if user_school else "Votre École"
    }
    return render(request, 'profiles/direction_create_teacher.html', context) # Assurez-vous que le template est correct ici

# --- Nouvelle Vue : direction_teacher_Registration ---
#@login_required
#@user_passes_test(is_school_admin_or_director)
def direction_teacher_registration(request):
    user_school = request.user.school # Récupérer l'école de l'utilisateur connecté

    if request.method == 'POST':
        # Ne passez PAS school_instance ici pour le POST
        form = TeacherRegistrationForm(request.POST) 
        if form.is_valid():
            # Passez l'instance de l'école à la méthode save() du formulaire
            teacher = form.save(school=user_school) 
            messages.success(request, f"L'enseignant {teacher.first_name} {teacher.last_name} a été enregistré avec succès.")
            return redirect('profiles:direction_manage_users') # Redirige vers la liste des utilisateurs
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        # Ne passez PAS school_instance ici pour le GET
        form = TeacherRegistrationForm() 

    context = {
        'form': form,
        'school_name': user_school.name if user_school else "Votre École"
    }
    return render(request, 'profiles/direction_teacher_registration.html', context)

# ... (le reste de vos vues) ...

@login_required
@user_passes_test(lambda u: u.is_approved and u.user_type == UserRole.TEACHER)
def teacher_student_detail_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    teacher_user = request.user

    # VERIFICATION 1: Sécurité - L'enseignant est-il assigné à la classe de l'élève ?
    #if not is_teacher_assigned_to_student_class(teacher_user, student):
     #   messages.error(request, "Vous n'êtes pas autorisé à voir le profil de cet élève ou à gérer ses notes.")
      #  return redirect('profiles:teacher_list_students_view')

    # --- Données pour les cours de l'élève que l'enseignant enseigne ---
    teacher_courses_for_this_student = Course.objects.filter(
        teachers=teacher_user,
        enrollments__student=student,
        school=teacher_user.school
    ).distinct().order_by('name')

    academic_periods = AcademicPeriod.objects.filter(school=teacher_user.school).order_by('-start_date')

    # --- Gestion des Évaluations et Notes (avec filtre par date) ---
    selected_date_str = request.GET.get('evaluation_date_filter')

    # CORRECTION DE L'ERREUR PRÉCÉDENTE "Cannot resolve keyword 'course_enrollments_student'"
    # La traversée doit se faire via le related_name correct de Enrollment vers Course.
    # Si Enrollment a une ForeignKey 'course' sans related_name, le défaut est 'enrollment_set'
    # Sinon, si 'enrollment' est le related_name, c'est 'enrollment'.
    # Ici, nous utilisons 'enrollment' qui est un choix courant.
    evaluations_query = Evaluation.objects.filter(
        Q(course__in=teacher_courses_for_this_student) &
        Q(course_enrollments_student=student) # Supposant que le related_name de Enrollment.course est 'enrollment'
    ).distinct()

    if selected_date_str:
        try:
            filter_date = timezone.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            evaluations_query = evaluations_query.filter(date=filter_date)
        except ValueError:
            messages.warning(request, "Format de date invalide pour le filtre. Affichage de toutes les évaluations.")
            selected_date_str = None

    evaluations_for_display = evaluations_query.order_by('-date', 'course__name')

    grades_data = []
    for evaluation in evaluations_for_display:
        enrollment_for_eval_course = Enrollment.objects.filter(student=student, course=evaluation.course).first()
        grade = None
        if enrollment_for_eval_course:
            grade = Grade.objects.filter(enrollment=enrollment_for_eval_course, evaluation=evaluation).first()

        grades_data.append({
            'evaluation': evaluation,
            'grade_obj': grade,
            'score': grade.score if grade else '',
            'remarks': grade.remarks if grade else '',
            'notation': grade.get_notation() if grade else 'N/A'
        })

    # --- Données pour les Actions Disciplinaires ---
    disciplinary_records = DisciplinaryRecord.objects.filter(student=student).order_by('-created_at')

    # Initialisation du formulaire disciplinaire pour les requêtes GET ou si le POST n'est pas lié
    disciplinary_form = DisciplinaryRecordForm()

    # --- Traitement des POST (Ajout d'évaluation et Saisie/Modification de notes, Ajout Disciplinaire) ---
    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        if action_type == 'add_evaluation':
            name = request.POST.get('name')
            course_id = request.POST.get('course')
            evaluation_type = request.POST.get('evaluation_type')
            date_str = request.POST.get('date')
            max_score = request.POST.get('max_score')
            description = request.POST.get('description')
            academic_period_id = request.POST.get('academic_period')

            try:
                course = teacher_courses_for_this_student.get(id=course_id)
                academic_period = AcademicPeriod.objects.get(id=academic_period_id, school=teacher_user.school)
                date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
                max_score = float(max_score)

                Evaluation.objects.create(
                    name=name,
                    course=course,
                    evaluation_type=evaluation_type,
                    date=date,
                    max_score=max_score,
                    description=description,
                    created_by=teacher_user,
                    academic_period=academic_period
                )
                messages.success(request, "Évaluation ajoutée avec succès.")
            except Course.DoesNotExist:
                messages.error(request, "Cours non trouvé ou non assigné à votre profil pour cet élève.")
            except AcademicPeriod.DoesNotExist:
                messages.error(request, "Période académique non trouvée.")
            except ValueError:
                messages.error(request, "Erreur de format de date ou de score maximum.")
            except Exception as e:
                messages.error(request, f"Erreur lors de l'ajout de l'évaluation : {e}")

        elif action_type == 'save_grade':
            with transaction.atomic():
                grades_saved_count = 0
                grades_deleted_count = 0
                errors_count = 0
                
                for item in grades_data: 
                    evaluation = item['evaluation']
                    
                    score_str = request.POST.get(f'score_{evaluation.id}')
                    remarks = request.POST.get(f'remarks_{evaluation.id}', '').strip()

                    if not evaluation.course.teachers.filter(id=teacher_user.id).exists():
                        messages.warning(request, f"Vous n'êtes pas autorisé à modifier les notes pour l'évaluation '{evaluation.name}'.")
                        errors_count += 1
                        continue

                    enrollment_for_grade = Enrollment.objects.filter(student=student, course=evaluation.course).first()
                    
                    if not enrollment_for_grade:
                        messages.warning(request, f"L'élève n'est pas inscrit au cours de l'évaluation '{evaluation.name}'. Note non enregistrée.")
                        errors_count += 1
                        continue

                    existing_grade = Grade.objects.filter(
                        evaluation=evaluation,
                        enrollment=enrollment_for_grade
                    ).first()

                    if score_str:
                        try:
                            score = float(score_str)
                            if not (0 <= score <= float(evaluation.max_score)):
                                messages.warning(request, f"La note saisie ({score}) est hors des limites ({evaluation.max_score}) pour l'évaluation '{evaluation.name}'.")
                                errors_count += 1
                                continue
                            
                            if existing_grade:
                                existing_grade.score = score
                                existing_grade.remarks = remarks
                                existing_grade.graded_by = teacher_user
                                existing_grade.save()
                                grades_saved_count += 1
                            else:
                                Grade.objects.create(
                                    enrollment=enrollment_for_grade,
                                    evaluation=evaluation,
                                    score=score,
                                    remarks=remarks,
                                    graded_by=teacher_user
                                )
                                grades_saved_count += 1
                        except ValueError:
                            messages.error(request, f"La note saisie pour l'évaluation '{evaluation.name}' n'est pas un nombre valide.")
                            errors_count += 1
                    else:
                        if existing_grade:
                            existing_grade.delete()
                            grades_deleted_count += 1
                
                if grades_saved_count > 0:
                    messages.success(request, f"{grades_saved_count} note(s) enregistrée(s) ou mise(s) à jour avec succès.")
                if grades_deleted_count > 0:
                    messages.info(request, f"{grades_deleted_count} note(s) supprimée(s).")
                if errors_count > 0:
                    messages.error(request, f"Des erreurs sont survenues lors du traitement de {errors_count} note(s).")
                if grades_saved_count == 0 and grades_deleted_count == 0 and errors_count == 0:
                    messages.info(request, "Aucune modification de note à enregistrer.")

        elif action_type == 'add_disciplinary_record':
            disciplinary_form = DisciplinaryRecordForm(request.POST)
            if disciplinary_form.is_valid():
                record = disciplinary_form.save(commit=False)
                record.student = student
                record.reported_by = teacher_user
                record.school = teacher_user.school
                record.save()
                messages.success(request, "Dossier disciplinaire ajouté avec succès.")

                parents = student.parents.all()
                if parents.exists():
                    message_subject = f"Action Disciplinaire concernant votre enfant {student.full_name}"
                    message_body = (
                        f"Cher parent,\n\n"
                        f"Nous vous informons qu'une action disciplinaire a été enregistrée pour votre enfant, {student.full_name}, "
                        f"concernant un incident le {record.incident_date.strftime('%d/%m/%Y')}.\n"
                        f"Description: {record.description}\n"
                        f"Action prise: {record.action_taken}\n\n"
                        f"Veuillez en discuter avec votre enfant.\n\nCordialement,\nVotre école."
                    )
                    for parent_user in parents:
                        Notification.objects.create(
                            recipient=parent_user,
                            sender=teacher_user,
                            subject=message_subject,
                            message=message_body,
                            notification_type='DISCIPLINARY'
                        )
                else:
                    messages.warning(request, f"L'élève {student.full_name} n'a pas de parents liés pour la notification disciplinaire.")

            else:
                messages.error(request, "Erreur lors de l'ajout du dossier disciplinaire. Veuillez vérifier les champs.")
        
        return redirect('profiles:teacher_student_detail', student_id=student.id)

    context = {
        'title': f'Profil de l\'Élève : {student.full_name}',
        'student': student,
        'evaluations_for_student': grades_data,
        'teacher_courses_for_this_student': teacher_courses_for_this_student,
        'academic_periods': academic_periods,
        'evaluation_types': EvaluationType.choices,
        'selected_date_str': selected_date_str,
        'disciplinary_records': disciplinary_records,
        'disciplinary_form': disciplinary_form,
    }
    return render(request, 'profiles/teacher_student_detail.html', context)

@login_required
@user_passes_test(is_direction, login_url='/login/')
def course_create(request):
    user = request.user # La direction connectée

    if not user.school:
        messages.error(request, "Votre compte n'est pas lié à une école. Impossible d'ajouter un cours.")
        return redirect('profiles:direction_dashboard') # Ou une autre page pertinente

    if request.method == 'POST':
        # Passez request et school à votre formulaire
        form = CourseForm(request.POST, request=request, school=user.school)
        if form.is_valid():
            course = form.save() # Le .save() du formulaire gérera l'assignation de l'école et les M2M
            messages.success(request, f"Le cours '{course.name}' a été ajouté avec succès.")
            return redirect('profiles:course_list') # Redirigez vers une liste des cours (à créer aussi)
        else:
            messages.error(request, "Erreur lors de l'ajout du cours. Veuillez corriger les erreurs ci-dessous.")
    else: # GET request
        # Instanciez un formulaire vide pour l'affichage
        form = CourseForm(request=request, school=user.school)

    context = {
        'form': form,
        'title': "Ajouter un nouveau Cours"
    }
    return render(request, 'profiles/course_form.html', context) # Assurez-vous que ce template existe

def is_teacher(user):
    return user.is_authenticated and user.user_type == UserRole.TEACHER

@login_required
@user_passes_test(is_teacher, login_url='/login/')
def teacher_manage_student_enrollments(request):
    teacher_user = request.user
    if not teacher_user.school:
        messages.error(request, "Votre compte enseignant n'est pas lié à une école. Veuillez contacter l'administrateur.")
        return redirect('profiles:teacher_dashboard') # Redirigez vers le tableau de bord de l'enseignant

    # Filtrer les classes que cet enseignant enseigne
    # Supposons que les cours sont liés à une classe, et les enseignants aux cours
    # On peut trouver les classes via les cours enseignés
    teacher_classes_ids = Course.objects.filter(
        teachers=teacher_user, 
        school=teacher_user.school
    ).values_list('classes__id', flat=True).distinct()

    teacher_classes = Classe.objects.filter(id__in=teacher_classes_ids, school=teacher_user.school)

    # Récupérer les inscriptions existantes pour les classes de cet enseignant
    # Filtrer les inscriptions qui concernent les cours que l'enseignant dispense
    # ou les élèves dans les classes qu'il enseigne.
    # Pour l'instant, on liste juste les élèves de l'école de l'enseignant
    # avec leurs inscriptions si elles existent dans les cours de l'enseignant.
    
    # Option 1: Afficher toutes les inscriptions des cours enseignés par cet enseignant
    enrollments_managed_by_teacher = Enrollment.objects.filter(
        course__teachers=teacher_user,
        course__school=teacher_user.school
    ).select_related('student', 'course', 'academic_period').order_by(
        'course__name', 'student__last_name'
    )

    context = {
        'title': 'Gérer les Inscriptions des Élèves',
        'teacher_classes': teacher_classes, # Utile pour un filtre ou une navigation
        'enrollments': enrollments_managed_by_teacher,
    }
    return render(request, 'profiles/teacher_manage_student_enrollments.html', context)

@login_required
@user_passes_test(is_teacher, login_url='/login/')
def teacher_add_enrollment(request):
    teacher_user = request.user
    if not teacher_user.school:
        messages.error(request, "Votre compte enseignant n'est pas lié à une école.")
        return redirect('profiles:teacher_dashboard')

    # Important : Passer le teacher_user au formulaire pour filtrer les choix
    # et potentiellement la classe si un enseignant est lié à une seule classe pour l'inscription
    form = EnrollmentForm(teacher_user=teacher_user, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            try:
                with transaction.atomic():
                    enrollment = form.save(commit=False)
                    # L'école de l'inscription est celle du cours sélectionné, ou celle de l'enseignant
                    enrollment.enrollment_date = timezone.now().date() # Date d'inscription automatique
                    enrollment.save()
                    messages.success(request, f"L'élève '{enrollment.student.full_name}' a été inscrit au cours '{enrollment.course.name}' avec succès.")
                    return redirect('profiles:teacher_manage_student_enrollments') # Redirigez vers la liste des inscriptions gérées par l'enseignant
            except Exception as e:
                messages.error(request, f"Une erreur s'est produite lors de l'inscription : {e}")
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")

    context = {
        'title': 'Inscrire un Élève à un Cours',
        'form': form,
    }
    return render(request, 'profiles/teacher_add_enrollment.html', context)

@login_required
@user_passes_test(lambda u: u.is_approved and u.user_type == UserRole.TEACHER)
def teacher_student_detail_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    teacher_user = request.user

    # VERIFICATION 1: Sécurité - L'enseignant est-il assigné à la classe de l'élève ?
    #if not is_teacher_assigned_to_student_class(teacher_user, student):
     #   messages.error(request, "Vous n'êtes pas autorisé à voir le profil de cet élève ou à gérer ses notes.")
      #  return redirect('profiles:teacher_list_students_view')

    # --- Données pour les cours de l'élève que l'enseignant enseigne ---
    teacher_courses_for_this_student = Course.objects.filter(
        teachers=teacher_user,
        enrollments__student=student,
        school=teacher_user.school
    ).distinct().order_by('name')

    academic_periods = AcademicPeriod.objects.filter(school=teacher_user.school).order_by('-start_date')

    # --- Gestion des Évaluations et Notes (avec filtre par date) ---
    selected_date_str = request.GET.get('evaluation_date_filter')

    # CORRECTION DE L'ERREUR PRÉCÉDENTE "Cannot resolve keyword 'course_enrollments_student'"
    # La traversée doit se faire via le related_name correct de Enrollment vers Course.
    # Si Enrollment a une ForeignKey 'course' sans related_name, le défaut est 'enrollment_set'
    # Sinon, si 'enrollment' est le related_name, c'est 'enrollment'.
    # Ici, nous utilisons 'enrollment' qui est un choix courant.
    evaluations_query = Evaluation.objects.filter(
        Q(course__in=teacher_courses_for_this_student) &
        Q(course__enrollments__student=student) # Supposant que le related_name de Enrollment.course est 'enrollment'
    ).distinct()

    if selected_date_str:
        try:
            filter_date = timezone.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            evaluations_query = evaluations_query.filter(date=filter_date)
        except ValueError:
            messages.warning(request, "Format de date invalide pour le filtre. Affichage de toutes les évaluations.")
            selected_date_str = None

    evaluations_for_display = evaluations_query.order_by('-date', 'course__name')

    grades_data = []
    for evaluation in evaluations_for_display:
        enrollment_for_eval_course = Enrollment.objects.filter(student=student, course=evaluation.course).first()
        grade = None
        if enrollment_for_eval_course:
            grade = Grade.objects.filter(enrollment=enrollment_for_eval_course, evaluation=evaluation).first()

        grades_data.append({
            'evaluation': evaluation,
            'grade_obj': grade,
            'score': grade.score if grade else '',
            'remarks': grade.remarks if grade else '',
            'notation': grade.get_notation() if grade else 'N/A'
        })

    # --- Données pour les Actions Disciplinaires ---
    disciplinary_records = DisciplinaryRecord.objects.filter(student=student).order_by('-created_at')

    # Initialisation du formulaire disciplinaire pour les requêtes GET ou si le POST n'est pas lié
    disciplinary_form = DisciplinaryRecordForm()

    # --- Traitement des POST (Ajout d'évaluation et Saisie/Modification de notes, Ajout Disciplinaire) ---
    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        if action_type == 'add_evaluation':
            name = request.POST.get('name')
            course_id = request.POST.get('course')
            evaluation_type = request.POST.get('evaluation_type')
            date_str = request.POST.get('date')
            max_score = request.POST.get('max_score')
            description = request.POST.get('description')
            academic_period_id = request.POST.get('academic_period')

            try:
                course = teacher_courses_for_this_student.get(id=course_id)
                academic_period = AcademicPeriod.objects.get(id=academic_period_id, school=teacher_user.school)
                date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
                max_score = float(max_score)

                Evaluation.objects.create(
                    name=name,
                    course=course,
                    evaluation_type=evaluation_type,
                    date=date,
                    max_score=max_score,
                    description=description,
                    created_by=teacher_user,
                    academic_period=academic_period
                )
                messages.success(request, "Évaluation ajoutée avec succès.")
            except Course.DoesNotExist:
                messages.error(request, "Cours non trouvé ou non assigné à votre profil pour cet élève.")
            except AcademicPeriod.DoesNotExist:
                messages.error(request, "Période académique non trouvée.")
            except ValueError:
                messages.error(request, "Erreur de format de date ou de score maximum.")
            except Exception as e:
                messages.error(request, f"Erreur lors de l'ajout de l'évaluation : {e}")

        elif action_type == 'save_grade':
            with transaction.atomic():
                grades_saved_count = 0
                grades_deleted_count = 0
                errors_count = 0
                
                for item in grades_data: 
                    evaluation = item['evaluation']
                    
                    score_str = request.POST.get(f'score_{evaluation.id}')
                    remarks = request.POST.get(f'remarks_{evaluation.id}', '').strip()

                    if not evaluation.course.teachers.filter(id=teacher_user.id).exists():
                        messages.warning(request, f"Vous n'êtes pas autorisé à modifier les notes pour l'évaluation '{evaluation.name}'.")
                        errors_count += 1
                        continue

                    enrollment_for_grade = Enrollment.objects.filter(student=student, course=evaluation.course).first()
                    
                    if not enrollment_for_grade:
                        messages.warning(request, f"L'élève n'est pas inscrit au cours de l'évaluation '{evaluation.name}'. Note non enregistrée.")
                        errors_count += 1
                        continue

                    existing_grade = Grade.objects.filter(
                        evaluation=evaluation,
                        enrollment=enrollment_for_grade
                    ).first()

                    if score_str:
                        try:
                            score = float(score_str)
                            if not (0 <= score <= float(evaluation.max_score)):
                                messages.warning(request, f"La note saisie ({score}) est hors des limites ({evaluation.max_score}) pour l'évaluation '{evaluation.name}'.")
                                errors_count += 1
                                continue
                            
                            if existing_grade:
                                existing_grade.score = score
                                existing_grade.remarks = remarks
                                existing_grade.graded_by = teacher_user
                                existing_grade.save()
                                grades_saved_count += 1
                            else:
                                Grade.objects.create(
                                    enrollment=enrollment_for_grade,
                                    evaluation=evaluation,
                                    score=score,
                                    remarks=remarks,
                                    graded_by=teacher_user
                                )
                                grades_saved_count += 1
                        except ValueError:
                            messages.error(request, f"La note saisie pour l'évaluation '{evaluation.name}' n'est pas un nombre valide.")
                            errors_count += 1
                    else:
                        if existing_grade:
                            existing_grade.delete()
                            grades_deleted_count += 1
                
                if grades_saved_count > 0:
                    messages.success(request, f"{grades_saved_count} note(s) enregistrée(s) ou mise(s) à jour avec succès.")
                if grades_deleted_count > 0:
                    messages.info(request, f"{grades_deleted_count} note(s) supprimée(s).")
                if errors_count > 0:
                    messages.error(request, f"Des erreurs sont survenues lors du traitement de {errors_count} note(s).")
                if grades_saved_count == 0 and grades_deleted_count == 0 and errors_count == 0:
                    messages.info(request, "Aucune modification de note à enregistrer.")

        elif action_type == 'add_disciplinary_record':
            disciplinary_form = DisciplinaryRecordForm(request.POST)
            if disciplinary_form.is_valid():
                record = disciplinary_form.save(commit=False)
                record.student = student
                record.reported_by = teacher_user
                record.school = teacher_user.school
                record.save()
                messages.success(request, "Dossier disciplinaire ajouté avec succès.")

                parents = student.parents.all()
                if parents.exists():
                    message_subject = f"Action Disciplinaire concernant votre enfant {student.full_name}"
                    message_body = (
                        f"Cher parent,\n\n"
                        f"Nous vous informons qu'une action disciplinaire a été enregistrée pour votre enfant, {student.full_name}, "
                        f"concernant un incident le {record.incident_date.strftime('%d/%m/%Y')}.\n"
                        f"Description: {record.description}\n"
                        f"Action prise: {record.action_taken}\n\n"
                        f"Veuillez en discuter avec votre enfant.\n\nCordialement,\nVotre école."
                    )
                    for parent_user in parents:
                        Notification.objects.create(
                            recipient=parent_user,
                            sender=teacher_user,
                            subject=message_subject,
                            message=message_body,
                            notification_type='DISCIPLINARY'
                        )
                else:
                    messages.warning(request, f"L'élève {student.full_name} n'a pas de parents liés pour la notification disciplinaire.")

            else:
                messages.error(request, "Erreur lors de l'ajout du dossier disciplinaire. Veuillez vérifier les champs.")
        
        return redirect('profiles:teacher_student_detail', student_id=student.id)

    context = {
        'title': f'Profil de l\'Élève : {student.full_name}',
        'student': student,
        'evaluations_for_student': grades_data,
        'teacher_courses_for_this_student': teacher_courses_for_this_student,
        'academic_periods': academic_periods,
        'evaluation_types': EvaluationType.choices,
        'selected_date_str': selected_date_str,
        'disciplinary_records': disciplinary_records,
        'disciplinary_form': disciplinary_form,
    }
    return render(request, 'profiles/teacher_student_detail.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.TEACHER, login_url='/login/')
def teacher_generate_report_card(request):
    teacher_user = request.user
    if not teacher_user.school:
        messages.error(request, "Votre compte enseignant n'est pas lié à une école.")
        return redirect('profiles:teacher_dashboard')

    # Filtrer les classes et périodes académiques disponibles pour cet enseignant
    # Les classes que cet enseignant enseigne directement
    teacher_classes = Classe.objects.filter(
        Q(teachers=teacher_user) | Q(main_teacher=teacher_user), # Si l'enseignant est dans la ManyToMany ou main_teacher
        school=teacher_user.school,
    ).distinct().order_by('name')

    # Les périodes académiques de son école
    academic_periods = AcademicPeriod.objects.filter(school=teacher_user.school).order_by('-start_date')

    selected_class_id = request.GET.get('class_id')
    selected_period_id = request.GET.get('period_id')

    students_with_grades = []
    selected_class = None
    selected_period = None

    if selected_class_id and selected_period_id:
        try:
            selected_class = get_object_or_404(Classe, id=selected_class_id, school=teacher_user.school)
            selected_period = get_object_or_404(AcademicPeriod, id=selected_period_id, school=teacher_user.school)

            # Vérifier si l'enseignant est bien associé à cette classe ou à un cours de cette classe
            if not (selected_class in teacher_classes):
                 messages.error(request, "Vous n'êtes pas autorisé à générer le bulletin pour cette classe.")
                 return redirect('profiles:teacher_generate_report_card')

            # Récupérer les élèves inscrits à cette classe pour cette période
            students_in_class = Student.objects.filter(
                current_classe=selected_class,
                enrollment__academic_period=selected_period,
                school=teacher_user.school
            ).distinct().order_by('last_name', 'first_name')

            for student in students_in_class:
                student_grades_info = {
                    'student': student,
                    'courses_grades': [],
                    'total_score': 0,
                    'total_max_score': 0,
                    'overall_average': 'N/A'
                }

                # Récupérer les inscriptions de cet élève pour cette période
                enrollments = Enrollment.objects.filter(
                    student=student,
                    academic_period=selected_period,
                    course__classes=selected_class # Assurez-vous que l'inscription est pour un cours de cette classe
                ).select_related('course').order_by('course__name')

                for enrollment in enrollments:
                    # Récupérer toutes les notes pour cette inscription dans cette période
                    grades = Grade.objects.filter(
                        enrollment=enrollment,
                        evaluation__academic_period=selected_period # Assurez-vous que l'évaluation est dans la bonne période
                    ).select_related('evaluation').order_by('evaluation__date')

                    course_total_score = sum(g.score for g in grades if g.score is not None)
                    course_max_possible_score = sum(g.evaluation.max_score for g in grades)

                    course_avg = 'N/A'
                    if course_max_possible_score > 0:
                        course_avg = (course_total_score / course_max_possible_score) * 100 # Pourcentage
                        course_avg = round(course_avg, 2) # Arrondi à 2 décimales

                    student_grades_info['courses_grades'].append({
                        'course': enrollment.course,
                        'grades': grades, # Détails des notes individuelles pour ce cours
                        'course_total_score': course_total_score,
                        'course_max_possible_score': course_max_possible_score,
                        'course_average': course_avg,
                    })
                    
                    # Accumuler pour la moyenne générale
                    student_grades_info['total_score'] += course_total_score
                    student_grades_info['total_max_score'] += course_max_possible_score

                if student_grades_info['total_max_score'] > 0:
                    student_grades_info['overall_average'] = round((student_grades_info['total_score'] / student_grades_info['total_max_score']) * 100, 2)
                
                students_with_grades.append(student_grades_info)

        except (Classe.DoesNotExist, AcademicPeriod.DoesNotExist):
            messages.error(request, "Classe ou période académique non trouvée.")
        except Exception as e:
            messages.error(request, f"Une erreur inattendue s'est produite lors de la génération du bulletin : {e}")

    context = {
        'title': 'Générer les Bulletins Scolaires',
        'teacher_classes': teacher_classes,
        'academic_periods': academic_periods,
        'selected_class_id': int(selected_class_id) if selected_class_id else None,
        'selected_period_id': int(selected_period_id) if selected_period_id else None,
        'selected_class': selected_class,
        'selected_period': selected_period,
        'students_with_grades': students_with_grades,
    }
    return render(request, 'profiles/teacher_generate_report_card.html', context)
# profiles/views.py



# ... (vos autres imports et fonctions) ...


# Nouveau formulaire pour l'envoi de messages
class TeacherMessageForm(forms.Form):
    # Les choix pour les destinataires seront définis dynamiquement dans _init_
    recipients = forms.MultipleChoiceField(
        widget=CheckboxSelectMultiple,
        label="Sélectionner les parents destinataires",
        required=True # Rendu False si "envoyer à tous" est coché
    )
    
    subject = forms.CharField(max_length=255, label="Objet du message")
    message_body = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}), label="Contenu du message")
    
    send_to_all_in_course = forms.BooleanField(
        label="Envoyer à tous les parents du cours sélectionné",
        required=False,
        initial=False
    )
    
    # Champ caché pour le cours sélectionné
    course = forms.ModelChoiceField(
        queryset=Course.objects.none(), # Sera rempli dynamiquement
        required=True,
        widget=forms.HiddenInput()
    )

    def __init__(self, *args, **kwargs):
        teacher_user = kwargs.pop('teacher_user', None)
        selected_course_id = kwargs.pop('selected_course_id', None)
        super().__init__(*args, **kwargs)

        if teacher_user and selected_course_id:
            try:
                selected_course = Course.objects.filter(
                    id=selected_course_id,
                    teachers=teacher_user,
                    school=teacher_user.school
                ).first()

                if selected_course:
                    self.fields['course'].queryset = Course.objects.filter(id=selected_course.id)
                    self.fields['course'].initial = selected_course.id

                    # Obtenir tous les élèves inscrits à ce cours et leurs parents
                    student_enrollments = Enrollment.objects.filter(course=selected_course).select_related('student')
                    
                    parent_choices = []
                    unique_parent_ids = set() # Pour éviter les doublons si un parent a plusieurs enfants dans le même cours

                    for enrollment in student_enrollments:
                        for parent_obj in enrollment.student.parents.all():
                            if parent_obj.id not in unique_parent_ids:
                                parent_choices.append((str(parent_obj.id), parent_obj.full_name))
                                unique_parent_ids.add(parent_obj.id)
                    
                    # Trier les choix par nom de parent
                    parent_choices.sort(key=lambda x: x[1])
                    self.fields['recipients'].choices = parent_choices
                else:
                    self.add_error(None, "Cours sélectionné non valide ou non accessible.")
            except Exception as e:
                self.add_error(None, f"Erreur lors du chargement des destinataires: {e}")
                print(f"Error loading message recipients: {e}") # For debugging
        else:
            # Si aucun cours sélectionné, désactiver le champ recipients
            self.fields['recipients'].choices = []
            self.fields['recipients'].widget.attrs['disabled'] = True


@login_required
@user_passes_test(lambda u: u.user_type == UserRole.TEACHER, login_url='/login/')
def teacher_message_view(request):
    teacher_user = request.user
    if not teacher_user.school:
        messages.error(request, "Votre compte enseignant n'est pas lié à une école.")
        return redirect('profiles:teacher_dashboard')

    teacher_courses = Course.objects.filter(teachers=teacher_user, school=teacher_user.school).order_by('name')
    
    selected_course_id = request.GET.get('course_id') # Pour la sélection initiale du cours
    selected_course = None
    if selected_course_id:
        try:
            selected_course = teacher_courses.get(id=selected_course_id)
        except Course.DoesNotExist:
            messages.error(request, "Cours non trouvé ou non accessible.")
            selected_course_id = None # Réinitialiser si invalide

    form = None
    if selected_course:
        if request.method == 'POST':
            form = TeacherMessageForm(request.POST, teacher_user=teacher_user, selected_course_id=selected_course.id)
            if form.is_valid():
                subject = form.cleaned_data['subject']
                message_body = form.cleaned_data['message_body']
                send_to_all = form.cleaned_data['send_to_all_in_course']
                
                recipients_ids = []
                if send_to_all:
                    # Si "Envoyer à tous", obtenir tous les parents des élèves du cours
                    enrollments = Enrollment.objects.filter(course=selected_course).select_related('student')
                    for enrollment in enrollments:
                        for parent_obj in enrollment.student.parents.all():
                            recipients_ids.append(parent_obj.id)
                    recipients_ids = list(set(recipients_ids)) # Éliminer les doublons de parents
                else:
                    # Sinon, utiliser les destinataires sélectionnés du formulaire
                    recipients_ids = form.cleaned_data['recipients']

                if not recipients_ids:
                    messages.warning(request, "Veuillez sélectionner au moins un parent ou choisir d'envoyer à tous.")
                else:
                    try:
                        with transaction.atomic():
                            for parent_id in recipients_ids:
                                parent_user = get_object_or_404(CustomUser, id=parent_id, user_type=UserRole.PARENT)
                                Notification.objects.create(
                                    recipient=parent_user,
                                    sender=teacher_user,
                                    subject=subject,
                                    message=message_body,
                                    notification_type='MESSAGE' # Ou un autre type si vous en avez un pour les messages génériques
                                )
                        messages.success(request, f"Message envoyé avec succès à {len(recipients_ids)} parent(s).")
                        return redirect('profiles:send_message') # Recharger la page avec le cours sélectionné
                    except Exception as e:
                        messages.error(request, f"Une erreur est survenue lors de l'envoi du message : {e}")
                        # Re-instantiate form in case of error
                        form = TeacherMessageForm(teacher_user=teacher_user, selected_course_id=selected_course.id)
            else:
                messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
                # Si le formulaire n'est pas valide, il faut le réinstancier avec les données POST pour afficher les erreurs
                form = TeacherMessageForm(request.POST, teacher_user=teacher_user, selected_course_id=selected_course.id)
        else:
            # GET request or initial load after POST redirect
            form = TeacherMessageForm(teacher_user=teacher_user, selected_course_id=selected_course.id)
    else:
        # Si aucun cours n'est sélectionné, initialiser un formulaire vide (ou null)
        form = None


    context = {
        'title': 'Messagerie Enseignant-Parents',
        'teacher_courses': teacher_courses,
        'selected_course_id': int(selected_course_id) if selected_course_id else None,
        'form': form,
        'selected_course': selected_course,
    }
    return render(request, 'profiles/teacher_message.html', context) # Changement de template name ici
# ... (autres imports)

@require_POST
@login_required
def check_parent_email_ajax(request):
    data = json.loads(request.body)
    email = data.get('email')
    school = request.user.school # Pour filtrer par école si nécessaire

    if email:
        try:
            parent_user = CustomUser.objects.get(
                email=email, 
                user_type=UserRole.PARENT,
                school=school # Filtrage optionnel
            )
            return JsonResponse({
                'exists': True,
                'full_name': parent_user.full_name,
                'first_name': parent_user.first_name,
                'last_name': parent_user.last_name,
                'phone_number': parent_user.phone_number,
                'address': parent_user.address, # Si ces champs sont sur CustomUser
            })
        except CustomUser.DoesNotExist:
            return JsonResponse({'exists': False})
    return JsonResponse({'error': 'Email non fourni'}, status=400)

# profiles/views.py (là où vous avez défini ExistingParentForm)
from django import forms
from django_select2 import forms as s2forms # Importez Select2 forms

# ... votre modèle CustomUser et UserRole

class ExistingParentWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        'first_name__icontains',
        'last_name__icontains',
        'email__icontains',
        # Ajoutez d'autres champs sur lesquels vous voulez chercher, ex:
        # 'phone_number__icontains',
    ]
    # Si vous voulez afficher le nom complet dans la liste de résultats
    def label_from_instance(self, obj):
        return f"{obj.first_name} {obj.last_name} ({obj.email})"


# profiles/views.py ou profiles/forms.py (si vous déplacez le formulaire là)

# Assurez-vous d'importer forms
# Vos modèles

# Formulaire pour choisir un parent existant (simplifié pour JS)


def search_parents_ajax(request):
    term = request.GET.get('term', '')
    user_school = request.user.school

    if not user_school:
        return JsonResponse([], safe=False)

    # Appel de filter() corrigé : l'objet Q comme premier argument positionnel
    parents_found = CustomUser.objects.filter(
        Q(first_name__icontains=term) |
        Q(last_name__icontains=term) |
        Q(email__icontains=term),  # <-- Notez la virgule ici, après l'objet Q combiné
        user_type=UserRole.PARENT,
        school=user_school
    ).values('id', 'first_name', 'last_name')

    results = []
    for parent in parents_found:
        results.append({
            'id': parent['id'],
            'text': f"{parent['first_name']} {parent['last_name']}"
        })
    return JsonResponse(results, safe=False)

@login_required
@user_passes_test(is_direction, login_url='/login/') # Assurez-vous que 'login_url' est correct
def add_student_view(request):
    user_school = request.user.school

    if not user_school:
        messages.error(request, "Votre compte n'est affilié à aucune école. Veuillez contacter un administrateur.")
        # Rediriger vers une page d'erreur ou d'accueil appropriée
        return redirect('some_error_page') # Remplacez 'some_error_page' par une URL valide

    # Instanciation initiale des formulaires pour la requête GET ou le rendu initial
    # TOUTES les instanciations reçoivent user_school ici
    student_form = StudentForm(user_school=user_school, prefix='student')
    parent_creation_form = ParentCreationForm(user_school=user_school, prefix='new_parent')
    existing_parent_form = ExistingParentForm(user_school=user_school, prefix='existing_parent')

    # Définir l'onglet actif par défaut pour la requête GET
    active_tab = 'create_new'

    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        student_form = StudentForm(request.POST, request.FILES, user_school=user_school, prefix='student')

        # Instanciation conditionnelle des formulaires parent avec les données POST ou en tant que formulaires vides
        if action_type == 'select_existing':
            existing_parent_form = ExistingParentForm(request.POST, user_school=user_school, prefix='existing_parent')
            # Le formulaire de création est vide si on sélectionne un parent existant
            parent_creation_form = ParentCreationForm(user_school=user_school, prefix='new_parent')
            active_tab = 'select_existing' # Maintenir l'onglet actif
        elif action_type == 'create_new':
            parent_creation_form = ParentCreationForm(request.POST, user_school=user_school, prefix='new_parent')
            # Le formulaire existant est vide si on crée un nouveau parent
            existing_parent_form = ExistingParentForm(user_school=user_school, prefix='existing_parent')
            active_tab = 'create_new' # Maintenir l'onglet actif
        else:
            # Cas où aucun type d'action valide n'est sélectionné (par ex. si JS ne l'a pas envoyé)
            messages.error(request, "Veuillez choisir de sélectionner un parent existant ou d'en créer un nouveau.")
            # Assurez-vous que tous les formulaires sont passés au contexte, y compris user_school
            context = {
                'student_form': student_form,
                'parent_creation_form': ParentCreationForm(user_school=user_school, prefix='new_parent'),
                'existing_parent_form': ExistingParentForm(user_school=user_school, prefix='existing_parent'),
                'title': "Ajouter un Nouvel Élève et son Parent",
                'active_tab': active_tab # Restaure l'onglet actif (par défaut ou celui qui était censé être)
            }
            return render(request, 'profiles/add_student.html', context)

        # Procéder à la validation et à la sauvegarde
        if student_form.is_valid():
            try:
                with transaction.atomic():
                    parent_to_link = None # Initialiser à None

                    if action_type == 'select_existing':
                        if existing_parent_form.is_valid():
                            parent_to_link = existing_parent_form.cleaned_data.get('parent_id')
                            messages.info(request, f"Parent existant ({parent_to_link.full_name}) sélectionné.")
                        else:
                            messages.error(request, "Erreur lors de la sélection du parent existant.")
                            # Rendre le template avec les erreurs du formulaire existant
                            context = {
                                'student_form': student_form,
                                'parent_creation_form': parent_creation_form, # Formulaire de création vide
                                'existing_parent_form': existing_parent_form, # Formulaire existant avec erreurs
                                'title': "Ajouter un Nouvel Élève et son Parent",
                                'active_tab': active_tab
                            }
                            return render(request, 'profiles/add_student.html', context)

                    elif action_type == 'create_new':
                        if parent_creation_form.is_valid():
                            parent_user = parent_creation_form.save(commit=False)
                            parent_user.school = user_school
                            parent_user.user_type = UserRole.PARENT
                            parent_user.save()
                            parent_to_link = parent_user
                            messages.success(request, f"Nouveau parent ({parent_to_link.full_name}) créé.")
                        else:
                            messages.error(request, "Veuillez corriger les erreurs dans le formulaire de création du parent.")
                            # Rendre le template avec les erreurs du formulaire de création
                            context = {
                                'student_form': student_form,
                                'parent_creation_form': parent_creation_form, # Formulaire de création avec erreurs
                                'existing_parent_form': existing_parent_form, # Formulaire existant vide
                                'title': "Ajouter un Nouvel Élève et son Parent",
                                'active_tab': active_tab
                            }
                            return render(request, 'profiles/add_student.html', context)

                    # Si un parent a été sélectionné ou créé avec succès
                    if parent_to_link:
                        student = student_form.save(commit=False)
                        student.school = user_school
                        student.save()
                        student.parents.add(parent_to_link) # Lier l'élève au parent

                        messages.success(request, f"L'élève {student.full_name} a été ajouté avec succès et lié au parent {parent_to_link.full_name}.")
                        return redirect('profiles:list_students') # Redirigez vers la liste des élèves
                    else:
                        # Cas où le parent_to_link est toujours None (logique impossible si les validations ci-dessus sont strictes)
                        messages.error(request, "Impossible de lier l'élève : aucun parent valide n'a été trouvé ou créé.")
                        context = {
                            'student_form': student_form,
                            'parent_creation_form': parent_creation_form,
                            'existing_parent_form': existing_parent_form,
                            'title': "Ajouter un Nouvel Élève et son Parent",
                            'active_tab': active_tab
                        }
                        return render(request, 'profiles/add_student.html', context)

            except Exception as e:
                # Log l'erreur pour le débogage serveur
                logger.exception("Une erreur inattendue s'est produite lors de l'ajout de l'élève et du parent.")
                messages.error(request, f"Une erreur inattendue s'est produite : {e}")
                # Assurez-vous que les formulaires sont correctement passés au contexte en cas d'exception
                context = {
                    'student_form': student_form,
                    'parent_creation_form': parent_creation_form,
                    'existing_parent_form': existing_parent_form,
                    'title': "Ajouter un Nouvel Élève et son Parent",
                    'active_tab': active_tab
                }
                return render(request, 'profiles/add_student.html', context)
        else: # student_form n'est pas valide
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire de l'élève.")
            # Les formulaires de parent (parent_creation_form, existing_parent_form)
            # conservent leurs données et erreurs s'ils ont été instanciés avec request.POST.
            # Sinon, ils sont déjà instanciés vides avec user_school.
            context = {
                'student_form': student_form,
                'parent_creation_form': parent_creation_form,
                'existing_parent_form': existing_parent_form,
                'title': "Ajouter un Nouvel Élève et son Parent",
                'active_tab': active_tab
            }
            return render(request, 'profiles/add_student.html', context)
    else: # Requête GET (affichage initial du formulaire)
        context = {
            'student_form': student_form,
            'parent_creation_form': parent_creation_form,
            'existing_parent_form': existing_parent_form,
            'title': "Ajouter un Nouvel Élève et son Parent",
            'active_tab': active_tab # Par défaut, 'create_new'
        }
        return render(request, 'profiles/add_student.html', context)


def send_notification_to_user(recipient_user, subject, message_body, email_template, context, attachments=None):
    print(f"Envoi d'email à {recipient_user.email}: {subject}")
    # Simuler l'envoi d'email
    if attachments:
        for path, name, mime in attachments:
            print(f"  Avec pièce jointe: {name} de {path}")
# Fonctions de test pour les permissions (à réutiliser)
def is_admin(user):
    return user.is_authenticated and user.user_type == UserRole.ADMIN

def is_accountant(user):
    return user.is_authenticated and user.user_type == UserRole.ACCOUNTANT

def is_direction(user):
    return user.is_authenticated and user.user_type == UserRole.DIRECTION

# Rôle pour l'accès aux fonctionnalités financières (Comptable, Direction, Admin)
def can_access_accounting(user):
    return user.is_authenticated and user.user_type in [UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.DIRECTION]

class PaymentCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'profiles/payment_create.html'
    success_url = reverse_lazy('profiles:accounting_dashboard')

    def test_func(self):
        return self.request.user.user_type in [UserRole.ACCOUNTANT, UserRole.DIRECTION, UserRole.ADMIN]

    def get_form_kwargs(self):
        # Cette méthode est appelée AVANT get_form pour préparer les arguments du formulaire
        kwargs = super().get_form_kwargs()
        user = self.request.user
        current_school = user.school if hasattr(user, 'school') else None
        
        if not current_school:
            messages.error(self.request, "Vous n'êtes associé à aucune école.")
            # Si vous utilisez Http404 ici, assurez-vous de l'importer de django.http
            raise Http404("No school associated with user.") 

        kwargs['school_id'] = current_school.id
        kwargs['user'] = user
        return kwargs

    # --- NOUVELLE MÉTHODE get_form POUR L'INITIALISATION DE L'ÉLÈVE ---
    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class() # Récupère le PaymentForm
        
        # Récupère les arguments préparés par get_form_kwargs
        kwargs = self.get_form_kwargs()

        # Récupérer l'ID de l'élève depuis les paramètres GET de l'URL
        student_id = self.request.GET.get('student_id')
        
        if student_id:
            try:
                current_school = kwargs['school_id'] # Récupère school_id de kwargs
                # Il faut l'objet School, pas seulement l'ID, pour la requête Student.objects.get
                school_obj = School.objects.get(id=current_school) 
                selected_student = Student.objects.get(id=student_id, school=school_obj)
                kwargs['initial'] = {'student': selected_student} # Définit l'initial pour le champ 'student'
            except Student.DoesNotExist:
                messages.warning(self.request, "L'élève spécifié n'existe pas ou n'appartient pas à votre école.")
            except School.DoesNotExist: # Au cas où school_id de kwargs serait invalide
                messages.error(self.request, "Erreur interne: École associée à l'utilisateur introuvable.")
                raise Http404("School not found for user.")
        
        return form_class(**kwargs) # Crée et retourne l'instance du formulaire

    # --- Pas de changement dans form_valid, form_invalid, et get_context_data (sauf si vous aviez des lignes spécifiques pour le formulaire) ---
    def form_valid(self, form):
        user = self.request.user
        current_school = user.school
        
        try:
            active_period = AcademicPeriod.objects.get(school=current_school, is_current=True)
        except AcademicPeriod.DoesNotExist:
            messages.error(self.request, "Aucune période académique active définie pour votre école. Impossible d'enregistrer le paiement.")
            return self.form_invalid(form)

        with transaction.atomic():
            payment = form.save(commit=False)
            payment.academic_period = active_period
            payment.recorded_by = user

            while True:
                receipt_number = f"REC-{uuid.uuid4().hex[:8].upper()}"
                if not Payment.objects.filter(receipt_number=receipt_number).exists():
                    payment.receipt_number = receipt_number
                    break
            
            payment.save()
            messages.success(self.request, f"Paiement de {payment.amount_paid}$ enregistré avec succès ! Reçu #{payment.receipt_number}")

            try:
                # 1. Appeler votre fonction qui génère le PDF dans le dossier temporaire
                pdf_path = generate_receipt_pdf(payment) # Cette fonction doit retourner le chemin COMPLET du fichier généré (ex: C:\...\temp_receipts\REC-XYZ.pdf)

                print(f"DEBUG: PDF généré à l'emplacement temporaire : {pdf_path}")
                if not os.path.exists(pdf_path):
                    raise FileNotFoundError(f"Le fichier PDF n'a pas été trouvé à {pdf_path} après génération.")
                print(f"DEBUG: Taille du fichier PDF temporaire : {os.path.getsize(pdf_path)} octets")

                # 2. Ouvrir le fichier PDF temporaire en mode binaire lecture
                with open(pdf_path, 'rb') as pdf_file_handle:
                    file_content_bytes = pdf_file_handle.read()
                    
                    # 3. Sauvegarder le contenu du fichier dans le FileField de Django
                    #    C'est cette ligne qui fait le travail de copier le fichier
                    #    dans MEDIA_ROOT/receipts/ (ou l'upload_to de votre FileField)
                    #    et de mettre à jour le chemin dans l'objet 'payment'.
                    django_filename = os.path.basename(pdf_path) # Récupère juste le nom du fichier (ex: 'receipt_REC-xxx.pdf')
                    payment.receipt_file.save(django_filename, ContentFile(file_content_bytes))
                    
                    # NOTE IMPORTANTE : Après payment.receipt_file.save(), vous n'avez PLUS besoin de faire payment.save()
                    # Si vous faites payment.save(update_fields=['receipt_file']), cela ne fera que resauvegarder l'objet
                    # en base de données avec le chemin mis à jour PAR la méthode .save() du FileField.
                    # Le .save() du FileField met déjà à jour l'instance du modèle et la base de données.
                    # Cependant, pour être sûr, on peut laisser le payment.save() après si d'autres champs doivent être mis à jour,
                    # ou si on veut s'assurer que le chemin est bien persistant.
                    # Dans ce cas, comme le save() du FileField est sensé faire le travail, on peut le supprimer si rien d'autre n'est à updater.
                    # Si vous l'aviez après votre première génération de payment.save(), il est superflu,
                    # mais il ne fait pas de mal s'il n'y a pas de problème de performance.
                    # La ligne importante était d'appeler payment.receipt_file.save() avec ContentFile.

                print(f"DEBUG: Fichier PDF sauvegardé dans le FileField de Django.")
                print(f"DEBUG: Chemin final du fichier dans MEDIA_ROOT : {payment.receipt_file.path}")
                print(f"DEBUG: URL pour le téléchargement : {payment.receipt_file.url}")
                print(f"DEBUG: Le fichier existe-t-il physiquement dans MEDIA_ROOT après l'opération ? {os.path.exists(payment.receipt_file.path)}")

                # IMPORTANT pour le comptable :
                # Si le comptable doit conserver une copie dans C:\Users\user\school_project\temp_receipts\,
                # NE PAS supprimer le fichier ici.
                # Sinon, si ce dossier n'est qu'un temporaire, vous pouvez le supprimer :
                # if os.path.exists(pdf_path):
                #     os.remove(pdf_path)
                #     print(f"DEBUG: Fichier temporaire supprimé : {pdf_path}")
                # Comme vous avez dit que le comptable doit rester avec une copie,
                # nous laissons le fichier dans temp_receipts_root.

                # ... (le reste de votre code pour l'envoi d'email, etc.)
                # Assurez-vous que l'attachement dans send_notification_to_user utilise le chemin TEMPORAIRE,
                # car le fichier est encore là pour cet envoi.
                # attachments=[(pdf_path, f"Reçu_{payment.receipt_number}.pdf", 'application/pdf')]
                # C'est parfait, vous utilisez déjà `pdf_path` pour l'attachement, ce qui est correct.

                student = payment.student
                if student.parents.exists():
                    for parent_user in student.parents.all():
                        email_subject = f"Reçu de paiement pour {student.full_name} - {payment.receipt_number}"
                        email_context = {
                            'student_name': student.full_name,
                            'amount_paid': payment.amount_paid,
                            'payment_date': payment.payment_date,
                            'receipt_number': payment.receipt_number,
                            'fee_type_name': payment.fee_type.name if payment.fee_type else 'Frais',
                            'school_name': current_school.name,
                            'parent_name': parent_user.full_name,
                        }
                        send_notification_to_user(
                            recipient_user=parent_user,
                            subject=email_subject,
                            message_body=f"Veuillez trouver ci-joint le reçu pour le paiement de {payment.amount_paid}$ pour {student.full_name}.",
                            email_template='school/receipt_email_template.html',
                            context=email_context,
                            attachments=[(pdf_path, f"Reçu_{payment.receipt_number}.pdf", 'application/pdf')]
                        )
                    messages.info(self.request, "Reçu PDF généré et envoyé aux parents.")
                else:
                    messages.warning(self.request, "Aucun parent n'est lié à cet élève pour l'envoi du reçu.")

            except Exception as e:
                import logging
                logger = logging.getLogger(__name__) # Assurez-vous d'avoir un logger configuré
                logger.error(f"Erreur lors de la génération ou l'envoi du reçu pour le paiement {payment.id}: {e}", exc_info=True)
                messages.error(self.request, f"Paiement enregistré, mais erreur lors de la génération ou l'envoi du reçu : {e}")
                if os.path.exists(pdf_path):
                     os.remove(pdf_path)

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Erreur lors de l'enregistrement du paiement. Veuillez vérifier les informations.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        current_school = user.school if hasattr(user, 'school') else None
        
        context['title'] = "Enregistrer un Nouveau Paiement"
        context['current_school'] = current_school

        # Récupérer l'élève sélectionné pour l'afficher au-dessus du formulaire si besoin
        student_id = self.request.GET.get('student_id')
        if student_id:
            try:
                # Récupère l'objet School
                school_obj = School.objects.get(id=current_school.id) 
                selected_student = Student.objects.get(id=student_id, school=school_obj)
                context['selected_student'] = selected_student
            except (Student.DoesNotExist, School.DoesNotExist):
                messages.warning(self.request, "L'élève spécifié n'existe pas ou n'appartient pas à votre école.")
        
        # Le formulaire est maintenant géré par get_form, pas besoin de le recréer ici
        return context

class AccountingDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'profiles/accounting_dashboard.html'

    def test_func(self):
        # Autoriser l'accès uniquement aux ADMIN, ACCOUNTANT, DIRECTION
        return self.request.user.user_type in [UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.DIRECTION]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # --- DÉBUT DES LIGNES DE DÉBOGAGE ---
        print(f"\n--- DÉBUT DÉBOGAGE AccountingDashboardView.get_context_data ---")
        print(f"DEBUG: Utilisateur connecté: {user.username} (ID: {user.id}), Type: {user.user_type}")
        # --- FIN DES LIGNES DE DÉBOGAGE ---

        current_school = user.school if hasattr(user, 'school') else None
        context['current_school'] = current_school

        # --- DÉBUT DES LIGNES DE DÉBOGAGE ---
        print(f"DEBUG: École de l'utilisateur: {current_school.name if current_school else 'AUCUNE ÉCOLE'}")
        # --- FIN DES LIGNES DE DÉBOGAGE ---

        if current_school:
            try:
                active_period = AcademicPeriod.objects.get(school=current_school, is_current=True)
            except AcademicPeriod.DoesNotExist:
                active_period = AcademicPeriod.objects.filter(school=current_school).order_by('-start_date').first()

            if not active_period:
                messages.warning(self.request, "Aucune période académique active ou définie pour votre école.")
                # --- DÉBUT DES LIGNES DE DÉBOGAGE ---
                print("DEBUG: Aucune période académique active trouvée pour l'école.")
                print(f"--- FIN DÉBOGAGE AccountingDashboardView.get_context_data (early exit) ---")
                # --- FIN DES LIGNES DE DÉBOGAGE ---
                return context

            context['active_period'] = active_period
            # --- DÉBUT DES LIGNES DE DÉBOGAGE ---
            print(f"DEBUG: Période académique active: {active_period.name} (ID: {active_period.id})")
            # --- FIN DES LIGNES DE DÉBOGAGE ---
            
            # --- Formulaires ---
            context['payment_form'] = PaymentForm(school_id=current_school.id, user=user)
            context['tuition_fee_form'] = TuitionFeeForm(school_id=current_school.id)
            context['fee_type_form'] = FeeTypeForm() # Pour créer de nouveaux intitulés de frais

            # --- Calculs Généraux ---
            payments_in_period = Payment.objects.filter(academic_period=active_period, student__school=current_school)
            total_paid_for_school = payments_in_period.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
            context['total_paid_for_school'] = total_paid_for_school

            expected_fees_by_classe = TuitionFee.objects.filter(
                academic_period=active_period,
                classe__school=current_school
            ).values('classe').annotate(
                total_amount_per_classe=Sum('amount')
            )

            total_expected_for_school = 0
            for item in expected_fees_by_classe:
                classe_id = item['classe']
                fees_for_this_classe = item['total_amount_per_classe']
                num_students_in_class = Student.objects.filter(
                    current_classe_id=classe_id,
                    academic_period=active_period,
                    school=current_school
                ).count()
                total_expected_for_school += (fees_for_this_classe * num_students_in_class)

            context['total_expected_for_school'] = total_expected_for_school
            context['remaining_balance_for_school'] = total_expected_for_school - total_paid_for_school

            # --- Détails par Type de Frais ---
            payments_by_fee_type = payments_in_period \
                                .values('fee_type__name') \
                                .annotate(total=Sum('amount_paid')) \
                                .order_by('fee_type__name')
            context['payments_by_fee_type'] = payments_by_fee_type

            # --- Statut des Paiements par Élève AVEC FILTRAGE ---
            student_payment_status = [] # Ceci sera la liste finale pour le contexte du template

            # Récupérer la classe sélectionnée depuis les paramètres GET
            context['classes'] = Classe.objects.filter(school=current_school).order_by('name')
            selected_class_id = self.request.GET.get('class_id')
            
            # --- DÉBUT DES LIGNES DE DÉBOGAGE POUR LE FILTRE DE CLASSE ---
            print(f"DEBUG: selected_class_id brut (depuis GET): '{selected_class_id}'")
            # --- FIN DES LIGNES DE DÉBOGAGE POUR LE FILTRE DE CLASSE ---

            context['selected_class_id'] = int(selected_class_id) if selected_class_id else None
            
            # --- DÉBUT DES LIGNES DE DÉBOGAGE POUR LE FILTRE DE CLASSE ---
            print(f"DEBUG: selected_class_id converti (int ou None): {context['selected_class_id']}")
            # --- FIN DES LIGNES DE DÉBOGAGE POUR LE FILTRE DE CLASSE ---

            # Construction de la requête de base pour les élèves, AVANT d'appliquer le filtre de classe
            # C'est cette requête qui doit retourner des résultats si des élèves existent dans l'école et la période active
            base_students_query = Student.objects.filter(
                school=current_school,
                #academic_period=active_period
            ).select_related('current_classe', 'user_account', 'school','academic_period').prefetch_related('parents')

            # --- DÉBUT DES LIGNES DE DÉBOGAGE ---
            print(f"DEBUG: Nombre d'élèves dans la requête de base (tous élèves de la période active SANS filtre de classe): {base_students_query.count()}")
            # --- FIN DES LIGNES DE DÉBOGAGE ---

            # La liste des élèves à traiter (soit tous, soit ceux d'une classe spécifique)
            students_to_process = base_students_query 

            if selected_class_id:
                try:
                    selected_class_instance = Classe.objects.get(id=selected_class_id, school=current_school)
                    students_to_process = base_students_query.filter(current_classe=selected_class_instance)
                    # --- DÉBUT DES LIGNES DE DÉBOGAGE ---
                    print(f"DEBUG: Classe sélectionnée trouvée: '{selected_class_instance.name}' (ID: {selected_class_instance.id})")
                    print(f"DEBUG: Nombre d'élèves après application du filtre de classe: {students_to_process.count()}")
                    # --- FIN DES LIGNES DE DÉBOGAGE ---
                except Classe.DoesNotExist:
                    messages.warning(self.request, "La classe sélectionnée n'existe pas ou n'appartient pas à votre école. Affichage de tous les élèves.")
                    # students_to_process reste base_students_query car l'ID était invalide.
                    # --- DÉBUT DES LIGNES DE DÉBOGAGE ---
                    print(f"DEBUG: ERREUR: Classe sélectionnée (ID: {selected_class_id}) introuvable ou n'appartient pas à l'école. Revert à tous les élèves de la période active.")
                    # --- FIN DES LIGNES DE DÉBOGAGE ---
            else:
                # --- DÉBUT DES LIGNES DE DÉBOGAGE ---
                print(f"DEBUG: Pas de classe sélectionnée. Traitement de tous les élèves de la période active (non filtrés).")
                # --- FIN DES LIGNES DE DÉBOGAGE ---

            # --- DÉBUT DES LIGNES DE DÉBOGAGE ---
            print(f"DEBUG: Début de la boucle pour construire student_payment_status. Itérant sur {students_to_process.count()} élèves.")
            # --- FIN DES LIGNES DE DÉBOGAGE ---

            # Boucle pour calculer le statut de paiement pour CHAQUE élève dans students_to_process
            for student in students_to_process:
                # Montant total des frais que cet élève doit
                fees_due_for_student = TuitionFee.objects.filter(
                    academic_period=active_period,
                    classe=student.current_classe,
                    fee_type__school=current_school # Les types de frais doivent aussi être liés à l'école ou globaux
                ).aggregate(Sum('amount'))['amount__sum'] or 0

                # Montant total payé par cet élève
                amount_paid_by_student = Payment.objects.filter(
                    academic_period=active_period,
                    student=student
                ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0

                remaining_balance = fees_due_for_student - amount_paid_by_student
                
                status_text = "À Jour"
                status_class = "status-paid"
                if remaining_balance > 0:
                    status_text = "Dû"
                    status_class = "status-due"
                elif remaining_balance < 0:
                    status_text = "Trop Payé"
                    status_class = "status-overpaid"

                # Récupérer les parents liés à cet élève
                parents_list = list(student.parents.all())
                
                student_payment_status.append({
                    'student': student,
                    'fees_due': fees_due_for_student,
                    'amount_paid': amount_paid_by_student,
                    'remaining_balance': remaining_balance,
                    'status_text': status_text,
                    'status_class': status_class,
                    'parents': parents_list
                })
            
            context['student_payment_status'] = sorted(student_payment_status, key=lambda x: x['remaining_balance'], reverse=True)

            # --- DÉBUT DES LIGNES DE DÉBOGAGE ---
            print(f"DEBUG: Nombre final d'éléments dans context['student_payment_status'] (pour le tableau): {len(context['student_payment_status'])}")
            # --- FIN DES LIGNES DE DÉBOGAGE ---


            # NOTE: La variable 'students_in_selected_class' est maintenant redondante
            # si vous utilisez toujours 'student_payment_status' pour votre tableau principal.
            # Cependant, si une autre partie de votre template l'utilise, vous pouvez la garder
            # en la définissant comme ceci :
            context['students_in_selected_class'] = students_to_process.order_by('last_name', 'first_name')
            
            # --- Frais de scolarité définis ---
            context['tuition_fees_set'] = TuitionFee.objects.filter(
                academic_period=active_period,
                classe__school=current_school
            ).select_related('classe', 'academic_period', 'set_by', 'fee_type').order_by('classe__name', 'fee_type__name')

            # --- Derniers paiements ---
            context['payments_list'] = payments_in_period.select_related('student', 'academic_period', 'recorded_by', 'fee_type').order_by('-payment_date')[:20]

        # --- DÉBUT DES LIGNES DE DÉBOGAGE DE FIN ---
        print(f"--- FIN DÉBOGAGE AccountingDashboardView.get_context_data ---")
        # --- FIN DES LIGNES DE DÉBOGAGE DE FIN ---
        return context

    def post(self, request, *args, **kwargs):
        user = request.user
        current_school = user.school if hasattr(user, 'school') else None

        if not current_school:
            messages.error(request, "Vous n'êtes associé à aucune école.")
            return redirect(reverse_lazy('profiles:accounting_dashboard')) # Retourne toujours un redirect en cas d'erreur de base

        # Récupérer la période académique active
        try:
            active_period = AcademicPeriod.objects.get(school=current_school, is_current=True)
        except AcademicPeriod.DoesNotExist:
            messages.error(request, "Aucune période académique active définie pour votre école. Impossible d'effectuer l'opération.")
            return redirect(reverse_lazy('profiles:accounting_dashboard'))

        # --- Gérer l'ajout d'un nouveau paiement ---
        if 'add_payment' in request.POST:
            payment_form = PaymentForm(request.POST, user=user, school_id=current_school.id)
            if payment_form.is_valid():
                payment = payment_form.save(commit=False)
                payment.academic_period = active_period # Assigner la période active
                payment.recorded_by = user # L'utilisateur connecté est celui qui enregistre
                
                # Générer un numéro de reçu unique
                while True:
                    receipt_number = f"REC-{uuid.uuid4().hex[:8].upper()}"
                    if not Payment.objects.filter(receipt_number=receipt_number).exists():
                        payment.receipt_number = receipt_number
                        break
                
                payment.save()
                messages.success(request, f"Paiement de {payment.amount_paid}$ enregistré avec succès ! Reçu #{payment.receipt_number}")

                # --- Automatisation : Générer et envoyer le reçu PDF ---
                try:
                    pdf_path = generate_receipt_pdf(payment)
                    filename = os.path.basename(pdf_path)
                    with open(pdf_path, 'rb') as pdf_file:
                        payment.receipt_file.save(filename, ContentFile(pdf_file_content.read()))
                        
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path) # Supprimer le fichier temporaire après l'enregistrement

                    # Envoyer le reçu au(x) parent(s) de l'élève
                    student = payment.student
                    if student.parents.exists():
                        for parent_user in student.parents.all():
                            email_subject = f"Reçu de paiement pour {student.full_name} - {payment.receipt_number}"
                            email_context = {
                                'student_name': student.full_name,
                                'amount_paid': payment.amount_paid,
                                'payment_date': payment.payment_date,
                                'receipt_number': payment.receipt_number,
                                'fee_type_name': payment.fee_type.name if payment.fee_type else 'Frais',
                                'school_name': current_school.name,
                                'parent_name': parent_user.full_name,
                                'receipt_url': request.build_absolute_uri(payment.receipt_file.url) # URL du fichier sauvegardé
                            }
                            # Assurez-vous que send_notification_to_user gère les attachments
                            send_notification_to_user(
                                recipient_user=parent_user,
                                subject=email_subject,
                                message_body=f"Veuillez trouver ci-joint le reçu pour le paiement de {payment.amount_paid}$ pour {student.full_name}.",
                                email_template='school/receipt_email_template.html', # Créez ce template si besoin
                                context=email_context,
                                # Note: Envoyer un fichier directement comme attachment nécessite une implémentation robuste de send_notification_to_user
                                # Pour l'instant, le lien dans le template est plus simple si la fonction ne gère pas les pièces jointes
                            )
                        messages.info(request, "Reçu PDF généré et notification envoyée aux parents.")
                    else:
                        messages.warning(request, "Aucun parent n'est lié à cet élève pour l'envoi du reçu.")

                except Exception as e:
                    messages.error(request, f"Erreur lors de la génération ou l'envoi du reçu : {e}. Veuillez contacter l'administrateur.")
                    # Supprimer le fichier de reçu si l'enregistrement a échoué après génération
                    if payment.receipt_file and os.path.exists(payment.receipt_file.path):
                        payment.receipt_file.delete(save=False) # Ne pas sauvegarder le modèle à nouveau
                    print(f"ERROR: Erreur de génération/envoi de reçu: {e}") # Log d'erreur détaillé

            else:
                messages.error(request, "Erreur lors de l'enregistrement du paiement. Veuillez vérifier les informations.")
                context = self.get_context_data() # Recharge le contexte avec les erreurs du formulaire
                context['payment_form'] = payment_form # Passe le formulaire avec les erreurs
                return render(request, self.template_name, context)

        # --- Gérer la définition des frais de scolarité ---
        elif 'set_tuition_fee' in request.POST:
            tuition_fee_form = TuitionFeeForm(request.POST, school_id=current_school.id)
            if tuition_fee_form.is_valid():
                fee_type_instance = tuition_fee_form.cleaned_data['fee_type']
                classe_instance = tuition_fee_form.cleaned_data['classe']
                
                existing_fee = TuitionFee.objects.filter(
                    fee_type=fee_type_instance,
                    classe=classe_instance,
                    academic_period=active_period
                ).first()

                if existing_fee:
                    existing_fee.amount = tuition_fee_form.cleaned_data['amount']
                    existing_fee.set_by = user
                    existing_fee.save()
                    messages.success(request, f"Frais de scolarité mis à jour pour {classe_instance.name} ({fee_type_instance.name}).")
                    tuition_fee = existing_fee
                else:
                    tuition_fee = tuition_fee_form.save(commit=False)
                    tuition_fee.academic_period = active_period
                    tuition_fee.set_by = user
                    tuition_fee.save()
                    messages.success(request, f"Nouveaux frais de scolarité définis pour {classe_instance.name} ({fee_type_instance.name}).")
                
                # --- Automatisation : Notifier les parents ---
                students_in_classe = Student.objects.filter(current_classe=classe_instance, academic_period=active_period, school=current_school).prefetch_related('parents')
                if students_in_classe.exists():
                    notified_parents = set()
                    email_subject = f"Nouveaux frais pour la classe {classe_instance.name}"
                    email_template = 'profiles/fees_set_notification_email.html' # Créez ce template
                    
                    for student in students_in_classe:
                        if student.parents.exists():
                            for parent_user in student.parents.all():
                                if parent_user not in notified_parents:
                                    email_context = {
                                        'parent_name': parent_user.full_name,
                                        'student_name': student.full_name,
                                        'classe_name': classe_instance.name,
                                        'fee_type_name': fee_type_instance.name,
                                        'amount': tuition_fee.amount,
                                        'academic_period_name': active_period.name,
                                        'school_name': current_school.name,
                                        'dashboard_url': request.build_absolute_uri(reverse_lazy('profiles:accounting_dashboard')) # Assurez-vous que le namespace est 'profiles'
                                    }
                                    send_notification_to_user(
                                        recipient_user=parent_user,
                                        subject=email_subject,
                                        message_body=f"Les frais de {fee_type_instance.name} pour la classe {classe_instance.name} ont été fixés à {tuition_fee.amount}$.",
                                        email_template=email_template,
                                        context=email_context
                                    )
                                    notified_parents.add(parent_user)
                    if notified_parents:
                        messages.info(request, f"Notification envoyée à {len(notified_parents)} parent(s) pour les frais de {classe_instance.name}.")
                    else:
                        messages.warning(request, "Aucun parent trouvé pour les élèves de cette classe. Notification non envoyée.")

            else:
                messages.error(request, "Erreur lors de la définition des frais. Veuillez vérifier les informations.")
                context = self.get_context_data()
                context['tuition_fee_form'] = tuition_fee_form
                return render(request, self.template_name, context)

        # --- Gérer la création d'un nouveau type de frais ---
        elif 'add_fee_type' in request.POST:
            fee_type_form = FeeTypeForm(request.POST)
            if fee_type_form.is_valid():
                new_fee_type = fee_type_form.save(commit=False)
                new_fee_type.school = current_school
                new_fee_type.save()
                messages.success(request, f"Type de frais '{new_fee_type.name}' ajouté avec succès.")
            else:
                messages.error(request, "Erreur lors de l'ajout du type de frais. Veuillez vérifier les informations.")
                context = self.get_context_data()
                context['fee_type_form'] = fee_type_form
                return render(request, self.template_name, context)

        # --- Gérer l'envoi de notification manuelle aux parents (si toujours dans le template) ---
        elif 'recipient_user_id' in request.POST and 'message' in request.POST:
            recipient_id = request.POST.get('recipient_user_id')
            message_content = request.POST.get('message')
            try:
                recipient_user = CustomUser.objects.get(id=recipient_id)
                send_notification_to_user(recipient_user, "Notification de l'école", message_content)
                messages.success(request, f"Notification envoyée à {recipient_user.full_name}.")
            except CustomUser.DoesNotExist:
                messages.error(request, "Destinataire de la notification introuvable.")
            except Exception as e:
                messages.error(request, f"Erreur lors de l'envoi de la notification : {e}")

        return redirect(reverse_lazy('profiles:accounting_dashboard')) # Redirige après un POST réussi
def dashboard_charts_view(request):
    user_school = request.user.school # Supposons que votre CustomUser a un lien vers l'école
    
    # Récupérer la période académique active ou la plus récente
    current_academic_period = AcademicPeriod.objects.filter(school=user_school).order_by('-start_date').first()

    charts = {}
    
    if user_school:
        charts['students_by_class'] = ChartGenerator.generate_students_by_class_chart(user_school)
        
        if current_academic_period:
            charts['grades_distribution'] = ChartGenerator.generate_grades_distribution_chart(user_school, current_academic_period)
            charts['attendance_rate'] = ChartGenerator.generate_attendance_rate_chart(user_school, current_academic_period)
            charts['payment_status'] = ChartGenerator.generate_payment_status_chart(user_school, current_academic_period)
            charts['teacher_performance'] = ChartGenerator.generate_teacher_performance_chart(user_school, current_academic_period)
            charts['class_comparison'] = ChartGenerator.generate_class_comparison_chart(user_school, current_academic_period)
        
        charts['monthly_payments'] = ChartGenerator.generate_monthly_payments_chart(user_school, datetime.now().year)
    
    context = {
        'charts': charts,
        'school_name': user_school.name if user_school else "Votre École"
    }
    return render(request, 'profiles/dashboard_charts.html', context)