from .base import *

# Cookies — insecure is fine over local http://
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# No SSL redirect/HSTS locally — you're not serving HTTPS
<<<<<<< HEAD
SECURE_SSL_REDIRECT = False

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
=======
SECURE_SSL_REDIRECT = False
>>>>>>> 6fe02047874f2a41b2024f6c526d69b183b30d75
