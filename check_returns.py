#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, ReturnItem
from django.db.models import Count, Sum

# Get all returns
returns = Return.objects.all().select_related('shop', 'created_by').order_by('-created_at')

print(f"Total Returns in Database: {returns.count()}")
print("\n" + "="*80)
print("RETURN DETAILS")
print("="*80)

for r in returns:
    print(f"\nReturn #{r.id} - {r.return_number}")
    print(f"  Shop: {r.shop.shop_name}")
    print(f"  Return Status: {r.return_status}")
    print(f"  Settlement Method: {r.settlement_method}")
    print(f"  Settlement Status: {r.settlement_status}")
    print(f"  Total Amount: Rs. {r.total_amount}")
    print(f"  Items Count: {r.items.count()}")
    print(f"  Created: {r.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Created By: {r.created_by.username if r.created_by else 'N/A'}")
    print(f"  Cash Receipt Number: {r.cash_receipt_number or 'None'}")
    print(f"  Cash Paid By: {r.cash_paid_by.username if r.cash_paid_by else 'N/A'}")
    print(f"  Cash Paid At: {r.cash_paid_at.strftime('%Y-%m-%d %H:%M:%S') if r.cash_paid_at else 'N/A'}")
    
    # Show items
    items = r.items.all()
    if items:
        print(f"  Items:")
        for item in items:
            print(f"    - {item.product.product_name}: {item.quantity} x Rs. {item.unit_price} = Rs. {item.quantity * item.unit_price}")

print("\n" + "="*80)
print("STATUS BREAKDOWN")
print("="*80)

status_counts = Return.objects.values('return_status').annotate(
    count=Count('id'), 
    total=Sum('total_amount')
).order_by('return_status')

for s in status_counts:
    print(f"{s['return_status'].upper()}: {s['count']} returns, Total Rs. {s['total'] or 0}")

print("\n" + "="*80)
print("SETTLEMENT STATUS BREAKDOWN")
print("="*80)

settlement_counts = Return.objects.values('settlement_status').annotate(
    count=Count('id'), 
    total=Sum('total_amount')
).order_by('settlement_status')

for s in settlement_counts:
    print(f"{s['settlement_status'].upper()}: {s['count']} returns, Total Rs. {s['total'] or 0}")

print("\n" + "="*80)
print("SETTLEMENT METHOD BREAKDOWN")
print("="*80)

method_counts = Return.objects.values('settlement_method').annotate(
    count=Count('id'), 
    total=Sum('total_amount')
).order_by('settlement_method')

for m in method_counts:
    print(f"{m['settlement_method'].upper()}: {m['count']} returns, Total Rs. {m['total'] or 0}")
