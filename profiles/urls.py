# school_project/profiles/urls.py

from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views # Importez les vues d'authentification de Django

app_name = 'profiles'

urlpatterns = [
    # AUTHENTIFICATION
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('admin-accounting-dashboard/', views.accounting_dashboard_view, name='accounting_dashboard'),

    # INSCRIPTION
    path('register/choice/', views.register_view, name='register_choice'),
    #path('register/parent/', views.register_parent_view, name='register_parent'),
    path('register/teacher/', views.register_teacher_view, name='register_teacher'),
    path('home/', views.home_view, name='home'),

    # PAGES D'ACCUEIL ET DASHBOARDS (UNE SEULE DÉFINITION)
    path('', views.home_view, name='home'),
    path('parent-dashboard/', views.parent_dashboard_view, name='parent_dashboard'),
    path('teacher-dashboard/', views.teacher_dashboard_view, name='teacher_dashboard'),
    path('direction-dashboard/', views.direction_dashboard_view, name='direction_dashboard'),
    path('accounting-dashboard/', views.accounting_dashboard_view, name='accounting_dashboard'),

    # GESTION DES UTILISATEURS (Direction)
    path('direction/users/', views.direction_manage_users, name='direction_manage_users'),
    path('direction/users/<int:user_id>/approve/', views.direction_approve_user, name='direction_approve_user'),
    path('direction/manage-class-assignments/', views.direction_manage_class_assignments, name='direction_manage_class_assignments'),
    path('direction/manage-class-assignments/<int:assignment_id>/delete/', views.direction_delete_class_assignment, name='direction_delete_class_assignment'),
    path('student/add/', views.add_student_view, name='add_student'),
    path('courses/edit/<int:pk>/', views.course_update, name='course_update'),
    path('courses/delete/<int:pk>/', views.course_delete, name='course_delete'),
    path('students/', views.list_students_view, name='list_students'),
    path('courses/add/', views.course_create, name='course_create'),
    #path('courses/', views.course_list, name='course_list'),
    path('classes/<int:classe_id>/courses/', views.course_list, name='class_courses'), # Ensure this is present if class-filtered courses are needed
    path('courses/', views.all_courses_view, name='course_list'),
    # FONCTIONNALITÉS ENSEIGNANT
    path('teacher/students/', views.teacher_list_students_view, name='teacher_list_students_view'),
    path('teacher/class/<int:class_id>/manage-students/', views.teacher_add_remove_students_to_class, name='teacher_add_remove_students_to_class'),
    path('teacher/attendance/', views.teacher_attendance_view, name='teacher_attendance_view'),
    path('teacher/evaluations/', views.teacher_manage_evaluations, name='teacher_manage_evaluations'),
    path('teacher/evaluations/add/', views.teacher_add_evaluation, name='teacher_add_evaluation'),
    path('teacher/evaluations/<int:evaluation_id>/enter_grades/', views.teacher_enter_grades, name='teacher_enter_grades'),
    path('teacher/grades/', views.teacher_grades_view, name='manage_grades'),
    path('teacher/messages/', views.teacher_message_view, name='send_message'),
    path('teacher/evaluations/<int:evaluation_id>/delete/', views.teacher_delete_evaluation, name='teacher_delete_evaluation'),
    path('teacher/students/<int:student_id>/detail/', views.teacher_student_detail_view, name='teacher_student_detail'),
    path('teacher/send-message-to-parents/<int:student_id>/', views.teacher_send_message_to_parents, name='teacher_send_message_to_parents'),

    # URLs pour les Classes (Classe) - CONSOLIDER ICI
    path('classes/', views.class_list, name='class_list'), # <-- GARDER SEULEMENT CELUI-CI
    path('classes/add/', views.classe_create, name='classe_create'),
    path('classes/edit/<int:pk>/', views.classe_create, name='classe_update'), # Revoir si classe_create est bien pour update
    # path('classes/<int:pk>/', views.classe_detail, name='classe_detail'), # Décommenter si nécessaire
    # path('classes/<int:pk>/edit/', views.classe_update, name='classe_update'), # Décommenter si nécessaire (et différencier de classe_create)
    # path('classes/<int:pk>/delete/', views.classe_delete, name='classe_delete'), # Décommenter si nécessaire

    # FONCTIONNALITÉS PARENT
    path('parent/child/<int:child_id>/', views.parent_child_detail_view, name='parent_child_detail'),
    path('parent/child/<int:student_id>/payments/', views.parent_child_payments_view, name='child_payments'),
    path('parent/notifications/', views.parent_notifications_view, name='parent_notifications'),
    path('parent/notifications/mark-read/<int:notification_id>/', views.parent_mark_notification_read, name='parent_mark_notification_read'),
    path('parent/children/<int:student_id>/payments/', views.parent_child_payments_view, name='parent_child_payments'), # Dupliqué de child_payments?
    path('parent/evaluations/', views.parent_evaluations_view, name='parent_evaluations'),
    path('parent/attendance/', views.parent_attendance_view, name='parent_attendance'),
    path('parent/my_children/', views.parent_my_children_list_view, name='parent_my_children'),
    path('parent/child/<int:student_id>/evaluations/', views.parent_evaluations_view, name='parent_child_evaluations'), # Dupliqué de parent_evaluations?
    path('send-notification/', views.send_notification_view, name='send_notification'),
    # ...
    # NOUVELLES URLS DE NOTIFICATIONS/MESSAGERIE (pour la direction) ---
    # Nettoyage des URLs de notification qui posaient conflit
    # La page d'entrée générale pour l'envoi de notifications (choix du type de destinataire)
    path('send-notification/', views.direction_send_notification_view, name='direction_send_notification'),

    # Envoyer un message à un parent spécifique (via l'ID de l'élève pour trouver le parent)
    path('send-notification/to-parent/<int:student_id>/', views.direction_send_message_to_single_parent, name='direction_send_message_to_single_parent'),

    # Envoyer un message aux parents de toutes les classes (ajouté précédemment, confirmé)
    path('send-notification/to-all-parents/', views.direction_send_message_to_all_parents, name='direction_send_message_to_all_parents'),

    # Envoyer un message aux parents d'une classe spécifique
    path('send-notification/to-class-parents/<int:classe_id>/', views.direction_send_message_to_class_parents, name='direction_send_message_to_class_parents'),
    path('academic-periods/add/', views.academic_period_create, name='academic_period_create'),
    path('students/<int:student_id>/profile/', views.student_profile_view, name='student_profile'),

    # URLS DE RÉINITIALISATION DE MOT DE PASSE (Django's built-in views)
    path('password_reset/',
         auth_views.PasswordResetView.as_view(template_name='profiles/password_reset_form.html'),
         name='password_reset'),
    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='profiles/password_reset_done.html'),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='profiles/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(template_name='profiles/password_reset_complete.html'),
         name='password_reset_complete'),
    path('academic-periods/', views.academic_period_list, name='academic_period_list'), # <-- ADD THIS LINE
    #path('academic-periods/add/', views.academic_period_create, name='academic_period_create'),
]