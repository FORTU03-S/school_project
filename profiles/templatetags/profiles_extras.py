# profiles/templatetags/profiles_extras.py
from django import template

register = template.Library()

@register.filter
def get_classe_name(course):
    """Retourne le nom de la classe d'un cours ou 'N/A' si la classe est nulle."""
    if course.classe:
        return course.classe.name
    return 'N/A'

@register.filter
def get_classe_full_name(course):
    """Retourne le nom complet de la classe (Nom du cours (Nom de la classe)) ou Nom du cours (N/A)."""
    if course.classe:
        return f"{course.name} ({course.classe.name})"
    return f"{course.name} (N/A)"