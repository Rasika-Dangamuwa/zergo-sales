"""
Fix Bill.calculate_totals() to exclude cancelled settlements

ROOT CAUSE ANALYSIS:
=====================
Bill #90 shows:
- Total: Rs. 900.00
- Paid: Rs. 0.00 (WRONG - should be Rs. 180.00)
- Balance: Rs. 900.00 (WRONG - should be Rs. 720.00)

Has 4 settlements:
- SET-20260125-035: completed, Rs. 90 ✓
- SET-20260125-036: cancelled, Rs. 90 ✗ (should not count)
- SET-20260125-037: cancelled, Rs. 90 ✗ (should not count)
- SET-20260125-038: completed, Rs. 90 ✓

Problem in sales/models.py line 104:
    self.paid_amount = sum(payment.amount for payment in self.payments.all())
    
This counts ALL settlements including cancelled ones!

FIX:
====
Change to:
    self.paid_amount = sum(
        payment.amount 
        for payment in self.payments.filter(settlement_status='completed')
    )

This matches the pattern already used in payments/views.py line 345:
    other_settlements = settlement.bill.settlements.exclude(pk=settlement.pk).exclude(settlement_status='cancelled')
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill

# Test with Bill #90
bill = Bill.objects.get(pk=90)

print("=" * 80)
print("BEFORE FIX - Bill #90 Status")
print("=" * 80)
print(f"Total Amount: Rs. {bill.total_amount}")
print(f"Paid Amount: Rs. {bill.paid_amount}")
print(f"Balance Amount: Rs. {bill.balance_amount}")
print(f"Settlement Status: {bill.settlement_status}")
print()

# Show all settlements
print("All Settlements:")
for s in bill.settlements.all():
    print(f"  {s.settlement_number}: {s.settlement_status}, Rs. {s.amount}")
print()

# Show only completed settlements (what should be counted)
completed = bill.settlements.filter(settlement_status='completed')
correct_paid = sum(s.amount for s in completed)
print(f"Completed settlements only: Rs. {correct_paid}")
print(f"Expected balance: Rs. {bill.total_amount - correct_paid}")
print()

print("=" * 80)
print("The fix will update Bill.calculate_totals() to exclude cancelled settlements")
print("=" * 80)
