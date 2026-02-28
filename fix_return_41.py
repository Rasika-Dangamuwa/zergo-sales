#!/usr/bin/env python
"""
Fix Return #41 settlement status
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return

print("Fixing Return #41 settlement status...")

r41 = Return.objects.get(id=41)
print(f"\nReturn #{r41.id} - {r41.return_number}")
print(f"  Current settlement_status: {r41.settlement_status}")
print(f"  Total amount: Rs. {r41.total_amount}")
print(f"  Applied amount: Rs. {r41.applied_amount}")

if r41.applied_amount >= r41.total_amount:
    r41.settlement_status = 'fully_applied'
    r41.save(update_fields=['settlement_status'])
    print(f"  ✅ FIXED: Updated to 'fully_applied'")
else:
    print(f"  ℹ️  No fix needed")
