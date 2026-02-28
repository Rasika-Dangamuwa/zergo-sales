"""
Fix existing cancelled settlements that don't have reversal transactions
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from payments.models import SalesAccountSettlement
from django.utils import timezone

def fix_cancelled_commissions():
    """Create reversal transactions for cancelled settlements that don't have them"""
    
    # Find all cancelled/bounced settlements
    cancelled_settlements = SalesAccountSettlement.objects.filter(
        settlement_status__in=['cancelled', 'bounced']
    )
    
    print(f"Found {cancelled_settlements.count()} cancelled/bounced settlements")
    
    fixed_count = 0
    already_fixed = 0
    
    for settlement in cancelled_settlements:
        # Find the original positive commission transaction
        original_txn = CommissionTransaction.objects.filter(
            transaction_type='payment_received',
            settlement=settlement,
            commission_earned__gt=0
        ).first()
        
        if not original_txn:
            print(f"  ⚠️  No original transaction found for {settlement.settlement_number}")
            continue
        
        # Check if reversal already exists (check for both old and new transaction types)
        reversal_exists = CommissionTransaction.objects.filter(
            settlement=settlement,
            commission_earned__lt=0
        ).exists()
        
        if reversal_exists:
            already_fixed += 1
            print(f"  ✅ Reversal already exists for {settlement.settlement_number}")
            continue
        
        # Create reversal transaction with new transaction_type
        reversal = CommissionTransaction.objects.create(
            transaction_type='payment_cancelled',
            transaction_date=timezone.now(),
            sales_rep=original_txn.sales_rep,
            bill=original_txn.bill,
            settlement=settlement,
            collected_amount=-original_txn.collected_amount,
            notes=f"REVERSAL: Settlement {settlement.settlement_number} {settlement.settlement_status} - Commission cancelled"
        )
        
        fixed_count += 1
        print(f"  ✅ Created reversal for {settlement.settlement_number}: {reversal.commission_earned}")
    
    print(f"\n📊 Summary:")
    print(f"   Fixed: {fixed_count}")
    print(f"   Already had reversals: {already_fixed}")
    print(f"   Total processed: {cancelled_settlements.count()}")

if __name__ == '__main__':
    fix_cancelled_commissions()
