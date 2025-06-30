# profiles/forms.py

from django import forms
from django.forms import formset_factory
from .models import CustomUser, Student, Parent, UserRole, Notification
from school.models import Classe, School, AcademicPeriod, ClassAssignment, Course, Grade, Attendance, DisciplinaryRecord
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

# --- Formulaires d'authentification et d'inscription ---

class CustomAuthenticationForm(forms.Form):
    email = forms.EmailField(label="Adresse Email")
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = CustomUser.objects.filter(email=email).first()
            if self.user_cache is None:
                raise forms.ValidationError("Email ou mot de passe invalide.")
            if not self.user_cache.check_password(password):
                raise forms.ValidationError("Email ou mot de passe invalide.")
            if not self.user_cache.is_active:
                raise forms.ValidationError("Ce compte est inactif.")
        return self.cleaned_data

    def get_user(self):
        return self.user_cache

class ParentCreationForm(forms.ModelForm):
    # Champ pour le mot de passe initial du parent
    password = forms.CharField(widget=forms.PasswordInput, label="Mot de passe du Parent")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirmer le mot de passe")

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address']
        labels = {
            'first_name': "Prénom du Parent",
            'last_name': "Nom du Parent",
            'email': "Adresse Email du Parent",
            'phone_number': "Téléphone du Parent",
            'address': "Adresse du Parent",
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Les mots de passe ne correspondent pas.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        # Définir le type d'utilisateur et l'approuver par défaut lors de la création par la direction
        user.user_type = CustomUser.UserRole.PARENT if hasattr(CustomUser, 'UserRole') else 'PARENT'
        user.is_approved = True # La direction approuve le compte directement
        if commit:
            user.save()
        return user

class TeacherRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Mot de passe")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirmer le mot de passe")

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address', 'password', 'password_confirm', 'school']
        labels = {
            'first_name': "Votre Prénom",
            'last_name': "Votre Nom de Famille",
            'email': "Votre Adresse Email",
            'phone_number': "Votre Numéro de Téléphone",
            'address': "Votre Adresse Postale",
            'school': "École à laquelle vous êtes affilié(e)"
        }

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Les mots de passe ne correspondent pas.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.user_type = UserRole.TEACHER
        user.is_active = True
        user.is_approved = False
        if commit:
            user.save()
        return user

class StudentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user_school = kwargs.pop('user_school', None)
        is_parent_form = kwargs.pop('is_parent_form', False)
        
        super().__init__(*args, **kwargs) 
        
        if 'student_id_code' in self.fields:
            self.fields['student_id_code'].widget = forms.HiddenInput()
            self.fields['student_id_code'].required = False
            self.fields['student_id_code'].help_text = "Sera généré automatiquement."

        if user_school:
            if 'current_classe' in self.fields:
                self.fields['current_classe'].queryset = Classe.objects.filter(school=user_school).order_by('name')
            
            # Ne pas afficher les parents existants dans ce formulaire, car on en crée un nouveau.
            # On va supprimer ce champ du formulaire StudentForm
            if 'parents' in self.fields:
                del self.fields['parents'] # On ne gère plus la sélection de parents existants ici

        if is_parent_form:
            # Assurez-vous que le student_id_code est également masqué ici
            if 'student_id_code' in self.fields:
                self.fields['student_id_code'].widget = forms.HiddenInput()
                self.fields['student_id_code'].required = False

            if 'school' in self.fields: self.fields['school'].widget = forms.HiddenInput(); self.fields['school'].required = False
            if 'current_classe' in self.fields: self.fields['current_classe'].widget = forms.HiddenInput(); self.fields['current_classe'].required = False
            if 'is_active' in self.fields: self.fields['is_active'].widget = forms.HiddenInput(); self.fields['is_active'].required = False
            if 'enrollment_date' in self.fields: self.fields['enrollment_date'].widget = forms.HiddenInput(); self.fields['enrollment_date'].required = False
            
            # Si is_parent_form, le champ parents devrait être masqué ou inexistant aussi
            if 'parents' in self.fields:
                del self.fields['parents']


    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'middle_name',
            'date_of_birth', 'gender',
            'address', 'phone_number', 'email', # L'email ici est pour l'élève, pas le parent
            'profile_picture',
            'student_id_code', 
            'school', 'current_classe', # 'parents' est retiré des fields ici
            'is_active', 'enrollment_date',
        ]
        labels = {
            # ... (vos labels existants) ...
            'email': "Adresse Email de l'élève", # Pour éviter la confusion avec l'email du parent
        }
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'enrollment_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
        
class DirectionUserApprovalForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['is_approved', 'user_type', 'school']
        labels = {
            'is_approved': "Approuvé",
            'user_type': "Type d'utilisateur",
            'school': "École Affiliée"
        }

class ClassAssignmentForm(forms.ModelForm):
    class Meta:
        model = ClassAssignment
        fields = ['teacher', 'classe', 'academic_period']
        labels = {
            'teacher': "Enseignant",
            'classe': "Classe",
            'academic_period': "Période Académique"
        }
    # CORRECTION : _init_ doit avoir deux underscores de chaque côté
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) # CORRECTION : Utiliser super().init_
        self.fields['teacher'].queryset = CustomUser.objects.filter(
            Q(user_type=UserRole.TEACHER) | Q(user_type=UserRole.ADMIN)
        )
        self.fields['classe'].queryset = Classe.objects.all()
        self.fields['academic_period'].queryset = AcademicPeriod.objects.all().order_by('-start_date')

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = (
            'email',
            'user_type',
            'school',
            'first_name',
            'last_name',
            'phone_number',
            'address',
            'profile_picture',
            'date_of_birth',
            'is_approved',
            'is_active',
            'is_staff',
            'is_superuser',
            'groups',
            'user_permissions',
        )

    # AJOUTEZ CETTE MÉTHODE clean()
    def clean(self):
        cleaned_data = super().clean()
        # Ici, nous allons imprimer les erreurs si le formulaire n'est pas valide
        if not self.is_valid():
            print("\n--- DEBUG FORM ERRORS ---")
            print("Form errors:", self.errors)
            print("Non-field errors:", self.non_field_errors())
            print("--- END DEBUG FORM ERRORS ---\n")
        return cleaned_data

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = (
            'email',
            'user_type',
            'first_name',
            'last_name',
            'phone_number',
            'address',
            'date_of_birth',
            'school',
            'is_active',
            'is_staff',
            'is_superuser',
            'is_approved',
            'groups',
            'user_permissions',
            'password', # Pour la modification du mot de passe (dans UserChangeForm, c'est 'password')
        )
        labels = {
            'email': "Email",
            'user_type': "Type d'utilisateur",
            'first_name': "Prénom",
            'last_name': "Nom de famille",
            'phone_number': "Numéro de Téléphone",
            'address': "Adresse",
            'date_of_birth': "Date de naissance",
            'school': "École Affiliée",
            'is_active': "Actif",
            'is_staff': "Statut du personnel",
            'is_superuser': "Superutilisateur",
            'is_approved': "Approuvé",
            'groups': "Groupes",
            'user_permissions': "Permissions de l'utilisateur",
            'password': "Mot de Passe"
        }

