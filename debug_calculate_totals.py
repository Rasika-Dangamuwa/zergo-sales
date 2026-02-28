"""
Debug calculate_totals() execution
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill

bill = Bill.objects.get(pk=90)

print("Testing Bill.calculate_totals():")
print("=" * 80)

# Check settlements before
print("Settlements BEFORE:")
all_sett = bill.settlements.all()
completed_sett = bill.settlements.filter(settlement_status='completed')
print(f"  Total: {all_sett.count()}")
print(f"  Completed: {completed_sett.count()}")
print(f"  Sum of completed: Rs. {sum(s.amount for s in completed_sett)}")

print()
print("Bill state BEFORE calculate_totals():")
print(f"  Paid: Rs. {bill.paid_amount}")
print(f"  Balance: Rs. {bill.balance_amount}")
print(f"  Status: {bill.settlement_status}")

print()
print("Calling bill.calculate_totals()...")
bill.calculate_totals()

print()
print("Bill state AFTER calculate_totals() (from memory):")
print(f"  Paid: Rs. {bill.paid_amount}")
print(f"  Balance: Rs. {bill.balance_amount}")
print(f"  Status: {bill.settlement_status}")

print()
print("Refreshing from database...")
bill.refresh_from_db()

print()
print("Bill state AFTER refresh_from_db():")
print(f"  Paid: Rs. {bill.paid_amount}")
print(f"  Balance: Rs. {bill.balance_amount}")
print(f"  Status: {bill.settlement_status}")

print()
print("=" * 80)

# Manual test of the calculation
print("MANUAL TEST OF CALCULATION:")
items = bill.items.all()
subtotal = sum(item.line_total for item in items)
discount = (subtotal * bill.discount_percentage) / 100
tax = sum(item.tax_amount for item in items)
total = subtotal - discount + tax

completed = bill.settlements.filter(settlement_status='completed')
paid = sum(s.amount for s in completed)
balance = total - paid

print(f"  Subtotal: Rs. {subtotal}")
print(f"  Discount: Rs. {discount}")
print(f"  Tax: Rs. {tax}")
print(f"  Total: Rs. {total}")
print(f"  Paid (completed settlements): Rs. {paid}")
print(f"  Balance: Rs. {balance}")
