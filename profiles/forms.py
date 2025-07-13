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

# Dans profiles/forms.py

 # Assurez-vous que CustomUser est importé
# Si UserRole est ailleurs, importez-le : from users.models import UserRole # Exemple

class ParentCreationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # 1. Récupérez (pop) l'argument 'user_school' de kwargs AVANT d'appeler super()._init_()
        self.user_school = kwargs.pop('user_school', None) # Le met dans une variable d'instance et le retire de kwargs

        super().__init__(*args, **kwargs) # Passez le reste des arguments (y compris 'prefix') au parent

        # 2. Utilisez self.user_school ici si vous avez besoin de filtrer ou de définir des valeurs initiales
        # Par exemple, si ParentCreationForm a un champ 'school' que vous voulez pré-remplir ou cacher :
        if self.user_school:
            if 'school' in self.fields:
                self.fields['school'].initial = self.user_school
                # Vous pourriez aussi vouloir le cacher si l'utilisateur ne doit pas le modifier
                # self.fields['school'].widget = forms.HiddenInput()
                # self.fields['school'].required = False # Si vous le remplissez manuellement après
            # Si le ParentCreationForm ne gère pas de champ 'school' directement (ce qui est probable
            # puisque vous le définissez dans la vue: parent_user.school = user_school),
            # alors cette partie if 'school' in self.fields n'est pas strictement nécessaire ici.
    class Meta:
        model = CustomUser
        fields = [
            'first_name',
            'last_name',
            # 'middle_name',  <-- SUPPRIMER OU COMMENTER
            'date_of_birth',
            # 'gender',       <-- SUPPRIMER OU COMMENTER
            'email',
            'phone_number',
            'address',
            'profile_picture', # Si vous voulez que la photo de profil soit téléchargeable pour un parent
            # N'incluez PAS 'school' ici si vous le définissez manuellement dans la vue.
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
}
    


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

    def save(self, commit=True, school=None):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.user_type = UserRole.TEACHER
        user.is_active = True
        user.is_approved = False
        if commit:
            user.save()
        return user


# profiles/forms.py

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
            # Définir l'école par défaut (et potentiellement la cacher)
            if 'school' in self.fields:
                self.fields['school'].initial = user_school
                self.fields['school'].queryset = School.objects.filter(id=user_school.id) # S'assure que seule cette école est visible
                # Ou si vous ne voulez pas qu'elle soit modifiable par l'utilisateur:
                # self.fields['school'].widget = forms.HiddenInput()
                # self.fields['school'].required = False # Si vous le remplissez manuellement après

            if 'current_classe' in self.fields:
                self.fields['current_classe'].queryset = Classe.objects.filter(school=user_school).order_by('name')

        if is_parent_form:
            # SUPPRIMEZ la ligne suivante :
            # if 'parents' in self.fields:
            #    del self.fields['parents']

            hidden_fields = ['school', 'current_classe', 'is_active', 'enrollment_date']
            for field in hidden_fields:
                if field in self.fields:
                    self.fields[field].widget = forms.HiddenInput()
                    self.fields[field].required = False


    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'middle_name',
            'date_of_birth', 'gender',
            'address', 'phone_number', # 'email',
            'profile_picture',
            'student_id_code',
            'school', 'current_classe',
            'is_active', 'enrollment_date',
            # SUPPRIMEZ 'parents' de cette liste :
            # 'parents',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'enrollment_date': forms.DateInput(attrs={'type': 'date'}),
        }

 
# Dans profiles/forms.py

from django import forms
from .models import CustomUser # Assurez-vous d'importer CustomUser
# from school_app.models import School # Si School est dans une autre app

class DirectionUserApprovalForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        # Incluez UNIQUEMENT les champs que la direction est censée modifier ou valider lors de l'approbation.
        # Le plus simple est juste 'is_approved'.
        fields = ('is_approved',)
        # Vous pouvez également rendre le champ 'is_approved' non modifiable directement par l'utilisateur
        # si vous voulez que la vue seule le mette à jour.
        # widgets = {
        #     'is_approved': forms.CheckboxInput(attrs={'disabled': 'disabled'}),
        # }

    # Si vous devez modifier d'autres champs (comme l'école) via ce formulaire, vous pouvez les ajouter ici
    # school = forms.ModelChoiceField(queryset=School.objects.all(), required=False) # Exemple

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Vous pouvez désactiver tous les autres champs ici si ce formulaire ne doit servir qu'à l'approbation
        # for field_name, field in self.fields.items():
        #     if field_name != 'is_approved':
        #         field.widget.attrs['readonly'] = True
        #         field.required = False # Rendre les autres champs non requis pour la validation


#CustomUser = get_user_model()

