from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class User(AbstractUser):
    ROLE_CHOICES = [
        ('CLIENT', 'Client'),
        ('AGENT', 'Agent de station'),
        ('TECH', 'Technicien'),
        ('FINANCE', 'Agent Financier'),
        ('SUPPORT', 'Support Client'),
        ('ADMIN', 'Administrateur'),
    ]
    
    # Modification du champ username pour autoriser les espaces
    username = models.CharField(
        max_length=150,
        unique=True,
        blank=False,
        validators=[],  # Suppression des validateurs par défaut
        error_messages={
            'unique': "Ce nom d'utilisateur est déjà utilisé.",
        }
    )
    
    role = models.CharField(
        max_length=10, 
        choices=ROLE_CHOICES, 
        default='CLIENT',
        verbose_name="Rôle utilisateur"
    )
    
    phone = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="Téléphone"
    )
    
    teams = models.JSONField(
        default=list,
        verbose_name="Équipes assignées",
        help_text="Liste des équipes auxquelles appartient l'utilisateur"
    )
    
    assigned_station = models.ForeignKey(
        'Station',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Station assignée"
    )

    # Mapping constant des rôles vers les équipes
    ROLE_TO_TEAMS = {
        'TECH': ['TECH'],
        'FINANCE': ['FINANCE'],
        'SUPPORT': ['SUPPORT'],
        'AGENT': ['STATION'],  # Les agents vont dans l'équipe STATION
        'ADMIN': [],  # Pas d'équipe pour les admins
        'CLIENT': []  # Pas d'équipe pour les clients
    }

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['last_name', 'first_name']

    @property
    def is_specialist(self) -> bool:
        """Détermine si l'utilisateur est un spécialiste"""
        return self.role in {'TECH', 'FINANCE', 'SUPPORT', 'AGENT'}

    @property
    def is_agent(self) -> bool:
        """Vérifie si l'utilisateur est un agent de station"""
        return self.role == 'AGENT'

    def save(self, *args, **kwargs):
        """
        Surcharge de la méthode save pour :
        - Assigner automatiquement les équipes
        - Gérer le cas particulier des agents
        """
        is_new = not self.pk  
        
        # assignation automatique des équipes pour les nouveaux utilisateurs
        if is_new and self.is_specialist:
            self._assign_teams_by_role()
        
        super().save(*args, **kwargs)
        
        if is_new and not self.is_superuser and self.role == 'ADMIN':
            AdminProfile.objects.create(user=self)

        if self.is_agent and is_new:
            self._handle_agent_assignment()

    def _assign_teams_by_role(self):
        """Assignation des équipes selon le rôle"""
        try:
            self.teams = self.ROLE_TO_TEAMS.get(self.role, [])
            logger.info(f"Assignation initiale des équipes pour {self.email}: {self.teams}")
        except Exception as e:
            logger.error(f"Erreur d'assignation des équipes pour {self.email}: {str(e)}")

    def _handle_agent_assignment(self):
        """Gestion spéciale des agents et de leur station"""
        try:
            if self.assigned_station and 'STATION' not in self.teams:
                self.teams.append('STATION')
                self.save()
                logger.info(f"Agent {self.email} assigné à la station {self.assigned_station}")
        except Exception as e:
            logger.error(f"Erreur d'assignation de l'agent {self.email}: {str(e)}")

    def get_team_display(self) -> str:
        """Retourne le nom d'affichage de l'équipe principale"""
        team_map = {
            'TECH': 'Équipe Technique',
            'FINANCE': 'Équipe Financière',
            'SUPPORT': 'Support Client',
            'STATION': 'Agent de Station'
        }
        primary_team = self.teams[0] if self.teams else None
        return team_map.get(primary_team, 'Aucune équipe')

    def __str__(self) -> str:
        """Représentation textuelle de l'utilisateur"""
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    @property
    def can_create_reclamation(self):
        """Détermine si l'utilisateur peut créer des réclamations"""
        return self.role in ['CLIENT', 'ADMIN']  # Rôles autorisés


