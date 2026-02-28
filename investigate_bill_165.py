import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill
from payments.models import SalesAccountSettlement

bill = Bill.objects.get(id=165)
print(f"=== BILL 165 INVESTIGATION ===")
print(f"Bill Number: {bill.bill_number}")
print(f"Total Amount: Rs. {bill.total_amount}")
print(f"Balance Amount: Rs. {bill.balance_amount}")

print(f"\n--- CURRENT STATE ---")
print(f"bill.paid_amount: Rs. {bill.paid_amount}")

print(f"\n--- SETTLEMENTS (via bill.settlements) ---")
for s in bill.settlements.all():
    print(f"  ID: {s.id}, Number: {s.settlement_number}, Amount: Rs. {s.amount}, Status: {s.settlement_status}")

print(f"\n--- MANUAL CALCULATION ---")
completed_settlements = bill.settlements.filter(settlement_status='completed')
manual_paid = sum(s.amount for s in completed_settlements)
print(f"Sum of completed settlements: Rs. {manual_paid}")
print(f"Expected paid_amount: Rs. {manual_paid}")
print(f"Actual paid_amount: Rs. {bill.paid_amount}")
print(f"Difference: Rs. {bill.paid_amount - manual_paid}")

print(f"\n--- RECALCULATING TOTALS ---")
bill.calculate_totals()
print(f"After calculate_totals():")
print(f"  paid_amount: Rs. {bill.paid_amount}")
print(f"  balance_amount: Rs. {bill.balance_amount}")
print(f"  settlement_status: {bill.settlement_status}")

print(f"\n--- CHECKING FOR DUPLICATE SETTLEMENTS ---")
all_settlements_for_shop = SalesAccountSettlement.objects.filter(shop=bill.shop, bill=bill)
print(f"Total settlements linked to this bill: {all_settlements_for_shop.count()}")
for s in all_settlements_for_shop:
    print(f"  ID: {s.id}, Number: {s.settlement_number}, Amount: Rs. {s.amount}, Status: {s.settlement_status}, Created: {s.created_at}")
