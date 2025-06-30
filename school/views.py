# school/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.forms import formset_factory
from django import forms
from django.db import transaction
from django.db.models import Q
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from school.forms import ClasseForm, Student, StudentForm, EnrollmentForm, GradeForm, AttendanceForm, CourseForm, NotificationForm  # Assurez-vous que ce formulaire est défini dans school/forms.py
from school.models import Classe, Attendance, AcademicPeriod, Course, Enrollment, Notification, Payment, Subject, Evaluation, ReportCard, DisciplinaryRecord, Grade, EvaluationType # Assurez-vous que ce formulaire est défini dans school/forms.py
from datetime import date 
from .models import (
    AcademicPeriod, Course, Enrollment, Grade, Evaluation# Assurez-vous que EvaluationType est déjà géré via Evaluation.evaluation_type.choices
)
from .forms import AcademicPeriodForm # Assurez-vous que ce formulaire est défini dans school/forms.py
# Assurez-vous d'importer votre modèle CustomUser et UserRole depuis profiles
# Si Student est dans profiles.models, importez-le aussi ici si vous en avez besoin.
from profiles.models import CustomUser, UserRole, Student as ProfileStudent, Classe, School as User

class GradeEntryForm(forms.Form):
    enrollment_id = forms.IntegerField(widget=forms.HiddenInput())
    student_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'})
    )
    score = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        help_text="Laisser vide si pas de note",
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )
    remarks = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'cols': 30})
    )

# --- VUES POUR LES ENSEIGNANTS ---

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.TEACHER, login_url='/login/')
def teacher_evaluations_list(request):
    """
    Vue permettant à l'enseignant de voir la liste des évaluations de ses cours.
    """
    # Correction: le related_name sur Course.teachers est 'teachers'
    evaluations = Evaluation.objects.filter(course_teachers=request.user).order_by('-date', 'course_name')

    context = {
        'title': 'Mes Évaluations',
        'evaluations': evaluations,
    }
    return render(request, 'school/teacher_evaluations_list.html', context)


@login_required
@user_passes_test(lambda u: u.user_type == UserRole.TEACHER, login_url='/login/')
def teacher_create_evaluation(request):
    """
    Vue permettant à l'enseignant de créer une nouvelle évaluation.
    """
    class EvaluationForm(forms.ModelForm):
        class Meta:
            model = Evaluation
            fields = ['name', 'course', 'evaluation_type', 'date', 'max_score', 'description', 'academic_period']
            widgets = {
                'date': forms.DateInput(attrs={'type': 'date'}),
            }

        # Correction: _init_ avec doubles underscores
        def _init_(self, *args, **kwargs):
            teacher = kwargs.pop('teacher', None)
            super()._init_(*args, **kwargs)
            if teacher:
                self.fields['course'].queryset = Course.objects.filter(teachers=teacher)
            self.fields['academic_period'].queryset = AcademicPeriod.objects.filter(is_current=True) # Ou toutes les périodes si vous préférez

    if request.method == 'POST':
        form = EvaluationForm(request.POST, teacher=request.user)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.created_by = request.user
            evaluation.save()
            messages.success(request, f"L'évaluation '{evaluation.name}' a été créée avec succès.")
            return redirect('teacher_evaluations_list')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = EvaluationForm(teacher=request.user)

    context = {
        'title': 'Créer une Nouvelle Évaluation',
        'form': form,
    }
    return render(request, 'school/teacher_create_evaluation.html', context)


@login_required
@user_passes_test(lambda u: u.user_type == UserRole.TEACHER, login_url='/login/')
def teacher_enter_grades_view(request, evaluation_id):
    """
    Vue pour l'enseignant afin d'enregistrer ou de modifier les notes pour une évaluation spécifique.
    """
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)

    # Vérifier que l'enseignant a le droit d'accéder à cette évaluation (enseigne ce cours)
    if not evaluation.course.teachers.filter(id=request.user.id).exists():
        messages.error(request, "Vous n'êtes pas autorisé à gérer les notes de cette évaluation.")
        return redirect('teacher_evaluations_list')

    enrollments_in_course = Enrollment.objects.filter(
        course=evaluation.course,
        academic_period=evaluation.academic_period
    ).order_by('student_last_name', 'student_first_name') # Correction: double underscore

    GradeFormSet = formset_factory(GradeEntryForm, extra=0)

    if request.method == 'POST':
        formset = GradeFormSet(request.POST)
        if formset.is_valid():
            with transaction.atomic():
                for form_data in formset.cleaned_data:
                    enrollment_id = form_data.get('enrollment_id')
                    score = form_data.get('score')
                    remarks = form_data.get('remarks')

                    enrollment = get_object_or_404(Enrollment, id=enrollment_id)

                    if score is not None and score != '':
                        grade, created = Grade.objects.update_or_create(
                            evaluation=evaluation,
                            enrollment=enrollment,
                            defaults={
                                'score': score,
                                'remarks': remarks,
                                'graded_by': request.user,
                                'date_graded': timezone.now().date(),
                            }
                        )
                    else:
                        Grade.objects.filter(evaluation=evaluation, enrollment=enrollment).delete()

            messages.success(request, "Notes enregistrées avec succès !")
            return redirect('teacher_evaluations_list')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else: # GET request
        initial_data = []
        for enrollment in enrollments_in_course:
            existing_grade = Grade.objects.filter(evaluation=evaluation, enrollment=enrollment).first()
            initial_data.append({
                'enrollment_id': enrollment.id,
                'student_name': enrollment.student.full_name, # Assurez-vous que student a une propriété full_name
                'score': existing_grade.score if existing_grade else None,
                'remarks': existing_grade.remarks if existing_grade else '',
            })
        formset = GradeFormSet(initial=initial_data)

    context = {
        'title': f"Enregistrer les Notes pour {evaluation.name}",
        'evaluation': evaluation,
        'formset': formset,
        'enrollments': enrollments_in_course,
        'max_score': evaluation.max_score,
    }
    return render(request, 'school/teacher_enter_grades.html', context)


# --- VUES POUR LES PARENTS ---

# school/views.py - à l'intérieur de parent_grades_view
@login_required
@user_passes_test(lambda u: u.user_type == UserRole.PARENT, login_url='/login/')
def parent_grades_view(request):
    """
    Vue permettant au parent de consulter les notes de ses enfants.
    """
    parent_user = request.user
    children = parent_user.children.all()

    grades_by_child = {}
    for child in children:
        child_enrollments = Enrollment.objects.filter(student=child)
        # FIX: Filtre corrigé pour les notes
        child_grades = Grade.objects.filter(enrollment_in=child_enrollments).order_by('-evaluationdate', 'evaluationcourse_name')
        grades_by_child[child] = child_grades

    context = {
        'title': 'Notes de mes enfants',
        'grades_by_child': grades_by_child,
    }
    return render(request, 'school/parent_grades.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/') # Seule la direction peut gérer les périodes académiques
def academic_period_list(request):
    """
    Vue pour lister les périodes académiques de l'école de l'utilisateur connecté.
    """
    user = request.user
    if user.user_type != UserRole.DIRECTION:
        messages.error(request, "Vous n'êtes pas autorisé à accéder à cette page.")
        return redirect('home') # Redirigez vers une page appropriée pour les non-autorisés

    # Filtrer les périodes académiques par l'école de l'utilisateur connecté
    # Assurez-vous que votre modèle CustomUser a un champ 'school'
    if user.school:
        academic_periods = AcademicPeriod.objects.filter(school=user.school).order_by('-start_date')
    else:
        # Gérer le cas où un utilisateur de la direction n'est pas associé à une école
        messages.warning(request, "Votre compte n'est pas associé à une école. Veuillez contacter l'administrateur.")
        academic_periods = AcademicPeriod.objects.none() # Aucune période à afficher

    context = {
        'title': 'Gestion des Périodes Académiques',
        'academic_periods': academic_periods,
    }
    return render(request, 'school/academic_period_list.html', context)


@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/')
def academic_period_detail(request, pk):
    """
    Vue pour afficher les détails d'une période académique spécifique.
    """
    user = request.user
    if user.user_type != UserRole.DIRECTION:
        messages.error(request, "Vous n'êtes pas autorisé à accéder à cette page.")
        return redirect('home')

    academic_period = get_object_or_404(AcademicPeriod, pk=pk, school=user.school)
    # Le filtre 'school=user.school' est important pour la sécurité multi-écoles,
    # afin qu'une direction ne puisse voir que les périodes de SA propre école.

    context = {
        'title': f"Détails de la Période Académique : {academic_period.name}",
        'academic_period': academic_period,
    }
    return render(request, 'school/academic_period_detail.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/')
