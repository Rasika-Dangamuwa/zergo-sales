"""
Fix bills with incorrect status after return cancellation
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import transaction
from sales.models import Bill
from decimal import Decimal

def fix_return_cancellation_bills():
    print("\n" + "="*80)
    print("FIXING BILLS WITH INCORRECT STATUS AFTER RETURN CANCELLATION")
    print("="*80)
    
    # Fix Bill #125
    bill_125 = Bill.objects.get(id=125)
    print(f"\n{'='*60}")
    print(f"Bill #125 (BILL20260126026)")
    print(f"   BEFORE:")
    print(f"   Total: Rs. {bill_125.total_amount}")
    print(f"   Paid: Rs. {bill_125.paid_amount}")
    print(f"   Balance: Rs. {bill_125.balance_amount}")
    print(f"   Status: {bill_125.settlement_status}")
    
    with transaction.atomic():
        bill_125.paid_amount = Decimal('0')
        bill_125.balance_amount = bill_125.total_amount
        bill_125.settlement_status = 'unsettled'
        bill_125.save()
    
    print(f"\n   AFTER:")
    print(f"   Total: Rs. {bill_125.total_amount}")
    print(f"   Paid: Rs. {bill_125.paid_amount}")
    print(f"   Balance: Rs. {bill_125.balance_amount}")
    print(f"   Status: {bill_125.settlement_status}")
    print(f"   ✅ FIXED!")
    
    # Fix Bill #126
    bill_126 = Bill.objects.get(id=126)
    print(f"\n{'='*60}")
    print(f"Bill #126 (BILL20260126027)")
    print(f"   BEFORE:")
    print(f"   Total: Rs. {bill_126.total_amount}")
    print(f"   Paid: Rs. {bill_126.paid_amount}")
    print(f"   Balance: Rs. {bill_126.balance_amount}")
    print(f"   Status: {bill_126.settlement_status}")
    
    with transaction.atomic():
        bill_126.paid_amount = Decimal('0')
        bill_126.balance_amount = bill_126.total_amount
        bill_126.settlement_status = 'unsettled'
        bill_126.save()
    
    print(f"\n   AFTER:")
    print(f"   Total: Rs. {bill_126.total_amount}")
    print(f"   Paid: Rs. {bill_126.paid_amount}")
    print(f"   Balance: Rs. {bill_126.balance_amount}")
    print(f"   Status: {bill_126.settlement_status}")
    print(f"   ✅ FIXED!")
    
    print(f"\n{'='*80}")
    print("SUMMARY: 2 bills fixed")
    print("="*80 + "\n")

if __name__ == '__main__':
    fix_return_cancellation_bills()
