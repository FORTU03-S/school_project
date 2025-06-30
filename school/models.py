from django.db import models
from django.utils import timezone
from django.conf import settings


 # Assurez-vous que le modèle CustomUser est défini dans profiles.models

# IMPORTS: toujours éviter les imports circulaires avec profiles.models
# Nous utilisons des chaînes de caractères pour les références aux modèles d'autres applications
# comme 'profiles.CustomUser' ou 'profiles.Student' pour éviter les importations circulaires.

# --- Nouveau Modèle : School ---
class School(models.Model):
    """
    Représente une école au sein du système de gestion.
    Chaque école aura ses propres périodes académiques, classes, matières, etc.
    """
    name = models.CharField(max_length=200, unique=True, verbose_name="Nom de l'École")
    address = models.TextField(blank=True, null=True, verbose_name="Adresse")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Numéro de Téléphone")
    email = models.EmailField(blank=True, null=True, verbose_name="Email de contact")
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True, verbose_name="Logo de l'École")
    is_active = models.BooleanField(default=True, verbose_name="Active") # Pour activer/désactiver une école

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "École"
        verbose_name_plural = "Écoles"
        ordering = ['name']



## Modèles existants (modifiés pour inclure School et corrections)

### Modèle AcademicPeriod


class AcademicPeriod(models.Model):
    """
    Définit une période académique (par exemple, année scolaire, semestre) pour une école spécifique.
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='academic_periods', verbose_name="École")
    name = models.CharField(max_length=100, verbose_name="Nom de la Période")
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(verbose_name="Date de fin")
    is_current = models.BooleanField(default=False, verbose_name="Période Actuelle")

    def __str__(self):
        return f"{self.name} ({self.school.name})"

    class Meta:
        # Le nom de la période doit être unique PAR école
        unique_together = ('school', 'name')
        verbose_name = "Période Académique"
        verbose_name_plural = "Périodes Académiques"
        ordering = ['school__name', '-start_date']
        
class Classe(models.Model):
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=50) # Ex: 1ère Année, 2ème Année, etc.
    school = models.ForeignKey('School', on_delete=models.CASCADE, related_name='classes')
    
    description = models.TextField(blank=True, null=True, verbose_name="Description de la Classe")
    # Si vous ne voulez PAS de champ description pour une classe, alors supprimez cette ligne du modèle.

    # 2. Le champ 'teachers' (relation Many-to-Many avec les utilisateurs de type TEACHER)
    # C'est essentiel pour assigner des enseignants à la classe.
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, # Référence votre modèle d'utilisateur personnalisé (CustomUser)
        related_name='classes_taught', # Nom pour la relation inverse (User.classes_taught)
        limit_choices_to={'user_type': 'TEACHER'}, # Limite les choix aux utilisateurs de type ENSEIGNANT
        blank=True, # Rend le champ optionnel (une classe peut exister sans enseignant assigné au début)
        verbose_name="Enseignants de la Classe"
    )
    # --- AJOUTEZ CES DEUX CHAMPS À VOTRE MODÈLE CLASSE ---
    academic_period = models.ForeignKey(
        'school.AcademicPeriod', # Assurez-vous que c'est la bonne référence à votre modèle AcademicPeriod
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classes_in_period'
    )
    main_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Référence à votre modèle d'utilisateur personnalisé (CustomUser)
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='main_classes', # Les classes dont cet utilisateur est l'enseignant principal
        limit_choices_to={'user_type': 'TEACHER'} # Optionnel: Filtrer pour n'afficher que les utilisateurs de type Enseignant
    )
    # --- FIN DES CHAMPS À AJOUTER ---
    courses = models.ManyToManyField(
        'Course',
        related_name='classes_assigned', # Permet d'accéder aux classes via course.classes_assigned.all()
        blank=True, # Une classe peut être créée sans cours assignés au début
        verbose_name="Cours associés à cette Classe"
         )
    class Meta:
        unique_together = ('name', 'academic_period', 'school')
        verbose_name = "Classe"
        verbose_name_plural = "Classes"
        # Ajout d'un ordering par défaut
        ordering = ['school__name', 'academic_period__name', 'name']


    def __str__(self):
        # Amélioration du _str_ pour gérer les cas où academic_period est null
        period_name = self.academic_period.name if self.academic_period else 'N/A'
        return f"{self.name} ({self.level}) - {self.school.name} - {period_name}"
        
class Subject(models.Model):
    """
    Définit une matière enseignée dans une école.
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='subjects', verbose_name="École")
    name = models.CharField(max_length=100, verbose_name="Nom de la Matière")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    def __str__(self):
        return f"{self.name} ({self.school.name})"

    class Meta:
        # Unique par école
        unique_together = ('school', 'name')
        verbose_name = "Matière"
        verbose_name_plural = "Matières"
        ordering = ['school__name', 'name']
