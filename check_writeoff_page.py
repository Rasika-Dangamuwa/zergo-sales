"""
Check Bill BILL20260212002 - What the confirmation page should show
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import models
from sales.models import Bill

# Find the bill by number
bill = Bill.objects.filter(bill_number='BILL20260212002').first()

if not bill:
    print("Bill not found - searching for recent bills...")
    recent = Bill.objects.filter(
        shop__shop_name__icontains='Rasika'
    ).order_by('-created_at')[:5]
    print(f"\nFound {recent.count()} recent bills for Rasika:")
    for b in recent:
        print(f"  {b.bill_number}: Rs. {b.total_amount:,.2f} - {b.bill_date}")
    exit()

print("=" * 80)
print(f"WRITE-OFF CONFIRMATION PAGE CHECK")
print(f"Bill: {bill.bill_number}")
print("=" * 80)

# Bill data
print(f"\n📋 BILL DATA:")
print(f"   Total: Rs. {bill.total_amount:,.2f}")
print(f"   Bill Paid Amount: Rs. {bill.paid_amount:,.2f}")
print(f"   Bill Balance: Rs. {bill.balance_amount:,.2f}")

# Calculate what the view calculates
completed_settlements_total = bill.settlements.filter(
    settlement_status='completed'
).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

actual_balance = bill.total_amount - completed_settlements_total

print(f"\n🔢 CALCULATED (what view does):")
print(f"   Completed Settlements: Rs. {completed_settlements_total:,.2f}")
print(f"   Actual Balance: Rs. {actual_balance:,.2f}")

# Check for mismatch
amount_mismatch = bill.paid_amount != completed_settlements_total or bill.balance_amount != actual_balance

print(f"\n✅ PAGE DISPLAY:")
if amount_mismatch:
    print(f"   ⚠️  MISMATCH DETECTED - Page will show:")
    print(f"   Paid to Date: {bill.paid_amount:,.2f} → {completed_settlements_total:,.2f}")
    print(f"   Outstanding Balance: {bill.balance_amount:,.2f} → {actual_balance:,.2f}")
    print(f"   Warning box: YES")
else:
    print(f"   ✅ NO MISMATCH - Page will show:")
    print(f"   Paid to Date: Rs. {bill.paid_amount:,.2f}")
    print(f"   Outstanding Balance: Rs. {bill.balance_amount:,.2f}")
    print(f"   Warning box: NO")

print(f"\n💸 WRITE-OFF EXECUTION:")
print(f"   Write-off amount will be: Rs. {actual_balance:,.2f}")
print(f"   Bill will be marked as fully settled")
if bill.shop:
    print(f"   Shop balance will be reduced by: Rs. {actual_balance:,.2f}")
else:
    print(f"   No shop balance update (unregistered customer)")

# Pending settlements check
pending = bill.settlements.filter(settlement_status__in=['pending', 'pending_verification'])
if pending.exists():
    print(f"\n❌ BLOCKED: {pending.count()} pending settlements")
else:
    print(f"\n✅ OK: No pending settlements")

print("=" * 80)
