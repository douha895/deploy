# reclamations/admin_dashboard/views.py
from django.contrib.auth.decorators import user_passes_test, login_required
from django.views.generic import FormView, ListView, View
from django.contrib.auth import login
from django.utils.decorators import method_decorator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse_lazy
from django.db.models import Count, Q
from django.utils import timezone
from django.db import IntegrityError
from datetime import timedelta
from ..models import InscriptionRequest, User, Reclamation
from ..forms import AdminAuthenticationForm
import secrets
import logging

logger = logging.getLogger(__name__)

def is_admin(user):
    """Vérifie si l'utilisateur est un admin d'approbation"""
    return hasattr(user, 'admin_profile') and user.admin_profile.is_approval_admin

def is_staff_user(user):
    """Vérifie si l'utilisateur est staff ou superuser"""
    return user.is_staff or user.is_superuser

class AdminLoginView(FormView):
    template_name = 'admin_dashboard/login.html'
    form_class = AdminAuthenticationForm
    success_url = reverse_lazy('admin_dashboard:dashboard')
    
    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        return super().form_valid(form)

@method_decorator(user_passes_test(is_admin), name='dispatch')
class AdminDashboardView(ListView):
    template_name = 'admin_dashboard/dashboard.html'
    model = InscriptionRequest
    context_object_name = 'pending_requests_list'
    
    def get_queryset(self):
        return InscriptionRequest.objects.filter(status='PENDING')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ajouter les statistiques pour le template
        context.update(self.get_dashboard_stats())
        return context
    
    def get_dashboard_stats(self):
        # Statistiques des demandes d'inscription
        total_requests = InscriptionRequest.objects.count()
        pending_requests = InscriptionRequest.objects.filter(status='PENDING')
        approved_requests = InscriptionRequest.objects.filter(status='APPROVED').count()
        rejected_requests = InscriptionRequest.objects.filter(status='REJECTED').count()
        
        # Statistiques des utilisateurs
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        
        # Statistiques des réclamations
        try:
            total_reclamations = Reclamation.objects.count()
            today = timezone.now().date()
            reclamations_today = Reclamation.objects.filter(
                date_creation__date=today
            ).count()
        except:
            total_reclamations = 0
            reclamations_today = 0
        
        return {
            'total_requests': total_requests,
            'pending_requests_count': pending_requests.count(),
            'approved_requests': approved_requests,
            'rejected_requests': rejected_requests,
            'total_users': total_users,
            'active_users': active_users,
            'total_reclamations': total_reclamations,
            'reclamations_today': reclamations_today,
        }

@method_decorator(user_passes_test(is_admin), name='dispatch')
class ProcessRequestView(View):
    def post(self, request, pk):
        action = request.POST.get('action')
        inscription = get_object_or_404(InscriptionRequest, pk=pk)
        
        if action == 'approve':
            return self._approve_request(request, inscription)
        elif action == 'reject':
            return self._reject_request(request, inscription)
        
        return redirect('admin_dashboard:dashboard')

    def _approve_request(self, request, inscription):
        try:
            # Vérifier si l'utilisateur existe déjà
            if User.objects.filter(username=inscription.username).exists():
                messages.error(request, f"L'utilisateur '{inscription.username}' existe déjà.")
                return redirect('admin_dashboard:dashboard')
            
            if User.objects.filter(email=inscription.email).exists():
                messages.error(request, f"L'email '{inscription.email}' est déjà utilisé.")
                return redirect('admin_dashboard:dashboard')
            
            password = secrets.token_urlsafe(12)
            user = User.objects.create_user(
                username=inscription.username,
                email=inscription.email,
                password=password,
                role=inscription.role,
                is_active=True
            )
            
            # Email d'approbation
            message = f"""Votre compte Agilis a été approuvé

Bonjour {inscription.username},

Votre demande d'inscription a été approuvée.

Voici vos identifiants :
Email: {inscription.email}
Mot de passe: {password}

Connectez-vous pour changer votre mot de passe après la première connexion."""
            
            send_mail(
                subject="Votre compte Agilis a été approuvé",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[inscription.email]
            )
            
            inscription.status = 'APPROVED'
            inscription.save()
            
            messages.success(request, "Demande approuvée avec succès")
            
        except IntegrityError as e:
            logger.error(f"Erreur d'intégrité lors de l'approbation: {e}")
            messages.error(request, "Erreur lors de la création de l'utilisateur. Veuillez réessayer.")
        
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'approbation: {e}")
            messages.error(request, "Une erreur inattendue s'est produite.")
        
        return redirect('admin_dashboard:dashboard')

    def _reject_request(self, request, inscription):
        try:
            # Email de rejet
            message = f"""Votre demande Agilis

Bonjour {inscription.username},

Votre demande n'a pas été approuvée.

Contactez le support pour plus d'informations."""
            
            send_mail(
                subject="Votre demande Agilis",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[inscription.email]
            )
            
            inscription.status = 'REJECTED'
            inscription.save()
            
            messages.success(request, "Demande rejetée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors du rejet: {e}")
            messages.error(request, "Erreur lors du traitement du rejet")
        
        return redirect('admin_dashboard:dashboard')

# Vue fonction alternative pour le dashboard (au choix)
@login_required
@user_passes_test(is_staff_user)
def dashboard(request):
    # Statistiques des demandes d'inscription
    pending_requests = InscriptionRequest.objects.filter(status='PENDING')
    total_requests = InscriptionRequest.objects.count()
    approved_requests = InscriptionRequest.objects.filter(status='APPROVED').count()
    rejected_requests = InscriptionRequest.objects.filter(status='REJECTED').count()
    
    # Statistiques des utilisateurs
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    
    # Statistiques des réclamations
    try:
        total_reclamations = Reclamation.objects.count()
        today = timezone.now().date()
        reclamations_today = Reclamation.objects.filter(
            date_creation__date=today
        ).count()
    except:
        total_reclamations = 0
        reclamations_today = 0
    
    context = {
        'pending_requests': pending_requests,
        'pending_requests_count': pending_requests.count(),
        'total_requests': total_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests,
        'total_users': total_users,
        'active_users': active_users,
        'total_reclamations': total_reclamations,
        'reclamations_today': reclamations_today,
    }
    
    return render(request, 'admin_dashboard/dashboard.html', context)