def academic_period_update(request, pk):
    """
    Vue pour modifier une période académique existante.
    """
    user = request.user
    if user.user_type != UserRole.DIRECTION:
        messages.error(request, "Vous n'êtes pas autorisé à modifier une période académique.")
        return redirect('home')

    # Récupérer la période académique existante ou retourner une 404
    academic_period = get_object_or_404(AcademicPeriod, pk=pk, school=user.school)

    if request.method == 'POST':
        form = AcademicPeriodForm(request.POST, instance=academic_period)
        if form.is_valid():
            form.save()
            messages.success(request, f"La période académique '{academic_period.name}' a été mise à jour avec succès.")
            return redirect('academic_period_detail', pk=academic_period.pk)
        else:
            messages.error(request, "Erreur lors de la mise à jour de la période académique. Veuillez vérifier les informations.")
    else:
        form = AcademicPeriodForm(instance=academic_period) # Pré-remplir le formulaire avec les données existantes

    context = {
        'title': f"Modifier la Période Académique : {academic_period.name}",
        'form': form,
        'academic_period': academic_period, # Utile pour afficher le nom ou l'ID dans le template
    }
    # Réutiliser le même template que pour la création, en ajustant le titre dans le template
    return render(request, 'school/academic_period_form.html', context)


@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/')
def academic_period_delete(request, pk):
    """
    Vue pour supprimer une période académique.
    """
    user = request.user
    if user.user_type != UserRole.DIRECTION:
        messages.error(request, "Vous n'êtes pas autorisé à supprimer une période académique.")
        return redirect('home')

    academic_period = get_object_or_404(AcademicPeriod, pk=pk, school=user.school)

    if request.method == 'POST':
        academic_period.delete()
        messages.success(request, f"La période académique '{academic_period.name}' a été supprimée avec succès.")
        return redirect('academic_period_list')
    
    # Pour une requête GET, afficher une page de confirmation
    context = {
        'title': f"Confirmer la suppression de : {academic_period.name}",
        'academic_period': academic_period,
    }
    return render(request, 'school/academic_period_confirm_delete.html', context)





@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER], login_url='/login/')
def classe_detail(request, pk):
    """
    Vue pour afficher les détails d'une classe spécifique.
    """
    user = request.user
    
    # Vérification des autorisations
    if user.user_type not in [UserRole.DIRECTION, UserRole.TEACHER]:
        messages.error(request, "Vous n'êtes pas autorisé à accéder aux détails des classes.")
        return redirect('home')

    # Récupérer la classe ou retourner une 404
    # Filtrer par l'école de l'utilisateur pour la sécurité
    classe = get_object_or_404(Classe, pk=pk, school=user.school)

    # Logique spécifique si l'utilisateur est un enseignant
    if user.user_type == UserRole.TEACHER:
        # Si un enseignant ne peut voir que les classes qu'il enseigne :
        # Vérifiez si l'enseignant est lié à cette classe
        # Cela dépend de la relation que vous avez définie entre Teacher et Classe/Course.
        # Par exemple, si l'enseignant est le homeroom_teacher de cette classe:
        if classe.homeroom_teacher != user:
            # Ou si l'enseignant enseigne un cours dans cette classe (plus complexe, nécessiterait une requête plus avancée)
            # Pour l'instant, simplifions en disant que l'enseignant doit être le titulaire pour voir les détails
            # Ou commenter cette partie si les enseignants peuvent voir toutes les classes de leur école.
            messages.error(request, "Vous n'êtes pas l'enseignant titulaire de cette classe ou vous n'enseignez pas dans cette classe.")
            return redirect('classe_list') # Redirige vers la liste des classes


    context = {
        'title': f"Détails de la Classe : {classe.name} ({classe.level})",
        'classe': classe,
        # Vous pourriez ajouter ici d'autres données liées à la classe, par ex. liste des élèves
        # students = classe.students.all() # Si vous avez un related_name 'students' sur Classe
        # 'students': students,
    }
    return render(request, 'school/classe_detail.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/')
def classe_update(request, pk):
    """
    Vue pour modifier une classe existante.
    """
    user = request.user
    if user.user_type != UserRole.DIRECTION:
        messages.error(request, "Vous n'êtes pas autorisé à modifier une classe.")
        return redirect('home')

    # Récupérer la classe existante ou retourner une 404
    # Filtrer par l'école de l'utilisateur pour la sécurité
    classe = get_object_or_404(Classe, pk=pk, school=user.school)

    if request.method == 'POST':
        # Passez l'instance existante au formulaire pour la pré-remplir
        # et pour que form.save() mette à jour l'objet existant.
        # Passez également l'école pour filtrer les querysets du formulaire.
        form = ClasseForm(request.POST, instance=classe, school=user.school)
        if form.is_valid():
            form.save()
            messages.success(request, f"La classe '{classe.name}' a été mise à jour avec succès.")
            return redirect('classe_detail', pk=classe.pk) # Redirigez vers les détails de la classe
        else:
            messages.error(request, "Erreur lors de la mise à jour de la classe. Veuillez vérifier les informations.")
    else:
        # Pour une requête GET, pré-remplir le formulaire avec les données existantes.
        # Passez l'école pour filtrer les querysets du formulaire.
        form = ClasseForm(instance=classe, school=user.school)

    context = {
        'title': f"Modifier la Classe : {classe.name} ({classe.level})",
        'form': form,
        'classe': classe, # Passez l'objet classe au template pour le titre ou d'autres usages
    }
    # Réutiliser le même template que pour la création (classe_form.html)
    return render(request, 'school/classe_form.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/')
def classe_delete(request, pk):
    """
    Vue pour supprimer une classe.
    """
    user = request.user
    if user.user_type != UserRole.DIRECTION:
        messages.error(request, "Vous n'êtes pas autorisé à supprimer une classe.")
        return redirect('home')

    # Récupérer la classe à supprimer ou retourner une 404
    # Filtrer par l'école de l'utilisateur pour la sécurité
    classe = get_object_or_404(Classe, pk=pk, school=user.school)

    if request.method == 'POST':
        classe_name = classe.name # Sauvegarder le nom avant de supprimer
        classe.delete()
        messages.success(request, f"La classe '{classe_name}' a été supprimée avec succès.")
        return redirect('classe_list') # Redirigez vers la liste des classes après suppression
    
    # Pour une requête GET, afficher une page de confirmation
    context = {
        'title': f"Confirmer la suppression de la Classe : {classe.name} ({classe.level})",
        'classe': classe, # Passez l'objet classe au template pour l'affichage des détails
    }
    return render(request, 'school/classe_confirm_delete.html', context)

