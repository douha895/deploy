from django import forms
from django.core.exceptions import ValidationError
from .models import Reclamation, ReclamationUpdate, Card, Station
from django.contrib.auth.forms import UserCreationForm
from .models import Attachment 
from django.db.models import Count
from django.db.models import Q 
from .utils import _determine_file_type
# reclamations/forms.py
import logging
logger = logging.getLogger(__name__)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    widget = MultipleFileInput()

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(d, initial) for d in data]
        return single_clean(data, initial)

class ReclamationForm(forms.ModelForm):
    card_type = forms.ChoiceField(
        label="Type de carte",
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    station_coords = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

    incident_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    incident_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )

    card_number_manual = forms.CharField(
        label="Numéro de carte (saisie manuelle)",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Entrez votre numéro de carte'
        })
    )

    attachments = MultipleFileField(
        required=False,
        help_text="Formats acceptés : images, PDF, Word (max 5 MB par fichier).",
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,.pdf,.doc,.docx'
        }),
    )

    priority = forms.ChoiceField(
        choices=Reclamation.PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Priorité",
        required=True
    )

    class Meta:
        model = Reclamation
        fields = [
            'card_type',
            'card_number_manual',
            'station',
            'station_coords',
            'problem_type',
            'incident_date',
            'incident_time',
            'description',
            'priority',
            'attachments',
            'requires_callback',
            'contact_method'
        ]
        widgets = {
            'station': forms.Select(attrs={'class': 'form-select'}),
            'problem_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'minlength': 30
            }),
            'requires_callback': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'contact_method': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        

        self.fields['card_type'].choices = [('', '---------')] + list(Card.CARD_TYPES)
        
        
        if self.user and self.user.role == 'AGENT':
            self.fields['station'].queryset = Station.objects.filter(
                id=self.user.assigned_station.id) if self.user.assigned_station else Station.objects.none()
        
        # ajout du champ de sélection de carte pour les clients
        if self.user and self.user.role == 'CLIENT':
            self.fields['card'] = forms.ModelChoiceField(
                queryset=Card.objects.filter(user=self.user, is_active=True),
                label="Sélectionner une carte",
                required=False,
                widget=forms.Select(attrs={'class': 'form-select'})
            )
            self.fields['card_number_manual'].required = False

    def clean_description(self):
        desc = self.cleaned_data.get('description', '')
        if len(desc) < 30:
            raise ValidationError("La description doit contenir au moins 30 caractères.")
        return desc

    def clean_attachments(self):
        files = self.files.getlist('attachments')
        for f in files:
            if f.size > 5 * 1024 * 1024:
                raise ValidationError(f"Le fichier {f.name} dépasse 5 MB.")
        return files

    def clean(self):
        cleaned = super().clean()
        card_type = cleaned.get('card_type')
        manual = cleaned.get('card_number_manual', '').strip()

        if not card_type and not manual and not cleaned.get('card'):
            raise ValidationError(
                "Vous devez choisir un type de carte, sélectionner une carte ou saisir son numéro manuellement."
            )

        return cleaned

    def save(self, commit=True):
        """
        Saves the form instance with the current user and handles attachments.
        Ensures user is always set before saving to avoid NOT NULL constraint violation.
        """
    
        instance = super().save(commit=False)
        
        
        if not hasattr(instance, 'user') or not instance.user:
            instance.user = self.user
        
        if not commit:
            return instance
        
        try:
            
            instance.save()
            
            #attachments
            for uploaded_file in self.cleaned_data.get('attachments', []):
                Attachment.objects.create(
                    reclamation=instance,
                    file=uploaded_file,
                    description=uploaded_file.name[:200],  
                    file_type=_determine_file_type(uploaded_file.name)
                )
            
            #affectat auto
            if hasattr(self, 'assign_reclamation'):
                self.assign_reclamation(instance)
                
        except Exception as e:
            logger.error(f"Error saving reclamation: {str(e)}")
            raise  # Re-raise the exception after logging

        return instance

    def assign_reclamation(self, reclamation):
        from .utils import assign_reclamation
        assign_reclamation(reclamation)

class ReclamationUpdateForm(forms.ModelForm):
    new_status = forms.ChoiceField(
        choices=Reclamation.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Changer le statut"
    )

    class Meta:
        model = ReclamationUpdate
        fields = ['new_status', 'message', 'is_internal_note']
        widgets = {
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_internal_note': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_status'].choices = Reclamation.STATUS_CHOICES


from django.contrib.auth import get_user_model
User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'phone', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].widget.attrs.update({'class': 'form-select'})




from django import forms
from django.core.exceptions import ValidationError
import json
from .models import User

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'phone': forms.TextInput(attrs={'placeholder': 'Format: +212612345678'}),
        }

class SpecialistProfileForm(UserProfileForm):
    teams = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

    class Meta(UserProfileForm.Meta):
        fields = UserProfileForm.Meta.fields + ['teams']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.teams:
            self.initial['teams'] = json.dumps(self.instance.teams)
    
    def clean_teams(self):
        teams = self.cleaned_data.get('teams')
        if teams:
            try:
                return json.loads(teams)
            except json.JSONDecodeError:
                raise ValidationError("Format d'équipes invalide")
        return []




class ReassignmentForm(forms.Form):
    specialist = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Nouveau spécialiste"
    )
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': "Raison de la réaffectation..."
        }),
        label="Message (optionnel)"
    )

    def __init__(self, *args, **kwargs):
        team = kwargs.pop('team')
        current_specialist = kwargs.pop('current_specialist', None)
        super().__init__(*args, **kwargs)
        
        queryset = User.objects.filter(
            teams__contains=[team],
            is_active=True
        ).annotate(
            num_active_reclamations=Count(
                'assigned_reclamations',
                filter=Q(assigned_reclamations__status__in=['OPEN', 'IN_PROGRESS'])
            )
        ).exclude(
            pk=current_specialist.pk if current_specialist else None
        ).order_by('num_active_reclamations', 'first_name')
        
        self.fields['specialist'].queryset = queryset

from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

class AdminAuthenticationForm(AuthenticationForm):
    """
    Formulaire d'authentification personnalisé pour les administrateurs
    Vérifie que l'utilisateur a un profil admin associé
    """
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not hasattr(user, 'admin_profile'):
            raise ValidationError(
                "Accès réservé aux administrateurs d'approbation. "
                "Veuillez vous connecter via le portail standard."
            )