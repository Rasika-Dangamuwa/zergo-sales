"""Verify auto-approval implementation for returns."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return
from django.db.models import F

print("=" * 70)
print("RETURN AUTO-APPROVAL VERIFICATION")
print("=" * 70)

# Check all returns status distribution
print("\n1. Overall Return Status Distribution:")
print("-" * 70)
status_counts = {}
for status, label in Return.RETURN_STATUS_CHOICES:
    count = Return.objects.filter(return_status=status).count()
    status_counts[status] = count
    print(f"   {label:20s}: {count:4d}")

print(f"\n   Total Returns: {Return.objects.count()}")

# Check settlement method distribution for approved returns
print("\n2. Settlement Methods (Approved Returns Only):")
print("-" * 70)
for method, label in Return.SETTLEMENT_METHOD_CHOICES:
    count = Return.objects.filter(return_status='approved', settlement_method=method).count()
    print(f"   {label:20s}: {count:4d}")

# Check available returns (can be used in payment adjustments)
print("\n3. Available Returns for Payment Adjustments:")
print("-" * 70)
available_returns = Return.objects.filter(
    return_status='approved',
    settlement_method__in=['credit_note', 'next_bill']
).exclude(
    settlement_status='fully_applied'
).annotate(
    available_amount=F('total_amount') - F('applied_amount')
).filter(
    available_amount__gt=0
)
print(f"   Total Available: {available_returns.count()}")
print(f"   Total Value: Rs. {sum(r.total_amount - r.applied_amount for r in available_returns):,.2f}")

# Show shop 66 specifically
print("\n4. Shop 66 Returns (Test Case):")
print("-" * 70)
shop_66_all = Return.objects.filter(shop_id=66)
print(f"   Total returns: {shop_66_all.count()}")

shop_66_approved = shop_66_all.filter(return_status='approved')
print(f"   Approved: {shop_66_approved.count()}")

shop_66_available = shop_66_all.filter(
    return_status='approved',
    settlement_method__in=['credit_note', 'next_bill']
).exclude(
    settlement_status='fully_applied'
).annotate(
    available_amount=F('total_amount') - F('applied_amount')
).filter(
    available_amount__gt=0
)
print(f"   Available for adjustments: {shop_66_available.count()}")

if shop_66_available.exists():
    print("\n   Details:")
    for r in shop_66_available[:5]:
        available = r.total_amount - r.applied_amount
        print(f"     • {r.return_number}: Rs.{available:,.2f} ({r.get_settlement_method_display()})")

# Check recent returns (last 10)
print("\n5. Recent Returns (Last 10 Created):")
print("-" * 70)
recent = Return.objects.order_by('-return_date')[:10]
for r in recent:
    print(f"   {r.return_number:15s} | Status: {r.get_return_status_display():20s} | "
          f"Method: {r.get_settlement_method_display():20s} | "
          f"Settlement: {r.get_settlement_status_display():20s}")

print("\n" + "=" * 70)
print("✅ VERIFICATION COMPLETE")
print("=" * 70)
