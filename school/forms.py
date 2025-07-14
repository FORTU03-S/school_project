# school_project/school/forms.py
print("DEBUG: Chargement de school/forms.py")
from django import forms
from .models import  Classe, Course, Enrollment, Grade, Attendance, AcademicPeriod, Evaluation, Payment, FeeType, TuitionFee
from profiles.models import CustomUser, UserRole, Student, Notification # Important: Assurez-vous que UserRole est importé ici
from django.contrib.auth import get_user_model
from django.utils import timezone

# Formulaire pour ajouter/modifier un élève


# Formulaire pour la saisie des notes
class GradeForm(forms.ModelForm):
    # L'inscription (enrollment) doit être passée à la vue qui utilise ce formulaire
    # La note est directement saisie
    score = forms.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=20, label="Note")
    evaluation_type = forms.CharField(max_length=100, label="Type d'évaluation (Ex: Examen, Devoir)", required=False)

    class Meta:
        model = Grade
        fields = ['score', 'evaluation_type'] # enrollment et graded_by seront définis dans la vue

# Formulaire pour la gestion des présences
class AttendanceForm(forms.ModelForm):
    # L'inscription (enrollment) et la date sont passées à la vue
    is_present = forms.BooleanField(required=False, label="Est Présent ?") # Checkbox
    reason_for_absence = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, label="Raison de l'absence (si absent)")

    class Meta:
        model = Attendance
        fields = ['is_present', 'reason_for_absence'] # enrollment, date, marked_by seront définis dans la vue

# Formulaire pour envoyer une notification / un message
class TeacherMessageForm(forms.Form):
    # Les destinataires seront une liste de parents de la classe de l'enseignant
    recipients = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(user_type=UserRole.PARENT),
        widget=forms.CheckboxSelectMultiple,
        label="Sélectionner les parents destinataires",
        required=True
    )
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}), label="Message")
    notification_type = forms.ChoiceField()
    
    choices=[
            ('MESSAGE_TEACHER', 'Message de l\'enseignant'),
            ('HOMEWORK', 'Devoir à faire'),
            ('EVALUATION', 'Évaluation à venir'),
        ],
        
    label="Type de notification",
    required=True
    

class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'academic_period', 'status']
        labels = {
            'student': 'Élève',
            'course': 'Cours',
            'academic_period': 'Période Académique',
            'status': 'Statut d\'Inscription',
        }
        widgets = {
            # 'enrollment_date': forms.DateInput(attrs={'type': 'date'}), # Si vous voulez la gérer manuellement, sinon elle est auto dans la vue
        }

    def __init__(self, *args, **kwargs):
        # Récupérez l'utilisateur enseignant passé depuis la vue
        teacher_user = kwargs.pop('teacher_user', None)
        super().__init__(*args, **kwargs)

        if teacher_user and teacher_user.school:
            school = teacher_user.school

            # Filtrer les périodes académiques pour l'école de l'enseignant
            self.fields['academic_period'].queryset = AcademicPeriod.objects.filter(
                school=school
            ).order_by('-start_date')

            # Filtrer les cours que cet enseignant est assigné à enseigner dans son école
            teacher_courses_queryset = Course.objects.filter(
                teachers=teacher_user,
                school=school
            ).order_by('name')
            self.fields['course'].queryset = teacher_courses_queryset

            # Filtrer les élèves. Un enseignant ne devrait inscrire que les élèves de sa/ses classes.
            # On récupère d'abord les IDs des classes associées aux cours de l'enseignant
            teacher_related_class_ids = teacher_courses_queryset.values_list('classes__id', flat=True).distinct()

            # Puis on filtre les élèves par ces classes et par l'école
            self.fields['student'].queryset = Student.objects.filter(
                school=school,
                current_classe__id__in=teacher_related_class_ids # Élèves des classes où l'enseignant donne cours
            ).order_by('last_name', 'first_name')
        else:
            # Si pas d'enseignant ou pas d'école, les listes sont vides
            self.fields['student'].queryset = Student.objects.none()
            self.fields['course'].queryset = Course.objects.none()
            self.fields['academic_period'].queryset = AcademicPeriod.objects.none()
            
   
            
class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['enrollment', 'evaluation', 'score', 'remarks']
        labels = {
            'enrollment': 'Inscription (Élève - Cours - Période)',
            'evaluation': 'Évaluation',
            'score': 'Note Obtenue',
            'remarks': 'Remarques',
        }
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        super()._init_(*args, **kwargs)

        if school:
            # Filtrer les inscriptions (Enrollment) par les cours associés à l'école de l'utilisateur
            # Cela affiche: "Élève (Nom du Cours - Période)" pour faciliter la sélection
            self.fields['enrollment'].queryset = Enrollment.objects.filter(
                course_classe_school=school
            ).select_related('student', 'course', 'academic_period').order_by(
                'student_last_name', 'studentfirst_name', 'course_name'
            )
            
            # Filtrer les évaluations par les cours associés à l'école de l'utilisateur
            self.fields['evaluation'].queryset = Evaluation.objects.filter(
                course_classe_school=school
            ).select_related('course', 'academic_period').order_by(
                'course__name', '-date'
            )
        else:
            # Si aucune école n'est passée, les querysets sont vides ou tous (dépend de la logique de permission)
            self.fields['enrollment'].queryset = Enrollment.objects.none()
            self.fields['evaluation'].queryset = Evaluation.objects.none()
            
