"""Update print profile to use proper 80mm thermal paper"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.print_manager import PrintManager
from django.contrib.auth import get_user_model

User = get_user_model()

# Get admin user
user = User.objects.filter(username='admin').first()
if not user:
    user = User.objects.first()

print(f"Updating print profile for: {user.username}")

# Get print profile
profile = PrintManager.get_user_default(user, 'bill')

print(f"Current paper size: {profile.paper_size}")
print(f"Changing to: thermal_80mm (industry standard)")

# Update to 80mm thermal (3 inch - industry standard)
profile.paper_size = 'thermal_80mm'
profile.save()

print(f"✅ Updated to: {profile.paper_size}")
print()
print("Paper Size: 80mm (3 inch) - Industry Standard")
print("  - Used by Square, Clover, Toast POS systems")
print("  - Printable width: 72mm")
print("  - 42 characters per line")
print("  - Perfect for retail receipts")
