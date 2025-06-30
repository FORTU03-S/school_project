# school_project/school/admin.py

from django.contrib import admin
# Importez TOUS les modèles nécessaires de votre application 'school'
from .models import (
    AcademicPeriod, Classe, Course, Grade, Attendance,
    Payment, Enrollment, ReportCard, School, Subject, ClassAssignment,
    Evaluation
)
# Assurez-vous d'importer CustomUser (et Notification si elle est dans profiles.models et utilisée ici)
# CustomUser est nécessaire pour les autocomplete_fields des champs 'teacher', 'graded_by', 'marked_by', 'created_by', 'generated_by'
from profiles.models import CustomUser, Notification # N'oubliez pas Notification si elle est gérée ici

# --- Enregistrements des Modèles de Base (à faire en premier) ---

# 1. SchoolAdmin
@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone_number', 'email', 'is_active')
    search_fields = ('name', 'address', 'email')
    list_filter = ('is_active',)

# 2. AcademicPeriodAdmin
@admin.register(AcademicPeriod)
class AcademicPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'start_date', 'end_date', 'is_current')
    search_fields = ('name', 'school__name')
    list_filter = ('school', 'is_current')
    autocomplete_fields = ('school',) # SchoolAdmin est déjà défini ci-dessus

# 3. ClasseAdmin
@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'academic_period', 'main_teacher')
    search_fields = ('name', 'school_name', 'academic_periodname', 'main_teacherfirst_name', 'main_teacher_last_name')
    list_filter = ('school', 'academic_period')
    # Les autocomplete_fields pour ClasseAdmin : SchoolAdmin et AcademicPeriodAdmin sont définis
    # main_teacher est un CustomUser, donc CustomUserAdmin devra être défini
    autocomplete_fields = ('school', 'academic_period', 'main_teacher')


# 4. SubjectAdmin
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'description')
    search_fields = ('name', 'school__name')
    list_filter = ('school',)
    autocomplete_fields = ('school',) # SchoolAdmin est défini


# --- Autres Enregistrements de Modèles (qui peuvent dépendre des précédents) ---

# 5. CourseAdmin
# 5. CourseAdmin (CORRIGÉ POUR LA DÉFINITION DES MÉTHODES)
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_subjects', 'academic_period', 'school', 'code', 'display_classes')
    search_fields = ('name', 'subjects__name', 'school__name', 'code')
    list_filter = ('school', 'subjects', 'academic_period', 'classes', 'teachers')
    autocomplete_fields = ('school', 'subjects', 'teachers', 'academic_period')
    filter_horizontal = ('classes', 'subjects', 'teachers')

    # Assurez-vous que ces méthodes sont bien définies À L'INTÉRIEUR de la classe CourseAdmin
    # et qu'elles utilisent le décorateur @admin.display
    @admin.display(description="Matières Associées")
    def display_subjects(self, obj):
        return ", ".join([s.name for s in obj.subjects.all()]) or "Aucune"

    @admin.display(description="Classes Associées")
    def display_classes(self, obj):
        return ", ".join([classe.name for classe in obj.classes.all()]) or "Aucune"

# ... (le reste de vos classes Admin) ...


# 6. ClassAssignmentAdmin
@admin.register(ClassAssignment)
class ClassAssignmentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'classe', 'academic_period', 'school')
    search_fields = ('teacher__first_name', 'teacher__last_name', 'classe__name', 'school__name')
    list_filter = ('school', 'academic_period', 'classe', 'teacher')
    # Tous les modèles dans autocomplete_fields sont enregistrés
    autocomplete_fields = ('school', 'teacher', 'classe', 'academic_period')


# 7. EnrollmentAdmin
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'academic_period', 'enrollment_date', 'status')
    search_fields = (
        'student_user_first_name',
        'student_user_last_name',
        'course__name',
        'academic_period__name'
    )
    list_filter = (
        'status',
        'academic_period',
        'course',
        'student__school'
    )
    # Student et Course sont définis ailleurs, leurs ModelAdmin respectifs devront l'être
    autocomplete_fields = ('student', 'course', 'academic_period')


# 8. GradeAdmin
@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = (
        'enrollment',
        'score',
        'get_evaluation_name',
        'get_evaluation_type_display',
        'graded_by',
        'date_graded',
    )
    search_fields = (
        'enrollment__student__user__first_name',
        'enrollment__student__user__last_name',
        'enrollment__course__name',
        'evaluation__name',
        'graded_by__first_name',
        'graded_by__last_name',
    )
    list_filter = (
        'evaluation__evaluation_type',
        'date_graded',
        'graded_by',
        'evaluation__academic_period',
        'enrollment__course__classes', # ManyToMany, pas besoin de __name ici pour le filtre direct
    )
    # Tous les modèles dans autocomplete_fields devront être enregistrés
    autocomplete_fields = ('enrollment', 'graded_by', 'evaluation')

    @admin.display(description="Nom de l'évaluation")
    def get_evaluation_name(self, obj):
        return obj.evaluation.name if obj.evaluation else 'N/A'

    @admin.display(description="Type d'évaluation")
    def get_evaluation_type_display(self, obj):
        return obj.evaluation.get_evaluation_type_display() if obj.evaluation and obj.evaluation.evaluation_type else 'N/A'


# 9. AttendanceAdmin
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'date', 'is_present', 'marked_by')
    search_fields = (
        'enrollment__student__user__first_name',
        'enrollment__student__user__last_name',
        'enrollmen_t_course__name',
        'marked_by__first_name',
        'marked_by__last_name',
    )
    list_filter = (
        'date',
        'is_present',
        'marked_by',
        'enrollment__student__school',
        'enrollment__course__academic_period',
        'enrollment__course__classes',
    )
    # Tous les modèles dans autocomplete_fields devront être enregistrés
    autocomplete_fields = ('enrollment', 'marked_by')


# 10. NotificationAdmin (si Notification est dans profiles, cet admin devrait être dans profiles/admin.py)
# Si vous décidez de le garder ici, assurez-vous que CustomUser est importé et enregistré.


# 11. PaymentAdmin
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'academic_period', 'amount_paid', 'payment_date', 'payment_status', 'transaction_id')
    search_fields = (
        'student__user__first_name', 'student__user__last_name',
        'academic_period__name', 'transaction_id',
    )
    list_filter = ('payment_status', 'payment_date', 'academic_period', 'student__school')
    # Student et AcademicPeriod doivent être enregistrés
    autocomplete_fields = ('student', 'academic_period', 'recorded_by')


# 12. ReportCardAdmin
@admin.register(ReportCard)
class ReportCardAdmin(admin.ModelAdmin):
    list_display = ('student', 'academic_period', 'generated_date', 'status', 'generated_by')
    search_fields = (
        'student_userfirst_name', 'studentuser_last_name',
        'academic_period__name', 'status',
        'generated_by_first_name', 'generated_by_last_name', # Correction ici
    )
    list_filter = ('status', 'generated_date', 'academic_period', 'student__school')
    # Student, AcademicPeriod, CustomUser doivent être enregistrés
    autocomplete_fields = ('student', 'academic_period', 'generated_by')

# 13. EvaluationAdmin
@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'evaluation_type', 'date', 'max_score', 'academic_period', 'created_by']
    list_filter = ['course', 'evaluation_type', 'academic_period']
    search_fields = ['name', 'course__name', 'description']
    date_hierarchy = 'date'
    raw_id_fields = ['course', 'created_by', 'academic_period']
    # Course, AcademicPeriod, CustomUser doivent être enregistrés
    autocomplete_fields = ['course', 'academic_period', 'created_by']