class ClassAssignmentForm(forms.ModelForm):
    class Meta:
        model = ClassAssignment
        fields = ['teacher', 'classe', 'academic_period']
        labels = {
            'teacher': "Enseignant",
            'classe': "Classe",
            'academic_period': "Période Académique"
        }

    def __init__(self, *args, **kwargs):
        # Extrait user_school des kwargs avant d'appeler super()
        user_school = kwargs.pop('user_school', None)
        super().__init__(*args, **kwargs)

        if user_school:
            # Filtre les enseignants par l'école actuelle et le type d'utilisateur
            self.fields['teacher'].queryset = CustomUser.objects.filter(
                Q(user_type=UserRole.TEACHER) | Q(user_type=UserRole.ADMIN),
                school=user_school, # <-- CRUCIAL : Filtre par école
                is_active=True # <-- Bonne pratique pour n'afficher que les utilisateurs actifs
            ).order_by('first_name', 'last_name')

            # Filtre les classes par l'école actuelle
            self.fields['classe'].queryset = Classe.objects.filter(
                school=user_school
            ).order_by('name')

            # Filtre les périodes académiques par l'école actuelle
            self.fields['academic_period'].queryset = AcademicPeriod.objects.filter(
                school=user_school
            ).order_by('-start_date')
        else:
            # Si aucune user_school n'est fournie, définissez des querysets vides ou gérez l'erreur de manière appropriée
            # Cela évite d'afficher tous les enseignants si le contexte de l'école est manquant
            self.fields['teacher'].queryset = CustomUser.objects.none()
            self.fields['classe'].queryset = Classe.objects.none()
            self.fields['academic_period'].queryset = AcademicPeriod.objects.none()

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

    def clean(self):
        cleaned_data = super().clean()
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
            'password',
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


class NotificationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.sender_user = kwargs.pop('sender_user', None) 
        super().__init__(*args, **kwargs)

        if 'sender' in self.fields:
            self.fields['sender'].widget = forms.HiddenInput()
            if self.sender_user:
                self.fields['sender'].initial = self.sender_user.pk

        if 'recipient' in self.fields and self.sender_user and self.sender_user.school:
            self.fields['recipient'].queryset = CustomUser.objects.filter(school=self.sender_user.school)

    class Meta:
        model = Notification
        fields = ['recipient', 'subject', 'message', 'notification_type'] 
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Votre message ici...'}),
        }
        labels = {
            'recipient': "Destinataire",
            'subject': "Sujet de la notification",
            'message': "Contenu du message",
            'notification_type': "Type de notification",
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

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and hasattr(user, 'school') and user.school:
            self.fields['school'].queryset = School.objects.filter(pk=user.school.pk)
        elif user and not user.is_superuser:
            self.fields['school'].queryset = School.objects.none()
            self.fields['school'].help_text = "Votre compte n'est pas lié à une école. Veuillez contacter l'administrateur."
            self.fields['school'].disabled = True

#CustomUser = get_user_model() # Si nécessaire pour d'autres champs filtrés
class ClasseForm(forms.ModelForm):
    class Meta:
        model = Classe
        # Laissez 'school' ici si vous voulez qu'il apparaisse sur le formulaire (en lecture seule)
        # Sinon, retirez-le et définissez-le dans la méthode save() du formulaire ou dans la vue.
        fields = ['name', 'school', 'level', 'description'] # Ajustez selon votre modèle Classe

    def __init__(self, *args, **kwargs):
        # 1. Extrait 'request' (si passé) des kwargs
        self.request = kwargs.pop('request', None) # <-- AJOUTÉ ICI : Extrait 'request'
        
        # 2. Extrait 'school' (si passé) des kwargs (celui que nous avions déjà)
        self.user_school = kwargs.pop('school', None) 
        
        super().__init__(*args, **kwargs) # <-- Appel à la classe parente avec les kwargs restants

        # Maintenant, utilisez self.user_school pour initialiser/gérer le champ 'school'
        if 'school' in self.fields:
            if self.user_school:
                self.fields['school'].initial = self.user_school
                self.fields['school'].widget.attrs['readonly'] = 'readonly'
                # Ou si vous voulez le désactiver complètement
                # self.fields['school'].disabled = True
            else:
                self.fields['school'].widget = forms.HiddenInput()

        # Si vous avez d'autres logiques de filtrage qui nécessitent l'objet request
        # ou les données de l'utilisateur (comme user.school), utilisez self.request ou self.user_school
        # Exemple si vous deviez filtrer un autre champ basé sur l'utilisateur de la requête :
        # if self.request and self.request.user.is_authenticated:
        #     self.fields['some_other_field'].queryset = SomeModel.objects.filter(owner=self.request.user)
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'code', 'description', 'academic_period', 'classes', 'teachers']
        labels = {
            'name': "Nom du Cours",
            'code': "Code du Cours",
            'description': "Description",
            'academic_period': "Période Académique",
            'classes': "Classes Associées",
            'teachers': "Enseignants Assignés",
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'classes': forms.CheckboxSelectMultiple(),
            'teachers': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        # --- C'est la partie CRUCIALE pour résoudre le TypeError ---
        # 1. Extrait 'request' des kwargs
        self.request = kwargs.pop('request', None) 
        # 2. Extrait 'school' des kwargs
        self.user_school = kwargs.pop('school', None) 
        
        # Maintenant, appelez la méthode _init_ de la classe parente
        # avec les kwargs qui ne contiennent plus 'request' ni 'school'.
        super().__init__(*args, **kwargs) # <-- Cette ligne est la ligne 412 selon votre traceback

        # --- Maintenant, utilisez self.user_school et self.request pour vos filtres ---
        if self.user_school:
            self.fields['academic_period'].queryset = AcademicPeriod.objects.filter(
                school=self.user_school
            ).order_by('-start_date')
            
            self.fields['classes'].queryset = Classe.objects.filter(
                school=self.user_school
            ).order_by('name')
            
            # Note: pour les enseignants, assurez-vous que 'user_type' est bien la valeur correcte
            self.fields['teachers'].queryset = CustomUser.objects.filter(
                Q(user_type='TEACHER') | Q(user_type='ADMIN'), 
                school=self.user_school,
                is_active=True
            ).order_by('first_name', 'last_name')
        else:
            # Si l'école n'est pas fournie, définissez des querysets vides
            self.fields['academic_period'].queryset = AcademicPeriod.objects.none()
            self.fields['classes'].queryset = Classe.objects.none()
            self.fields['teachers'].queryset = CustomUser.objects.none()

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user_school and not instance.school_id:
            instance.school = self.user_school
        
        if commit:
            instance.save()
            self.save_m2m() # Important pour les champs ManyToMany (classes, teachers)
        return instance

class TeacherCreationForm(forms.ModelForm):
    """
    Formulaire pour créer un nouveau compte enseignant.
    """
    password = forms.CharField(widget=forms.PasswordInput, help_text="Entrez le mot de passe de l'enseignant.")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirmer le mot de passe")

    class Meta:
        model = CustomUser
        # Définissez les champs que vous voulez pour la création d'un enseignant
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'address', 'profile_picture', 'password')

    def __init__(self, *args, **kwargs):
        # Gérer user_school si vous voulez que les enseignants soient créés dans une école spécifique
        # Cela pourrait être l'école de l'administrateur qui crée l'enseignant.
        self.user_school = kwargs.pop('user_school', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Les mots de passe ne correspondent pas.")
        
        email = cleaned_data.get("email")
        if email and CustomUser.objects.filter(email=email).exists():
            self.add_error('email', "Cette adresse email est déjà utilisée.")
        
        return cleaned_data

    def save(self, commit=True, school=None):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.user_type = UserRole.TEACHER # Assurez-vous que TEACHER est un rôle valide dans UserRole
        if school:
            user.school = school
        elif self.user_school: # Utiliser l'école passée lors de l'initialisation du formulaire
            user.school = self.user_school
        if commit:
            user.save()
        return user
    
class ExistingParentForm(forms.Form):
    """
    Formulaire pour lier un élève à un parent existant via sa recherche.
    Le champ 'parent_id' est caché et rempli par JS.
    """
    # Ce champ est pour stocker l'ID du parent sélectionné via AJAX/JS.
    # Il est rendu requis au moment de la validation par le JS si l'onglet est actif.
    parent_id = forms.ModelChoiceField(
        queryset=CustomUser.objects.all(), # Le queryset complet sera filtré dans clean_parent_id
        label="ID du parent sélectionné",
        required=False, # Le JS le rendra requis si l'onglet est actif
        widget=forms.HiddenInput # Ce champ est caché et rempli par JavaScript
    )
    # Champ visible pour la recherche (non validé directement par ce formulaire, mais utilisé par JS)
    parent_search_term = forms.CharField(
        max_length=255,
        required=False, # Ce champ est pour l'affichage/recherche, pas pour la validation finale du formulaire
        label="Rechercher un Parent Existant",
        help_text="Tapez le nom, prénom ou email du parent."
    )

    def __init__(self, *args, **kwargs):
        # Récupérez 'user_school' des kwargs avant d'appeler super()._init_
        self.user_school = kwargs.pop('user_school', None)
        super().__init__(*args, **kwargs)

        # Si vous vouliez pré-filtrer le queryset du ModelChoiceField (pour une liste déroulante),
        # ce serait ici. Mais avec votre système d'autocomplétion JS, ce n'est pas nécessaire
        # car le champ parent_id est un HiddenInput et est validé dans clean_parent_id.

    def clean_parent_id(self):
        parent_instance = self.cleaned_data.get('parent_id')

        # Si le formulaire est soumis avec l'onglet "Sélectionner Parent Existant" actif,
        # le champ 'parent_id' doit avoir une valeur. Le JS doit le rendre 'required'.
        # Cette vérification est une validation secondaire côté serveur.
        # Si 'parent_id' est rendu 'required' par le JS et que l'utilisateur n'a pas sélectionné
        # ou si le JS n'a pas correctement rempli le champ caché, parent_instance sera None.
        if not parent_instance:
             # Cette erreur sera levée si l'ID n'est pas fourni ou est invalide
            raise forms.ValidationError("Veuillez sélectionner un parent valide dans la liste.")

        # Vérification cruciale : Assurez-vous que le parent sélectionné appartient à l'école de l'utilisateur connecté
        if parent_instance.user_type != UserRole.PARENT or parent_instance.school != self.user_school:
            raise forms.ValidationError("Le parent sélectionné est invalide ou n'appartient pas à votre école.")

        return parent_instance