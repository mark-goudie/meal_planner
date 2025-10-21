from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os

class Command(BaseCommand):
    help = 'Create a superuser'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        
        if not User.objects.filter(username=username).exists():
            if password:
                User.objects.create_superuser(username, email, password)
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created superuser: {username}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('DJANGO_SUPERUSER_PASSWORD not set, skipping superuser creation')
                )
        else:
            self.stdout.write(
                self.style.WARNING(f'Superuser {username} already exists')
            )