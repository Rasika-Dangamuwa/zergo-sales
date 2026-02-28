import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill, BillItem
from products.models import Product

bill = Bill.objects.get(id=171)
print(f"=== BILL {bill.bill_number} ===")
print(f"Shop: {bill.shop.shop_name}")
print(f"Total: Rs. {bill.total_amount}")

print(f"\n=== BILL ITEMS ===")
for item in bill.items.all():
    product = item.product
    print(f"\nProduct: {product.product_name}")
    print(f"  Sales Quantity: {item.quantity}")
    print(f"  FOC Quantity: {item.foc_quantity}")
    print(f"  Unit Price: Rs. {item.unit_price}")
    print(f"  Shop Price (Product): Rs. {product.shop_price}")
    print(f"  Sales Qty Per FOC (Product): {product.sales_qty_per_foc}")
    
    # Calculate standard FOC
    if product.sales_qty_per_foc and product.sales_qty_per_foc > 0:
        standard_foc_qty = item.quantity / product.sales_qty_per_foc
        print(f"  Standard FOC Qty: {standard_foc_qty}")
        standard_foc_value = standard_foc_qty * product.shop_price
        print(f"  Standard FOC Value: Rs. {standard_foc_value}")
    else:
        print(f"  Standard FOC: N/A (no sales_qty_per_foc)")
    
    # Actual FOC value
    actual_foc_value = item.foc_quantity * product.shop_price
    print(f"  Actual FOC Value: Rs. {actual_foc_value}")

# Check for FOC Usage model
print(f"\n=== CHECKING FOC USAGE MODEL ===")
try:
    from sales.foc_models import FOCUsage
    foc_usages = FOCUsage.objects.filter(bill=bill)
    print(f"FOC Usage records for this bill: {foc_usages.count()}")
    for usage in foc_usages:
        print(f"  Company: {usage.company.company_name}")
        print(f"  FOC Type: {usage.foc_type}")
        print(f"  Quantity: {usage.foc_quantity}")
        print(f"  Value: Rs. {usage.foc_value}")
except ImportError:
    print("FOCUsage model not found in sales.foc_models")
    try:
        from sales.models import FOCUsage
        foc_usages = FOCUsage.objects.filter(bill=bill)
        print(f"FOC Usage records for this bill: {foc_usages.count()}")
    except:
        print("FOCUsage model not found in sales.models either")
