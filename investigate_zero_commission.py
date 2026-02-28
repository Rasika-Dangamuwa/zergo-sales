"""
Investigate why reversal transaction has 0 commission
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from payments.models import SalesAccountSettlement

# Find settlement 032
settlement = SalesAccountSettlement.objects.filter(
    settlement_number='SET-20260125-032'
).first()

if settlement:
    print(f"\n{'='*80}")
    print(f"SETTLEMENT: {settlement.settlement_number}")
    print(f"Status: {settlement.settlement_status}")
    print(f"Amount: Rs. {settlement.amount}")
    print(f"{'='*80}\n")
    
    # Get all transactions for this settlement
    transactions = CommissionTransaction.objects.filter(
        settlement=settlement
    ).order_by('created_at')
    
    print(f"Transactions: {transactions.count()}\n")
    
    for i, txn in enumerate(transactions, 1):
        print(f"{i}. Transaction ID: {txn.id}")
        print(f"   Type: {txn.transaction_type}")
        print(f"   Created: {txn.created_at}")
        print(f"   Sales Rep: {txn.sales_rep.username}")
        print(f"   Collected Amount: {txn.collected_amount}")
        print(f"   Applicable Rate: {txn.applicable_rate}%")
        print(f"   Commission Earned: {txn.commission_earned}")
        print(f"   Running Balance: {txn.running_balance}")
        print(f"   Notes: {txn.notes or 'N/A'}")
        print()
        
        # Calculate what commission SHOULD be
        expected_commission = (txn.collected_amount * txn.applicable_rate) / 100
        print(f"   Expected Commission: {expected_commission}")
        if expected_commission != txn.commission_earned:
            print(f"   ⚠️  MISMATCH! Stored: {txn.commission_earned}, Expected: {expected_commission}")
        print()
else:
    print("Settlement not found!")
