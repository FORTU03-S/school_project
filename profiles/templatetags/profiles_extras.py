# profiles/templatetags/profiles_extras.py

from django import template

register = template.Library()

@register.filter
def get_classe_name(course):
    # 'classes' est un ManyToManyField, il faut itérer dessus pour obtenir les noms
    # Si un cours peut être associé à plusieurs classes, nous voulons afficher tous les noms.
    # Si vous voulez juste la première classe, utilisez .first()
    # Si vous voulez tous les noms séparés par des virgules :
    
    # Vérifiez si le cours a des classes associées
    if course.classes.exists():
        # Récupère tous les noms des classes et les joint avec une virgule
        return ", ".join([classe.name for classe in course.classes.all()])
    else:
        return "N/A" # Ou une autre indication si aucune classe n'est associée