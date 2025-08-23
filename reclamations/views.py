import os
import json
import logging
from django.contrib.auth.mixins import (
    LoginRequiredMixin, 
    UserPassesTestMixin
)
from django.views.generic import (
    ListView, CreateView, DetailView, 
    UpdateView, DeleteView, TemplateView
)
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse, FileResponse
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.views.generic.edit import FormView

from .models import Reclamation, ReclamationUpdate, Attachment, Station, Card
from .forms import (
    ReclamationForm, 
    ReclamationUpdateForm,
    SpecialistProfileForm,
    ReassignmentForm
)
from django.urls import reverse 
from .forms import CustomUserCreationForm
from .mixins import SpecialistRequiredMixin
from .utils import assign_reclamation, send_specialist_notification
logger = logging.getLogger(__name__)
User = get_user_model()

# ----------------------
# Helper functions
# ----------------------
def _determine_file_type(filename: str) -> str:
    """Détermine le type de fichier pour les pièces jointes"""
    ext = filename.split('.')[-1].lower()
    if ext in {'jpg', 'jpeg', 'png', 'gif'}:
        return 'IMAGE'
    elif ext == 'pdf':
        return 'PDF'
    return 'OTHER'

# ----------------------
# Authentication Viewsfrom django.contrib.auth import login
from django.contrib import messages
from django.urls import reverse
from django.views.generic import CreateView
from django.shortcuts import redirect
from django.core.mail import send_mail
from django.conf import settings
from .forms import CustomUserCreationForm
from .utils import assign_user_to_team
from .models import InscriptionRequest, AdminProfile
import logging
import traceback
from django.contrib.auth import login
from django.http import HttpResponseRedirect

logger = logging.getLogger(__name__)

class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'registration/register.html'

    def get_success_url(self):
        """
        Détermine la redirection après inscription réussie
        Basé sur le type d'utilisateur (spécialiste ou non)
        """
        user = self.object
        if user.is_specialist:
            return reverse('reclamations:specialist_dashboard')
        return reverse('reclamations:list')

    def form_valid(self, form):
        """
        Traitement du formulaire valide avec :
        - Pour les ADMINS : création directe du compte
        - Pour les autres rôles : création d'une demande d'inscription
        - Assignation automatique aux équipes pour les spécialistes
        - Connexion automatique si compte créé directement
        - Notifications appropriées
        """
        try:
            role = form.cleaned_data['role']
            
            # Cas des ADMINS (création directe)
            if role == 'ADMIN':
                response = super().form_valid(form)
                user = self.object
                
                # Création du profil admin
                AdminProfile.objects.create(user=user)
                
                # Assignation aux équipes si nécessaire
                if user.is_specialist and not assign_user_to_team(user):
                    logger.warning(f"Échec d'assignation aux équipes pour l'admin {user.email}")
                
                # Connexion automatique
                login(self.request, user)
                messages.success(self.request, 'Compte admin créé avec succès!')
                return response
            
            # Pour tous les autres rôles (demande d'inscription)
            InscriptionRequest.objects.create(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                role=role,
                phone=form.cleaned_data.get('phone', ''),
                status='PENDING'
            )
            
            # Notification à l'admin
            send_mail(
                subject="Nouvelle demande d'inscription",
                message=f"Une nouvelle demande d'inscription a été soumise:\n\n"
                        f"Nom: {form.cleaned_data['username']}\n"
                        f"Email: {form.cleaned_data['email']}\n"
                        f"Rôle: {dict(User.ROLE_CHOICES).get(role)}\n"
                        f"Date: {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=True
            )
            
            messages.info(self.request, 
                "Votre demande a été soumise pour approbation. "
                "Vous recevrez un email une fois votre compte activé."
            )
            
            # SOLUTION : Redirection par URL absolue au lieu du nom pour éviter CSRF
            return redirect('/accounts/login/')  # URL absolue

        except Exception as e:
            logger.error(f"Erreur lors de l'inscription : {str(e)}\n{traceback.format_exc()}")
            messages.error(self.request, "Une erreur est survenue lors de votre inscription.")
            return self.form_invalid(form)










        


    

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'registration/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.is_specialist:
            reclamations = Reclamation.objects.filter(
                assigned_specialist=user
            )
            template_name = 'specialist/profile.html'
        else:
            reclamations = Reclamation.objects.filter(user=user)
            template_name = 'registration/profile.html'
        
        context.update({
            'user': user,
            'nb_reclamations': reclamations.count(),
            'nb_reclamations_resolues': reclamations.filter(status='RESOLVED').count(),
            'nb_reclamations_encours': reclamations.exclude(
                status__in=['RESOLVED', 'CLOSED']
            ).count(),
            'last_activities': ReclamationUpdate.objects.filter(
                Q(reclamation__user=user) | Q(author=user)
            ).order_by('-created_at')[:5]
        })
        
        # Change le template selon le rôle
        self.template_name = template_name
        
        return context
    




