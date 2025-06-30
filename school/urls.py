# school_project/school/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views # Assurez-vous d'importer views. Vous devrez créer ce fichier views.py 

urlpatterns = [

    path('profiles/', include('profiles.urls')), # Assurez-vous d'avoir cette ligne si votre app profiles existe
    path('school/', include('school.urls')),    # <--- CETTE LIGNE EST INDISPENSABLE !
    # Vous pouvez aussi inclure directement à la racine si vous voulez : path('', include('school.urls')),
    
    # URLs pour les Périodes Académiques (AcademicPeriod)
    path('academic-periods/', views.academic_period_list, name='academic_period_list'),
    #path('classes/add/', views.classe_create, name='classe_create'),
 
   
    path('academic-periods/<int:pk>/', views.academic_period_detail, name='academic_period_detail'),
    path('academic-periods/<int:pk>/edit/', views.academic_period_update, name='academic_period_update'),
    path('academic-periods/<int:pk>/delete/', views.academic_period_delete, name='academic_period_delete'),

   

    # URLs pour les Étudiants (Student)
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.student_create, name='student_create'),
    path('students/<int:pk>/', views.student_detail, name='student_detail'),
    path('students/<int:pk>/edit/', views.student_update, name='student_update'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    path('students/<int:pk>/enroll/', views.student_enroll_course, name='student_enroll_course'), # Pour inscrire un élève à un cours

    # URLs pour les Cours (Course)
    

    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('courses/<int:pk>/edit/', views.course_update, name='course_update'),
    path('courses/<int:pk>/delete/', views.course_delete, name='course_delete'),

    # URLs pour les Notes (Grade)
    path('grades/', views.grade_list, name='grade_list'),
    path('grades/add/', views.grade_create, name='grade_create'),
    path('grades/<int:pk>/', views.grade_detail, name='grade_detail'),
    path('grades/<int:pk>/edit/', views.grade_update, name='grade_update'),
    path('grades/<int:pk>/delete/', views.grade_delete, name='grade_delete'),
    path('grades/student/<int:student_pk>/', views.student_grades, name='student_grades'), # Toutes les notes d'un élève

    # URLs pour les Présences (Attendance)
    
    path('attendances/', views.attendance_list, name='attendance_list'),
    path('attendances/add/', views.attendance_create, name='attendance_create'),
    path('attendances/<int:pk>/', views.attendance_detail, name='attendance_detail'),
    path('attendances/<int:pk>/edit/', views.attendance_update, name='attendance_update'),
    path('attendances/<int:pk>/delete/', views.attendance_delete, name='attendance_delete'),
    path('attendances/class/<int:classe_pk>/<str:date>/', views.class_attendance, name='class_attendance'), # Présence par classe et date

    # URLs pour les Notifications (Notification)
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/add/', views.notification_create, name='notification_create'),
    path('notifications/<int:pk>/', views.notification_detail, name='notification_detail'),
    path('notifications/<int:pk>/read/', views.notification_mark_read, name='notification_mark_read'), # Marquer comme lu
    path('notifications/<int:pk>/delete/', views.notification_delete, name='notification_delete'),


    # URLs pour les Paiements (Payment)
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/add/', views.payment_create, name='payment_create'),
    path('payments/<int:pk>/', views.payment_detail, name='payment_detail'),
    path('payments/<int:pk>/edit/', views.payment_update, name='payment_update'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
    path('payments/student/<int:student_pk>/', views.student_payments, name='student_payments') # Tous les paiements d'un élève
   
]