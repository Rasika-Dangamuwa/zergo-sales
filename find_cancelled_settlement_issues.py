"""
Find all bills with incorrect status due to cancelled settlements
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill
from payments.models import SalesAccountSettlement
from decimal import Decimal

def find_incorrect_statuses():
    print("\n" + "="*80)
    print("FINDING BILLS WITH INCORRECT STATUS AFTER SETTLEMENT CANCELLATION")
    print("="*80)
    
    # Get all bills
    all_bills = Bill.objects.all().order_by('id')
    
    incorrect_bills = []
    
    for bill in all_bills:
        # Calculate expected values
        completed_amount = sum(
            s.amount for s in bill.settlements.filter(settlement_status='completed')
        )
        
        # Calculate expected status
        if completed_amount == 0:
            expected_status = 'unsettled'
        elif completed_amount >= bill.total_amount:
            expected_status = 'settled'
        else:
            expected_status = 'partial_settled'
        
        expected_balance = bill.total_amount - completed_amount
        
        # Check if status or balance is wrong
        status_wrong = bill.settlement_status != expected_status
        balance_wrong = bill.balance_amount != expected_balance
        paid_wrong = bill.paid_amount != completed_amount
        
        if status_wrong or balance_wrong or paid_wrong:
            incorrect_bills.append({
                'bill': bill,
                'expected_status': expected_status,
                'actual_status': bill.settlement_status,
                'expected_paid': completed_amount,
                'actual_paid': bill.paid_amount,
                'expected_balance': expected_balance,
                'actual_balance': bill.balance_amount,
                'status_wrong': status_wrong,
                'balance_wrong': balance_wrong,
                'paid_wrong': paid_wrong,
            })
    
    print(f"\nFound {len(incorrect_bills)} bills with incorrect data:")
    
    for data in incorrect_bills:
        bill = data['bill']
        print(f"\n{'='*60}")
        print(f"❌ Bill #{bill.id} ({bill.bill_number or bill.sale_number})")
        print(f"   Total: Rs. {bill.total_amount}")
        
        if data['paid_wrong']:
            print(f"   💰 PAID WRONG:")
            print(f"      Expected: Rs. {data['expected_paid']}")
            print(f"      Actual: Rs. {data['actual_paid']}")
            print(f"      Diff: Rs. {data['expected_paid'] - data['actual_paid']}")
        
        if data['balance_wrong']:
            print(f"   💵 BALANCE WRONG:")
            print(f"      Expected: Rs. {data['expected_balance']}")
            print(f"      Actual: Rs. {data['actual_balance']}")
            print(f"      Diff: Rs. {data['expected_balance'] - data['actual_balance']}")
        
        if data['status_wrong']:
            print(f"   📊 STATUS WRONG:")
            print(f"      Expected: {data['expected_status']}")
            print(f"      Actual: {data['actual_status']}")
        
        # Show cancelled settlements
        cancelled = bill.settlements.filter(settlement_status='cancelled')
        if cancelled.exists():
            print(f"\n   ❌ Cancelled settlements ({cancelled.count()}):")
            for s in cancelled:
                print(f"      - {s.settlement_method}: Rs. {s.amount} (#{s.id})")
    
    print(f"\n{'='*80}")
    print(f"TOTAL: {len(incorrect_bills)} bills need fixing")
    print("="*80)
    
    return incorrect_bills

if __name__ == '__main__':
    find_incorrect_statuses()