# ... (vos autres formulaires) ...

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['enrollment', 'date', 'is_present', 'reason_for_absence']
        labels = {
            'enrollment': 'Inscription (Élève - Cours)',
            'date': 'Date de Présence',
            'is_present': 'Est Présent ?',
            'reason_for_absence': 'Raison de l\'Absence (si absent)',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'reason_for_absence': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)

        if school:
            # Filtrer les inscriptions (Enrollment) par les cours associés à l'école de l'utilisateur
            self.fields['enrollment'].queryset = Enrollment.objects.filter(
                course_classe_school=school
            ).select_related('student', 'course').order_by(
                'student__last_name', 'student__first_name', 'course__name'
            )
        else:
            self.fields['enrollment'].queryset = Enrollment.objects.none()
        
        # Le champ reason_for_absence ne doit pas être requis si is_present est coché
        self.fields['reason_for_absence'].required = False

    def clean(self):
        cleaned_data = super().clean()
        is_present = cleaned_data.get('is_present')
        reason_for_absence = cleaned_data.get('reason_for_absence')

        if not is_present and not reason_for_absence:
            self.add_error('reason_for_absence', "Veuillez fournir une raison d'absence si l'élève n'est pas présent.")
        if is_present and reason_for_absence:
             self.add_error('reason_for_absence', "Une raison d'absence ne peut être fournie si l'élève est présent.")
        return cleaned_data    
    
 
CustomUser = get_user_model()

# Formulaire pour enregistrer un nouveau paiement
class PaymentForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(), # Le queryset sera défini dans _init_
        label="Élève",
        help_text="Sélectionnez l'élève pour lequel le paiement est effectué."
    )
    fee_type = forms.ModelChoiceField(
        queryset=FeeType.objects.none(), # Le queryset sera défini dans _init_
        label="Type de frais",
        help_text="Sélectionnez le type de frais auquel ce paiement se rapporte."
    )
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Date du paiement",
        initial=forms.DateField().widget.render(name='payment_date', value=None) # Pour pré-remplir avec la date du jour si possible
    )
    # Champ pour la preuve de paiement (facultatif, si vous en avez un)
    # payment_proof = forms.FileField(
    #     label="Preuve de paiement (reçu, scan)",
    #     required=False,
    #     help_text="Uploadez une image ou un PDF du reçu de paiement."
    # )

    class Meta:
        model = Payment
        fields = ['student', 'fee_type', 'amount_paid', 'payment_date', 'description']
        widgets = {
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        school_id = kwargs.pop('school_id', None)
        user = kwargs.pop('user', None) # L'utilisateur connecté est maintenant passé à la vue
        super().__init__(*args, **kwargs)

        if school_id:
            # Filtre les élèves et types de frais par l'école de l'utilisateur
            self.fields['student'].queryset = Student.objects.filter(school_id=school_id).order_by('last_name', 'first_name')
            self.fields['fee_type'].queryset = FeeType.objects.filter(school_id=school_id).order_by('name')
        else:
            # Optionnel: Désactiver les champs si pas d'école (devrait être géré par UserPassesTestMixin)
            self.fields['student'].queryset = Student.objects.none()
            self.fields['fee_type'].queryset = FeeType.objects.none()

        # Rendre le champ payment_date requis et définir la date du jour comme valeur par défaut
        self.fields['payment_date'].required = True
        if not self.initial.get('payment_date'):
            self.initial['payment_date'] = timezone.now().date() # Import timezone from django.utils


    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        amount_paid = cleaned_data.get('amount_paid')

        # Ajoutez des validations personnalisées si nécessaire, par exemple:
        # Vérifier que le montant n'est pas négatif (déjà géré par min='0' dans le widget, mais bon de vérifier)
        if amount_paid is not None and amount_paid <= 0:
            self.add_error('amount_paid', "Le montant payé doit être supérieur à zéro.")

        # Assurez-vous que l'élève sélectionné appartient bien à l'école de l'utilisateur (double-vérification de sécurité)
        # (Cette validation est implicitement gérée par le queryset, mais peut être explicite ici)
        # if student and self.school_id and student.school_id != self.school_id:
        #    raise forms.ValidationError("L'élève sélectionné n'appartient pas à votre école.")

        return cleaned_data
class TuitionFeeForm(forms.ModelForm):
    class Meta:
        model = TuitionFee
        fields = ['fee_type', 'classe', 'academic_period', 'amount']
    
    def __init__(self, *args, **kwargs):
        self.school_id = kwargs.pop('school_id', None)
        super().__init__(*args, **kwargs)

        if self.school_id:
            self.fields['fee_type'].queryset = FeeType.objects.filter(school=self.school_id) | FeeType.objects.filter(school__isnull=True)
            self.fields['classe'].queryset = Classe.objects.filter(school=self.school_id)
            self.fields['academic_period'].queryset = AcademicPeriod.objects.filter(school=self.school_id) | AcademicPeriod.objects.filter(school__isnull=True)

# Formulaire pour créer un nouveau type de frais (intitulé)
class FeeTypeForm(forms.ModelForm):
    class Meta:
        model = FeeType
        fields = ['name', 'description', 'is_active']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Vous pouvez ajouter ici des validations spécifiques si nécessaire