class Course(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='courses',
        verbose_name="École"
    )
    name = models.CharField(max_length=100, verbose_name="Nom du Cours")

    subjects = models.ManyToManyField(
        'Subject',
        related_name='courses_offered',
        verbose_name="Matières"
    )

    code = models.CharField(
        max_length=20,
        unique=False, # ⭐ TRÈS IMPORTANT : Doit être 'False' car l'unicité est gérée par unique_together
        blank=True,
        null=True,
        verbose_name="Code du Cours"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description du Cours"
    )
    credits = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.0,
        verbose_name="Crédits ECTS/Unités"
    )
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='taught_courses',
        limit_choices_to={'user_type': 'TEACHER'},
        blank=True,
        verbose_name="Enseignants Associés"
    )
    
    # La relation 'classes' est bien définie ici, et aussi sur le modèle Classe.
    # C'est une relation ManyToMany bidirectionnelle, ce qui est correct.
    classes = models.ManyToManyField(
        'Classe', # Utilisation de la chaîne 'Classe' pour éviter les problèmes d'ordre de définition
        related_name='courses_taught',
        blank=True,
        verbose_name="Classes Associées"
    )

    academic_period = models.ForeignKey(
        'school.AcademicPeriod',
        on_delete=models.CASCADE,
        verbose_name="Période Académique",
    )

    def __str__(self):
        subjects_names = ", ".join([s.name for s in self.subjects.all()])
        subjects_display = subjects_names if subjects_names else "Aucune matière"
        code_display = f" ({self.code})" if self.code else ""
        return f"{self.name}{code_display} - {subjects_display} ({self.school.name} - {self.academic_period.name})"

    class Meta:
        # L'unicité du code est maintenant gérée par la combinaison de ces champs.
        # Un même code peut être utilisé dans une autre école ou période.
        unique_together = ('school', 'code', 'academic_period') 
        # Si vous préférez que le nom soit unique plutôt que le code, remplacez 'code' par 'name' ici.
        # unique_together = ('school', 'name', 'academic_period') 

        verbose_name = "Cours"
        verbose_name_plural = "Cours"
        ordering = ['school__name', 'academic_period__name', 'name']
        # 'subjects__name' peut causer des doublons dans le résultat si un cours a plusieurs matières
        # et n'est généralement pas utilisé dans l'ordering de Meta, sauf si vous comprenez les implications
        
