from django.urls import path, include
from django.views.generic.base import RedirectView, TemplateView
from django.contrib.auth import views as auth_views
from .views import (
    ReclamationListView,
    ReclamationCreateView,
    ReclamationDetailView,
    ReclamationUpdateView,
    ReclamationDeleteView,
    RegisterView,
    ProfileView,
    ProfileUpdateView,  # Nouvelle vue ajoutée
    download_attachment,
    update_reclamation_status,
    SpecialistDashboard, 
    SpecialistProfileView,
    SpecialistProfileUpdateView,
    TakeChargeView,
    SplashView,
)

app_name = 'reclamations'

urlpatterns = [
    path('', SplashView.as_view(), name='splash'),

    #redirection et page d'accueil
    path('', TemplateView.as_view(template_name='reclamations/home.html'), name='home'),
    
    # authentification
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='registration/login.html'
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(
        template_name='registration/logged_out.html',
        next_page='reclamations:login'
    ), name='logout'),

    #gestion des mots de passe
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change.html'
    ), name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset.html'
    ), name='password_reset'),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),

    # Inscription et profil
    path('accounts/register/', RegisterView.as_view(), name='register'),
    path('accounts/profile/', ProfileView.as_view(), name='profile'),
    path('accounts/profile/edit/', ProfileUpdateView.as_view(), name='profile_edit'),  # Nouvelle URL

    #gestion des réclamations
    path('reclamations/', ReclamationListView.as_view(), name='list'),
    path('reclamations/nouvelle/', ReclamationCreateView.as_view(), name='create'),
    path('reclamation/<int:pk>/', ReclamationDetailView.as_view(), name='detail'),
    path('reclamation/<int:pk>/modifier/', ReclamationUpdateView.as_view(), name='update'),
    path('reclamation/<int:pk>/supprimer/', ReclamationDeleteView.as_view(), name='delete'),
    path('reclamation/attachment/<int:pk>/telecharger/', download_attachment, name='download_attachment'),
    path('reclamation/<int:pk>/update-status/', update_reclamation_status, name='update_status'),

    #tableau de bord spécialiste
    path('specialist/dashboard/', SpecialistDashboard.as_view(), name='specialist_dashboard'),
    path('specialist/profile/', SpecialistProfileView.as_view(), name='specialist_profile'),
    path('specialist/profile/edit/', SpecialistProfileUpdateView.as_view(), name='specialist_profile_edit'),  # URL corrigée

    #prise en charge des réclamations
    path('reclamation/<int:pk>/take-charge/', TakeChargeView.as_view(), name='take_charge'),

    path('admin-dashboard/', include('reclamations.admin_dashboard.urls')),
]