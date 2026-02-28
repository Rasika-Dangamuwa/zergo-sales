"""
Clear all money account records - transactions, advance requests, and accounts
WARNING: This will delete ALL money account data!
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from accounts.money_account_models import UserMoneyAccount, MoneyTransaction, AdvanceRequest

def clear_all_money_accounts():
    """Delete all money account data"""
    
    print(f"\n{'='*80}")
    print("WARNING: This will delete ALL money account data!")
    print(f"{'='*80}\n")
    
    # Count existing records
    txn_count = MoneyTransaction.objects.count()
    adv_count = AdvanceRequest.objects.count()
    acc_count = UserMoneyAccount.objects.count()
    
    print(f"Records to be deleted:")
    print(f"  - {txn_count} Money Transactions")
    print(f"  - {adv_count} Advance Requests")
    print(f"  - {acc_count} User Money Accounts")
    
    if txn_count == 0 and adv_count == 0 and acc_count == 0:
        print("\n✅ No records to delete. All tables are already empty.")
        return
    
    print(f"\n{'='*80}")
    
    # Delete in order (transactions first, then requests, then accounts)
    print("Deleting Money Transactions...")
    MoneyTransaction.objects.all().delete()
    print(f"✅ Deleted {txn_count} transactions")
    
    print("Deleting Advance Requests...")
    AdvanceRequest.objects.all().delete()
    print(f"✅ Deleted {adv_count} advance requests")
    
    print("Deleting User Money Accounts...")
    UserMoneyAccount.objects.all().delete()
    print(f"✅ Deleted {acc_count} money accounts")
    
    print(f"\n{'='*80}")
    print("✅ All money account records cleared successfully!")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    clear_all_money_accounts()
