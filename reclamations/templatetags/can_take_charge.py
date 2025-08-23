from django import template

register = template.Library()

@register.filter
def can_take_charge(user, reclamation):
    """
    Vérifie si l'utilisateur peut prendre en charge la réclamation
    """
    return (
        user.is_authenticated and
        hasattr(user, 'is_specialist') and
        user.is_specialist and
        hasattr(user, 'teams') and
        reclamation.assigned_team in user.teams.all() and
        not reclamation.assigned_specialist
    )