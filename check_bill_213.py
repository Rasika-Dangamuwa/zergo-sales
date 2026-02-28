"""
Check Bill #213 - Why does it have no shop?
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill

bill = Bill.objects.get(pk=213)

print("=" * 80)
print(f"BILL #213 ANALYSIS")
print("=" * 80)
print(f"\nBill Number: {bill.bill_number}")
print(f"Bill Date: {bill.bill_date}")
print(f"Status: {bill.bill_status}")
print(f"Settlement Status: {bill.settlement_status}")
print(f"\nShop: {bill.shop}")
print(f"Shop ID: {bill.shop_id}")
print(f"\nTotal: Rs. {bill.total_amount:,.2f}")
print(f"Paid: Rs. {bill.paid_amount:,.2f}")
print(f"Balance: Rs. {bill.balance_amount:,.2f}")

if hasattr(bill, 'sales_rep'):
    print(f"\nSales Rep: {bill.sales_rep.get_full_name() if bill.sales_rep else 'None'}")

# Check if there are any items
items = bill.items.all()  # related_name='items'
print(f"\nBill Items: {items.count()}")
for item in items:
    print(f"  - {item.product.product_name}: {item.quantity} units @ Rs. {item.unit_price}")

print("\n" + "=" * 80)
print("STATUS:")
if not bill.shop and bill.customer_name:
    print("✅ This is an UNREGISTERED CUSTOMER bill")
    print(f"   Customer Name: {bill.customer_name}")
    print(f"   Write-off: Now supported! Shop balance won't be updated.")
elif not bill.shop:
    print("❌ This bill has no shop and no customer name assigned.")
    print("   Options:")
    print("   1. Add customer name for unregistered customer")
    print("   2. Assign a shop if it's a registered customer")
    print("   3. Delete this bill if it's invalid data")
else:
    print("✅ Bill has shop assigned, normal write-off applies")
print("=" * 80)
