# profiles/views.py
from django.db import models, IntegrityError
import logging 
logger = logging.getLogger(__name__)
#from .chart_generator import ChartGenerator
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
from school.forms import EnrollmentForm


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

#def is_accountant(user):
 #    return user.is_authenticated and user.user_type == 'ACCOUNTANT'
@login_required
@user_passes_test(is_accounting_or_admin_or_direction)
def accounting_dashboard_view(request):
    current_school = None
    if request.user.is_authenticated and request.user.school:
        current_school = request.user.school

    # --- 1. Vue d'ensemble des paiements ---
    total_paid_for_school = 0
    remaining_balance_for_school = 0
    payments_list = []

    if current_school:
        # Calcul du total payé pour l'école actuelle
        school_payments_summary = Payment.objects.filter(
            student__school=current_school
        ).aggregate(
            total_paid=Sum('amount_paid')
        )
        total_paid_for_school = school_payments_summary.get('total_paid') or 0

        # Calcul du total des frais de scolarité dus pour la période actuelle et l'école
        # Assurez-vous que votre modèle AcademicPeriod a un champ 'is_current'
        total_tuition_fees = TuitionFee.objects.filter(
            classe__school=current_school,
            academic_period__is_current=True # Filtrer par la période académique actuelle
        ).aggregate(total_fees=Sum('amount'))['total_fees'] or 0

        remaining_balance_for_school = total_tuition_fees - total_paid_for_school

        # Récupération des 15 derniers paiements pour l'école actuelle
        payments_list = Payment.objects.filter(
            student__school=current_school
        ).order_by('-payment_date', '-id')[:15] # Ajout de '-id' pour un tri stable

    # --- 2. Gestion des formulaires (Ajouter Paiement, Définir Frais) ---
    payment_form = PaymentForm(user_school=current_school)
    tuition_fee_form = TuitionFeeForm(user_school=current_school)

    if request.method == 'POST':
        # Gérer l'ajout de paiement
        if 'add_payment' in request.POST:
            payment_form = PaymentForm(request.POST, user_school=current_school)
            if payment_form.is_valid():
                new_payment = payment_form.save(commit=False)
                new_payment.recorded_by = request.user
                new_payment.save()
                
                # --- LOGIQUE D'ENVOI DE NOTIFICATION AUX PARENTS (CORRIGÉE pour ManyToManyField) ---
                student = new_payment.student
                
                # Récupérer TOUS les parents liés à cet élève via le champ 'Parents' (au pluriel)
                parents_for_notification = student.Parents.all() # Accès via .all() car c'est un ManyToManyField

                if parents_for_notification.exists(): # Vérifie s'il y a au moins un parent lié
                    for parent_user in parents_for_notification:
                        # Assurez-vous que le parent est bien un CustomUser de type 'PARENT'
                        # Utilisez la même logique de comparaison de type que pour le décorateur
                        if parent_user.user_type == 'PARENT': # Si UserRole est une enum, utilisez CustomUser.UserRole.PARENT
                            Notification.objects.create(
                                recipient=parent_user, # Le CustomUser du parent est le destinataire
                                sender=request.user, # L'utilisateur connecté est l'expéditeur
                                subject=f"Confirmation de Paiement - {new_payment.student.full_name}",
                                message=f"Bonjour {parent_user.full_name},\n\n"
                                        f"Nous confirmons la réception d'un paiement de {new_payment.amount_paid:.2f} $ pour {new_payment.student.full_name} "
                                        f"concernant la période académique : {new_payment.academic_period.name}.\n\n"
                                        f"Date de paiement : {new_payment.payment_date.strftime('%d/%m/%Y')}\n"
                                        f"Statut : {new_payment.get_payment_status_display()}\n"
                                        f"ID de transaction : {new_payment.transaction_id if new_payment.transaction_id else 'N/A'}\n\n"
                                        f"Merci pour votre paiement.\n"
                                        f"Cordialement,\nVotre Administration Scolaire.",
                                notification_type='PAYMENT', # Assurez-vous que ce type existe dans votre modèle Notification
                                is_read=False,
                            )
                    messages.success(request, f"Paiement enregistré et notification(s) envoyée(s) aux parent(s) de {student.full_name}.")
                else:
                    messages.warning(request, f"Paiement enregistré. Aucun parent de type PARENT associé à {student.full_name} pour la notification.")
                # --- FIN LOGIQUE NOTIFICATION ---

                return redirect('profiles:accounting_dashboard') # Redirection après succès
            else:
                messages.error(request, "Erreur lors de l'enregistrement du paiement. Veuillez vérifier les informations.")
                print(payment_form.errors) # Pour le débogage en console

        # Gérer la définition des frais de scolarité
        elif 'set_tuition_fee' in request.POST:
            tuition_fee_form = TuitionFeeForm(request.POST, user_school=current_school)
            if tuition_fee_form.is_valid():
                new_fee = tuition_fee_form.save(commit=False)
                new_fee.set_by = request.user
                new_fee.save()
                messages.success(request, "Frais de scolarité définis avec succès.")
                return redirect('profiles:accounting_dashboard') # Redirection après succès
            else:
                messages.error(request, "Erreur lors de la définition des frais de scolarité. Veuillez vérifier les informations.")
                print(tuition_fee_form.errors) # Pour le débogage en console

    # --- 3. Liste des élèves par classe (avec filtrage) ---
    selected_class_id = request.GET.get('class_id')
    classes = []
    students_in_selected_class = []

    if current_school:
        classes = Classe.objects.filter(school=current_school).order_by('name')
        if selected_class_id:
            try:
                selected_class = Classe.objects.get(id=selected_class_id, school=current_school)
                students_in_selected_class = Student.objects.filter(
                    current_classe=selected_class,
                    school=current_school
                ).order_by('last_name', 'first_name')
            except Classe.DoesNotExist:
                messages.error(request, "La classe sélectionnée n'existe pas.")
                pass # Continue à afficher le reste du tableau de bord même si la classe est invalide

    # --- 4. Récupération des frais de scolarité définis ---
    tuition_fees_set = []
    if current_school:
        tuition_fees_set = TuitionFee.objects.filter(
            classe__school=current_school
        ).order_by('-academic_period__start_date', 'classe__name') # Correction ici pour '_'


    context = {
        'current_school': current_school,
        'total_paid_for_school': total_paid_for_school,
        'remaining_balance_for_school': remaining_balance_for_school,
        'payments_list': payments_list,
        'payment_form': payment_form, 
        'tuition_fee_form': tuition_fee_form, 
        'classes': classes,
        'selected_class_id': int(selected_class_id) if selected_class_id else None,
        'students_in_selected_class': students_in_selected_class,
        'tuition_fees_set': tuition_fees_set,
        'title': 'Tableau de Bord Comptable'
    }

    return render(request, 'profiles/accounting_dashboard.html', context)

