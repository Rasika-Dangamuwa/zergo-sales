from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'List all users in the system'

    def handle(self, *args, **options):
        users = User.objects.all().order_by('username')
        
        self.stdout.write('\n=== Existing Users in System ===\n')
        
        for user in users:
            self.stdout.write(f'Username: {user.username}')
            self.stdout.write(f'  Full Name: {user.get_full_name() or "Not set"}')
            self.stdout.write(f'  Email: {user.email or "Not set"}')
            self.stdout.write(f'  Staff: {"Yes" if user.is_staff else "No"}')
            self.stdout.write(f'  Superuser: {"Yes" if user.is_superuser else "No"}')
            self.stdout.write(f'  Active: {"Yes" if user.is_active else "No"}')
            self.stdout.write('')
        
        self.stdout.write(f'Total users: {users.count()}')
