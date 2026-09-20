from .base import *

DEBUG = True

# Cookies — insecure is fine over local http://
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# No SSL redirect/HSTS locally — you're not serving HTTPS
SECURE_SSL_REDIRECT = False