@login_required
@user_passes_test(is_direction, login_url='/login/')
def add_student_view(request):
    student_form = StudentForm(user_school=request.user.school) # Initialisation par défaut
    parent_form = ParentCreationForm() # Initialisation par défaut

    if request.method == 'POST':
        student_form = StudentForm(request.POST, request.FILES, user_school=request.user.school)
        parent_form = ParentCreationForm(request.POST)

        # Validez les deux formulaires
        if student_form.is_valid() and parent_form.is_valid():
            try:
                # Utilisation d'une transaction pour s'assurer que si la création du parent ou de l'élève échoue, tout est annulé.
                with transaction.atomic():
                    # 1. Création du compte Parent
                    parent_user = parent_form.save(commit=False)
                    parent_user.school = request.user.school # Le parent est lié à la même école que la direction qui l'ajoute
                    parent_user.save()

                    # 2. Création de l'élève
                    student = student_form.save(commit=False)
                    student.school = request.user.school # L'élève est lié à la même école que la direction
                    student.save() # Le student_id_code sera généré ici via la méthode save du modèle

                    # 3. Lier le parent à l'élève
                    student.parents.add(parent_user) # Ajoute le parent à la relation ManyToMany

                    messages.success(request, f"L'élève {student.full_name} et son parent {parent_user.full_name} ont été ajoutés avec succès.")
                    return redirect('profiles:list_students') # Redirigez vers la liste des élèves ou autre

            except Exception as e:
                messages.error(request, f"Une erreur s'est produite lors de l'ajout de l'élève et du parent : {e}")
                # Log l'erreur pour le débogage (dans un vrai projet)
                # logger.error(f"Erreur à l'ajout élève/parent: {e}")
        else:
            # Si un des formulaires n'est pas valide, les erreurs seront affichées automatiquement
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")

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
            return redirect('direction_manage_users')
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
    # CORRECTION: Notification.objects.filter(recipient=request.user) sera suffisant si toutes les notifications pertinentes
    # (directes et liées aux enfants) sont envoyées avec le parent comme `recipient`.
    # Si les notifications sont créées avec `recipient_student` ou `recipient_class`, la logique ci-dessous doit être affinée
    # pour récupérer toutes les notifications destinées à l'utilisateur parent ou à ses enfants.

    # Approche 1: Si toutes les notifications (directes et indirectes via enfant) ont le parent comme 'recipient'
    all_notifications = Notification.objects.filter(recipient=request.user).order_by('-timestamp')

    # Approche 2 (plus complexe si notifications sont liées à l'enfant/classe directement, PAS au parent comme recipient)
    # children_of_parent = request.user.children.all()
    # q_objects = Q(recipient=request.user) # Notifications envoyées directement au parent
    # for child in children_of_parent:
    # if hasattr(child, 'user_account') and child.user_account: # Si l'enfant a un compte utilisateur lié
    # q_objects |= Q(recipient=child.user_account)
    # # Si Notification a un champ ForeignKey vers Student ou Classe:
    # # q_objects |= Q(recipient_student=child)
    # # if child.current_classe:
    # # q_objects |= Q(recipient_class=child.current_classe)
    # all_notifications = Notification.objects.filter(q_objects).distinct().order_by('-timestamp')


    context = {
        'notifications': all_notifications,
        'title': "Vos Notifications"
    }
    return render(request, 'profiles/parent_notifications.html', context)



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

class PaymentForm(ModelForm):
    class Meta:
        model = Payment
        fields = ['student', 'academic_period', 'amount_paid', 'payment_date', 'payment_status', 'transaction_id']
        widgets = {
            'payment_date': DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        user_school = kwargs.pop('user_school', None)
        super().__init__(*args, **kwargs)
        if user_school:
            self.fields['student'].queryset = Student.objects.filter(school=user_school).order_by('first_name')
            self.fields['academic_period'].queryset = AcademicPeriod.objects.filter(school=user_school).order_by('-start_date')


class TuitionFeeForm(ModelForm):
    class Meta:
        model = TuitionFee
        fields = ['classe', 'academic_period', 'amount']

    def __init__(self, *args, **kwargs):
        user_school = kwargs.pop('user_school', None)
        super().__init__(*args, **kwargs)
        if user_school:
            self.fields['classe'].queryset = Classe.objects.filter(school=user_school).order_by('name')
            self.fields['academic_period'].queryset = AcademicPeriod.objects.filter(school=user_school).order_by('-start_date')

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