@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER], login_url='/login/')
def student_list(request):
    """
    Vue pour lister les étudiants, filtrés par l'école de l'utilisateur connecté.
    Les enseignants peuvent voir leurs étudiants, la direction tous les étudiants de l'école.
    """
    user = request.user
    
    if user.user_type == UserRole.DIRECTION:
        # La direction voit tous les étudiants de son école
        if user.school:
            students = Student.objects.filter(school=user.school).order_by('last_name', 'first_name')
        else:
            messages.warning(request, "Votre compte de direction n'est pas associé à une école.")
            students = Student.objects.none() # Aucun étudiant à afficher
    elif user.user_type == UserRole.TEACHER:
       # Un enseignant voit uniquement les étudiants des classes qu'il enseigne
        if user.school:
            # Assurez-vous que votre modèle TeacherProfile ou CustomUser a une relation vers Classe
            # Par exemple, via taught_courses -> Course -> Classe
            # OU si Classe a un ManyToManyField 'teachers' vers CustomUser
            students = Student.objects.filter(
                school=user.school,
                classe_course_teachers=user # Filtre les étudiants liés aux cours enseignés par cet utilisateur
            ).distinct().order_by('last_name', 'first_name')
            # Si votre CustomUser a une relation directe ManyToMany 'classes_taught', utilisez:
            # students = Student.objects.filter(classe__in=user.classes_taught, school=user.school).order_by('last_name', 'first_name')

        else:
            messages.warning(request, "Votre compte d'enseignant n'est pas associé à une école.")
            students = Student.objects.none()
    else:
        messages.error(request, "Vous n'êtes pas autorisé à voir cette page.")
        return redirect('home')

    context = {
        'title': 'Liste des Étudiants',
        'students': students,
    }
    return render(request, 'school/student_list.html', context)
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER], login_url='/login/')
def student_create(request):
    """
    Vue pour créer un nouvel étudiant (utilisée par la direction ou un enseignant).
    """
    user = request.user
    
    # Seule la direction et les enseignants peuvent créer des étudiants
    if user.user_type not in [UserRole.DIRECTION, UserRole.TEACHER]:
        messages.error(request, "Vous n'êtes pas autorisé à créer des étudiants.")
        return redirect('home')

    # Assurez-vous que l'utilisateur est associé à une école
    if not user.school:
        messages.warning(request, "Votre compte n'est pas associé à une école. Impossible de créer un étudiant.")
        return redirect('home')

    if request.method == 'POST':
        # Passez l'instance de l'école au formulaire pour filtrer les querysets (ex: Classe)
        form = StudentForm(request.POST, request.FILES, school=user.school)
        if form.is_valid():
            student = form.save(commit=False)
            student.school = user.school # Associez l'étudiant à l'école de l'utilisateur

            # Assurez-vous que student_id_code est unique ou générez-le si besoin
            if not student.student_id_code:
                # Génération d'un code temporaire si non fourni
                base_id = f"TEMP-{user.school.id}-{student.last_name[:3].upper()}-{student.first_name[:2].upper()}-{timezone.now().strftime('%m%d%H%M')}"
                counter = 0
                while True:
                    unique_id = f"{base_id}-{counter}" if counter > 0 else base_id
                    if not Student.objects.filter(student_id_code=unique_id).exists():
                        student.student_id_code = unique_id
                        break
                    counter += 1

            student.is_active = True # Actif par défaut lors de la création manuelle
            student.save()

            # Si l'enseignant ou la direction crée un élève sans parent défini via le formulaire,
            # et que Student.parents est un ManyToManyField obligatoire,
            # vous devrez soit le rendre non obligatoire, soit assigner un parent par défaut,
            # soit gérer l'assignation des parents après la création de l'élève par l'admin.
            # Pour l'instant, je suppose que 'parents' est un ManyToManyField non obligatoire ou géré ailleurs.

            messages.success(request, f"L'étudiant '{student.first_name} {student.last_name}' a été créé avec succès.")
            return redirect('student_list') # Redirigez vers la liste des étudiants
        else:
            print("Erreurs du formulaire étudiant:", form.errors) # Pour le débogage
            messages.error(request, "Erreur lors de la création de l'étudiant. Veuillez vérifier les informations.")
    else:
        # Passez l'instance de l'école au formulaire pour filtrer les querysets (ex: Classe)
        form = StudentForm(school=user.school)

    context = {
        'title': 'Ajouter un Nouvel Étudiant',
        'form': form,
    }
    # Réutiliser le même template de formulaire pour la création et la modification d'étudiants
    return render(request, 'school/student_form.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/')
def school_detail(request, pk):
    """
    Vue pour afficher les détails d'une école spécifique.
    Accessible uniquement par la direction de cette école.
    """
    user = request.user

    # Vérification des autorisations : Seule la direction peut voir les détails de SON école
    if user.user_type != UserRole.DIRECTION:
        messages.error(request, "Vous n'êtes pas autorisé à accéder aux détails de l'école.")
        return redirect('home')

    # Récupérer l'école ou retourner une 404
    # S'assurer que l'utilisateur ne peut voir que les détails de sa propre école
    if user.school and user.school.pk == pk:
        school = get_object_or_404(School, pk=pk)
    else:
        messages.error(request, "Vous n'êtes pas autorisé à voir cette école ou elle n'existe pas.")
        return redirect('home') # Ou rediriger vers une page d'erreur plus appropriée

    context = {
        'title': f"Détails de l'École : {school.name}",
        'school': school,
        # Vous pouvez ajouter ici d'autres données liées à l'école, par exemple:
        # 'classes_count': school.classes.count(),
        # 'students_count': school.students.count(), # Si Student a un related_name 'students' vers School
        # 'teachers_count': CustomUser.objects.filter(school=school, user_type=UserRole.TEACHER).count(),
    }
    return render(request, 'school/school_detail.html', context)

@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER, UserRole.PARENT], login_url='/login/')
def student_detail(request, pk):
    """
    Vue pour afficher les détails d'un étudiant spécifique.
    Accessible par la direction, les enseignants (pour leurs classes), et les parents (pour leurs enfants).
    """
    user = request.user
    
    # Récupérer l'étudiant ou retourner une 404
    # Filtrer par l'école de l'utilisateur pour la sécurité de base
    student = get_object_or_404(Student, pk=pk, school=user.school)

    # Vérification des autorisations basée sur le rôle
    authorized = False
    if user.user_type == UserRole.DIRECTION:
        # La direction peut voir tous les étudiants de son école
        authorized = True
    elif user.user_type == UserRole.TEACHER:
        # Un enseignant peut voir les étudiants de ses classes
        # Cela suppose que Student.classe est une ForeignKey vers Classe,
        # et Classe a une relation avec Course, qui a une relation avec les teachers.
        # OU si Student a une relation directe avec les classes enseignées par le prof.
        # Ici, je vais simplifier en vérifiant si l'étudiant est dans une classe où cet enseignant enseigne.
        # Cette requête peut varier selon votre modèle exact.
        if student.classe.course_set.filter(teachers=user).exists(): # Supposant Classe a related_name 'course_set'
            authorized = True
        elif student.classe.homeroom_teacher == user: # Si l'enseignant est le titulaire de la classe de l'étudiant
            authorized = True
        else:
            messages.error(request, "Vous n'êtes pas autorisé à voir les détails de cet étudiant (non dans vos classes).")
    elif user.user_type == UserRole.PARENT:
        # Un parent peut voir les détails de ses propres enfants
        # Cela suppose que le modèle Student a un ManyToManyField 'parents' vers CustomUser.
        if student.parents.filter(pk=user.pk).exists():
            authorized = True
        else:
            messages.error(request, "Vous n'êtes pas autorisé à voir les détails de cet étudiant (pas votre enfant).")

    if not authorized:
        return redirect('home') # Ou une page d'erreur spécifique

    context = {
        'title': f"Détails de l'Étudiant : {student.first_name} {student.last_name}",
        'student': student,
        # Vous pouvez ajouter ici d'autres données liées à l'étudiant, par ex. ses notes, présences
        # grades = student.grades_set.all() # Si Student a un related_name 'grades_set'
        # 'grades': grades,
    }
    return render(request, 'school/student_detail.html', context)

@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER], login_url='/login/')
def student_update(request, pk):
    """
    Vue pour modifier les informations d'un étudiant existant.
    Accessible par la direction et les enseignants (pour leurs étudiants).
    """
    user = request.user
    
    # Récupérer l'étudiant à modifier ou retourner une 404
    # Filtrer par l'école de l'utilisateur pour la sécurité de base
    student = get_object_or_404(Student, pk=pk, school=user.school)

    # Vérification des autorisations basée sur le rôle
    authorized_to_edit = False
    if user.user_type == UserRole.DIRECTION:
        authorized_to_edit = True
    elif user.user_type == UserRole.TEACHER:
        # Un enseignant ne peut modifier que les étudiants de ses classes
        # Reprise de la logique d'autorisation de student_detail pour les enseignants
        if student.classe and (student.classe.course_set.filter(teachers=user).exists() or student.classe.homeroom_teacher == user):
            authorized_to_edit = True
        else:
            messages.error(request, "Vous n'êtes pas autorisé à modifier cet étudiant (non dans vos classes).")
            return redirect('student_list') # Ou une page d'erreur spécifique
    
    if not authorized_to_edit:
        messages.error(request, "Vous n'êtes pas autorisé à modifier les détails de cet étudiant.")
        return redirect('home') # Ou rediriger vers une page d'erreur plus appropriée

    if request.method == 'POST':
        # Passez l'instance existante au formulaire pour la pré-remplir
        # et pour que form.save() mette à jour l'objet existant.
        # Passez également l'école pour filtrer les querysets du formulaire.
        form = StudentForm(request.POST, request.FILES, instance=student, school=user.school)
        if form.is_valid():
            form.save()
            messages.success(request, f"Les informations de l'étudiant '{student.first_name} {student.last_name}' ont été mises à jour avec succès.")
            return redirect('student_detail', pk=student.pk) # Redirigez vers les détails de l'étudiant
        else:
            print("Erreurs du formulaire étudiant:", form.errors) # Pour le débogage
            messages.error(request, "Erreur lors de la mise à jour de l'étudiant. Veuillez vérifier les informations.")
    else:
        # Pour une requête GET, pré-remplir le formulaire avec les données existantes.
        # Passez l'école pour filtrer les querysets du formulaire.
        form = StudentForm(instance=student, school=user.school)

    context = {
        'title': f"Modifier l'Étudiant : {student.first_name} {student.last_name}",
        'form': form,
        'student': student, # Passez l'objet étudiant au template pour le titre ou d'autres usages
    }
    # Réutiliser le même template que pour la création (student_form.html)
    return render(request, 'school/student_form.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/')
