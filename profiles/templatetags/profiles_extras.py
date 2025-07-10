# profiles/templatetags/profiles_extras.py (ou profiles_tags.py)
from django import template

register = template.Library()

@register.filter
def get_student_status(student_status_list, student_id):
    """
    Recherche le statut de paiement d'un élève dans une liste de dictionnaires.
    """
    for status in student_status_list:
        if hasattr(status.get('student'), 'id') and status.get('student').id == student_id:
            return status
    # Retourne un dictionnaire par défaut si l'élève n'est pas trouvé
    return {'fees_due': 0, 'amount_paid': 0, 'remaining_balance': 0, 'status_text': 'N/A', 'status_class': ''}

@register.filter
def replace(value, arg):
    """
    Remplace toutes les occurrences d'une sous-chaîne par une autre.
    Utilisation: {{ value|replace:"old,new" }}
    """
    if isinstance(value, str) and ',' in arg:
        old, new = arg.split(',', 1)
        return value.replace(old, new)
    return value # Retourne la valeur originale si non valide

@register.filter
def get_student_status(student_payment_status_list, student_id):
    """
    Looks up student payment status data from a list by student_id.
    Assumes student_payment_status_list is a list of dictionaries/objects,
    each having a 'student' attribute with an 'id'.
    """
    for status_data in student_payment_status_list:
        if hasattr(status_data, 'student') and status_data.student.id == student_id:
            return status_data
        elif isinstance(status_data, dict) and status_data.get('student') and status_data['student'].id == student_id:
            # Fallback for dictionary if 'student' is an object
            return status_data
        elif isinstance(status_data, dict) and status_data.get('student_id') == student_id:
            # Fallback for dictionary if it directly stores 'student_id'
            return status_data
    return None # Return None if not found, or an empty dict {} if you prefer