from django import template

register = template.Library()

@register.filter(name='is_specialist')
def is_specialist(user):
    """Vérifie si l'utilisateur est un spécialiste"""
    return user.role in {'TECH', 'FINANCE', 'SUPPORT', 'AGENT'}

@register.filter(name='subtract')
def subtract(value, arg):
    """Soustrait arg à value (pour les templates)"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value