def student_delete(request, pk):
    """
    Vue pour supprimer un étudiant.
    Accessible uniquement par la direction.
    """
    user = request.user
    if user.user_type != UserRole.DIRECTION:
        messages.error(request, "Vous n'êtes pas autorisé à supprimer un étudiant.")
        return redirect('home')

    # Récupérer l'étudiant à supprimer ou retourner une 404
    # Filtrer par l'école de l'utilisateur pour la sécurité
    student = get_object_or_404(Student, pk=pk, school=user.school)

    if request.method == 'POST':
        student_full_name = f"{student.first_name} {student.last_name}" # Sauvegarder le nom avant de supprimer
        student.delete()
        messages.success(request, f"L'étudiant '{student_full_name}' a été supprimé avec succès.")
        return redirect('student_list') # Redirigez vers la liste des étudiants après suppression
    
    # Pour une requête GET, afficher une page de confirmation
    context = {
        'title': f"Confirmer la suppression de l'Étudiant : {student.first_name} {student.last_name}",
        'student': student, # Passez l'objet étudiant au template pour l'affichage des détails
    }
    return render(request, 'school/student_confirm_delete.html', context)

@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/')
def student_enroll_course(request, pk):
    """
    Vue pour inscrire un étudiant à un cours.
    Accessible uniquement par la direction.
    """
    user = request.user
    if user.user_type != UserRole.DIRECTION:
        messages.error(request, "Vous n'êtes pas autorisé à inscrire des étudiants aux cours.")
        return redirect('home')

    # Récupérer l'étudiant ou retourner une 404
    student = get_object_or_404(Student, pk=pk, school=user.school)

    # Récupérer la période académique active (vous devrez peut-être ajuster cette logique)
    # Par exemple, vous pourriez avoir un champ 'is_active' sur AcademicPeriod, ou une configuration globale.
    active_academic_period = AcademicPeriod.objects.filter(
        school=user.school, 
        start_date__lte=timezone.now(), 
        end_date__gte=timezone.now()
    ).first()

    if not active_academic_period:
        messages.warning(request, "Aucune période académique active trouvée pour votre école. Impossible d'inscrire l'étudiant.")
        return redirect('student_detail', pk=student.pk)

    if request.method == 'POST':
        # Passez l'école et la période académique au formulaire pour filtrer les cours
        form = EnrollmentForm(request.POST, school=user.school, academic_period=active_academic_period)
        if form.is_valid():
            enrollment = form.save(commit=False)
            enrollment.student = student # Associez l'étudiant à l'inscription
            enrollment.enrollment_date = timezone.now().date() # Date d'inscription automatique
            
            # Vérifier si l'étudiant est déjà inscrit à ce cours pour cette période académique
            if Enrollment.objects.filter(student=student, course=enrollment.course, course__academic_period=active_academic_period).exists():
                messages.error(request, f"L'étudiant est déjà inscrit au cours '{enrollment.course.name}' pour cette période académique.")
            else:
                enrollment.save()
                messages.success(request, f"L'étudiant '{student.first_name} {student.last_name}' a été inscrit au cours '{enrollment.course.name}' avec succès.")
                return redirect('student_detail', pk=student.pk)
        else:
            messages.error(request, "Erreur lors de l'inscription au cours. Veuillez vérifier les informations.")
    else:
        # Initialiser le formulaire avec l'école et la période académique
        form = EnrollmentForm(school=user.school, academic_period=active_academic_period)

    context = {
        'title': f"Inscrire {student.first_name} {student.last_name} à un cours",
        'student': student,
        'form': form,
        'active_academic_period': active_academic_period,
    }
    return render(request, 'school/student_enroll_course.html', context)


# 2. Vue pour afficher les détails d'un cours
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER], login_url='/login/')
def course_detail(request, pk):
    """
    Vue pour afficher les détails d'un cours spécifique.
    Accessible par la direction et les enseignants (pour leurs cours).
    """
    user = request.user
    
    # Récupérer le cours ou retourner une 404. Filtrer par l'école de l'utilisateur.
    course = get_object_or_404(Course, pk=pk, classe__school=user.school)

    # Vérification des autorisations spécifiques pour les enseignants
    authorized = False
    if user.user_type == UserRole.DIRECTION:
        authorized = True
    elif user.user_type == UserRole.TEACHER:
        # Un enseignant peut voir les détails d'un cours s'il est assigné à ce cours
        if course.teachers.filter(pk=user.pk).exists():
            authorized = True
        else:
            messages.error(request, "Vous n'êtes pas autorisé à voir les détails de ce cours.")
    
    if not authorized:
        return redirect('course_list') # Ou une page d'erreur spécifique

    context = {
        'title': f"Détails du Cours : {course.name}",
        'course': course,
        # Vous pouvez ajouter ici la liste des élèves inscrits à ce cours, par exemple
        # 'enrollments': course.enrollments.all().order_by('student__last_name'),
    }
    return render(request, 'school/course_detail.html', context)


# 3. Vue pour modifier un cours existant
@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/')
def course_update(request, pk):
    """
    Vue pour modifier un cours existant. Accessible uniquement par la direction.
    """
    user = request.user
    # Récupérer le cours à modifier ou retourner une 404. Filtrer par l'école.
    course = get_object_or_404(Course, pk=pk, classe__school=user.school)

    if request.method == 'POST':
        # Passer l'instance existante et l'école au formulaire
        form = CourseForm(request.POST, instance=course, school=user.school)
        if form.is_valid():
            form.save()
            messages.success(request, f"Le cours '{course.name}' a été mis à jour avec succès.")
            return redirect('course_detail', pk=course.pk)
        else:
            messages.error(request, "Erreur lors de la mise à jour du cours. Veuillez vérifier les informations.")
    else:
        form = CourseForm(instance=course, school=user.school)

    context = {
        'title': f"Modifier le Cours : {course.name}",
        'form': form,
        'course': course, # Passez l'objet cours au template pour le titre
    }
    return render(request, 'school/course_form.html', context)


# 4. Vue pour supprimer un cours
@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/')
def course_delete(request, pk):
    """
    Vue pour supprimer un cours. Accessible uniquement par la direction.
    """
    user = request.user
    # Récupérer le cours à supprimer ou retourner une 404. Filtrer par l'école.
    course = get_object_or_404(Course, pk=pk, classe__school=user.school)

    if request.method == 'POST':
        course_name = course.name
        course.delete()
        messages.success(request, f"Le cours '{course_name}' a été supprimé avec succès.")
        return redirect('course_list')
    
    context = {
        'title': f"Confirmer la suppression du Cours : {course.name}",
        'course': course,
    }
    return render(request, 'school/course_confirm_delete.html', context)

# 1. Vue pour lister les notes
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER], login_url='/login/')
def grade_list(request):
    """
    Vue pour lister les notes, filtrées par l'école de l'utilisateur.
    La direction voit toutes les notes de l'école.
    L'enseignant voit les notes qu'il a données ou celles des cours qu'il enseigne.
    """
    user = request.user
    grades = Grade.objects.none()

    if user.school:
        if user.user_type == UserRole.DIRECTION:
            grades = Grade.objects.filter(
                enrollment_courseclasse_school=user.school
            ).select_related(
                'enrollment_student', 'enrollment_course', 'evaluation'
            ).order_by(
                'enrollment_studentlast_name', 'enrollmentcourse_name'
            )
        elif user.user_type == UserRole.TEACHER:
            grades = Grade.objects.filter(
                enrollment_courseclasse_school=user.school,
                enrollment_course_teachers=user # Les notes des cours que l'enseignant enseigne
            ).select_related(
                'enrollment_student', 'enrollment_course', 'evaluation'
            ).order_by(
                'enrollment_studentlast_name', 'enrollmentcourse_name'
            ).distinct() # Use distinct to avoid duplicates if a teacher teaches multiple courses with same students/grades

            # Alternativement, si on veut seulement les notes qu'il a données
            # grades = Grade.objects.filter(graded_by=user, enrollment_courseclasse_school=user.school)
    else:
        messages.warning(request, "Votre compte n'est pas associé à une école.")

    context = {
        'title': 'Liste des Notes',
        'grades': grades,
    }
    return render(request, 'school/grade_list.html', context)