from django.contrib.messages.views import SuccessMessageMixin
from .forms import UserProfileForm, SpecialistProfileForm

class ProfileUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = 'registration/profile_edit.html'
    success_message = "Profil mis à jour avec succès"

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return reverse('reclamations:profile')







# ----------------------
# Reclamation Views
# ----------------------
class ReclamationListView(LoginRequiredMixin, ListView):
    model = Reclamation
    template_name = 'reclamations/list.html'
    context_object_name = 'reclamations'
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if user.role == 'CLIENT':
            qs = qs.filter(user=user)
        elif user.role == 'AGENT':
            qs = qs.filter(station=user.assigned_station)
        elif user.is_specialist:
            qs = qs.filter(assigned_team__in=user.teams)
            
            assignment_filter = self.request.GET.get('assignment')
            if assignment_filter == 'assigned':
                qs = qs.filter(assigned_specialist=user)
            elif assignment_filter == 'unassigned':
                qs = qs.filter(assigned_specialist__isnull=True)
        
        status_filter = self.request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['status_filter'] = self.request.GET.get('status', '')
        
        if user.is_specialist:
            ctx['unassigned_reclamations'] = Reclamation.objects.filter(
                assigned_team__in=user.teams,
                assigned_specialist__isnull=True
            ).exclude(status='RESOLVED')
        
        return ctx

from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic.edit import CreateView
import logging
import traceback
from .models import Reclamation, Station, Attachment
from .forms import ReclamationForm
from .utils import assign_reclamation, _determine_file_type

logger = logging.getLogger(__name__)

class ReclamationCreateView(LoginRequiredMixin, CreateView):
    model = Reclamation
    form_class = ReclamationForm
    template_name = 'reclamations/create.html'

    def dispatch(self, request, *args, **kwargs):
        """Vérifie les permissions avant de traiter la requête"""
        if not request.user.can_create_reclamation:
            messages.error(request, "Seuls les clients peuvent créer des réclamations")
            return HttpResponseRedirect(reverse('reclamations:dashboard'))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stations = Station.objects.all().values('id', 'name', 'latitude', 'longitude')
        context['stations_json'] = list(stations)
        
        
        if not self.request.user.can_create_reclamation:
            context['permission_message'] = "Action réservée aux clients"
            
        return context

    @transaction.atomic
    def form_valid(self, form):
        """Handle successful form submission with transaction"""
        try:
            
            if not self.request.user.can_create_reclamation:
                raise PermissionDenied("Violation de sécurité : tentative de création non autorisée")
            
            self.object = form.save(commit=False)
            self.object.user = self.request.user
            self.object.status = 'OPEN'
            self.object.save()
            
            
            assign_reclamation(self.object) 
            

            for f in self.request.FILES.getlist('attachments'):
                Attachment.objects.create(
                    reclamation=self.object,
                    file=f,
                    description=f.name[:200],
                    file_type=_determine_file_type(f.name)
                )
            
            messages.success(self.request, f"Réclamation #{self.object.id} créée avec succès")
            return HttpResponseRedirect(self.get_success_url())
            
        except PermissionDenied:
            logger.warning("Tentative de création non autorisée par %s", self.request.user)
            raise  
            
        except Exception as e:
            logger.error("Error creating reclamation: %s\n%s", 
                        str(e), traceback.format_exc())
            messages.error(self.request, "Une erreur est survenue lors de la création de votre réclamation")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('reclamations:detail', kwargs={'pk': self.object.pk})




