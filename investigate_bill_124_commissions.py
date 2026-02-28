"""
Investigate Bill #124 settlements and commission tracking
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill, CommissionTransaction
from payments.models import SalesAccountSettlement
from decimal import Decimal

def investigate_bill_124_commissions():
    print("\n" + "="*80)
    print("INVESTIGATING BILL #124 SETTLEMENTS & COMMISSION TRACKING")
    print("="*80)
    
    bill = Bill.objects.get(id=124)
    
    print(f"\n📋 BILL DETAILS:")
    print(f"   ID: {bill.id}")
    print(f"   Number: {bill.bill_number}")
    print(f"   Shop: {bill.shop.shop_name}")
    print(f"   Sales Rep: {bill.sales_rep.get_full_name()}")
    print(f"   Total: Rs. {bill.total_amount}")
    print(f"   Date: {bill.bill_date.strftime('%Y-%m-%d')}")
    
    # Get ALL settlements (including cancelled)
    all_settlements = SalesAccountSettlement.objects.filter(bill=bill).order_by('id')
    
    print(f"\n💰 ALL SETTLEMENTS ({all_settlements.count()}):")
    
    for s in all_settlements:
        print(f"\n   Settlement #{s.id} - {s.settlement_number}")
        print(f"   Method: {s.settlement_method}")
        print(f"   Amount: Rs. {s.amount}")
        print(f"   Status: {s.settlement_status}")
        print(f"   Date: {s.settlement_date.strftime('%Y-%m-%d %H:%M')}")
        
        # Check for commission transactions
        commissions = CommissionTransaction.objects.filter(settlement=s)
        
        if commissions.exists():
            print(f"   ✅ Commission Transactions ({commissions.count()}):")
            for c in commissions:
                print(f"      - Type: {c.transaction_type}")
                print(f"        Collected: Rs. {c.collected_amount}")
                print(f"        Commission: Rs. {c.commission_earned}")
                print(f"        Date: {c.transaction_date.strftime('%Y-%m-%d %H:%M')}")
        else:
            print(f"   ❌ NO COMMISSION TRANSACTIONS!")
            
            # Check if this should have commission
            if s.settlement_status == 'completed':
                print(f"      ⚠️ PROBLEM: Completed settlement missing commission!")
            elif s.settlement_status == 'cancelled':
                print(f"      ⚠️ PROBLEM: Cancelled settlement missing reversal commission!")
    
    # Check for bill creation commission
    bill_commissions = CommissionTransaction.objects.filter(
        bill=bill,
        transaction_type='bill_created'
    )
    
    print(f"\n📊 BILL CREATION COMMISSION:")
    if bill_commissions.exists():
        for c in bill_commissions:
            print(f"   ✅ Commission #{c.id}")
            print(f"      Sales Amount: Rs. {c.sales_amount}")
            print(f"      Commission: Rs. {c.commission_earned}")
    else:
        print(f"   ❌ NO BILL CREATION COMMISSION!")
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY:")
    print(f"{'='*80}")
    
    total_settlements = all_settlements.count()
    completed = all_settlements.filter(settlement_status='completed').count()
    cancelled = all_settlements.filter(settlement_status='cancelled').count()
    
    total_commissions = CommissionTransaction.objects.filter(settlement__bill=bill).count()
    
    print(f"Total Settlements: {total_settlements}")
    print(f"  - Completed: {completed}")
    print(f"  - Cancelled: {cancelled}")
    print(f"Total Settlement Commissions: {total_commissions}")
    
    # Check what's missing
    expected_completed_commissions = completed  # Each completed should have payment_received
    expected_cancelled_commissions = cancelled  # Each cancelled should have payment_cancelled
    expected_total = expected_completed_commissions + expected_cancelled_commissions
    
    print(f"\nExpected Commission Transactions:")
    print(f"  - For completed settlements: {expected_completed_commissions}")
    print(f"  - For cancelled settlements: {expected_cancelled_commissions}")
    print(f"  - Total expected: {expected_total}")
    print(f"  - Actual: {total_commissions}")
    print(f"  - Missing: {expected_total - total_commissions}")
    
    print("="*80 + "\n")

if __name__ == '__main__':
    investigate_bill_124_commissions()