# 2. Vue pour créer une nouvelle note
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER], login_url='/login/')
def grade_create(request):
    """
    Vue pour ajouter une nouvelle note. Accessible par la direction et les enseignants.
    """
    user = request.user
    if not user.school:
        messages.warning(request, "Votre compte n'est pas associé à une école. Impossible d'ajouter une note.")
        return redirect('home')

    if request.method == 'POST':
        form = GradeForm(request.POST, school=user.school)
        if form.is_valid():
            grade = form.save(commit=False)
            grade.graded_by = user # L'utilisateur connecté est celui qui donne la note
            grade.save()
            messages.success(request, f"La note pour {grade.enrollment.student.get_full_name} en {grade.enrollment.course.name} a été ajoutée.")
            return redirect('grade_detail', pk=grade.pk)
        else:
            messages.error(request, "Erreur lors de l'ajout de la note. Veuillez vérifier les informations.")
    else:
        form = GradeForm(school=user.school)

    context = {
        'title': 'Ajouter une Note',
        'form': form,
    }
    return render(request, 'school/grade_form.html', context)


# 3. Vue pour afficher les détails d'une note
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER, UserRole.PARENT, UserRole.STUDENT], login_url='/login/')
def grade_detail(request, pk):
    """
    Vue pour afficher les détails d'une note spécifique.
    Accessible par la direction, les enseignants, les parents et les élèves (pour leurs propres notes).
    """
    user = request.user
    grade = get_object_or_404(
        Grade.objects.select_related('enrollment_student', 'enrollment_course', 'evaluation', 'graded_by'),
        pk=pk,
        enrollment_courseclasse_school=user.school # S'assurer que la note appartient à l'école de l'utilisateur
    )

    # Vérification des autorisations :
    authorized = False
    if user.user_type == UserRole.DIRECTION:
        authorized = True
    elif user.user_type == UserRole.TEACHER:
        # L'enseignant peut voir la note s'il l'a donnée ou s'il enseigne le cours associé
        if grade.graded_by == user or grade.enrollment.course.teachers.filter(pk=user.pk).exists():
            authorized = True
    elif user.user_type == UserRole.PARENT:
        # Un parent peut voir la note si l'élève est l'un de ses enfants
        if user.parent_profile.children.filter(pk=grade.enrollment.student.pk).exists():
            authorized = True
    elif user.user_type == UserRole.STUDENT:
        # Un élève peut voir sa propre note
        if grade.enrollment.student.user == user:
            authorized = True
    
    if not authorized:
        messages.error(request, "Vous n'êtes pas autorisé à voir cette note.")
        return redirect('grade_list') # Redirige vers la liste des notes ou un autre endroit approprié

    context = {
        'title': 'Détails de la Note',
        'grade': grade,
    }
    return render(request, 'school/grade_detail.html', context)


# 4. Vue pour modifier une note existante
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER], login_url='/login/')
def grade_update(request, pk):
    """
    Vue pour modifier une note existante. Accessible par la direction et l'enseignant qui l'a donnée.
    """
    user = request.user
    grade = get_object_or_404(
        Grade.objects.select_related('enrollment_courseclasse_school'),
        pk=pk,
        enrollment_courseclasse_school=user.school
    )

    # L'enseignant peut modifier uniquement s'il a donné la note (ou si la direction peut faire plus)
    if user.user_type == UserRole.TEACHER and grade.graded_by != user:
        messages.error(request, "Vous n'êtes pas autorisé à modifier cette note.")
        return redirect('grade_detail', pk=grade.pk) # Ou à la liste des notes

    if request.method == 'POST':
        form = GradeForm(request.POST, instance=grade, school=user.school)
        if form.is_valid():
            form.save()
            messages.success(request, f"La note pour {grade.enrollment.student.get_full_name} a été mise à jour.")
            return redirect('grade_detail', pk=grade.pk)
        else:
            messages.error(request, "Erreur lors de la mise à jour de la note. Veuillez vérifier les informations.")
    else:
        form = GradeForm(instance=grade, school=user.school)

    context = {
        'title': 'Modifier la Note',
        'form': form,
        'grade': grade, # Passez l'objet grade pour le titre et les liens
    }
    return render(request, 'school/grade_form.html', context)


# 5. Vue pour supprimer une note
@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/')
def grade_delete(request, pk):
    """
    Vue pour supprimer une note. Accessible uniquement par la direction.
    """
    user = request.user
    grade = get_object_or_404(
        Grade.objects.select_related('enrollment_student', 'enrollment_course'),
        pk=pk,
        enrollment_courseclasse_school=user.school
    )

    if request.method == 'POST':
        student_name = grade.enrollment.student.get_full_name()
        course_name = grade.enrollment.course.name
        grade.delete()
        messages.success(request, f"La note de {student_name} en {course_name} a été supprimée.")
        return redirect('grade_list')
    
    context = {
        'title': 'Confirmer la Suppression de la Note',
        'grade': grade,
    }
    return render(request, 'school/grade_confirm_delete.html', context)


# 6. Vue pour afficher toutes les notes d'un élève
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER, UserRole.PARENT, UserRole.STUDENT], login_url='/login/')
def student_grades(request, student_pk):
    """
    Vue pour afficher toutes les notes d'un élève spécifique.
    Accessible par la direction, les enseignants, les parents (pour leurs enfants) et l'élève lui-même.
    """
    user = request.user
    
    # Récupérer l'objet Student (de l'application profiles ou school, assurez-vous d'utiliser le bon)
    # Si student est dans profiles.models, utilisez ProfileStudent
    student = get_object_or_404(ProfileStudent, pk=student_pk, school=user.school)

    # Vérification des autorisations :
    authorized = False
    if user.user_type == UserRole.DIRECTION:
        authorized = True
    elif user.user_type == UserRole.TEACHER:
        # Un enseignant peut voir les notes des élèves de ses classes ou des cours qu'il enseigne
        if student.classes.filter(homeroom_teacher=user).exists() or student.enrollments.filter(course__teachers=user).exists():
            authorized = True
    elif user.user_type == UserRole.PARENT:
        if student.parents.filter(user=user).exists(): # Assurez-vous que cette relation existe
            authorized = True
    elif user.user_type == UserRole.STUDENT:
        if student.user == user:
            authorized = True
    
    if not authorized:
        messages.error(request, "Vous n'êtes pas autorisé à voir les notes de cet élève.")
        return redirect('home') # Ou une page d'erreur

    grades = Grade.objects.filter(
        enrollment__student=student,
        enrollment_courseclasse_school=user.school
    ).select_related(
        'enrollment__course', 'evaluation', 'graded_by'
    ).order_by(
        'enrollment_academic_periodstart_date', 'enrollmentcoursename', '-evaluation_date'
    )

    context = {
        'title': f"Notes de {student.get_full_name()}",
        'student': student,
        'grades': grades,
    }
    return render(request, 'school/student_grades.html', context)

# ... (vos autres vues) ...

# 1. Vue pour lister les présences
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER], login_url='/login/')
def attendance_list(request):
    """
    Vue pour lister les enregistrements de présence/absence, filtrés par l'école de l'utilisateur.
    La direction voit toutes les présences de l'école.
    L'enseignant voit les présences des cours qu'il enseigne.
    """
    user = request.user
    attendances = Attendance.objects.none()

    if user.school:
        if user.user_type == UserRole.DIRECTION:
            attendances = Attendance.objects.filter(
                enrollment_courseclasse_school=user.school
            ).select_related(
                'enrollment_student', 'enrollment_course', 'marked_by'
            ).order_by(
                '-date', 'enrollment_student_last_name'
            )
        elif user.user_type == UserRole.TEACHER:
            # L'enseignant voit les présences pour les cours qu'il enseigne
            attendances = Attendance.objects.filter(
                enrollment_courseclasse_school=user.school,
                enrollment_course_teachers=user
            ).select_related(
                'enrollment_student', 'enrollment_course', 'marked_by'
            ).order_by(
                '-date', 'enrollment_student_last_name'
            ).distinct()
    else:
        messages.warning(request, "Votre compte n'est pas associé à une école.")

    context = {
        'title': 'Liste des Présences/Absences',
        'attendances': attendances,
    }
    return render(request, 'school/attendance_list.html', context)


