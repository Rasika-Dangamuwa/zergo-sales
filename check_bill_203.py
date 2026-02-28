import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill
from decimal import Decimal

bill = Bill.objects.get(pk=203)
items = bill.items.all()

print('=== BILL #203 ===')
print(f'Bill Number: {bill.bill_number}')
print(f'Total Amount: Rs. {bill.total_amount}')
print()

for item in items:
    print(f'Product: {item.product.product_name}')
    print(f'Sales Qty: {item.quantity}')
    print(f'FOC Qty: {item.foc_quantity}')
    print(f'Unit Price: Rs. {item.unit_price}')
    print(f'Shop Price: Rs. {item.product.shop_price}')
    print(f'FOC Ratio: {item.product.shop_foc_buy}+{item.product.shop_foc_free}')
    print()
    
    # Calculate Standard FOC
    if item.product.shop_foc_buy and item.product.shop_foc_buy > 0:
        std_foc_qty = (item.quantity / Decimal(str(item.product.shop_foc_buy))) * Decimal(str(item.product.shop_foc_free))
    else:
        std_foc_qty = Decimal('0')
    
    std_foc_val = std_foc_qty * item.product.shop_price
    print(f'Standard FOC Qty: {std_foc_qty} bottles')
    print(f'Standard FOC Value: Rs. {std_foc_val}')
    print()
    
    # Calculate Actual FOC
    actual_explicit = item.foc_quantity * item.product.shop_price
    print(f'Actual Explicit FOC (Free bottles): Rs. {actual_explicit} ({item.foc_quantity} bottles)')
    
    if item.unit_price < item.product.shop_price:
        implicit = (item.product.shop_price - item.unit_price) * item.quantity
    else:
        implicit = Decimal('0')
    print(f'Actual Implicit FOC (Price discount): Rs. {implicit}')
    
    total_actual = actual_explicit + implicit
    print(f'Total Actual FOC: Rs. {total_actual}')
    print()
    
    variance = total_actual - std_foc_val
    print(f'Variance: Rs. {variance}')
    
    # Breakdown
    print()
    print('=== VARIANCE BREAKDOWN ===')
    bottle_impact = actual_explicit - std_foc_val
    print(f'Bottle Impact (Explicit FOC - Standard FOC): Rs. {bottle_impact}')
    print(f'Discount Impact (Implicit FOC): Rs. {implicit}')
    print(f'Total Variance: Rs. {variance}')
