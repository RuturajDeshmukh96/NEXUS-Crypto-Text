import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@ciphervault.io', 'admin123')
    print("Superuser created: admin / admin123")
else:
    print("Superuser already exists")
