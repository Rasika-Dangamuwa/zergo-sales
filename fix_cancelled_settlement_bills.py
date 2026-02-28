"""
Fix the 2 bills with incorrect status after settlement cancellation
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import transaction
from sales.models import Bill
from decimal import Decimal

def fix_cancelled_settlement_bills():
    print("\n" + "="*80)
    print("FIXING BILLS WITH INCORRECT STATUS AFTER SETTLEMENT CANCELLATION")
    print("="*80)
    
    # Fix Bill #119
    bill_119 = Bill.objects.get(id=119)
    print(f"\n{'='*60}")
    print(f"Bill #119 (BILL20260126020)")
    print(f"   BEFORE:")
    print(f"   Total: Rs. {bill_119.total_amount}")
    print(f"   Paid: Rs. {bill_119.paid_amount}")
    print(f"   Balance: Rs. {bill_119.balance_amount}")
    print(f"   Status: {bill_119.settlement_status}")
    
    with transaction.atomic():
        bill_119.paid_amount = Decimal('0')
        bill_119.balance_amount = bill_119.total_amount
        bill_119.settlement_status = 'unsettled'
        bill_119.save()
    
    print(f"\n   AFTER:")
    print(f"   Total: Rs. {bill_119.total_amount}")
    print(f"   Paid: Rs. {bill_119.paid_amount}")
    print(f"   Balance: Rs. {bill_119.balance_amount}")
    print(f"   Status: {bill_119.settlement_status}")
    print(f"   ✅ FIXED!")
    
    # Fix Bill #124
    bill_124 = Bill.objects.get(id=124)
    print(f"\n{'='*60}")
    print(f"Bill #124 (BILL20260126025)")
    print(f"   BEFORE:")
    print(f"   Total: Rs. {bill_124.total_amount}")
    print(f"   Paid: Rs. {bill_124.paid_amount}")
    print(f"   Balance: Rs. {bill_124.balance_amount}")
    print(f"   Status: {bill_124.settlement_status}")
    
    with transaction.atomic():
        bill_124.paid_amount = Decimal('0')
        bill_124.balance_amount = bill_124.total_amount
        bill_124.settlement_status = 'unsettled'
        bill_124.save()
    
    print(f"\n   AFTER:")
    print(f"   Total: Rs. {bill_124.total_amount}")
    print(f"   Paid: Rs. {bill_124.paid_amount}")
    print(f"   Balance: Rs. {bill_124.balance_amount}")
    print(f"   Status: {bill_124.settlement_status}")
    print(f"   ✅ FIXED!")
    
    print(f"\n{'='*80}")
    print("SUMMARY: 2 bills fixed")
    print("="*80 + "\n")

if __name__ == '__main__':
    fix_cancelled_settlement_bills()