# 2. Vue pour créer un nouvel enregistrement de présence
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER], login_url='/login/')
def attendance_create(request):
    """
    Vue pour ajouter un nouvel enregistrement de présence/absence.
    Accessible par la direction et les enseignants.
    """
    user = request.user
    if not user.school:
        messages.warning(request, "Votre compte n'est pas associé à une école. Impossible d'ajouter une présence.")
        return redirect('home')

    if request.method == 'POST':
        form = AttendanceForm(request.POST, school=user.school)
        if form.is_valid():
            try:
                attendance = form.save(commit=False)
                attendance.marked_by = user # L'utilisateur connecté est celui qui marque la présence
                attendance.save()
                messages.success(request, f"L'état de présence de {attendance.enrollment.student.get_full_name()} pour le {attendance.date} a été enregistré.")
                return redirect('attendance_detail', pk=attendance.pk)
            except IntegrityError:
                messages.error(request, "Un enregistrement de présence pour cet élève à cette date et ce cours existe déjà.")
        else:
            messages.error(request, "Erreur lors de l'ajout de la présence. Veuillez vérifier les informations.")
    else:
        form = AttendanceForm(initial={'date': date.today()}, school=user.school) # Pré-remplir la date avec la date du jour

    context = {
        'title': 'Ajouter une Présence/Absence',
        'form': form,
    }
    return render(request, 'school/attendance_form.html', context)


# 3. Vue pour afficher les détails d'un enregistrement de présence
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER, UserRole.PARENT, UserRole.STUDENT], login_url='/login/')
def attendance_detail(request, pk):
    """
    Vue pour afficher les détails d'un enregistrement de présence spécifique.
    Accessible par la direction, les enseignants, les parents et les élèves (pour leurs propres enregistrements).
    """
    user = request.user
    attendance = get_object_or_404(
        Attendance.objects.select_related('enrollment_student', 'enrollment_course', 'marked_by'),
        pk=pk,
        enrollment_courseclasse_school=user.school # S'assurer que l'enregistrement appartient à l'école de l'utilisateur
    )

    # Vérification des autorisations :
    authorized = False
    if user.user_type == UserRole.DIRECTION:
        authorized = True
    elif user.user_type == UserRole.TEACHER:
        # L'enseignant peut voir l'enregistrement s'il l'a marqué ou s'il enseigne le cours associé
        if attendance.marked_by == user or attendance.enrollment.course.teachers.filter(pk=user.pk).exists():
            authorized = True
    elif user.user_type == UserRole.PARENT:
        # Un parent peut voir l'enregistrement si l'élève est l'un de ses enfants
        if user.parent_profile.children.filter(pk=attendance.enrollment.student.pk).exists():
            authorized = True
    elif user.user_type == UserRole.STUDENT:
        # Un élève peut voir son propre enregistrement
        if attendance.enrollment.student.user == user:
            authorized = True
    
    if not authorized:
        messages.error(request, "Vous n'êtes pas autorisé à voir cet enregistrement de présence.")
        return redirect('attendance_list')

    context = {
        'title': 'Détails de la Présence',
        'attendance': attendance,
    }
    return render(request, 'school/attendance_detail.html', context)


# 4. Vue pour modifier un enregistrement de présence existant
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER], login_url='/login/')
def attendance_update(request, pk):
    """
    Vue pour modifier un enregistrement de présence existant.
    Accessible par la direction et l'enseignant qui l'a marqué.
    """
    user = request.user
    attendance = get_object_or_404(
        Attendance.objects.select_related('enrollment_courseclasse_school'),
        pk=pk,
        enrollment_courseclasse_school=user.school
    )

    # L'enseignant peut modifier uniquement s'il a marqué la présence
    if user.user_type == UserRole.TEACHER and attendance.marked_by != user:
        messages.error(request, "Vous n'êtes pas autorisé à modifier cet enregistrement.")
        return redirect('attendance_detail', pk=attendance.pk)

    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=attendance, school=user.school)
        if form.is_valid():
            form.save()
            messages.success(request, f"L'enregistrement de présence de {attendance.enrollment.student.get_full_name()} a été mis à jour.")
            return redirect('attendance_detail', pk=attendance.pk)
        else:
            messages.error(request, "Erreur lors de la mise à jour de l'enregistrement. Veuillez vérifier les informations.")
    else:
        form = AttendanceForm(instance=attendance, school=user.school)

    context = {
        'title': 'Modifier la Présence',
        'form': form,
        'attendance': attendance, # Passez l'objet attendance pour le titre et les liens
    }
    return render(request, 'school/attendance_form.html', context)


# 5. Vue pour supprimer un enregistrement de présence
@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/')
def attendance_delete(request, pk):
    """
    Vue pour supprimer un enregistrement de présence. Accessible uniquement par la direction.
    """
    user = request.user
    attendance = get_object_or_404(
        Attendance.objects.select_related('enrollment_student', 'enrollment_course'),
        pk=pk,
        enrollment_courseclasse_school=user.school
    )

    if request.method == 'POST':
        student_name = attendance.enrollment.student.get_full_name()
        date_attendance = attendance.date
        attendance.delete()
        messages.success(request, f"L'enregistrement de présence de {student_name} pour le {date_attendance} a été supprimé.")
        return redirect('attendance_list')
    
    context = {
        'title': 'Confirmer la Suppression de la Présence',
        'attendance': attendance,
    }
    return render(request, 'school/attendance_confirm_delete.html', context)


