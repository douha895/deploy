from django.db.models import Count, Q
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import User, Reclamation, ReclamationUpdate
import logging
import traceback
import os
from typing import Optional

logger = logging.getLogger(__name__)


PROBLEM_TYPE_TO_TEAM = {
    'CARD_BLOCKED': 'TECH',
    'CARD_REJECTED': 'TECH',
    'STATION_ISSUE': 'TECH',
    'DAMAGED_CARD': 'TECH',
    'BALANCE_ERROR': 'FINANCE',
    'DOUBLE_CHARGE': 'FINANCE',
    'LIMIT_ISSUE': 'FINANCE',
    'PAYMENT_REFUSED': 'FINANCE'
}


ROLE_TO_TEAM_MAPPING = {
    'TECH': ['TECH'],
    'FINANCE': ['FINANCE'],
    'SUPPORT': ['SUPPORT'],
    'AGENT': ['STATION']
}

def assign_user_to_team(user: User) -> bool:
    """
    Assignation automatique des utilisateurs spécialistes à leurs équipes
    selon leur rôle.
    
    Args:
        user: Instance User à assigner
        
    Returns:
        bool: True si réussite, False si échec
    """
    try:
        if not hasattr(user, 'is_specialist') or not user.is_specialist:
            return True 

        
        user.teams = ROLE_TO_TEAM_MAPPING.get(user.role, [])

        
        if user.role == 'AGENT' and user.assigned_station:
            if 'STATION' not in user.teams:
                user.teams.append('STATION')

        user.save()
        logger.info(f"Assignation réussie pour {user.email} aux équipes: {user.teams}")
        return True

    except Exception as e:
        logger.error(f"Échec d'assignation pour {getattr(user, 'email', '')}: {str(e)}")
        return False

def assign_reclamation(reclamation: Reclamation) -> bool:
    """Assignation automatique des réclamations"""
    try:
        #det eq
        reclamation.assigned_team = PROBLEM_TYPE_TO_TEAM.get(
            reclamation.problem_type,
            'SUPPORT'  #equipe par défaut
        )
        reclamation.save()

        #rech spe
        specialist = find_available_specialist(reclamation.assigned_team)
        if not specialist:
            logger.warning(f"Aucun spécialiste disponible pour l'équipe {reclamation.assigned_team}")
            return False

        
        return _finalize_assignment(reclamation, specialist)

    except Exception as e:
        logger.error(f"Erreur d'assignation : {str(e)}\n{traceback.format_exc()}")
        return False

def _finalize_assignment(reclamation: Reclamation, specialist: User) -> bool:
    """Finalise l'assignation"""
    try:
        reclamation.assigned_specialist = specialist
        reclamation.save()

        
        ReclamationUpdate.objects.create(
            reclamation=reclamation,
            author=None,
            message=f"Assigné à {specialist.get_full_name()}",
            is_status_change=False
        )

        
        send_specialist_notification(reclamation, specialist)
        return True

    except Exception as e:
        logger.error(f"Erreur de finalisation : {str(e)}")
        return False

def find_available_specialist(team: str) -> Optional[User]:
    """Trouve un spécialiste disponible"""
    try:
        specialists = User.objects.filter(
            is_active=True,
            is_specialist=True,
            teams__contains=[team]  # PostgreSQL
        ).annotate(
            num_active=Count('specialist_reclamations',
                filter=Q(specialist_reclamations__status__in=['OPEN', 'IN_PROGRESS'])
            )
        ).order_by('num_active')

        return specialists.first() if specialists.exists() else None

    except Exception as e:
        logger.error(f"Erreur de recherche : {str(e)}")
        return None

def send_specialist_notification(reclamation: Reclamation, specialist: User) -> None:
    """Envoi de notification au spécialiste"""
    try:
        context = {
            'reclamation': reclamation,
            'specialist': specialist,
            'priority': reclamation.get_priority_display(),
            'problem_type': reclamation.get_problem_type_display(),
            'detail_url': f"{settings.BASE_URL}/reclamations/{reclamation.id}/"
        }

        send_mail(
            subject=f"Nouvelle réclamation (#{reclamation.id})",
            message=render_to_string('emails/specialist_assignment.txt', context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[specialist.email],
            html_message=render_to_string('emails/specialist_assignment.html', context),
            fail_silently=False
        )

    except Exception as e:
        logger.error(f"Erreur d'envoi de notification : {str(e)}")
        raise

def _determine_file_type(filename: str) -> str:
    """Détermine le type de fichier"""
    extension = os.path.splitext(filename)[1].lower()
    return {
        '.jpg': 'IMAGE',
        '.jpeg': 'IMAGE',
        '.png': 'IMAGE',
        '.gif': 'IMAGE',
        '.bmp': 'IMAGE',
        '.pdf': 'PDF',
        '.doc': 'DOCUMENT',
        '.docx': 'DOCUMENT',
        '.xls': 'SPREADSHEET',
        '.xlsx': 'SPREADSHEET'
    }.get(extension, 'OTHER')