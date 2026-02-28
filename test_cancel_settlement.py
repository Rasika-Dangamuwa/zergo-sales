"""
Test cancelling settlement and watch commission changes
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from payments.models import SalesAccountSettlement
from sales.models import CommissionTransaction

# Find a completed settlement to test cancellation
settlement = SalesAccountSettlement.objects.filter(
    settlement_status='completed',
    bill__isnull=False
).first()

if settlement:
    print(f"\n{'='*80}")
    print(f"BEFORE CANCELLATION:")
    print(f"Settlement: {settlement.settlement_number}")
    print(f"Status: {settlement.settlement_status}")
    print(f"Amount: Rs. {settlement.amount}")
    print(f"{'='*80}\n")
    
    # Check existing transactions
    before_txns = CommissionTransaction.objects.filter(
        settlement=settlement
    ).count()
    print(f"Commission transactions BEFORE: {before_txns}\n")
    
    # Cancel the settlement
    print("🔄 Cancelling settlement...")
    settlement.settlement_status = 'cancelled'
    settlement.save()
    print("✅ Settlement cancelled\n")
    
    # Check transactions after
    print(f"{'='*80}")
    print(f"AFTER CANCELLATION:")
    print(f"Settlement: {settlement.settlement_number}")
    print(f"Status: {settlement.settlement_status}")
    print(f"{'='*80}\n")
    
    after_txns = CommissionTransaction.objects.filter(
        settlement=settlement
    ).order_by('created_at')
    
    print(f"Commission transactions AFTER: {after_txns.count()}\n")
    
    for i, txn in enumerate(after_txns, 1):
        direction = "+" if txn.commission_earned >= 0 else ""
        print(f"{i}. Amount: {txn.collected_amount:>10.2f} | "
              f"Commission: {direction}{txn.commission_earned:>8.2f} | "
              f"Balance: {txn.running_balance:>10.2f}")
        if txn.notes:
            print(f"   Notes: {txn.notes}")
    
    if after_txns.count() == before_txns:
        print("\n❌ ERROR: No reversal transaction was created!")
    else:
        print("\n✅ SUCCESS: Reversal transaction created!")
        
else:
    print("No completed settlement found to test!")