class Card(models.Model):
    CARD_TYPES = [
        ('GOLD_VAL', 'Gold Valeur (Multi-produits)'),
        ('GOLD_VOL', 'Gold Volume (Mono-produit)'),
        ('CASH_PRE', 'Cash Prépayée'),
        ('CASH_POST', 'Cash Postpayée'),
    ]
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cards'
    )
    card_number = models.CharField(max_length=20, unique=True)
    card_type = models.CharField(max_length=10, choices=CARD_TYPES)
    is_active = models.BooleanField(default=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credit_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    issue_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    pin_code = models.CharField(max_length=4, blank=True)

    def __str__(self):
        return f"{self.get_card_type_display()} - {self.card_number}"

class Station(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    opening_hours = models.CharField(max_length=100, default="24/7")
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='managed_stations'
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class Reclamation(models.Model):
    PROBLEM_TYPES = [
        ('CARD_REJECTED', 'Carte rejetée lors du paiement'),
        ('CARD_BLOCKED', 'Carte bloquée/inactive'),
        ('BALANCE_ERROR', 'Solde incorrect'),
        ('RECHARGE_ISSUE', 'Recharge non reçue'),
        ('LIMIT_ISSUE', 'Problème de plafond'),
        ('LOST_STOLEN', 'Carte volée/perdue'),
        ('PAYMENT_REFUSED', 'Paiement refusé après utilisation'),
        ('DOUBLE_CHARGE', 'Double facturation'),
        ('DAMAGED_CARD', 'Carte endommagée'),
        ('DELIVERY_DELAY', 'Livraison en retard'),
        ('STATION_ISSUE', 'Problème technique en station'),
        ('FRAUD', 'Fraude suspectée'),
        ('OTHER', 'Autre problème'),
    ]

    STATUS_CHOICES = [
        ('OPEN', 'Ouverte'),
        ('IN_PROGRESS', 'En cours'),
        ('RESOLVED', 'Résolue'),
        ('REJECTED', 'Rejetée'),
    ]

    PRIORITY_CHOICES = [
        ('LOW', 'Basse'),
        ('MEDIUM', 'Moyenne'),
        ('HIGH', 'Haute'),
    ]

    TEAM_CHOICES = [
        ('TECH', 'Équipe Technique'),
        ('FINANCE', 'Équipe Financière'),
        ('SUPPORT', 'Support Client'),
        ('STATION', 'Agent de Station'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Utilisateur",
        related_name='reclamations'
    )

    card_type = models.CharField(
        "Type de carte",
        max_length=10,
        choices=Card.CARD_TYPES,
        blank=True,
        null=True,
    )
    card_number_manual = models.CharField(
        "Numéro de carte saisie",
        max_length=20,
        blank=True
    )

    problem_type = models.CharField(max_length=20, choices=PROBLEM_TYPES)

    station = models.ForeignKey(
        Station,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    station_coords = models.CharField(
        "Coordonnées de la station (lat,lng)",
        max_length=50,
        blank=True,
        null=True
    )

    description = models.TextField()
    incident_date = models.DateField()
    incident_time = models.TimeField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN', verbose_name="Statut")
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='MEDIUM'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    estimated_resolution = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date estimée de résolution"
    )

    assigned_agent = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='agent_reclamations'
    )
    
    assigned_team = models.CharField(
        max_length=20,
        choices=TEAM_CHOICES,
        blank=True,
        null=True
    )
    
    assigned_specialist = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='specialist_reclamations'
    )

    requires_callback = models.BooleanField(default=False)
    contact_method = models.CharField(
        max_length=10,
        choices=[('EMAIL', 'Email'), ('PHONE', 'Téléphone')],
        default='EMAIL'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Réclamation'
        verbose_name_plural = 'Réclamations'

    def get_problem_type_resolution_time(self):
        """Retourne la durée estimée selon le type de problème"""
        resolution_times = {
            'CARD_REJECTED': timedelta(days=2),
            'CARD_BLOCKED': timedelta(days=2),
            'BALANCE_ERROR': timedelta(days=1),
            'RECHARGE_ISSUE': timedelta(days=1),
            'LIMIT_ISSUE': timedelta(days=2),
            'LOST_STOLEN': timedelta(days=3),
            'PAYMENT_REFUSED': timedelta(days=1),
            'DOUBLE_CHARGE': timedelta(days=4),
            'DAMAGED_CARD': timedelta(days=2),
            'DELIVERY_DELAY': timedelta(days=3),
            'STATION_ISSUE': timedelta(days=2),
            'FRAUD': timedelta(days=5),
            'OTHER': timedelta(days=2),
        }
        return resolution_times.get(self.problem_type, timedelta(days=2))

    def calculate_estimated_resolution(self):
        """Calcule automatiquement la date de résolution estimée"""
        if self.status == 'OPEN' and not self.estimated_resolution:
            self.estimated_resolution = timezone.now() + self.get_problem_type_resolution_time()
            return True
        return False

    @property
    def resolution_progress(self):
        """Retourne le pourcentage de progression vers la résolution"""
        if not self.estimated_resolution:
            return 0
            
        total_duration = self.get_problem_type_resolution_time()
        elapsed = timezone.now() - (self.estimated_resolution - total_duration)
        return min(100, max(0, int((elapsed.total_seconds() / total_duration.total_seconds()) * 100)))

    @property
    def is_overdue(self):
        """Vérifie si la résolution est en retard"""
        return (self.estimated_resolution and 
                self.status != 'RESOLVED' and 
                timezone.now() > self.estimated_resolution)

    def save(self, *args, **kwargs):
        """Surcharge de la méthode save pour calculer automatiquement le temps estimé"""
        self.calculate_estimated_resolution()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Réclamation #{self.id} - {self.get_status_display()}"

class ReclamationUpdate(models.Model):
    reclamation = models.ForeignKey(
        Reclamation,
        on_delete=models.CASCADE,
        related_name='updates'
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_status_change = models.BooleanField(default=False)
    new_status = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_internal_note = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Update #{self.id} pour Réclamation {self.reclamation.id}"

class Attachment(models.Model):
    reclamation = models.ForeignKey(
        Reclamation,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='reclamations/attachments/%Y/%m/%d/')
    description = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_type = models.CharField(
        max_length=20,
        choices=[('IMAGE', 'Image'), ('PDF', 'PDF'), ('OTHER', 'Autre')],
        default='IMAGE'
    )

    def __str__(self):
        return f"Pièce jointe #{self.id}"

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('FUEL', 'Carburant'),
        ('SHOP', 'Boutique'),
        ('RECHARGE', 'Recharge'),
    ]
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    station = models.ForeignKey(
        Station,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    date = models.DateTimeField()
    fuel_type = models.CharField(max_length=20, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_successful = models.BooleanField(default=True)
    reference = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['card', 'date']),
        ]

    def __str__(self):
        return f"Transaction #{self.reference}"
    


from django.db import models
from django.conf import settings
from django.utils import timezone

class AdminProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_profile'
    )
    is_approval_admin = models.BooleanField(
        default=True,
        verbose_name="Administrateur d'approbation",
        help_text="Peut approuver les demandes d'inscription"
    )
    
    class Meta:
        verbose_name = "Profil Administrateur"
        verbose_name_plural = "Profils Administrateurs"
    
    def __str__(self):
        return f"Profil Admin - {self.user.username}"
    


from .constants import ROLE_CHOICES
class InscriptionRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('APPROVED', 'Approuvée'),
        ('REJECTED', 'Rejetée'),
    ]
    
    # Informations de base
    username = models.CharField(
        max_length=150,
        # RETIRER unique=True
        verbose_name="Nom d'utilisateur"
    )
    email = models.EmailField(verbose_name="Adresse email")
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        verbose_name="Rôle demandé"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Téléphone"
    )
    
    # Gestion du statut
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="Statut"
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='processed_requests',
        verbose_name="Traité par"
    )
    
    # Dates importantes
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de traitement"
    )
    
    # Métadonnées
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Adresse IP"
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent"
    )
    
    class Meta:
        verbose_name = "Demande d'inscription"
        verbose_name_plural = "Demandes d'inscription"
        ordering = ['-created_at']
        permissions = [
            ("can_approve_requests", "Peut approuver les demandes"),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()}) - {self.get_status_display()}"
    
    def approve(self, admin_user):
        """Approuve la demande et crée l'utilisateur"""
        from django.contrib.auth.hashers import make_password
        import secrets
        
        password = secrets.token_urlsafe(12)
        user = settings.AUTH_USER_MODEL.objects.create_user(
            username=self.username,
            email=self.email,
            password=password,
            role=self.role,
            phone=self.phone,
            is_active=True
        )
        
        self.status = 'APPROVED'
        self.processed_by = admin_user
        self.processed_at = timezone.now()
        self.save()
        
        return user, password
    
    def reject(self, admin_user):
        """Rejette la demande"""
        self.status = 'REJECTED'
        self.processed_by = admin_user
        self.processed_at = timezone.now()
        self.save()