# 6. Vue pour gérer la présence d'une classe pour une date donnée
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER], login_url='/login/')
def class_attendance(request, classe_pk, date_str):
    """
    Permet de visualiser et de marquer la présence pour tous les élèves d'une classe
    pour une date donnée.
    La date est passée sous forme de chaîne de caractères (YYYY-MM-DD).
    """
    user = request.user
    classe = get_object_or_404(Classe, pk=classe_pk, school=user.school)
    
    try:
        attendance_date = date.fromisoformat(date_str) # Convertir la chaîne en objet date
    except ValueError:
        messages.error(request, "Format de date invalide. Utilisez YYYY-MM-DD.")
        return redirect('classe_detail', pk=classe.pk) # Rediriger vers la page de la classe

    # Vérification des autorisations pour la classe :
    if user.user_type == UserRole.TEACHER and not classe.homeroom_teacher == user and not classe.courses.filter(teachers=user).exists():
        messages.error(request, "Vous n'êtes pas autorisé à gérer la présence de cette classe.")
        return redirect('home') # Ou dashboard de l'enseignant

    # Récupérer tous les élèves inscrits à des cours de cette classe
    # Il est plus logique de regarder les élèves assignés à la classe directement
    students_in_class = ProfileStudent.objects.filter(
        classes=classe,
        school=user.school
    ).order_by('last_name', 'first_name')

    # Récupérer les enregistrements de présence existants pour cette classe et cette date
    existing_attendances = Attendance.objects.filter(
        enrollment_student_in=students_in_class,
        date=attendance_date,
        enrollment_course_classe=classe, # S'assurer que c'est bien la classe et pas juste l'élève
        enrollment_courseclasse_school=user.school
    ).select_related('enrollment_student', 'enrollment_course')

    # Créer un dictionnaire pour un accès facile par élève et cours
    attendance_map = {}
    for att in existing_attendances:
        key = (att.enrollment.student.pk, att.enrollment.course.pk) # Clé (student_id, course_id)
        attendance_map[key] = att

    if request.method == 'POST':
        # Gérer la soumission du formulaire de présence par élève/cours
        errors = False
        for student in students_in_class:
            for enrollment in student.enrollments.filter(course_classe=classe, courseclasse_school=user.school):
                is_present_key = f'is_present_{enrollment.pk}'
                reason_key = f'reason_for_absence_{enrollment.pk}'
                
                is_present = request.POST.get(is_present_key) == 'on' # Checkbox value
                reason = request.POST.get(reason_key, '').strip()

                existing_att = attendance_map.get((enrollment.student.pk, enrollment.course.pk))

                if not is_present and not reason:
                    messages.error(request, f"Veuillez fournir une raison d'absence pour {enrollment.student.get_full_name()} en {enrollment.course.name}.")
                    errors = True
                    break # Sortir du loop interne pour éviter plusieurs erreurs
                
                if existing_att:
                    # Mettre à jour l'enregistrement existant
                    if existing_att.is_present != is_present or existing_att.reason_for_absence != reason:
                        existing_att.is_present = is_present
                        existing_att.reason_for_absence = reason if not is_present else ''
                        existing_att.marked_by = user
                        existing_att.save()
                else:
                    # Créer un nouvel enregistrement
                    if not is_present or reason: # Créer un enregistrement si absent ou si une raison est donnée même si présent (shouldn't happen with clean method)
                        try:
                            Attendance.objects.create(
                                enrollment=enrollment,
                                date=attendance_date,
                                is_present=is_present,
                                reason_for_absence=reason if not is_present else '',
                                marked_by=user
                            )
                        except IntegrityError:
                            messages.warning(request, f"Doublon pour {enrollment.student.get_full_name()} en {enrollment.course.name} à cette date.")
                            errors = True
                            break

            if errors: # Si une erreur a été détectée, ne pas continuer la soumission
                break
        
        if not errors:
            messages.success(request, f"La présence pour la classe {classe.name} du {attendance_date.strftime('%d/%m/%Y')} a été mise à jour.")
            return redirect('class_attendance', classe_pk=classe.pk, date_str=date_str)
        
        # Re-charger les enregistrements après soumission pour que le template ait les dernières données
        existing_attendances = Attendance.objects.filter(
            enrollment_student_in=students_in_class,
            date=attendance_date,
            enrollment_course_classe=classe,
            enrollment_courseclasse_school=user.school
        ).select_related('enrollment_student', 'enrollment_course')

        attendance_map = {}
        for att in existing_attendances:
            key = (att.enrollment.student.pk, att.enrollment.course.pk)
            attendance_map[key] = att

    context = {
        'title': f"Gestion de la Présence pour {classe.name} le {attendance_date.strftime('%d/%m/%Y')}",
        'classe': classe,
        'attendance_date': attendance_date,
        'students_in_class': students_in_class,
        'attendance_map': attendance_map, # Passer le dictionnaire d'objets Attendance
        # Optionnel: Préparez les données pour afficher tous les cours associés à la classe
        'courses_in_class': Course.objects.filter(classe=classe, school=user.school).order_by('name'),
    }
    return render(request, 'school/class_attendance.html', context)


# ... (vos autres vues) ...

# 1. Vue pour lister les notifications
@login_required
def notification_list(request):
    """
    Vue pour lister les notifications.
    Chaque utilisateur voit ses notifications reçues.
    La direction voit toutes les notifications de son école.
    """
    user = request.user
    notifications = Notification.objects.none()

    if user.school:
        if user.user_type == UserRole.DIRECTION:
            # La direction voit toutes les notifications de son école
            notifications = Notification.objects.filter(
                Q(sender_school=user.school) | Q(recipient_school=user.school) # Assurez-vous d'avoir Q importé
            ).select_related(
                'sender', 'recipient'
            ).order_by('-date_sent')
        else:
            # Les autres utilisateurs voient les notifications qu'ils ont envoyées ou reçues
            notifications = Notification.objects.filter(
                Q(sender=user) | Q(recipient=user)
            ).select_related(
                'sender', 'recipient'
            ).order_by('-date_sent')
    else:
        messages.warning(request, "Votre compte n'est pas associé à une école. Impossible d'afficher les notifications.")

    # Pour les notifications non lues du user
    unread_notifications_count = notifications.filter(is_read=False, recipient=user).count()

    context = {
        'title': 'Mes Notifications',
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    }
    return render(request, 'school/notification_list.html', context)


# 2. Vue pour créer une nouvelle notification
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.TEACHER, UserRole.ACCOUNTING], login_url='/login/')
def notification_create(request):
    """
    Vue pour envoyer une nouvelle notification.
    Accessible par la direction, les enseignants et la comptabilité.
    """
    user = request.user
    if not user.school:
        messages.warning(request, "Votre compte n'est pas associé à une école. Impossible d'envoyer une notification.")
        return redirect('home')

    if request.method == 'POST':
        form = NotificationForm(request.POST, school=user.school)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.sender = user # L'utilisateur connecté est l'expéditeur
            notification.date_sent = timezone.now()
            notification.save()
            messages.success(request, f"Notification envoyée à {notification.recipient.get_full_name()}.")
            return redirect('notification_list')
        else:
            messages.error(request, "Erreur lors de l'envoi de la notification. Veuillez vérifier les informations.")
    else:
        form = NotificationForm(school=user.school)

    context = {
        'title': 'Envoyer une Notification',
        'form': form,
    }
    return render(request, 'school/notification_form.html', context)


# 3. Vue pour afficher les détails d'une notification
@login_required
def notification_detail(request, pk):
    """
    Vue pour afficher les détails d'une notification spécifique et la marquer comme lue.
    Accessible par l'expéditeur, le destinataire et la direction (de la même école).
    """
    user = request.user
    notification = get_object_or_404(
        Notification.objects.select_related('sender', 'recipient'),
        pk=pk,
    )

    # Assurez-vous que la notification est liée à l'école de l'utilisateur
    if not (notification.sender and notification.sender.school == user.school) and \
       not (notification.recipient and notification.recipient.school == user.school):
        messages.error(request, "Vous n'êtes pas autorisé à voir cette notification (hors de votre école).")
        return redirect('notification_list')

    # Vérification des autorisations :
    authorized = False
    if user.user_type == UserRole.DIRECTION:
        authorized = True
    elif notification.sender == user or notification.recipient == user:
        authorized = True
    
    if not authorized:
        messages.error(request, "Vous n'êtes pas autorisé à voir cette notification.")
        return redirect('notification_list')

    # Marquer la notification comme lue si l'utilisateur actuel est le destinataire et qu'elle n'est pas déjà lue
    if notification.recipient == user and not notification.is_read:
        notification.is_read = True
        notification.save()
        messages.info(request, "La notification a été marquée comme lue.")

    context = {
        'title': 'Détails de la Notification',
        'notification': notification,
    }
    return render(request, 'school/notification_detail.html', context)


# 4. Vue pour modifier une notification existante (généralement peu courant pour les notifications envoyées)
@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/') # Seule la direction peut modifier une notification envoyée
def notification_update(request, pk):
    """
    Vue pour modifier une notification existante.
    Normalement, seules les notifications non envoyées (brouillons) seraient modifiables.
    Pour simplifier, seul un utilisateur de la direction peut modifier n'importe quelle notification.
    """
    user = request.user
    notification = get_object_or_404(
        Notification.objects.select_related('sender', 'recipient'),
        pk=pk,
    )

    # S'assurer que la notification est liée à l'école de l'utilisateur
    if not (notification.sender and notification.sender.school == user.school) and \
       not (notification.recipient and notification.recipient.school == user.school):
        messages.error(request, "Vous n'êtes pas autorisé à modifier cette notification (hors de votre école).")
        return redirect('notification_list')

    if request.method == 'POST':
        form = NotificationForm(request.POST, instance=notification, school=user.school)
        if form.is_valid():
            form.save()
            messages.success(request, "Notification mise à jour avec succès.")
            return redirect('notification_detail', pk=notification.pk)
        else:
            messages.error(request, "Erreur lors de la mise à jour de la notification. Veuillez vérifier les informations.")
    else:
        form = NotificationForm(instance=notification, school=user.school)

    context = {
        'title': 'Modifier la Notification',
        'form': form,
        'notification': notification,
    }
    return render(request, 'school/notification_form.html', context)


# 5. Vue pour marquer une notification comme lue (séparément du détail si besoin)
@login_required
def notification_mark_read(request, pk):
    """
    Marque une notification spécifique comme lue.
    Accessible uniquement par le destinataire de la notification.
    """
    user = request.user
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=user, # Seul le destinataire peut la marquer comme lue
        is_read=False # Ne la marque que si elle n'est pas déjà lue
    )

    if notification:
        notification.is_read = True
        notification.save()
        messages.success(request, "Notification marquée comme lue.")
    else:
        messages.warning(request, "Notification non trouvée ou déjà lue, ou vous n'êtes pas le destinataire.")
    
    # Rediriger vers l'endroit où l'utilisateur était ou la liste des notifications
    return redirect(request.META.get('HTTP_REFERER', 'notification_list'))


