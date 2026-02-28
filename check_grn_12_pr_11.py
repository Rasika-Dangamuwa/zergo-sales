import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Purchase, PurchaseReturn

# Check GRN #12
print("=" * 80)
print("CHECKING GRN #12 (Purchase ID 12)")
print("=" * 80)
try:
    grn = Purchase.objects.get(pk=12)
    print(f"\nGRN Number: {grn.grn_number}")
    print(f"GRN Date: {grn.grn_date}")
    print(f"Company: {grn.company.company_name}")
    print(f"Total Amount: Rs. {grn.total_amount:,.2f}")
    print(f"\nItems:")
    for item in grn.items.all():
        print(f"  - {item.product.product_name}")
        print(f"    Quantity: {item.quantity}")
        print(f"    Marked Price: Rs. {item.marked_price:.2f}")
        print(f"    Shop Discount: {item.shop_discount_percentage}%")
        print(f"    Invoice Price (Shop Price): Rs. {item.invoice_price:.2f}")
        print(f"    Company Discount: {item.company_discount_percentage}%")
        print(f"    Unit Price (Final): Rs. {item.unit_price:.2f}")
        print(f"    Line Total: Rs. {item.line_total:.2f}")
        print()
except Purchase.DoesNotExist:
    print("GRN #12 not found")

# Check Purchase Return #11
print("\n" + "=" * 80)
print("CHECKING PURCHASE RETURN #11")
print("=" * 80)
try:
    pr = PurchaseReturn.objects.get(pk=11)
    print(f"\nReturn Number: {pr.pr_number}")
    print(f"Return Date: {pr.return_date}")
    print(f"Company: {pr.company.company_name}")
    print(f"Status: {pr.status}")
    print(f"Total Amount: Rs. {pr.total_amount:,.2f}")
    
    if pr.approved_amount:
        print(f"Approved Amount: Rs. {pr.approved_amount:,.2f}")
    if pr.company_approved_date:
        print(f"Company Approved Date: {pr.company_approved_date}")
    if pr.settlement_type:
        print(f"Settlement Type: {pr.settlement_type}")
    
    print(f"\nItems:")
    for item in pr.items.all():
        print(f"  - {item.product.product_name}")
        print(f"    Quantity: {item.quantity}")
        print(f"    Marked Price: Rs. {item.marked_price:.2f}")
        print(f"    Shop Discount: {item.shop_discount_percentage}%")
        print(f"    Invoice Price (Shop Price): Rs. {item.invoice_price:.2f}")
        print(f"    Company Discount: {item.company_discount_percentage}%")
        print(f"    Unit Price (Final): Rs. {item.unit_price:.2f}")
        print(f"    Line Total: Rs. {item.line_total:.2f}")
        print()
except PurchaseReturn.DoesNotExist:
    print("Purchase Return #11 not found")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
