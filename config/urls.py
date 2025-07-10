# school_project/config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from profiles import views as profiles_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('profiles/', include('profiles.urls', namespace='profiles')), # <-- Vérifiez cette ligne
    # ... autres include d'applications ...
    path('', include('profiles.urls', namespace='profiles')),
    path('login/', profiles_views.login_view, name='login'),  # Authentification
    path('profiles_home/', profiles_views.home_view, name='home'),  # Page d'accueil
    path('select2/', include('django_select2.urls')),
]


# Pour servir les fichiers statiques et médias UNIQUEMENT en mode développement
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)