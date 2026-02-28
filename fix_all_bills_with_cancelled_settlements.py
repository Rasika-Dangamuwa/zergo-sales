"""
Fix all bills affected by the cancelled settlement bug

This script:
1. Finds all bills with cancelled settlements
2. Recalculates their totals correctly
3. Reports the fixes
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill
from payments.models import SalesAccountSettlement
from django.db.models import Count, Q

# Find bills that have at least one cancelled settlement
bills_with_cancelled = Bill.objects.filter(
    settlements__settlement_status='cancelled'
).distinct()

print("=" * 80)
print(f"BILLS WITH CANCELLED SETTLEMENTS: {bills_with_cancelled.count()}")
print("=" * 80)
print()

fixed_count = 0
for bill in bills_with_cancelled:
    # Get current state
    old_paid = bill.paid_amount
    old_balance = bill.balance_amount
    old_status = bill.settlement_status
    
    # Count settlements
    all_settlements = bill.settlements.all()
    completed_settlements = bill.settlements.filter(settlement_status='completed')
    cancelled_settlements = bill.settlements.filter(settlement_status='cancelled')
    
    # Calculate what paid amount should be
    correct_paid = sum(s.amount for s in completed_settlements)
    
    # Only fix if there's a discrepancy
    if old_paid != correct_paid:
        print(f"Bill #{bill.pk}: {bill.bill_number if hasattr(bill, 'bill_number') else bill.sale_number}")
        print(f"  Total: Rs. {bill.total_amount}")
        print(f"  Settlements: {all_settlements.count()} total ({completed_settlements.count()} completed, {cancelled_settlements.count()} cancelled)")
        print(f"  OLD - Paid: Rs. {old_paid}, Balance: Rs. {old_balance}, Status: {old_status}")
        
        # Recalculate using the fixed calculate_totals()
        bill.calculate_totals()
        bill.refresh_from_db()
        
        print(f"  NEW - Paid: Rs. {bill.paid_amount}, Balance: Rs. {bill.balance_amount}, Status: {bill.settlement_status}")
        print(f"  ✓ Fixed: Paid amount corrected by Rs. {bill.paid_amount - old_paid}")
        print()
        fixed_count += 1
    else:
        # Already correct (maybe already called calculate_totals with the fix)
        pass

print("=" * 80)
print(f"SUMMARY: Fixed {fixed_count} bills")
print("=" * 80)

# Verify Bill #90 specifically
print()
print("=" * 80)
print("BILL #90 VERIFICATION")
print("=" * 80)
bill_90 = Bill.objects.get(pk=90)
print(f"Total: Rs. {bill_90.total_amount}")
print(f"Paid: Rs. {bill_90.paid_amount}")
print(f"Balance: Rs. {bill_90.balance_amount}")
print(f"Status: {bill_90.settlement_status}")
print()
print("Settlements:")
for s in bill_90.settlements.all():
    print(f"  {s.settlement_number}: {s.settlement_status}, Rs. {s.amount}")
print()

expected_paid = sum(s.amount for s in bill_90.settlements.filter(settlement_status='completed'))
if bill_90.paid_amount == expected_paid:
    print("✓ Bill #90 is now CORRECT!")
else:
    print(f"✗ Bill #90 still has issue: paid={bill_90.paid_amount}, expected={expected_paid}")
