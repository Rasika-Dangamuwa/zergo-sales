"""
Investigate Settlement SET-20260125-043 and Return RN-20260125-00
User reports these are cancelled but cancellation not showing in commission dashboard
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction, Return
from payments.models import SalesAccountSettlement
from django.utils import timezone

print("=" * 80)
print("INVESTIGATING SETTLEMENT SET-20260125-043")
print("=" * 80)
print()

# Check settlement
settlement = SalesAccountSettlement.objects.filter(
    settlement_number='SET-20260125-043'
).first()

if settlement:
    print(f"Settlement Found: {settlement.settlement_number}")
    print(f"  Status: {settlement.settlement_status}")
    print(f"  Amount: Rs. {settlement.amount}")
    print(f"  Date: {settlement.settlement_date}")
    print(f"  Bill: {settlement.bill.bill_number if settlement.bill else 'None'}")
    print(f"  Received By: {settlement.received_by.username if settlement.received_by else 'None'}")
    print(f"  Created: {settlement.created_at}")
    print(f"  Updated: {settlement.updated_at}")
    print()
    
    # Get ALL commission transactions for this settlement
    txns = CommissionTransaction.objects.filter(
        settlement=settlement
    ).order_by('transaction_date', 'id')
    
    print(f"Commission Transactions: {txns.count()}")
    for txn in txns:
        print(f"  ID {txn.id}: {txn.transaction_type}")
        print(f"    Date: {txn.transaction_date}")
        print(f"    Amount: {txn.collected_amount}")
        print(f"    Commission: {txn.commission_earned}")
        print(f"    Balance: {txn.running_balance}")
        print(f"    Sales Rep: {txn.sales_rep.username}")
        print()
    
    # Check if settlement is cancelled but has no reversal
    if settlement.settlement_status == 'cancelled':
        has_received = txns.filter(transaction_type='payment_received').exists()
        has_cancelled = txns.filter(transaction_type='payment_cancelled').exists()
        
        if has_received and not has_cancelled:
            print("❌ ISSUE FOUND: Settlement is cancelled but has no reversal transaction!")
            print()
else:
    print("❌ Settlement SET-20260125-043 not found!")
    print()

print("=" * 80)
print("INVESTIGATING RETURN RN-20260125-00")
print("=" * 80)
print()

# Check return
return_obj = Return.objects.filter(
    return_number__startswith='RN-20260125-00'
).first()

if return_obj:
    print(f"Return Found: {return_obj.return_number}")
    print(f"  Verified: {return_obj.is_verified}")
    print(f"  Amount: Rs. {return_obj.total_amount}")
    print(f"  Date: {return_obj.return_date}")
    print(f"  Shop: {return_obj.shop.shop_name if return_obj.shop else 'None'}")
    print(f"  Created By: {return_obj.created_by.username if return_obj.created_by else 'None'}")
    print()
    
    # Get commission transactions related to this return
    return_txns = CommissionTransaction.objects.filter(
        notes__icontains=return_obj.return_number
    ).order_by('transaction_date', 'id')
    
    print(f"Commission Transactions: {return_txns.count()}")
    for txn in return_txns:
        print(f"  ID {txn.id}: {txn.transaction_type}")
        print(f"    Date: {txn.transaction_date}")
        print(f"    Commission: {txn.commission_earned}")
        print(f"    Balance: {txn.running_balance}")
        print(f"    Sales Rep: {txn.sales_rep.username}")
        print()
    
    # Check if return has settlement applications
    settlements = SalesAccountSettlement.objects.filter(
        return_ref=return_obj
    )
    
    print(f"Settlements using this return: {settlements.count()}")
    for s in settlements:
        print(f"  {s.settlement_number}: {s.settlement_status}, Rs. {s.amount}")
    print()
else:
    print("❌ Return not found!")
    print()

# Check transactions around 01:12-01:13 AM on Jan 26
print("=" * 80)
print("ALL TRANSACTIONS AROUND 01:12-01:13 AM (Jan 26)")
print("=" * 80)
print()

from datetime import datetime
start_time = datetime(2026, 1, 26, 1, 10, 0)
end_time = datetime(2026, 1, 26, 1, 15, 0)

txns = CommissionTransaction.objects.filter(
    transaction_date__range=[start_time, end_time]
).order_by('transaction_date', 'id')

print(f"Found {txns.count()} transactions")
for txn in txns:
    settlement_info = f"Settlement: {txn.settlement.settlement_number} ({txn.settlement.settlement_status})" if txn.settlement else "No settlement"
    print(f"{txn.transaction_date.strftime('%H:%M:%S')} | "
          f"ID:{txn.id} | "
          f"{txn.transaction_type:20s} | "
          f"{settlement_info:40s} | "
          f"Rep: {txn.sales_rep.username:10s} | "
          f"Comm: {str(txn.commission_earned):>7s} | "
          f"Bal: {str(txn.running_balance):>8s}")

print()
print("=" * 80)
print("DIAGNOSIS")
print("=" * 80)

if settlement and settlement.settlement_status == 'cancelled':
    print("The settlement IS cancelled in the database.")
    has_reversal = CommissionTransaction.objects.filter(
        settlement=settlement,
        transaction_type='payment_cancelled'
    ).exists()
    
    if not has_reversal:
        print("❌ The reversal transaction (payment_cancelled) was NOT created!")
        print("   This is why the cancellation doesn't show in the dashboard.")
        print()
        print("ROOT CAUSE:")
        print("  The commission signal for settlement cancellation didn't fire,")
        print("  or the settlement was cancelled before the signal system was implemented.")
