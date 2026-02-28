"""
Fix all money account balances after correcting the balance calculation logic
Run this script to recalculate all user account balances
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from accounts.money_account_models import UserMoneyAccount

def fix_all_balances():
    """Recalculate all account balances"""
    accounts = UserMoneyAccount.objects.all()
    
    print(f"\n{'='*80}")
    print(f"Recalculating balances for {accounts.count()} accounts...")
    print(f"{'='*80}\n")
    
    for account in accounts:
        print(f"User: {account.user.get_full_name()}")
        print(f"  Old Balance: Rs. {account.current_balance:,.2f}")
        print(f"  Old Outstanding Advance: Rs. {account.outstanding_advance:,.2f}")
        
        # Recalculate
        account.update_balance()
        account.refresh_from_db()
        
        print(f"  New Balance: Rs. {account.current_balance:,.2f}")
        print(f"  New Outstanding Advance: Rs. {account.outstanding_advance:,.2f}")
        print(f"  Credits: Rs. {account.total_credited:,.2f}")
        print(f"  Debits: Rs. {account.total_debited:,.2f}")
        print(f"  Advances Given: Rs. {account.total_advance_given:,.2f}")
        print(f"  Advances Recovered: Rs. {account.total_advance_recovered:,.2f}")
        print()
    
    print(f"{'='*80}")
    print("✅ All balances recalculated successfully!")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    fix_all_balances()
