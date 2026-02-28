import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill

bill = Bill.objects.get(id=161)
print(f"Bill Number: {bill.bill_number}")
print(f"Bill Date: {bill.bill_date}")
print(f"Shop: {bill.shop.shop_name}")
print(f"Sales Rep: {bill.sales_rep.get_full_name()}")
print(f"Bill Status: {bill.bill_status}")
print(f"\n--- Amounts ---")
print(f"Subtotal: Rs. {bill.subtotal}")
print(f"Discount: Rs. {bill.discount_amount} ({bill.discount_percentage}%)")
print(f"Tax: Rs. {bill.tax_amount}")
print(f"Total Amount: Rs. {bill.total_amount}")
print(f"Paid Amount: Rs. {bill.paid_amount}")
print(f"Balance Amount: Rs. {bill.balance_amount}")
print(f"Settlement Status: {bill.settlement_status}")

print(f"\n--- Bill Items ---")
print(f"Total Items: {bill.items.count()}")
for item in bill.items.all():
    print(f"  - {item.product.product_name}: Qty {item.quantity} @ Rs. {item.unit_price} = Rs. {item.line_total}")

print(f"\n--- Settlements ---")
print(f"Total Settlements: {bill.settlements.count()}")
for s in bill.settlements.all():
    print(f"  - {s.settlement_number}: {s.settlement_method} - Rs. {s.amount} - Status: {s.settlement_status}")
    if s.return_ref:
        print(f"    → Linked Return: {s.return_ref.return_number}")
    if s.reference_number:
        print(f"    → Reference: {s.reference_number}")

