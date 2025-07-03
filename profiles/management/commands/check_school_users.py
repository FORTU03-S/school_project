from django.core.management.base import BaseCommand
from profiles.models import CustomUser
from school.models import School

class Command(BaseCommand):
    help = 'Vérifie et liste les utilisateurs (en particulier les enseignants) associés à une école spécifique.'

    def handle(self, *args, **kwargs):
        nom_exact_de_l_ecole = "LYCEE" # Définissez le nom de l'école ici

        self.stdout.write(self.style.NOTICE(f"Tentative de recherche de l'école : '{nom_exact_de_l_ecole}'"))
        try:
            ma_school = School.objects.get(name=nom_exact_de_l_ecole)
            self.stdout.write(self.style.SUCCESS(f"École trouvée : {ma_school.name} (ID : {ma_school.id})"))
        except School.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"ERREUR : L'école '{nom_exact_de_l_ecole}' n'a pas été trouvée."))
            ma_school = None

        if ma_school:
            self.stdout.write(self.style.NOTICE("\n--- Liste des ENSEIGNANTS pour LYCEE ---"))
            enseignants_de_mon_ecole = CustomUser.objects.filter(user_type='TEACHER', school=ma_school)

            if not enseignants_de_mon_ecole.exists():
                self.stdout.write(self.style.WARNING("AUCUN utilisateur de type 'TEACHER' trouvé pour cette école."))
            # ... (code précédent) ...
            else:
                    for enseignant in enseignants_de_mon_ecole:
                        # Enveloppez la f-string multiligne entre parenthèses
                        self.stdout.write(self.style.HTTP_INFO(
                            (f"  - ID: {enseignant.id}, Nom: {enseignant.get_full_name()}, Email: {enseignant.email}, Type: {enseignant.user_type}, "
                             f"École: {enseignant.school.name if enseignant.school else 'N/A'}, Actif: {enseignant.is_active}")
                        ))
# ... (code suivant) ...
        else:
            self.stdout.write(self.style.ERROR("\nDiagnostic des enseignants impossible car l'école n'a pas été trouvée."))