class GradeForm(forms.ModelForm):
    EVALUATION_CHOICES = [
        ('EXERCISE_CLASS', 'Exercice en classe'),
        ('HOMEWORK', 'Devoir à la maison'),
        ('QUIZ', 'Interrogation / Quiz'),
        ('EXAM', 'Examen'),
        ('PROJECT', 'Projet'),
        ('PARTICIPATION', 'Participation'),
        ('OTHER', 'Autre'),
    ]
    evaluation_type = forms.ChoiceField(choices=EVALUATION_CHOICES, label="Type d'Évaluation")

    class Meta:
        model = Grade
        fields = ['enrollment', 'score', 'evaluation_type']
        widgets = {
            'enrollment': forms.Select(attrs={'class': 'form-control'}),
            'score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    # CORRECTION : _init_ doit avoir deux underscores de chaque côté
    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        super()._init_(*args, **kwargs) # CORRECTION : Utiliser super().init_
        if teacher:
            # Assurez-vous que le modèle Enrollment est importé ou défini si vous l'utilisez ici.
            # Example: from school.models import Enrollment # ou là où il est défini
            # self.fields['enrollment'].queryset = Enrollment.objects.filter(
            #     course__teachers=teacher,
            #     academic_period__is_current=True
            # )
            pass # Laissez ceci vide si Enrollment n'est pas encore défini ou importé

class NotificationForm(forms.ModelForm):
    def _init_(self, *args, **kwargs):
        # EXTRAIRE 'sender_user' de kwargs AVANT d'appeler super()._init_
        self.sender_user = kwargs.pop('sender_user', None) 
        # Le 'None' est pour le cas où sender_user ne serait pas passé, pour éviter une KeyError

        super()._init_(*args, **kwargs)

        # Maintenant, vous pouvez utiliser self.sender_user pour configurer le formulaire si nécessaire
        # Par exemple, pour définir l'expéditeur initial ou cacher le champ
        if 'sender' in self.fields: # Vérifiez que le champ 'sender' existe dans le formulaire
            self.fields['sender'].widget = forms.HiddenInput()
            if self.sender_user:
                self.fields['sender'].initial = self.sender_user.pk # Utilisez la PK pour les FKs

        # Si le champ 'recipient' est un ModelChoiceField et que vous voulez le filtrer
        # par l'école de l'expéditeur ou d'autres critères :
        if 'recipient' in self.fields and self.sender_user and self.sender_user.school:
            # Filtrez les destinataires pour qu'ils soient dans la même école que l'expéditeur
            self.fields['recipient'].queryset = User.objects.filter(school=self.sender_user.school)

    class Meta:
        model = Notification
        # Incluez les champs que l'utilisateur voit et/ou remplit.
        # 'sender' est inclus ici car nous le gérons dans _init_ et le cachons.
        # 'recipient' est inclus car l'utilisateur peut le choisir (ou il est filtré).
        fields = ['recipient', 'subject', 'message', 'notification_type'] 
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Votre message ici...'}),
            # 'sender': forms.HiddenInput(), # C'est mieux de le définir dans _init_ pour plus de flexibilité
        }
        labels = {
            'recipient': "Destinataire",
            'subject': "Sujet de la notification",
            'message': "Contenu du message",
            'notification_type': "Type de notification",
            #'sender': "Expéditeur", # Ce label ne sera pas visible car le champ est caché
        }

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['is_present', 'reason_for_absence']
        widgets = {
            'is_present': forms.HiddenInput(),
            'reason_for_absence': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Raison de l\'absence (facultatif)'}),
        }
        labels = {
            'reason_for_absence': 'Raison de l\'absence',
        }

class DisciplinaryRecordForm(forms.ModelForm):
    class Meta:
        model = DisciplinaryRecord
        fields = ['incident_date', 'description', 'action_taken']
        widgets = {
            'incident_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'action_taken': forms.Textarea(attrs={'rows': 2}),
        }

class AcademicPeriodForm(forms.ModelForm):
    class Meta:
        model = AcademicPeriod
        fields = ['name', 'start_date', 'end_date', 'school']
        labels = {
            'name': 'Nom de la Période',
            'start_date': 'Date de Début',
            'end_date': 'Date de Fin',
            'school': 'École',
        }
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    # CORRECTION : _init_ doit avoir deux underscores de chaque côté
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs) # CORRECTION : Utiliser super().init_

        if user and hasattr(user, 'school') and user.school:
            self.fields['school'].queryset = School.objects.filter(pk=user.school.pk)
        elif user and not user.is_superuser:
            self.fields['school'].queryset = School.objects.none()
            self.fields['school'].help_text = "Votre compte n'est pas lié à une école. Veuillez contacter l'administrateur."
            self.fields['school'].disabled = True

