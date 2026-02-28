"""
Fix all completed settlements that didn't update bill balances
This happens because signal handler fails when calculate_payment_totals() doesn't exist
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import transaction
from payments.models import SalesAccountSettlement
from sales.models import Bill
from decimal import Decimal

def fix_completed_settlements():
    """Recalculate all bills with completed settlements"""
    
    print("\n" + "="*80)
    print("FIXING ALL BILLS WITH COMPLETED SETTLEMENTS")
    print("="*80)
    
    # Get all bills that have settlements
    bills_with_settlements = Bill.objects.filter(
        settlements__settlement_status='completed'
    ).distinct().order_by('id')
    
    print(f"\nFound {bills_with_settlements.count()} bills with completed settlements")
    
    fixed_count = 0
    correct_count = 0
    
    for bill in bills_with_settlements:
        # Calculate expected paid amount from completed settlements
        expected_paid = sum(
            s.amount for s in bill.settlements.filter(settlement_status='completed')
        )
        
        actual_paid = bill.paid_amount
        
        if expected_paid != actual_paid:
            print(f"\n{'='*60}")
            print(f"❌ NEEDS FIX: Bill #{bill.id} ({bill.bill_number or bill.sale_number})")
            print(f"   Total: Rs. {bill.total_amount}")
            print(f"   Expected paid: Rs. {expected_paid}")
            print(f"   Actual paid: Rs. {actual_paid}")
            print(f"   Difference: Rs. {expected_paid - actual_paid}")
            
            # Show settlements
            settlements = bill.settlements.filter(settlement_status='completed')
            print(f"\n   Completed settlements ({settlements.count()}):")
            for s in settlements:
                print(f"     - {s.settlement_method}: Rs. {s.amount} (ID: {s.id})")
            
            # Fix it
            with transaction.atomic():
                bill.paid_amount = expected_paid
                bill.balance_amount = bill.total_amount - bill.paid_amount
                
                # Update status
                if bill.paid_amount >= bill.total_amount:
                    bill.settlement_status = 'settled'
                elif bill.paid_amount > 0:
                    bill.settlement_status = 'partial_settled'
                else:
                    bill.settlement_status = 'unsettled'
                
                bill.save()
            
            print(f"\n   ✅ FIXED: paid_amount set to Rs. {bill.paid_amount}, balance Rs. {bill.balance_amount}")
            fixed_count += 1
        else:
            correct_count += 1
            print(f"✅ Bill #{bill.id} ({bill.bill_number or bill.sale_number}): Correct (Rs. {actual_paid})")
    
    print(f"\n" + "="*80)
    print(f"SUMMARY:")
    print(f"  Total bills checked: {bills_with_settlements.count()}")
    print(f"  Already correct: {correct_count}")
    print(f"  Fixed: {fixed_count}")
    print("="*80 + "\n")

if __name__ == '__main__':
    fix_completed_settlements()
