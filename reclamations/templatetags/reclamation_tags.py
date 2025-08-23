from django import template

register = template.Library()

@register.filter(name='can_update_reclamation')
def can_update_reclamation(user, reclamation):
    """
    Vérifie si l'utilisateur peut mettre à jour une réclamation.
    Permet à:
    - L'utilisateur qui a créé la réclamation
    - Les administrateurs
    - Les agents de la station concernée
    - Tous les membres de l'équipe assignée à la réclamation
    """
    if not user.is_authenticated:
        return False
        
    
    if user.is_superuser or getattr(user, 'role', None) == 'ADMIN':
        return True
        
    
    if user == reclamation.user:
        return True
        

    if getattr(user, 'role', None) == 'AGENT' and hasattr(user, 'assigned_station'):
        return user.assigned_station == reclamation.station
        

    if hasattr(user, 'teams') and reclamation.assigned_team in user.teams:
        return True
        
    return False

@register.filter(name='in_statuses')
def in_statuses(value, statuses):
    """
    Vérifie si un statut est dans une liste de statuts séparés par des virgules.
    Usage: {{ reclamation.status|in_statuses:"OPEN,IN_PROGRESS" }}
    """
    status_list = [s.strip().upper() for s in statuses.split(',')]
    return value in status_list

@register.filter(name='can_view_internal_notes')
def can_view_internal_notes(user):
    """
    Vérifie si l'utilisateur peut voir les notes internes.
    """
    return getattr(user, 'role', None) in ['ADMIN', 'AGENT', 'TECH', 'FINANCE', 'SUPPORT']

@register.simple_tag
def get_status_badge_class(status):
    """
    Retourne la classe Bootstrap pour le badge de statut.
    """
    status_classes = {
        'OPEN': 'bg-info',
        'IN_PROGRESS': 'bg-warning text-dark',
        'RESOLVED': 'bg-success',
        'REJECTED': 'bg-danger',
        'CLOSED': 'bg-secondary'
    }
    return status_classes.get(status, 'bg-secondary')