# 6. Vue pour supprimer une notification
@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/') # Seule la direction peut supprimer
def notification_delete(request, pk):
    """
    Vue pour supprimer une notification.
    Accessible uniquement par la direction.
    """
    user = request.user
    notification = get_object_or_404(
        Notification.objects.select_related('sender', 'recipient'),
        pk=pk
    )

    # S'assurer que la notification est liée à l'école de l'utilisateur
    if not (notification.sender and notification.sender.school == user.school) and \
       not (notification.recipient and notification.recipient.school == user.school):
        messages.error(request, "Vous n'êtes pas autorisé à supprimer cette notification (hors de votre école).")
        return redirect('notification_list')

    if request.method == 'POST':
        notification.delete()
        messages.success(request, "Notification supprimée avec succès.")
        return redirect('notification_list')
    
    context = {
        'title': 'Confirmer la Suppression de la Notification',
        'notification': notification,
    }
    return render(request, 'school/notification_confirm_delete.html', context)


# ... (vos autres vues) ...

# 1. Vue pour lister les paiements
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.ACCOUNTING], login_url='/login/')
def payment_list(request):
    """
    Vue pour lister les paiements, filtrés par l'école de l'utilisateur.
    La direction et la comptabilité voient tous les paiements de l'école.
    """
    user = request.user
    payments = Payment.objects.none()

    if user.school:
        payments = Payment.objects.filter(
            student__school=user.school # Filtrer les paiements par l'école de l'élève
        ).select_related(
            'student', 'academic_period', 'received_by'
        ).order_by(
            '-payment_date', 'student__last_name' # Par date de paiement la plus récente
        )
    else:
        messages.warning(request, "Votre compte n'est pas associé à une école.")

    context = {
        'title': 'Liste des Paiements',
        'payments': payments,
    }
    return render(request, 'school/payment_list.html', context)


# 2. Vue pour créer un nouveau paiement
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.ACCOUNTING], login_url='/login/')
def payment_create(request):
    """
    Vue pour enregistrer un nouveau paiement.
    Accessible par la direction et la comptabilité.
    """
    user = request.user
    if not user.school:
        messages.warning(request, "Votre compte n'est pas associé à une école. Impossible d'ajouter un paiement.")
        return redirect('home')

    if request.method == 'POST':
        form = PaymentForm(request.POST, school=user.school)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.received_by = user # L'utilisateur connecté est celui qui reçoit le paiement
            payment.save()
            messages.success(request, f"Le paiement de {payment.amount} pour {payment.student.get_full_name()} a été enregistré.")
            return redirect('payment_detail', pk=payment.pk)
        else:
            messages.error(request, "Erreur lors de l'enregistrement du paiement. Veuillez vérifier les informations.")
    else:
        form = PaymentForm(initial={'payment_date': date.today()}, school=user.school) # Pré-remplir la date du jour

    context = {
        'title': 'Enregistrer un Nouveau Paiement',
        'form': form,
    }
    return render(request, 'school/payment_form.html', context)


# 3. Vue pour afficher les détails d'un paiement
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.ACCOUNTING, UserRole.PARENT, UserRole.STUDENT], login_url='/login/')
def payment_detail(request, pk):
    """
    Vue pour afficher les détails d'un paiement spécifique.
    Accessible par la direction, la comptabilité, les parents et l'élève (pour leurs propres paiements).
    """
    user = request.user
    payment = get_object_or_404(
        Payment.objects.select_related('student', 'academic_period', 'received_by'),
        pk=pk,
        student__school=user.school # S'assurer que le paiement appartient à l'école de l'utilisateur
    )

    # Vérification des autorisations :
    authorized = False
    if user.user_type in [UserRole.DIRECTION, UserRole.ACCOUNTING]:
        authorized = True
    elif user.user_type == UserRole.PARENT:
        # Un parent peut voir le paiement si l'élève est l'un de ses enfants
        if user.parent_profile.children.filter(pk=payment.student.pk).exists():
            authorized = True
    elif user.user_type == UserRole.STUDENT:
        # Un élève peut voir ses propres paiements
        if payment.student.user == user:
            authorized = True
    
    if not authorized:
        messages.error(request, "Vous n'êtes pas autorisé à voir ce paiement.")
        return redirect('payment_list')

    context = {
        'title': 'Détails du Paiement',
        'payment': payment,
    }
    return render(request, 'school/payment_detail.html', context)


# 4. Vue pour modifier un paiement existant
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.ACCOUNTING], login_url='/login/')
def payment_update(request, pk):
    """
    Vue pour modifier un paiement existant.
    Accessible par la direction et la comptabilité (celui qui l'a reçu ou tout membre de la comptabilité).
    """
    user = request.user
    payment = get_object_or_404(
        Payment.objects.select_related('student__school'),
        pk=pk,
        student__school=user.school
    )

    # La comptabilité peut modifier si elle a reçu le paiement
    # Ou la direction peut modifier n'importe quel paiement
    if user.user_type == UserRole.ACCOUNTING and payment.received_by != user:
        messages.error(request, "Vous n'êtes pas autorisé à modifier ce paiement.")
        return redirect('payment_detail', pk=payment.pk)

    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment, school=user.school)
        if form.is_valid():
            form.save()
            messages.success(request, f"Le paiement de {payment.amount} pour {payment.student.get_full_name()} a été mis à jour.")
            return redirect('payment_detail', pk=payment.pk)
        else:
            messages.error(request, "Erreur lors de la mise à jour du paiement. Veuillez vérifier les informations.")
    else:
        form = PaymentForm(instance=payment, school=user.school)

    context = {
        'title': 'Modifier le Paiement',
        'form': form,
        'payment': payment,
    }
    return render(request, 'school/payment_form.html', context)


# 5. Vue pour supprimer un paiement
@login_required
@user_passes_test(lambda u: u.user_type == UserRole.DIRECTION, login_url='/login/') # Seule la direction peut supprimer un paiement
def payment_delete(request, pk):
    """
    Vue pour supprimer un paiement. Accessible uniquement par la direction.
    """
    user = request.user
    payment = get_object_or_404(
        Payment.objects.select_related('student', 'academic_period'),
        pk=pk,
        student__school=user.school
    )

    if request.method == 'POST':
        student_name = payment.student.get_full_name()
        amount = payment.amount
        payment.delete()
        messages.success(request, f"Le paiement de {amount} pour {student_name} a été supprimé.")
        return redirect('payment_list')
    
    context = {
        'title': 'Confirmer la Suppression du Paiement',
        'payment': payment,
    }
    return render(request, 'school/payment_confirm_delete.html', context)


# 6. Vue pour afficher tous les paiements d'un élève
@login_required
@user_passes_test(lambda u: u.user_type in [UserRole.DIRECTION, UserRole.ACCOUNTING, UserRole.PARENT, UserRole.STUDENT], login_url='/login/')
def student_payments(request, student_pk):
    """
    Vue pour afficher tous les paiements d'un élève spécifique.
    Accessible par la direction, la comptabilité, les parents (pour leurs enfants) et l'élève lui-même.
    """
    user = request.user
    
    student = get_object_or_404(ProfileStudent, pk=student_pk, school=user.school)

    # Vérification des autorisations :
    authorized = False
    if user.user_type in [UserRole.DIRECTION, UserRole.ACCOUNTING]:
        authorized = True
    elif user.user_type == UserRole.PARENT:
        if student.parents.filter(user=user).exists(): # Assurez-vous que cette relation existe
            authorized = True
    elif user.user_type == UserRole.STUDENT:
        if student.user == user:
            authorized = True
    
    if not authorized:
        messages.error(request, "Vous n'êtes pas autorisé à voir les paiements de cet élève.")
        return redirect('home')

    payments = Payment.objects.filter(
        student=student,
        student__school=user.school
    ).select_related(
        'academic_period', 'received_by'
    ).order_by(
        '-payment_date'
    )

    context = {
        'title': f"Historique des Paiements de {student.get_full_name()}",
        'student': student,
        'payments': payments,
    }
    return render(request, 'school/student_payments.html', context)

# ... (vos autres vues) ... 