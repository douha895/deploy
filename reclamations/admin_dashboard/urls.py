# reclamations/admin_dashboard/urls.py
from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('login/', views.AdminLoginView.as_view(), name='login'),
    path('', RedirectView.as_view(pattern_name='admin_dashboard:dashboard', permanent=False), name='index'),
    
    # CHOISIR UNE SEULE OPTION POUR LE DASHBOARD :
    
    # Option 1 : Utiliser la vue de classe (recommandé)
    path('dashboard/', views.AdminDashboardView.as_view(), name='dashboard'),
    
    # Option 2 : Utiliser la vue fonction
    # path('dashboard/', views.dashboard, name='dashboard'),
    
    path('process/<int:pk>/', views.ProcessRequestView.as_view(), name='process_request'),
]