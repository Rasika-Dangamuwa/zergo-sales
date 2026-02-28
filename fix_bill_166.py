import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill

bill = Bill.objects.get(id=166)
print(f"Bill {bill.bill_number} - BEFORE:")
print(f"  Paid Amount: Rs. {bill.paid_amount}")
print(f"  Balance: Rs. {bill.balance_amount}")

# Recalculate
bill.calculate_totals()

print(f"\nBill {bill.bill_number} - AFTER:")
print(f"  Paid Amount: Rs. {bill.paid_amount}")
print(f"  Balance: Rs. {bill.balance_amount}")
print(f"  Status: {bill.settlement_status}")
print(f"\n✓ Bill 166 fixed!")
