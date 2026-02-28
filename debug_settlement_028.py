"""
Check the exact sequence of transactions for SET-20260125-028
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from payments.models import SalesAccountSettlement

# Find the settlement
settlement = SalesAccountSettlement.objects.filter(
    settlement_number='SET-20260125-028'
).first()

if settlement:
    print(f"\n{'='*80}")
    print(f"SETTLEMENT: {settlement.settlement_number}")
    print(f"Status: {settlement.settlement_status}")
    print(f"Amount: Rs. {settlement.amount}")
    print(f"Created: {settlement.created_at}")
    print(f"{'='*80}\n")
    
    # Find all commission transactions for this settlement
    transactions = CommissionTransaction.objects.filter(
        settlement=settlement
    ).order_by('created_at')
    
    print(f"Commission Transactions for this settlement: {transactions.count()}\n")
    
    for i, txn in enumerate(transactions, 1):
        direction = "+" if txn.commission_earned >= 0 else ""
        print(f"{i}. Created: {txn.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Collected Amount: {txn.collected_amount:>10.2f}")
        print(f"   Commission: {direction}{txn.commission_earned:>8.2f}")
        print(f"   Running Balance: {txn.running_balance:>10.2f}")
        print(f"   Notes: {txn.notes or 'N/A'}")
        print()
else:
    print("Settlement SET-20260125-028 not found!")
