"""One-time password reset. Delete this file after use."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User

user = User.objects.get(username="admin")
user.set_password("***REMOVED***")
user.save()
print(f"Password reset for {user.username}")
