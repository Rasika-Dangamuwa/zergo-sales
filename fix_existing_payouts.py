"""
Fix existing payouts - create missing CommissionTransactions to clear balances
Run this once to fix all historical payouts that didn't clear commission balances
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.commission_schedule_models import CommissionPayoutHistory, UserCommissionPayout
from sales.models import CommissionTransaction
from django.db import transaction
from decimal import Decimal

def fix_existing_payouts():
    """Create missing CommissionTransactions for existing payouts"""
    
    print("\n=== Fixing Existing Payouts ===\n")
    
    # Get all successful payouts
    payouts = CommissionPayoutHistory.objects.filter(
        status='success'
    ).order_by('execution_date')
    
    total_fixed = 0
    
    for payout in payouts:
        print(f"\nProcessing: {payout.payout_number}")
        print(f"  Execution Date: {payout.execution_date}")
        print(f"  Total Amount: Rs. {payout.total_amount_credited:,.2f}")
        print(f"  Users: {payout.total_users_processed}")
        
        # Get user payouts
        user_payouts = UserCommissionPayout.objects.filter(
            history=payout,
            status='success'
        )
        
        fixed_count = 0
        
        for user_payout in user_payouts:
            # Check if CommissionTransaction already exists for this payout
            existing_txn = CommissionTransaction.objects.filter(
                sales_rep=user_payout.user,
                transaction_type='adjustment',
                commission_earned=-user_payout.amount_credited,
                transaction_date=payout.execution_date
            ).first()
            
            if existing_txn:
                print(f"    ✓ {user_payout.user.get_full_name()}: Already has clearing transaction")
                continue
            
            # Create the missing CommissionTransaction
            with transaction.atomic():
                CommissionTransaction.objects.create(
                    transaction_type='adjustment',
                    transaction_date=payout.execution_date,
                    sales_rep=user_payout.user,
                    applicable_rate=Decimal('0.00'),
                    commission_earned=-user_payout.amount_credited,  # NEGATIVE to clear
                    notes=f'Commission cleared - {payout.payout_number} (Retroactive fix)',
                    bill=None,
                    settlement=None,
                    return_ref=None
                )
            
            print(f"    ✓ {user_payout.user.get_full_name()}: Created clearing transaction (Rs. {user_payout.amount_credited:,.2f})")
            fixed_count += 1
        
        if fixed_count > 0:
            print(f"  → Fixed {fixed_count} user(s)")
            total_fixed += fixed_count
        else:
            print(f"  → No fixes needed")
    
    print(f"\n{'='*60}")
    print(f"✅ Total user payouts fixed: {total_fixed}")
    print(f"{'='*60}\n")
    
    # Verify balances are now correct
    print("\n=== Verifying Commission Balances ===\n")
    
    from accounts.models import User
    sales_reps = User.objects.filter(user_type='sales_rep', is_active=True)
    
    for rep in sales_reps:
        balance = CommissionTransaction.get_rep_balance(rep)
        if balance != 0:
            print(f"⚠️  {rep.get_full_name()}: Rs. {balance:,.2f} (non-zero balance)")
        else:
            print(f"✓  {rep.get_full_name()}: Rs. 0.00")
    
    print("\n✅ Fix complete!\n")

if __name__ == '__main__':
    fix_existing_payouts()
