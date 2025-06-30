# school_project/school_project/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required # Importez ceci
from . import views

# profiles/views.py (extrait)

@login_required
def home_view(request):
    # Assurez-vous que ce template existe (profiles/templates/profiles/home.html)
    return render(request, 'profiles/home.html')

@login_required # Cette ligne assure que seul un utilisateur connecté peut accéder à cette vue
def dashboard_home_view(request):
    return render(request, 'dashboard_home.html')

@login_required
def teacher_dashboard_view(request):
    # Vous pouvez ajouter ici de la logique spécifique à l'enseignant
    return render(request, 'dashboard_teacher.html')

@login_required # <-- Assurez-vous que cette fonction est bien là
def parent_dashboard_view(request):
    # Vous pouvez ajouter ici de la logique spécifique au parent
    return render(request, 'dashboard_parent.html')

@login_required
def student_dashboard_view(request):
    return render(request, 'dashboard_student.html')

@login_required
def direction_dashboard_view(request):
    return render(request, 'dashboard_direction.html')