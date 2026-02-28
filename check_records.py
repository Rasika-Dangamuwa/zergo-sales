#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, Sale

print("Checking Return #41...")
r = Return.objects.filter(id=41).first()
if r:
    print(f"  Return Number: {r.return_number}")
    print(f"  Shop: {r.shop.shop_name}")
    print(f"  Status: {r.return_status}")
    print(f"  Settlement Method: {r.settlement_method}")
    print(f"  Settlement Status: {r.settlement_status}")
    print(f"  Total: Rs. {r.total_amount}")
    print(f"  Created: {r.created_at}")
    print(f"  Items: {r.items.count()}")
else:
    print("  NOT FOUND")

print("\nChecking Sale #46...")
s = Sale.objects.filter(id=46).first()
if s:
    print(f"  Sale Number: {s.sale_number}")
    print(f"  Shop: {s.shop.shop_name}")
    print(f"  Total: Rs. {s.total_amount}")
    print(f"  Payment Status: {s.payment_status}")
    print(f"  Created: {s.created_at}")
else:
    print("  NOT FOUND")