class ClassAssignment(models.Model):
    """
    Associe un enseignant à une classe pour une période académique donnée.
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='class_assignments', verbose_name="École")
    teacher = models.ForeignKey(
        'profiles.CustomUser', # Référence par chaîne de caractères
        on_delete=models.CASCADE,
        related_name='class_assignments',
        limit_choices_to={'user_type': 'TEACHER'},
        verbose_name="Enseignant Assigné"
    )
    classe = models.ForeignKey(
        Classe,
        on_delete=models.CASCADE,
        related_name='assigned_teachers',
        verbose_name="Classe Assignée"
    )
    academic_period = models.ForeignKey(
        AcademicPeriod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Période Académique"
    )

    class Meta:
        # Unique par école, enseignant, classe et période pour éviter les doublons
        unique_together = ('school', 'teacher', 'classe', 'academic_period')
        verbose_name = "Assignation de Classe"
        verbose_name_plural = "Assignations de Classes"
        # Correction : chemins corrects pour les champs liés
        ordering = ['school__name', 'academic_period__start_date', 'classe__name', 'teacher__last_name', 'teacher__first_name']
        
class Enrollment(models.Model):
    """
    Représente l'inscription d'un élève à un cours pour une période académique.
    """
    # Définition des choix pour le statut d'inscription
    ENROLLMENT_STATUS_CHOICES = [
        ('active', 'Actif'),
        ('inactive', 'Inactif'),
        ('suspended', 'Suspendu'),
        ('completed', 'Terminé'),
        ('withdrawn', 'Abandonné'),
    ]

    # La relation avec l'école est implicitement définie via student_school ou course_school
    student = models.ForeignKey(
        'profiles.Student', # Référence par chaîne de caractères
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name="Élève"
    )
    course = models.ForeignKey(
        'school.Course', # Ajouté 'school.' pour la clarté si Course est dans le même app
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name="Cours"
    )
    academic_period = models.ForeignKey(
        'school.AcademicPeriod', # Ajouté 'school.' pour la clarté si AcademicPeriod est dans le même app
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name="Période Académique"
    )
    enrollment_date = models.DateField(auto_now_add=True, verbose_name="Date d'inscription")

    # NOUVEAU CHAMP : status
    status = models.CharField(
        max_length=20,
        choices=ENROLLMENT_STATUS_CHOICES,
        default='active', # Statut par défaut à 'active'
        verbose_name="Statut d'Inscription",
        help_text="Statut actuel de l'inscription de l'étudiant à ce cours."
    )

    def __str__(self):
        student_name = f"{self.student.first_name} {self.student.last_name}" if self.student else "Élève Inconnu"
        course_name = self.course.name if self.course else "Cours Inconnu"
        academic_period_name = self.academic_period.name if self.academic_period else "Période Inconnue"
        return f"{student_name} inscrit à {course_name} ({academic_period_name}) - Statut: {self.get_status_display()}"

    class Meta:
        # Un étudiant ne peut s'inscrire qu'une seule fois à un cours donné pour une période académique donnée
        unique_together = ('student', 'course', 'academic_period')
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"
        # Correction : accès correct aux champs des modèles liés
        ordering = ['student__school__name', 'student__last_name', 'student__first_name', 'course__name']
          
class Grade(models.Model):
    """
    Enregistre la note obtenue par un élève pour une inscription (enrollment) donnée.
    """
    enrollment = models.ForeignKey (
        'Enrollment', # Utilisez une chaîne si Enrollment est défini plus loin dans le même fichier
        on_delete=models.CASCADE,
        related_name='grades',
        verbose_name="Inscription"
    )
    # C'est ici que vous ajoutez/remplacez la référence à l'évaluation
    evaluation = models.ForeignKey(
        'Evaluation', # AJOUT/REMPLACEMENT CLÉ: Lie la note à une évaluation spécifique
        on_delete=models.CASCADE,
        related_name='grades', 
        verbose_name="Évaluation"
    )
    score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Note")

    # evaluation_type n'est plus nécessaire ici car il est dans le modèle Evaluation
    # Vous pouvez le supprimer : evaluation_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="Type d'évaluation")

    graded_by = models.ForeignKey(
        'profiles.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='grades_given',
        limit_choices_to={'user_type': 'TEACHER'},
        verbose_name="Noté par"
    )
    date_graded = models.DateField(auto_now_add=True, null=True, blank=True, verbose_name="Date de notation")
    remarks = models.TextField(blank=True, null=True, verbose_name="Remarques") # Assurez-vous d'avoir ce champ pour les remarques

    def __str__(self):
        student_info = ""
        course_info = ""
        if self.enrollment:
            if self.enrollment.student:
                student_info = f"{self.enrollment.student.first_name} {self.enrollment.student.last_name}"
            if self.enrollment.course:
                course_info = self.enrollment.course.name
        # Mise à jour du _str_ pour inclure l'évaluation
        return f"Note de {self.score}/{self.evaluation.max_score} pour {student_info} en {course_info} ({self.evaluation.name})"

    class Meta:
        verbose_name = "Note"
        verbose_name_plural = "Notes"
        # Ajout de unique_together pour éviter les doublons pour une même évaluation et inscription
        unique_together = ('enrollment', 'evaluation')
        ordering = ['-date_graded', 'enrollment__student__last_name', 'enrollment__student__first_name']
    def get_notation(self):
        if self.score is None:
            return "Non Noté"
        
        max_score = float(self.evaluation.max_score) 
        if max_score == 0:
            return "N/A"  # Si le score maximum est 0, on ne peut pas calculer de pourcentage
        
        percentage = (float(self.score) / max_score) * 100
        
        if percentage >= 90:
            return "Excellent"
        elif percentage >= 75:
            return "Très Bien"
        elif percentage >= 60:
            return "Bien"
        elif percentage >= 50:
            return "Passable"
        elif percentage >= 40:
            return "Insuffisant"
                 
    @property
    def percentage_score(self):
        if self.evaluation and self.evaluation.max_score > 0:
            return (self.score / self.evaluation.max_score) * 100
        return 0
        # unique_together = ('enrollment', 'evaluation_type') # Décommentez si chaque type d'évaluation doit être unique par inscription

class Attendance(models.Model):
    """
    Enregistre la présence ou l'absence d'un élève pour une date et une inscription donnée.
    """
    # La relation avec l'école est implicitement définie via enrollment_course_school
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='attendances_related',
        verbose_name="Inscription"
    )
    date = models.DateField(verbose_name="Date")
    is_present = models.BooleanField(default=True, verbose_name="Présent")
    marked_by = models.ForeignKey(
        'profiles.CustomUser', # Référence par chaîne de caractères
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendances_marked',
        limit_choices_to={'user_type__in': ['TEACHER', 'DIRECTION']},
        verbose_name="Marqué par"
    )
    reason_for_absence = models.TextField(blank=True, null=True, verbose_name="Raison de l'absence")

    def __str__(self):
        status = "Présent" if self.is_present else "Absent"
        student_info = ""
        course_info = ""
        if self.enrollment:
            if self.enrollment.student:
                student_info = f"{self.enrollment.student.first_name} {self.enrollment.student.last_name}"
            if self.enrollment.course:
                course_info = self.enrollment.course.name
        return f"{student_info} : {status} le {self.date} en {course_info}"

    class Meta:
        verbose_name = "Présence"
        verbose_name_plural = "Présences"
        unique_together = ('enrollment', 'date')
        # Correction : accès correct aux champs des modèles liés
        ordering = ['-date', 'enrollment__student__last_name' , 'enrollment__student__first_name']
        

        
class Payment(models.Model):
    """
    Enregistre les paiements effectués par les élèves.
    """
    # La relation avec l'école est implicitement définie via student__school
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='payments_made', verbose_name="École")
    student = models.ForeignKey('profiles.Student', on_delete=models.CASCADE, related_name='payments', verbose_name="Élève")
    academic_period = models.ForeignKey(
        AcademicPeriod,
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Période académique concernée par ce paiement.",
        verbose_name="Période Académique"
    )
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant payé")
    payment_date = models.DateField( verbose_name="Date de paiement")
    payment_status_choices = [
        ('FULL', 'Totalement Réglé'),
        ('PARTIAL', 'Partiellement Réglé'),
        ('DUE', 'Dû / En Attente'),
        ('OVERDUE', 'En Retard'),
    ]
    payment_status = models.CharField(max_length=50, choices=payment_status_choices, default='DUE', verbose_name="Statut du paiement")
    recorded_by = models.ForeignKey(
        'profiles.CustomUser', # Référence par chaîne de caractères
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments_recorded',
        limit_choices_to={'user_type': 'ACCOUNTANT'},
        verbose_name="Enregistré par"
    )
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True, help_text="Numéro de transaction ou référence du paiement.", verbose_name="ID Transaction")

    def __str__(self):
        student_name = f"{self.student.first_name} {self.student.last_name}" if self.student else "Élève Inconnu"
        academic_period_name = self.academic_period.name if self.academic_period else "Période Inconnue"
        return f"Paiement de {self.amount_paid} pour {student_name} ({academic_period_name})"

    class Meta:
        verbose_name = "Paiement"
        # Correction : verbose_plural doit être verbose_name_plural
        verbose_name_plural = "Paiements"
        ordering = ['-payment_date', 'student__last_name']
        
class ReportCard(models.Model):
    """
    Représente le bulletin scolaire d'un élève pour une période académique donnée.
    """
    # La relation avec l'école est implicitement définie via student__school
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='report_cards_generated', verbose_name="École")
    student = models.ForeignKey('profiles.Student', on_delete=models.CASCADE, related_name='report_cards', verbose_name="Élève")
    academic_period = models.ForeignKey(
        AcademicPeriod,
        on_delete=models.CASCADE,
        related_name='report_cards',
        verbose_name="Période Académique"
    )
    pdf_file = models.FileField(upload_to='report_cards/', blank=True, null=True, verbose_name="Fichier PDF du Bulletin")
    generated_date = models.DateField(auto_now_add=True, verbose_name="Date de génération")
    generated_by = models.ForeignKey(
        'profiles.CustomUser', # Référence par chaîne de caractères
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_report_cards',
        verbose_name="Généré par"
    )
    status_choices = [
        ('DRAFT', 'Brouillon'),
        ('FINAL', 'Final'),
        ('SENT', 'Envoyé aux Parents'),
    ]
    status = models.CharField(max_length=50, default='DRAFT', choices=status_choices, verbose_name="Statut du Bulletin")

    def __str__(self):
        student_name = f"{self.student.first_name} {self.student.last_name}" if self.student else "Élève Inconnu"
        academic_period_name = self.academic_period.name if self.academic_period else "Période Inconnue"
        return f"Bulletin de {student_name} pour {academic_period_name}"

    class Meta:
        verbose_name = "Bulletin Scolaire" 
        # Correction : verbose_plural doit être verbose_name_plural
        verbose_name_plural = "Bulletins Scolaires"
        unique_together = ('student', 'academic_period')
        # Correction : accès correct aux champs des modèles liés (suppression de l'espace après student__)
        ordering = ['-academic_period__start_date', 'student__last_name', 'student__first_name']
        
class EvaluationType(models.TextChoices):
    EXAM = 'EXAM', 'Examen'
    QUIZ = 'QUIZ', 'Quiz'
    HOMEWORK = 'HOMEWORK', 'Devoir'
    PROJECT = 'PROJECT', 'Projet'
    PARTICIPATION = 'PARTICIPATION', 'Participation'
    OTHER = 'OTHER', 'Autre'

class Evaluation(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nom de l'évaluation")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='evaluations', verbose_name="Cours")
    evaluation_type = models.CharField(max_length=50, choices=EvaluationType.choices, default=EvaluationType.EXAM, verbose_name="Type d'évaluation")
    date = models.DateField(verbose_name="Date de l'évaluation")
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=20.00, verbose_name="Score maximum") # Ex: sur 20, ou sur 100
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    created_by = models.ForeignKey('profiles.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_evaluations', verbose_name="Créé par")
    academic_period = models.ForeignKey(AcademicPeriod, on_delete=models.CASCADE, related_name='evaluations', verbose_name="Période Académique")


    class Meta:
        verbose_name = "Évaluation"
        verbose_name_plural = "Évaluations"
        ordering = ['-date', 'course__name', 'name']
        unique_together = ('name', 'course', 'date', 'academic_period') # Pour éviter les doublons

    def __str__(self):
        return f"{self.name} ({self.course.name} - {self.date})"   
    
# school_project/school/models.py
# ... (autres imports) ...
 # Importer CustomUser et UserRole du module profiles

class DisciplinaryRecord(models.Model):
    student = models.ForeignKey('profiles.Student', on_delete=models.CASCADE, related_name='disciplinary_records')
    reported_by = models.ForeignKey('profiles.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_disciplinary_records')
    incident_date = models.DateField()
    description = models.TextField()
    action_taken = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-incident_date', '-created_at']

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new:
            # Assurez-vous que Notification est importé en haut de ce fichier ou accessible
            # Si Notification est dans profiles.models, l'import profiles.models entier peut être en haut
            # Si Notification est dans le même fichier school.models, aucun import spécial n'est nécessaire ici.
            # Dans votre cas, Notification est dans school.models, donc pas besoin d'import local ici.
            from profiles.models import Notification
            parents = self.student.parents.all()

            if parents.exists():
                subject = f"Nouveau Dossier Disciplinaire pour {self.student.full_name}"
                message = (
                    f"Cher parent,\n\n"
                    f"Nous vous informons qu'un nouveau dossier disciplinaire a été créé pour votre enfant, {self.student.full_name}, "
                    f"concernant un incident survenu le {self.incident_date.strftime('%d/%m/%Y')}.\n\n"
                    f"Description de l'incident : {self.description}\n"
                )
                if self.action_taken:
                    message += f"Action prise : {self.action_taken}\n"
                message += "\nCordialement,\nL'Administration Scolaire."

                for parent_user in parents:
                    Notification.objects.create( # Notification est accessible car dans le même app
                        recipient=parent_user,
                        sender=self.reported_by,
                        subject=subject, # CORRECTION ICI : 'subject' en minuscule
                        message=message,
                        notification_type='GENERAL' # 'DISCIPLINARY' n'est pas dans les choix actuels, utilisez 'GENERAL' ou ajoutez 'DISCIPLINARY'
                        # Si vous voulez un type 'DISCIPLINARY', ajoutez-le dans Notification.notification_type_choices
                    )
            else:
                print(f"INFO: Dossier disciplinaire créé pour {self.student.full_name}, mais aucun parent lié pour la notification.")

    def __str__(self): # Correction de l'orthographe
        return f"Dossier pour {self.student.full_name} le {self.incident_date.strftime('%Y-%m-%d')}"
    
class TuitionFee(models.Model):
    """
    Définit les frais de scolarité pour une classe spécifique et une période académique donnée.
    """
    classe = models.ForeignKey(
        'Classe',
        on_delete=models.CASCADE,
        related_name='tuition_fees',
        verbose_name="Classe"
    )
    academic_period = models.ForeignKey(
        'AcademicPeriod',
        on_delete=models.CASCADE,
        related_name='tuition_fees',
        verbose_name="Période Académique"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant des frais")
    date_set = models.DateField(auto_now_add=True, verbose_name="Date de définition")
    set_by = models.ForeignKey(
        'profiles.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'user_type__in': ['ADMIN', 'ACCOUNTANT', 'DIRECTION']},
        verbose_name="Défini par"
    )

    class Meta:
        # Assure qu'il n'y a qu'une seule définition de frais par classe et période académique
        unique_together = ('classe', 'academic_period')
        verbose_name = "Frais de Scolarité"
        verbose_name_plural = "Frais de Scolarité"
        ordering = ['-academic_period', 'classe__name']

    def _str_(self):
        return f"{self.amount} $ pour {self.classe.name} en {self.academic_period.name}"