from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import DetailView
from django.db.models import Q
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from .models import Reclamation, ReclamationUpdate, Attachment
from .forms import ReclamationUpdateForm
from .utils import _determine_file_type

class ReclamationDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Reclamation
    template_name = 'reclamations/detail.html'
    context_object_name = 'reclamation'

    def test_func(self):
        """Vérifie les permissions d'accès"""
        user = self.request.user
        reclamation = self.get_object()
        
        
        if user.is_superuser or user.role == 'ADMIN':
            return True
            
        
        if user.role == 'CLIENT' and reclamation.user == user:
            return True
            
        
        if user.role == 'AGENT' and user.assigned_station == reclamation.station:
            return True
            
        
        if user.is_specialist and (reclamation.assigned_team in user.teams or reclamation.assigned_specialist == user):
            return True
            
        return False

    def get_queryset(self):
        """Filtrage initial pour optimiser les requêtes"""
        qs = super().get_queryset()
        user = self.request.user
        
        if user.role == 'CLIENT':
            return qs.filter(user=user)
        elif user.role == 'AGENT':
            return qs.filter(station=user.assigned_station)
        elif user.is_specialist:
            return qs.filter(Q(assigned_specialist=user) | Q(assigned_team__in=user.teams))
        elif user.is_superuser or user.role == 'ADMIN':
            return qs
        return qs.none()

    def get_context_data(self, **kwargs):
        """Prépare le contexte pour le template"""
        ctx = super().get_context_data(**kwargs)
        reclamation = self.object
        
        
        ctx['update_form'] = ReclamationUpdateForm(
            initial={
                'new_status': reclamation.status,
                'message': ''
            }
        )
        
        
        ctx['can_update'] = self._can_update_reclamation()
        
        
        ctx['updates'] = reclamation.updates.select_related('author').order_by('-created_at')
        
        
        ctx['attachments'] = reclamation.attachments.all()
        
        return ctx

    def _can_update_reclamation(self):
        """Détermine si l'utilisateur peut mettre à jour la réclamation"""
        user = self.request.user
        obj = self.object
        
        return any([
            user.is_superuser,
            user.role == 'ADMIN',
            user == obj.user,
            (user.role == 'AGENT' and obj.station == user.assigned_station),
            
            (user.is_specialist and obj.assigned_team in getattr(user, 'teams', []))
            
        ])

    def post(self, request, *args, **kwargs):
        """Gère les soumissions de formulaire de mise à jour"""
        self.object = self.get_object()
        
        if not self._can_update_reclamation():
            messages.error(request, "Permission refusée")
            return redirect('reclamations:detail', pk=self.object.pk)

        form = ReclamationUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            return self._process_valid_update(form)

        # Si le formulaire est invalide
        ctx = self.get_context_data()
        ctx['update_form'] = form
        return self.render_to_response(ctx)

    def _process_valid_update(self, form):
        """Traite une mise à jour valide"""
        update = form.save(commit=False)
        update.reclamation = self.object
        update.author = self.request.user
        
        
        new_status = form.cleaned_data.get('new_status')
        if new_status and new_status != self.object.status:
            update.is_status_change = True
            self.object.status = new_status
            self.object.save()
        
        update.save()

        
        for f in self.request.FILES.getlist('attachments'):
            Attachment.objects.create(
                reclamation=self.object,
                file=f,
                description=f.name[:200],  
                file_type=_determine_file_type(f.name),
                update=update  
            )

        messages.success(self.request, 'Mise à jour enregistrée avec succès!')
        return redirect('reclamations:detail', pk=self.object.pk)

    def handle_no_permission(self):
        """Gère les accès refusés"""
        messages.error(self.request, "Vous n'avez pas accès à cette réclamation")
        return redirect('reclamations:list')



