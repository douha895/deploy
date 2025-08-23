from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q

class SpecialistRequiredMixin(UserPassesTestMixin):
    """
    Mixin qui vérifie que l'utilisateur est un spécialiste
    et a accès à la ressource demandée
    """
    def test_func(self):
        user = self.request.user
        
        
        if not getattr(user, 'is_specialist', False):
            raise PermissionDenied("Accès réservé aux spécialistes")
        
        
        if hasattr(self, 'get_object'):
            obj = self.get_object()
            if hasattr(obj, 'assigned_specialist'):
                return obj.assigned_specialist == user
        
        return True

class SpecialistFilterMixin:
    """
    Mixin pour filtrer les réclamations selon le rôle de l'utilisateur
    """
    
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if user.is_specialist:
            return self.filter_for_specialist(qs, user)
        elif user.role == 'AGENT':
            return self.filter_for_agent(qs, user)
        elif user.role == 'CLIENT':
            return self.filter_for_client(qs, user)
        elif user.is_superuser or user.role == 'ADMIN':
            return qs  
        
        raise PermissionDenied("Accès non autorisé à ces réclamations")

    def filter_for_specialist(self, qs, user):
        """Filtre spécifique pour les spécialistes"""
        return qs.filter(
            Q(assigned_specialist=user) |
            Q(assigned_team__in=user.teams, assigned_specialist__isnull=True)
        ).distinct()

    def filter_for_agent(self, qs, user):
        """Filtre pour les agents de station"""
        if not user.assigned_station:
            return qs.none()
        return qs.filter(station=user.assigned_station)

    def filter_for_client(self, qs, user):
        """Filtre pour les clients"""
        return qs.filter(user=user)

    def get_context_data(self, **kwargs):
        """Ajoute des informations contextuelles utiles"""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.is_specialist:
            context['unassigned_count'] = self.get_queryset().filter(
                assigned_team__in=user.teams,
                assigned_specialist__isnull=True
            ).count()
        
        return context

class TeamRequiredMixin(UserPassesTestMixin):
    """
    Mixin qui vérifie que l'utilisateur appartient à une équipe spécifique
    """
    team = None 
    
    def test_func(self):
        user = self.request.user
        if not user.is_specialist:
            return False
        return self.team in getattr(user, 'teams', [])