import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill
from decimal import Decimal

bill = Bill.objects.get(id=171)
print(f"=== VERIFYING FOC ANALYSIS FOR BILL {bill.bill_number} ===\n")

for item in bill.items.all():
    product = item.product
    print(f"Product: {product.product_name}")
    print(f"Sales Quantity: {item.quantity}")
    print(f"Unit Price: Rs. {item.unit_price}")
    print(f"FOC Quantity (Explicit): {item.foc_quantity}")
    print(f"\nProduct Settings:")
    print(f"  Shop Price: Rs. {product.shop_price}")
    print(f"  Shop FOC Ratio: Buy {product.shop_foc_buy} + Get {product.shop_foc_free} free")
    
    # Calculate Standard FOC
    if product.shop_foc_buy and product.shop_foc_buy > 0:
        standard_foc_qty = (item.quantity / Decimal(str(product.shop_foc_buy))) * Decimal(str(product.shop_foc_free))
        standard_foc_value = standard_foc_qty * product.shop_price
        print(f"\nSTANDARD FOC (Based on Ratio):")
        print(f"  Formula: ({item.quantity} / {product.shop_foc_buy}) × {product.shop_foc_free}")
        print(f"  Quantity: {standard_foc_qty:.2f} bottles")
        print(f"  Value: Rs. {standard_foc_value:.2f}")
    else:
        standard_foc_qty = Decimal('0')
        standard_foc_value = Decimal('0')
        print(f"\nSTANDARD FOC: N/A (no FOC ratio set)")
    
    # Calculate Actual FOC
    actual_explicit_foc_qty = item.foc_quantity
    actual_explicit_foc_value = actual_explicit_foc_qty * product.shop_price
    
    actual_implicit_foc_value = Decimal('0')
    if item.unit_price < product.shop_price:
        price_difference = product.shop_price - item.unit_price
        actual_implicit_foc_value = price_difference * item.quantity
        print(f"\nIMPLICIT FOC (Selling Below Shop Price):")
        print(f"  Shop Price: Rs. {product.shop_price}")
        print(f"  Sold At: Rs. {item.unit_price}")
        print(f"  Discount per bottle: Rs. {price_difference}")
        print(f"  Total Implicit FOC: Rs. {actual_implicit_foc_value:.2f}")
    
    actual_total_foc_value = actual_explicit_foc_value + actual_implicit_foc_value
    
    print(f"\nACTUAL FOC:")
    print(f"  Explicit (Free Bottles): {actual_explicit_foc_qty} bottles = Rs. {actual_explicit_foc_value:.2f}")
    print(f"  Implicit (Price Discount): Rs. {actual_implicit_foc_value:.2f}")
    print(f"  Total Value: Rs. {actual_total_foc_value:.2f}")
    
    # Calculate Variance
    variance_qty = actual_explicit_foc_qty - standard_foc_qty
    variance_value = actual_total_foc_value - standard_foc_value
    
    print(f"\nVARIANCE ANALYSIS:")
    print(f"  Quantity Variance: {'+' if variance_qty > 0 else ''}{variance_qty:.2f} bottles")
    print(f"  Value Variance: {'+' if variance_value > 0 else ''}Rs. {variance_value:.2f}")
    
    if variance_value > 0:
        print(f"  ⚠️  IMPACT: LOSS - Gave Rs. {variance_value:.2f} MORE than standard")
        print(f"  This is EXCESS FOC (bad for profit)")
    elif variance_value < 0:
        print(f"  ✓ IMPACT: PROFIT SAVED - Gave Rs. {abs(variance_value):.2f} LESS than standard")
        print(f"  This is GOOD for profit")
    else:
        print(f"  ✓ IMPACT: On target - exactly as per standard ratio")
    
    print("\n" + "="*60 + "\n")

print("\nVERIFICATION SUMMARY:")
print("="*60)
print("✓ Standard FOC: Calculated from shop_foc_buy / shop_foc_free ratio")
print("✓ Actual FOC: Explicit (free bottles) + Implicit (discount)")
print("✓ Variance: Actual - Standard")
print("✓ Loss Indicator: Positive variance = RED = Business Loss")
print("✓ Profit Indicator: Negative variance = GREEN = Profit Saved")
