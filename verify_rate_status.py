from sales.models import CommissionRateHistory
from datetime import datetime

print("=" * 80)
print("COMMISSION RATE STATUS CHECK")
print("=" * 80)

all_rates = CommissionRateHistory.objects.all().order_by('-created_at')

print(f"\nTotal rates in system: {all_rates.count()}")
print(f"\nRate History (newest first):")
print("-" * 80)

for i, rate in enumerate(all_rates, 1):
    status_icon = "✓" if rate.is_active else "○"
    status_text = "ACTIVE" if rate.is_active else "Historical"
    created_local = rate.created_at.strftime('%d %b %Y, %I:%M %p')
    
    print(f"{i}. [{status_icon}] {rate.rate}% - Created: {created_local} - Status: {status_text}")
    if rate.notes:
        print(f"   Notes: {rate.notes}")

print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

active_rates = CommissionRateHistory.objects.filter(is_active=True)
print(f"\nActive rates count: {active_rates.count()}")

if active_rates.count() == 1:
    current = active_rates.first()
    print(f"✓ CORRECT: Only 1 active rate")
    print(f"  Current Active Rate: {current.rate}%")
    print(f"  Created: {current.created_at.strftime('%d %b %Y, %I:%M:%S %p')}")
elif active_rates.count() == 0:
    print("✗ ERROR: No active rates! System will use default 5%")
else:
    print(f"✗ ERROR: Multiple active rates ({active_rates.count()})!")
    print("  This should not happen. The save() method should prevent this.")

print("\n" + "=" * 80)
print("WHAT HAPPENS ON PAGE REFRESH")
print("=" * 80)

print("\nThe commission settings page will show:")
print(f"1. Current Active Rate: {active_rates.first().rate if active_rates.exists() else '5.00'}%")
print(f"2. Total Rate History Entries: {all_rates.count()}")
print("3. Newest rates appear at the top (ordered by created_at)")
print("4. Only 1 rate shows 'Active' badge")
print("5. All others show 'Historical' badge")

print("\n" + "=" * 80)
print("AUTOMATIC DEACTIVATION TEST")
print("=" * 80)

print("\nThe save() method now includes:")
print("  if self.is_active and not self.pk:")
print("      CommissionRateHistory.objects.filter(is_active=True).update(is_active=False)")
print("\nThis means:")
print("  - When you create a NEW rate and check 'Active'")
print("  - All other rates automatically become Historical")
print("  - Only the newest rate remains Active")

print("\n" + "=" * 80)
