"""
Investigate Bill #124 (BILL20260126025) - Partially Settled Status Issue
User says it should NOT be partially settled - suspects cancellation issue
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill, Return
from payments.models import SalesAccountSettlement
from decimal import Decimal

def investigate_bill_124():
    print("\n" + "="*80)
    print("INVESTIGATING BILL #124 (BILL20260126025)")
    print("="*80)
    
    # Get the bill
    bill = Bill.objects.filter(bill_number='BILL20260126025').first()
    
    if not bill:
        print("❌ Bill not found!")
        return
    
    print(f"\n📋 BILL DETAILS:")
    print(f"   ID: {bill.id}")
    print(f"   Number: {bill.bill_number}")
    print(f"   Shop: {bill.shop.shop_name}")
    print(f"   Total: Rs. {bill.total_amount}")
    print(f"   Paid: Rs. {bill.paid_amount}")
    print(f"   Balance: Rs. {bill.balance_amount}")
    print(f"   Status: {bill.settlement_status}")
    
    # Get all settlements (including cancelled)
    all_settlements = SalesAccountSettlement.objects.filter(bill=bill).order_by('id')
    
    print(f"\n💰 ALL SETTLEMENTS ({all_settlements.count()}):")
    total_completed = Decimal('0')
    total_cancelled = Decimal('0')
    
    for s in all_settlements:
        status_icon = "✅" if s.settlement_status == 'completed' else "⏳" if s.settlement_status == 'pending' else "❌"
        print(f"\n   {status_icon} Settlement #{s.id}")
        print(f"      Number: {s.settlement_number}")
        print(f"      Method: {s.settlement_method}")
        print(f"      Amount: Rs. {s.amount}")
        print(f"      Status: {s.settlement_status}")
        print(f"      Date: {s.settlement_date.strftime('%Y-%m-%d %H:%M')}")
        
        if s.return_ref:
            print(f"      Return Ref: Return #{s.return_ref.id} ({s.return_ref.return_number})")
            print(f"      Return Settlement Status: {s.return_ref.settlement_status}")
        
        if s.settlement_status == 'completed':
            total_completed += s.amount
        elif s.settlement_status == 'cancelled':
            total_cancelled += s.amount
    
    print(f"\n   TOTALS:")
    print(f"   ✅ Completed: Rs. {total_completed}")
    print(f"   ❌ Cancelled: Rs. {total_cancelled}")
    print(f"   📊 Expected Paid Amount: Rs. {total_completed}")
    print(f"   📊 Actual Paid Amount: Rs. {bill.paid_amount}")
    
    # Check returns for this bill
    returns = Return.objects.filter(bill=bill).order_by('id')
    
    print(f"\n🔄 RETURNS FOR THIS BILL ({returns.count()}):")
    for r in returns:
        print(f"\n   Return #{r.id}")
        print(f"   Number: {r.return_number}")
        print(f"   Total: Rs. {r.total_amount}")
        print(f"   Settlement Method: {r.settlement_method}")
        print(f"   Settlement Status: {r.settlement_status}")
        
        # Check if this return was used in a settlement
        settlements_using_return = SalesAccountSettlement.objects.filter(return_ref=r)
        if settlements_using_return.exists():
            print(f"   Used in settlements:")
            for s in settlements_using_return:
                print(f"      - Settlement #{s.id} ({s.settlement_status})")
    
    # DIAGNOSIS
    print(f"\n" + "="*80)
    print("🔍 DIAGNOSIS:")
    print("="*80)
    
    if total_completed == 0:
        print("\n❌ PROBLEM: No completed settlements, but bill shows as partially_settled!")
        print("   Expected status: 'unsettled'")
        print("   Actual status: '{}'".format(bill.settlement_status))
        print("\n   💡 This means the bill status was NOT recalculated when settlements were cancelled.")
        
    elif total_completed != bill.paid_amount:
        print(f"\n❌ PROBLEM: Paid amount mismatch!")
        print(f"   Expected paid: Rs. {total_completed}")
        print(f"   Actual paid: Rs. {bill.paid_amount}")
        print(f"   Difference: Rs. {total_completed - bill.paid_amount}")
        
    else:
        print("\n✅ Paid amount is correct")
    
    # Check if status is correct
    if total_completed == 0:
        expected_status = 'unsettled'
    elif total_completed >= bill.total_amount:
        expected_status = 'settled'
    elif total_completed > 0:
        expected_status = 'partial_settled'
    else:
        expected_status = 'unsettled'
    
    if bill.settlement_status != expected_status:
        print(f"\n❌ PROBLEM: Status mismatch!")
        print(f"   Expected status: '{expected_status}'")
        print(f"   Actual status: '{bill.settlement_status}'")
        print(f"\n   💡 ROOT CAUSE: Settlement cancellation did NOT update bill status!")
    else:
        print(f"\n✅ Status is correct: '{bill.settlement_status}'")
    
    print("\n" + "="*80)

if __name__ == '__main__':
    investigate_bill_124()
