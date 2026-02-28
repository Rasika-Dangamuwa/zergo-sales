from accounts.models import User

print('\n=== Existing Users in System ===\n')

users = User.objects.all().order_by('username')

for u in users:
    print(f'Username: {u.username}')
    print(f'  Name: {u.get_full_name() or "Not set"}')
    print(f'  Email: {u.email or "Not set"}')
    print(f'  Staff: {"Yes" if u.is_staff else "No"}')
    print(f'  Superuser: {"Yes" if u.is_superuser else "No"}')
    print(f'  Active: {"Yes" if u.is_active else "No"}')
    print()

print('\n=== Login Credentials ===')
print('You can login with these users at http://127.0.0.1:8000/admin/\n')
