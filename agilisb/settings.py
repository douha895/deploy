from pathlib import Path
import os
from django.contrib.messages import constants as messages

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'azertyuiop^$qsdfghjklmù*wxcvbn,;:!123456789'
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'reclamations.apps.ReclamationsConfig',
    'tailwind',   
    'django_browser_reload',
]

AUTH_USER_MODEL = 'reclamations.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'agilisb.middleware.PublicAccessMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware',
    #'reclamations.middleware.RoleRedirectMiddleware',  
]

ROOT_URLCONF = 'agilisb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'reclamations' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'agilisb.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Tunis'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

#authentification config
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = 'reclamations:list'  
LOGOUT_REDIRECT_URL = 'reclamations:login'

# urls exemptées de l'authentification
LOGIN_EXEMPT_URLS = [
    r'^$',
    r'^accounts/register/',
    r'^accounts/login/',
    r'^accounts/password_reset/',
    r'^accounts/reset/',
    r'^static/',
    r'^media/',
]

# email config
ADMIN_EMAIL = 'Makrem.AGREBI@agil.com.tn'


EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'dhouhaaa@gmail.com'
# EMAIL_HOST_PASSWORD = 'root1234'
# DEFAULT_FROM_EMAIL = 'dhouhakth@gmail.com'

#config des messages
MESSAGE_TAGS = {
    messages.ERROR: 'danger',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.INFO: 'info',
}

#config pour les spécialistes
SPECIALIST_REDIRECT_URL = 'specialist_dashboard'
CLIENT_REDIRECT_URL = 'reclamations:list'

