"""
Check current commission balance and money account status
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from accounts.models import User
from accounts.money_account_models import UserMoneyAccount
from decimal import Decimal

def check_current_status():
    """Check commission balance and money account for sales rep"""
    
    print("\n=== Current Account Status ===\n")
    
    rep = User.objects.get(username='rep')
    
    # Commission Balance (what's earned but not paid)
    commission_balance = CommissionTransaction.get_rep_balance(rep)
    print(f"Sales Representative: {rep.get_full_name()}")
    print(f"\n1. COMMISSION BALANCE (Earned but not disbursed):")
    print(f"   Rs. {commission_balance:,.2f}")
    
    # Money Account Balance (what's been disbursed)
    try:
        money_account = UserMoneyAccount.objects.get(user=rep)
        print(f"\n2. MONEY ACCOUNT BALANCE (Already disbursed):")
        print(f"   Current Balance: Rs. {money_account.current_balance:,.2f}")
        print(f"   Total Earned: Rs. {money_account.total_credited:,.2f}")
        print(f"   Total Disbursed: Rs. {money_account.total_debited:,.2f}")
        print(f"   Advances Given: Rs. {money_account.total_advance_given:,.2f}")
    except UserMoneyAccount.DoesNotExist:
        print(f"\n2. MONEY ACCOUNT: Not created yet")
    
    print(f"\n3. ADVANCE REQUEST RULES:")
    print(f"   ✓ Maximum advance allowed: Rs. {commission_balance:,.2f}")
    print(f"   ✗ Cannot advance: Rs. 5,000.00 (exceeds balance)")
    
    print(f"\n4. TO REQUEST Rs. 5,000 ADVANCE:")
    print(f"   - Need to earn: Rs. {max(Decimal('5000') - commission_balance, Decimal('0')):,.2f} more in commission")
    print(f"   - OR request smaller advance: Up to Rs. {commission_balance:,.2f}")
    
    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    check_current_status()
