"""
Sync Company Account Balances
Recalculates current_balance for all company accounts based on transactions
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import CompanyAccount
from decimal import Decimal


def main():
    print("=" * 80)
    print("SYNCING COMPANY ACCOUNT BALANCES")
    print("=" * 80)
    print()
    
    accounts = CompanyAccount.objects.all()
    
    print(f"Found {accounts.count()} company accounts\n")
    
    for account in accounts:
        print(f"Company: {account.company.company_name}")
        print(f"  Opening Balance: Rs. {account.opening_balance:,.2f}")
        print(f"  Current Balance (BEFORE): Rs. {account.current_balance:,.2f}")
        
        # Count transactions
        txn_count = account.transactions.count()
        print(f"  Transactions: {txn_count}")
        
        # Recalculate balance
        old_balance = account.current_balance
        account.update_balance()
        account.refresh_from_db()
        new_balance = account.current_balance
        
        print(f"  Current Balance (AFTER): Rs. {new_balance:,.2f}")
        
        # Show change
        change = new_balance - old_balance
        if change != 0:
            print(f"  ⚠️  CORRECTED: Rs. {change:,.2f}")
        else:
            print(f"  ✅ Already Correct")
        
        print()
    
    print("=" * 80)
    print("SYNC COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