from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse
from django.views.generic.edit import UpdateView
import logging
from django.core.exceptions import PermissionDenied
import traceback
from django.shortcuts import redirect
from .models import Reclamation, Station, Attachment
from .utils import _determine_file_type
from .forms import ReclamationForm

logger = logging.getLogger(__name__)

class ReclamationUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Reclamation
    form_class = ReclamationForm
    template_name = 'reclamations/update.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['stations_json'] = list(
                Station.objects.values('id', 'name', 'latitude', 'longitude')
            )
        except Exception as e:
            logger.error(f"Error loading stations: {str(e)}")
            context['stations_json'] = []
        return context

    def get_success_url(self):
        return reverse('reclamations:detail', kwargs={'pk': self.object.pk})

    def _handle_attachments(self):
        """Handle file attachments for the reclamation"""
        for f in self.request.FILES.getlist('attachments'):
            Attachment.objects.create(
                reclamation=self.object,
                file=f,
                description=f.name[:200],
                file_type=_determine_file_type(f.name)
            )

    def _process_station_coords(self, form, coords):
        """Process station coordinates if provided"""
        try:
            lat, lng = map(float, coords.split(','))
            form.instance.latitude = lat
            form.instance.longitude = lng
        except ValueError:
            logger.warning(f"Invalid coordinates format: {coords}")

    def form_valid(self, form):
        try:
            if not form.instance.user_id:
                form.instance.user = self.request.user
            
            if coords := self.request.POST.get('station_coords', '').strip():
                self._process_station_coords(form, coords)
            
            response = super().form_valid(form)
            self._handle_attachments()
            
            messages.success(self.request, 'Reclamation updated successfully!')
            return response
            
        except Exception as e:
            logger.error(f"Update error: {str(e)}\n{traceback.format_exc()}")
            messages.error(self.request, 'Error during update')
            return self.form_invalid(form)

    def test_func(self):
        obj = self.get_object()
        user = self.request.user
        
        
        logger.debug(
            f"Permission check - User: {user.id} ({user.role}), "
            f"Owner: {obj.user_id}, Assigned specialist: {obj.assigned_specialist_id}, "
            f"User station: {getattr(user, 'assigned_station_id', None)}, "
            f"Reclamation station: {obj.station_id}, "
            f"User teams: {getattr(user, 'teams', [])}, "
            f"Reclamation team: {obj.assigned_team}"
        )

        #perrmissions hierarchy
        return any([
            
            user.is_superuser or user.role == 'ADMIN',
            
            
            user == obj.user,
            
            
            (user.role == 'AGENT' and 
             obj.station_id == getattr(user, 'assigned_station_id', None)),
            
        
            (getattr(user, 'is_specialist', False) and 
             obj.assigned_specialist_id == user.id),
            
            
            (getattr(user, 'is_specialist', False) and 
             obj.assigned_team in getattr(user, 'teams', []) and
             obj.assigned_specialist_id is None)
        ])

    def handle_no_permission(self):
        messages.error(self.request, "Access denied: insufficient permissions")
        return redirect('reclamations:detail', pk=self.kwargs.get('pk'))
    




    
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic.edit import DeleteView
from django.core.exceptions import PermissionDenied
import logging
from .models import Reclamation

logger = logging.getLogger(__name__)

class ReclamationDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Reclamation
    template_name = 'reclamations/confirm_delete.html'
    success_url = reverse_lazy('reclamations:list')

    def test_func(self):
        """Vérifie les permissions de suppression"""
        obj = self.get_object()
        user = self.request.user
        
        
        if user.is_superuser:
            return True
            
        
        if user.role == 'ADMIN' and obj.station in user.managed_stations.all():
            return True
            
        
        if user == obj.user:
            return True
            
        
        if (hasattr(user, 'is_specialist') and 
            user.is_specialist and 
            obj.assigned_specialist == user and
            obj.status in ['NEW', 'OPEN']):
            return True
            
        return False

    def handle_no_permission(self):
        """Gère les tentatives d'accès non autorisées"""
        if self.request.user.is_authenticated:
            messages.error(self.request, "Action non autorisée : droits insuffisants")
            return redirect('reclamations:detail', pk=self.kwargs.get('pk'))
        return super().handle_no_permission()

    def delete(self, request, *args, **kwargs):
        """Gère la suppression avec journalisation"""
        try:
            obj = self.get_object()
            logger.info(f"Suppression réclamation {obj.id} par {request.user.username}")
            
            
            if hasattr(obj, 'archive'):
                obj.archive()
                
            messages.success(request, f'Réclamation #{obj.id} supprimée avec succès.')
            return super().delete(request, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Erreur suppression réclamation: {str(e)}")
            messages.error(request, "Échec de la suppression : une erreur est survenue")
            return redirect('reclamations:detail', pk=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        """Ajoute des informations contextuelles"""
        context = super().get_context_data(**kwargs)
        context['can_delete'] = self.test_func()  # Passe la permission au template
        return context
# ----------------------
# Utility Views
# ----------------------

def download_attachment(request, pk):
    attachment = get_object_or_404(Attachment, pk=pk)
    if not (request.user == attachment.reclamation.user or 
            request.user.is_staff or
            (request.user.is_specialist and 
             attachment.reclamation.assigned_specialist == request.user)):
        raise PermissionDenied
    response = FileResponse(
        attachment.file.open(), 
        as_attachment=True
    )
    response['Content-Disposition'] = (
        f'attachment; filename="{os.path.basename(attachment.file.name)}"'
    )
    return response

def update_reclamation_status(request, pk):
    if request.method == 'POST' and request.headers.get(
        'x-requested-with'
    ) == 'XMLHttpRequest':
        reclamation = get_object_or_404(Reclamation, pk=pk)
        if request.user.role not in ['AGENT', 'ADMIN'] and not (
            request.user.is_specialist and 
            reclamation.assigned_specialist == request.user
        ):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        new_status = request.POST.get('status')
        if new_status not in dict(Reclamation.STATUS_CHOICES):
            return JsonResponse({'error': 'Invalid status'}, status=400)

        reclamation.status = new_status
        reclamation.save()

        ReclamationUpdate.objects.create(
            reclamation=reclamation,
            author=request.user,
            message=f'Statut changé à {new_status} via AJAX',
            is_status_change=True,
            new_status=new_status,
        )
        return JsonResponse({
            'success': True,
            'new_status': reclamation.get_status_display()
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)

# ----------------------
# Specialist Views
# ----------------------
from django.views.generic import TemplateView
from .models import Reclamation
from .mixins import SpecialistRequiredMixin

class SpecialistDashboard(SpecialistRequiredMixin, TemplateView):
    template_name = 'specialist/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        
        team_reclamations = Reclamation.objects.filter(
            assigned_team__in=user.teams,
            assigned_specialist__isnull=True
        ).exclude(
            status__in=['RESOLVED', 'CLOSED']
        ).order_by('-created_at')
        
        context.update({
            'team_reclamations': team_reclamations,
            'stats': {
                'total': team_reclamations.count(),
                'open': team_reclamations.filter(status='OPEN').count(),
                'in_progress': team_reclamations.filter(status='IN_PROGRESS').count(),
            }
        })
        return context



    


class SpecialistProfileView(SpecialistRequiredMixin, UpdateView):
    model = User
    form_class = SpecialistProfileForm
    template_name = 'specialist/profile.html'
    success_url = reverse_lazy('specialist_dashboard')

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Statistiques
        context.update({
            'nb_reclamations': Reclamation.objects.filter(assigned_specialist=user).count(),
            'nb_reclamations_encours': Reclamation.objects.filter(
                assigned_specialist=user,
                status='IN_PROGRESS'
            ).count(),
            'nb_reclamations_resolues': Reclamation.objects.filter(
                assigned_specialist=user,
                status='RESOLVED'
            ).count(),
            'user_full_name': user.get_full_name() or user.username  
        })
        return context
    



from django.views.generic import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import User
from .forms import SpecialistProfileForm

class SpecialistProfileUpdateView(SpecialistRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = SpecialistProfileForm
    template_name = 'specialist/profile_edit.html'
    success_message = "Profil mis à jour avec succès"

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return reverse('reclamations:specialist_profile')









from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from .models import Reclamation, ReclamationUpdate
from .mixins import SpecialistRequiredMixin

class TakeChargeView(SpecialistRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        reclamation = get_object_or_404(Reclamation, pk=self.kwargs['pk'])
        user = request.user
        
        
        if not user.is_specialist:
            messages.error(request, "Action réservée aux spécialistes")
            return redirect('reclamations:detail', pk=reclamation.pk)
            
        
        if reclamation.assigned_team not in user.teams:
            messages.error(request, "Cette réclamation n'est pas attribuée à votre équipe")
            return redirect('reclamations:detail', pk=reclamation.pk)
        
        
        if reclamation.status == 'OPEN':
            return self._handle_open_reclamation(request, reclamation, user)
        elif reclamation.status == 'IN_PROGRESS':
            return self._handle_in_progress_reclamation(request, reclamation, user)
        else:
            messages.warning(request, f"Action impossible sur une réclamation au statut {reclamation.get_status_display()}")
            return redirect('reclamations:detail', pk=reclamation.pk)
    
    def _handle_open_reclamation(self, request, reclamation, user):
        """Gère la prise en charge d'une réclamation ouverte"""
        
        estimated_time = timezone.now() + reclamation.get_problem_type_resolution_time()
        
        # mise à jour de la réclamation
        reclamation.status = 'IN_PROGRESS'
        reclamation.assigned_specialist = user
        reclamation.estimated_resolution = estimated_time
        reclamation.save()
        
        
        ReclamationUpdate.objects.create(
            reclamation=reclamation,
            author=user,
            message=f"Prise en charge par {user.get_full_name()} - Résolution estimée: {estimated_time.strftime('%d/%m/%Y')}",
            is_status_change=True,
            new_status='IN_PROGRESS'  
        )
        
        #notif
        self._send_notification_email(reclamation, user, estimated_time)
        
        messages.success(
            request, 
            f"Vous avez pris en charge la réclamation. Résolution estimée: {estimated_time.strftime('%d/%m/%Y')}"
        )
        return redirect('reclamations:detail', pk=reclamation.pk)
    
    def _handle_in_progress_reclamation(self, request, reclamation, user):
        """Gère le cas où la réclamation est déjà en cours"""
        if reclamation.assigned_specialist == user:
            messages.info(request, "Vous avez déjà pris en charge cette réclamation")
        else:
            specialist_name = reclamation.assigned_specialist.get_full_name()
            messages.warning(
                request, 
                f"Cette réclamation est déjà prise en charge par {specialist_name}"
            )
        return redirect('reclamations:detail', pk=reclamation.pk)
    
    def _send_notification_email(self, reclamation, specialist, estimated_time):
        """Envoie un email de notification au client"""
        subject = f"Votre réclamation #{reclamation.id} a été prise en charge"
        message = (
            f"Bonjour {reclamation.user.get_full_name()},\n\n"
            f"Votre réclamation #{reclamation.id} a été prise en charge par notre équipe.\n"
            f"Type de problème: {reclamation.get_problem_type_display()}\n"
            f"Statut: En cours de traitement\n"
            f"Date estimée de résolution: {estimated_time.strftime('%d/%m/%Y')}\n\n"
            f"Merci pour votre confiance,\n"
            f"L'équipe {reclamation.get_assigned_team_display()}"
        )
        
        send_mail(
            subject,
            message,
            'dhouhakth@gmail.com',
            [reclamation.user.email],
            fail_silently=False,
        )


from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from django.urls import reverse

class SplashView(TemplateView):
    template_name = 'registration/splash.html'
    
    def dispatch(self, request, *args, **kwargs):
        # user deja aurh
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse('reclamations:list'))
        return super().dispatch(request, *args, **kwargs)