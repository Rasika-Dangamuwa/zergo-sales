"""
Fix the 3 bills with incorrect paid amounts
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill

print("=" * 80)
print("FIXING BILL PAID AMOUNT MISMATCHES")
print("=" * 80)
print()

# The bills with mismatches
bill_ids = [73, 69, 38]

for bill_id in bill_ids:
    try:
        bill = Bill.objects.get(pk=bill_id)
        
        print(f"Bill #{bill_id}: {bill.bill_number}")
        print(f"  Total: Rs. {bill.total_amount}")
        print(f"  OLD Paid: Rs. {bill.paid_amount}")
        print(f"  OLD Balance: Rs. {bill.balance_amount}")
        print(f"  OLD Status: {bill.settlement_status}")
        
        # Recalculate using the fixed calculate_totals() method
        bill.calculate_totals()
        bill.refresh_from_db()
        
        print(f"  NEW Paid: Rs. {bill.paid_amount}")
        print(f"  NEW Balance: Rs. {bill.balance_amount}")
        print(f"  NEW Status: {bill.settlement_status}")
        print(f"  ✓ Fixed!")
        print()
        
    except Bill.DoesNotExist:
        print(f"❌ Bill #{bill_id} not found")
        print()

print("=" * 80)
print("All bill amounts have been recalculated")
print("=" * 80)
