"""
Debug commission transactions for cancelled settlements
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_distributors.settings')
django.setup()

from sales.models import CommissionTransaction
from payments.models import SalesAccountSettlement

# Get cancelled settlements
cancelled = SalesAccountSettlement.objects.filter(settlement_status='cancelled').order_by('-id')[:5]

print(f"\n{'='*80}")
print("CANCELLED SETTLEMENTS AND THEIR COMMISSION TRANSACTIONS")
print(f"{'='*80}\n")

for settlement in cancelled:
    print(f"Settlement: {settlement.settlement_number} - Status: {settlement.settlement_status}")
    
    # Get all commission transactions for this settlement
    transactions = CommissionTransaction.objects.filter(settlement=settlement).order_by('created_at')
    
    print(f"  Found {transactions.count()} transaction(s):")
    for txn in transactions:
        print(f"    - ID: {txn.id}")
        print(f"      Type: {txn.transaction_type}")
        print(f"      Collected: Rs. {txn.collected_amount}")
        print(f"      Commission: Rs. {txn.commission_earned}")
        print(f"      Notes: {txn.notes}")
        print(f"      Created: {txn.created_at}")
        print()
    
    print("-" * 80)
    print()