class ClasseForm(forms.ModelForm):
    # Ajoutez ce champ pour permettre de sélectionner les cours au moment de la création/modification de la classe
    # Le queryset sera filtré dans _init_
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.all(), # Sera filtré par école et période active
        required=False, # Un cours peut être ajouté plus tard si désiré
        label="Cours associés à cette classe"
    )

    class Meta:
        model = Classe
        # Assurez-vous que 'courses' est dans la liste des champs
        fields = ['name', 'level', 'description', 'teachers', 'courses']
        # 'school' et 'academic_period' seront gérés dans la vue ou via initial data

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request and self.request.user.school:
            user_school = self.request.user.school
            self.fields['teachers'].queryset = self.fields['teachers'].queryset.filter(school=user_school)

            # Filtrez les cours pour ne montrer que ceux de l'école et de la période académique active
            active_academic_period = AcademicPeriod.objects.filter(
                school=user_school,
                is_current=True
            ).first()

            if active_academic_period:
                self.fields['courses'].queryset = Course.objects.filter(
                    school=user_school,
                    academic_period=active_academic_period
                ).order_by('name')
            else:
                # Si aucune période active, ne proposez pas de cours ou avertissez
                self.fields['courses'].queryset = Course.objects.none()
                if not self.instance.pk: # Si c'est une nouvelle classe
                    self.fields['courses'].help_text = "Aucun cours disponible car aucune période académique active n'est définie pour votre école."

            # Si c'est une mise à jour d'une instance existante, pré-remplir les cours déjà liés
            if self.instance.pk:
                self.initial['courses'] = self.instance.courses_taught.all() # courses_taught est le related_name de Course.classes

class CourseForm(forms.ModelForm):
    # Si vous avez besoin de filtrer les choices pour les champs ManyToMany/ForeignKey ici,
    # vous pouvez le faire dans _init_ du formulaire ou laisser la vue le faire.
    # Pour l'instant, nous allons nous assurer que les champs sont corrects.

    class Meta:
        model = Course
        # LISTEZ ICI TOUS LES CHAMPS QUE VOUS VOULEZ INCLURE DANS LE FORMULAIRE.
        # Le champ 'classe' N'EXISTE PLUS dans le modèle Course.
        # Le nouveau champ est 'classes' (au pluriel) et c'est un ManyToManyField.
        fields = [
            'school',          # Si vous voulez que l'école soit sélectionnable dans le formulaire
            'name',
            'subjects',
            'code',
            'description',
            'credits',
            'teachers',        # ManyToManyField vers CustomUser (enseignants)
            'classes',         # <-- C'EST LE NOM CORRECT POUR LE MANYTO MANYFIELD
            'academic_period'  # ForeignKey vers AcademicPeriod
        ]
        # Vous pouvez également exclure des champs si vous les définissez ou les remplissez manuellement dans la vue.
        # Par exemple, si 'school' est toujours défini automatiquement par l'utilisateur connecté:
        # exclude = ['school']

    def __init__(self, *args, **kwargs):
        # Vous pouvez passer 'school' ou d'autres paramètres ici si nécessaire pour filtrer les querysets
        user_school = kwargs.pop('school', None) # Récupère l'école passée lors de l'instanciation du form
        super().__init__(*args, **kwargs)

        # Filtrer les classes pour l'école de l'utilisateur
        if 'classes' in self.fields and user_school:
            self.fields['classes'].queryset = Classe.objects.filter(school=user_school)

        # Filtrer les enseignants pour l'école de l'utilisateur
        if 'teachers' in self.fields and user_school:
            self.fields['teachers'].queryset = CustomUser.objects.filter(user_type='TEACHER', school=user_school)

        # Si le champ school est dans le formulaire, le limiter à l'école de l'utilisateur
        if 'school' in self.fields and user_school:
            self.fields['school'].queryset = School.objects.filter(pk=user_school.pk)
            # Et si vous voulez le désactiver pour qu'il ne soit pas modifiable par l'utilisateur:
            self.fields['school'].widget.attrs['disabled'] = 'disabled'
            self.fields['school'].required = False # Si désactivé, il ne doit pas être requis du POST direct