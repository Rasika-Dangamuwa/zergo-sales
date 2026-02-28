"""
Delete duplicate/incorrect payout records
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.commission_schedule_models import CommissionPayoutHistory, UserCommissionPayout
from sales.models import CommissionTransaction
from django.db import transaction

def fix_duplicate_payouts():
    """Remove duplicate payout for CP-20260127-003 and its clearing transaction"""
    
    print("\n=== Fixing Duplicate Payout ===\n")
    
    # Find the duplicate payout (CP-20260127-003)
    duplicate_payout = CommissionPayoutHistory.objects.filter(payout_number='CP-20260127-003').first()
    
    if not duplicate_payout:
        print("No duplicate payout found!")
        return
    
    print(f"Found duplicate payout: {duplicate_payout.payout_number}")
    print(f"  Execution Date: {duplicate_payout.execution_date}")
    print(f"  Amount: Rs. {duplicate_payout.total_amount_credited}")
    
    with transaction.atomic():
        # Delete UserCommissionPayout records
        user_payouts = UserCommissionPayout.objects.filter(history=duplicate_payout)
        user_count = user_payouts.count()
        user_payouts.delete()
        print(f"  ✓ Deleted {user_count} UserCommissionPayout record(s)")
        
        # Delete the clearing CommissionTransaction (the second -162.00 one)
        clearing_txn = CommissionTransaction.objects.filter(
            transaction_type='adjustment',
            transaction_date=duplicate_payout.execution_date,
            commission_earned__lt=0,
            notes__contains='CP-20260127-003'
        ).first()
        
        if clearing_txn:
            clearing_txn.delete()
            print(f"  ✓ Deleted clearing CommissionTransaction (-162.00)")
        
        # Delete the payout history record
        duplicate_payout.delete()
        print(f"  ✓ Deleted payout history: {duplicate_payout.payout_number}")
    
    print("\n✅ Duplicate payout removed successfully!\n")
    
    # Verify balance
    from accounts.models import User
    rep = User.objects.get(username='rep')
    balance = CommissionTransaction.get_rep_balance(rep)
    print(f"Current commission balance for {rep.get_full_name()}: Rs. {balance:,.2f}\n")

if __name__ == '__main__':
    fix_duplicate_payouts()
