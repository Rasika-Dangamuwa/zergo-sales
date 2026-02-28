"""Test Commission Settings Save/Load"""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionSettings
from decimal import Decimal

print("=== COMMISSION SETTINGS TEST ===\n")

# Get or create settings
settings = CommissionSettings.get_settings()
print(f"1. Initial Settings:")
print(f"   Default Rate: {settings.default_commission_rate}%")
print(f"   Updated At: {settings.updated_at}")
print(f"   Updated By: {settings.updated_by}")

# Test update
print(f"\n2. Testing Update...")
old_rate = settings.default_commission_rate
new_rate = Decimal('7.50')
settings.default_commission_rate = new_rate
settings.save()
print(f"   Changed from {old_rate}% to {new_rate}%")

# Verify persistence
print(f"\n3. Verifying Persistence...")
settings_reloaded = CommissionSettings.get_settings()
print(f"   Reloaded Rate: {settings_reloaded.default_commission_rate}%")

if settings_reloaded.default_commission_rate == new_rate:
    print(f"   ✓ SUCCESS: Rate persisted correctly!")
else:
    print(f"   ✗ FAILED: Rate not saved correctly")

# Reset to original
settings.default_commission_rate = old_rate
settings.save()
print(f"\n4. Reset to original: {old_rate}%")

print("\n=== TEST COMPLETE ===")
print("\nCommission settings are now working!")
print("You can update the rate at: /sales/commissions/settings/")
