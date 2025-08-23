from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from reclamations.views import RegisterView, ProfileView
from django.contrib.auth import views as auth_views
from django.views.generic.base import TemplateView
from django.urls import path, include
from reclamations.views import RegisterView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('admin-dashboard/', include('reclamations.admin_dashboard.urls')),


    #authentification views
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(template_name='registration/logged_out.html'), name='logout'),
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change.html'), name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'), name='password_change_done'),
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset.html'), name='password_reset'),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    #register et profile
    path('accounts/register/', RegisterView.as_view(), name='register'),
    path('accounts/profile/', ProfileView.as_view(), name='profile'),
    path('reclamations/', include('reclamations.urls', namespace='reclamations')),
    #page d'accueil publique
    path('', TemplateView.as_view(template_name='reclamations/home.html'), name='home'),

    path("__reload__/", include("django_browser_reload.urls")),


    #reclamations app
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)