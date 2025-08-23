import re
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
import logging

logger = logging.getLogger(__name__)

class PublicAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        try:
            self.exempt_urls = [re.compile(url) for url in settings.LOGIN_EXEMPT_URLS]
        except AttributeError:
            logger.error("LOGIN_EXEMPT_URLS not defined in settings")
            self.exempt_urls = []

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path_info.lstrip('/')
        
        # verif urls exempt
        if self._is_url_exempt(path):
            return None

        #les utilisateurs non auth
        if not request.user.is_authenticated:
            return self._handle_unauthenticated(request, view_func)

        #redirect apres log in
        if self._should_redirect_after_login(request):
            return self._role_based_redirect(request)

        # shkoun andou acces lel admin views
        if path.startswith('admin/'):
            return self._check_admin_access(request)

        return None

    def _is_url_exempt(self, path):
        """Vérifie si l'URL est dans la liste des exemptions"""
        return any(url.match(path) for url in self.exempt_urls)

    def _handle_unauthenticated(self, request, view_func):
        """Gère les utilisateurs non authentifiés"""
        if hasattr(view_func, 'view_class'):
            view_module = view_func.view_class.__module__
            if view_module.startswith('django.contrib.auth.'):
                return None
        
        messages.info(request, "Veuillez vous connecter pour accéder à cette page")
        return redirect(f"{settings.LOGIN_URL}?next={request.path}")

    def _should_redirect_after_login(self, request):
        """Détermine si une redirection post-login est nécessaire"""
        try:
            return (request.path == reverse('login') 
                    and request.user.is_authenticated
                    and not request.GET.get('next'))
        except Exception as e:
            logger.error(f"Error checking login redirect: {str(e)}")
            return False

    def _role_based_redirect(self, request):
        """Redirige en fonction du rôle de l'utilisateur"""
        try:
            if hasattr(request.user, 'is_specialist') and request.user.is_specialist:
                return redirect('specialist_dashboard')
            return redirect('reclamations:list')
        except Exception as e:
            logger.error(f"Role-based redirect failed: {str(e)}")
            return redirect('home')

    def _check_admin_access(self, request):
        """Vérifie l'accès à l'interface admin"""
        if not request.user.is_staff:
            messages.warning(request, "Accès refusé : droits insuffisants")
            return redirect('home')
        return None




from django.conf import settings
from django.shortcuts import redirect

class AuthRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        #redirect apres log in done
        if (request.path == reverse('login') and 
            request.user.is_authenticated and 
            not request.GET.get('next')):
            
            if hasattr(request.user, 'is_specialist') and request.user.is_specialist:
                return redirect('specialist_dashboard')
            return redirect('reclamations:list')
            
        return response