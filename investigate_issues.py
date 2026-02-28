#!/usr/bin/env python
"""
Investigation script for Return #41 and Sale/Bill #46
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, Sale, Bill

print("="*80)
print("INVESTIGATING RETURN #41")
print("="*80)

r41 = Return.objects.filter(id=41).select_related('shop').prefetch_related('items__product').first()
if r41:
    print(f"Return Number: {r41.return_number}")
    print(f"Shop: {r41.shop.shop_name}")
    print(f"Return Status: {r41.return_status}")
    print(f"Settlement Method: {r41.settlement_method}")
    print(f"Settlement Status: {r41.settlement_status}")
    print(f"Total Amount: Rs. {r41.total_amount}")
    print(f"Cash Receipt Number: {r41.cash_receipt_number or 'None'}")
    print(f"Applied Amount: Rs. {r41.applied_amount}")
    print(f"Items:")
    for item in r41.items.all():
        print(f"  - {item.product.product_name}: {item.quantity} x Rs. {item.unit_price} = Rs. {item.total_price}")
    
    # Check potential issues
    print("\nPOTENTIAL ISSUES:")
    issues = []
    
    # Check 1: Settlement status consistency
    if r41.return_status == 'approved' and r41.settlement_method == 'credit_note':
        if r41.applied_amount >= r41.total_amount and r41.settlement_status != 'fully_applied':
            issues.append(f"Settlement status should be 'fully_applied' but is '{r41.settlement_status}'")
        elif r41.applied_amount > 0 and r41.applied_amount < r41.total_amount and r41.settlement_status != 'partially_applied':
            issues.append(f"Settlement status should be 'partially_applied' but is '{r41.settlement_status}'")
        elif r41.applied_amount == 0 and r41.settlement_status != 'available':
            issues.append(f"Settlement status should be 'available' but is '{r41.settlement_status}'")
    
    # Check 2: For cash settlements
    if r41.settlement_method == 'cash':
        if r41.return_status == 'approved' and not r41.cash_receipt_number:
            issues.append("Approved cash return should have a cash receipt number")
    
    if issues:
        for issue in issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ No issues detected")
else:
    print("NOT FOUND")

print("\n" + "="*80)
print("INVESTIGATING SALE/BILL #46")
print("="*80)

# Check both Sale and Bill tables
try:
    s46 = Sale.objects.filter(id=46).first()
    b46 = Bill.objects.filter(id=46).first()
except Exception as e:
    print(f"Error querying: {e}")
    s46 = None
    b46 = None

if s46:
    print("FOUND IN SALE TABLE:")
    print(f"Sale Number: {s46.sale_number}")
    print(f"Shop: {s46.shop.shop_name}")
    print(f"Total Amount: Rs. {s46.total_amount}")
    print(f"Paid Amount: Rs. {s46.paid_amount}")
    print(f"Balance: Rs. {s46.balance_amount}")
    print(f"Sale Status: {s46.sale_status}")
    print(f"Payment Status: {s46.payment_status}")
elif b46:
    print("FOUND IN BILL TABLE:")
    print(f"Bill Number: {b46.bill_number}")
    print(f"Shop: {b46.shop.shop_name}")
    print(f"Total Amount: Rs. {b46.total_amount}")
    print(f"Paid Amount: Rs. {b46.paid_amount}")
    print(f"Balance: Rs. {b46.balance_amount}")
    print(f"Bill Status: {b46.bill_status}")
    print(f"Payment Status: {b46.payment_status}")
else:
    print("NOT FOUND IN EITHER TABLE")

print("\n" + "="*80)
print("DATABASE MODEL STATUS")
print("="*80)
print(f"Total Sales: {Sale.objects.count()}")
print(f"Total Bills: {Bill.objects.count()}")
print(f"Total Returns: {Return.objects.count()}")
