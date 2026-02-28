"""
Test to understand Bill's relationship with settlements
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill

bill = Bill.objects.get(pk=90)

print("Testing Bill #90 relationships:")
print("=" * 80)

# Try settlements
try:
    settlements = bill.settlements.all()
    print(f"✓ bill.settlements works: {settlements.count()} settlements")
    for s in settlements:
        print(f"  - {s.settlement_number}: {s.settlement_status}, Rs. {s.amount}")
except AttributeError as e:
    print(f"✗ bill.settlements failed: {e}")

print()

# Try payments
try:
    payments = bill.payments.all()
    print(f"✓ bill.payments works: {payments.count()} payments")
    for p in payments:
        print(f"  - {p}")
except AttributeError as e:
    print(f"✗ bill.payments failed: {e}")

print()
print("=" * 80)
