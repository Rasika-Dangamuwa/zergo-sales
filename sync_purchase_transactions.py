"""
Synchronization Script: Create CompanyTransaction records for existing GRNs and Returns
Run this once to backfill transaction history
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Purchase, PurchaseReturn, CompanyAccount, CompanyTransaction
from decimal import Decimal
from django.utils import timezone
from django.db import transaction as db_transaction


def sync_purchase_transactions():
    """Create CompanyTransaction records for all received GRNs"""
    print("=" * 80)
    print("SYNCING PURCHASE (GRN) TRANSACTIONS")
    print("=" * 80)
    
    # Get all received GRNs
    purchases = Purchase.objects.filter(status='received').select_related('company', 'created_by')
    total_count = purchases.count()
    created_count = 0
    skipped_count = 0
    
    print(f"\nFound {total_count} received GRNs to process...\n")
    
    for i, purchase in enumerate(purchases, 1):
        # Check if transaction already exists
        if purchase.account_transactions.exists():
            print(f"[{i}/{total_count}] SKIP - {purchase.grn_number}: Transaction already exists")
            skipped_count += 1
            continue
        
        try:
            with db_transaction.atomic():
                # Get or create company account
                account, created = CompanyAccount.objects.get_or_create(
                    company=purchase.company,
                    defaults={
                        'opening_balance': Decimal('0'),
                        'opening_date': timezone.now().date(),
                        'created_by': purchase.created_by
                    }
                )
                
                # Create transaction
                txn = CompanyTransaction.objects.create(
                    company_account=account,
                    transaction_type='purchase',
                    transaction_date=purchase.grn_date,
                    reference_number=purchase.grn_number,
                    amount=purchase.total_amount,
                    settlement_method='credit',
                    purchase=purchase,
                    description=f'GRN: {purchase.grn_number} - {purchase.company.company_name}',
                    created_by=purchase.created_by
                )
                
                print(f"[{i}/{total_count}] ✓ Created - {purchase.grn_number}: Rs. {purchase.total_amount:,.2f}")
                created_count += 1
                
        except Exception as e:
            print(f"[{i}/{total_count}] ✗ ERROR - {purchase.grn_number}: {str(e)}")
    
    print(f"\n" + "=" * 80)
    print(f"PURCHASE SYNC COMPLETE")
    print(f"Total GRNs: {total_count}")
    print(f"Created: {created_count}")
    print(f"Skipped: {skipped_count}")
    print("=" * 80 + "\n")
    
    return created_count


def sync_return_transactions():
    """Create CompanyTransaction records for all approved purchase returns"""
    print("=" * 80)
    print("SYNCING PURCHASE RETURN TRANSACTIONS")
    print("=" * 80)
    
    # Get all approved returns
    returns = PurchaseReturn.objects.filter(status='approved').select_related('company', 'created_by')
    total_count = returns.count()
    created_count = 0
    skipped_count = 0
    
    print(f"\nFound {total_count} approved returns to process...\n")
    
    for i, purchase_return in enumerate(returns, 1):
        # Check if transaction already exists
        if purchase_return.account_transactions.exists():
            print(f"[{i}/{total_count}] SKIP - {purchase_return.pr_number}: Transaction already exists")
            skipped_count += 1
            continue
        
        try:
            with db_transaction.atomic():
                # Get or create company account
                account, created = CompanyAccount.objects.get_or_create(
                    company=purchase_return.company,
                    defaults={
                        'opening_balance': Decimal('0'),
                        'opening_date': timezone.now().date(),
                        'created_by': purchase_return.created_by
                    }
                )
                
                # Create return transaction (negative amount = reduces what we owe)
                txn = CompanyTransaction.objects.create(
                    company_account=account,
                    transaction_type='return',
                    transaction_date=purchase_return.return_date,
                    reference_number=purchase_return.pr_number,
                    amount=-purchase_return.total_amount,  # Negative = credit
                    settlement_method='credit',
                    purchase_return=purchase_return,
                    description=f'Purchase Return: {purchase_return.pr_number}',
                    created_by=purchase_return.created_by
                )
                
                print(f"[{i}/{total_count}] ✓ Created - {purchase_return.pr_number}: Rs. {purchase_return.total_amount:,.2f} (credit)")
                created_count += 1
                
        except Exception as e:
            print(f"[{i}/{total_count}] ✗ ERROR - {purchase_return.pr_number}: {str(e)}")
    
    print(f"\n" + "=" * 80)
    print(f"RETURN SYNC COMPLETE")
    print(f"Total Returns: {total_count}")
    print(f"Created: {created_count}")
    print(f"Skipped: {skipped_count}")
    print("=" * 80 + "\n")
    
    return created_count


def recalculate_all_balances():
    """Recalculate balances for all company accounts"""
    print("=" * 80)
    print("RECALCULATING COMPANY ACCOUNT BALANCES")
    print("=" * 80 + "\n")
    
    accounts = CompanyAccount.objects.all()
    
    for account in accounts:
        old_balance = account.current_balance
        account.update_balance()
        new_balance = account.current_balance
        
        print(f"{account.company.company_name}")
        print(f"  Old Balance: Rs. {old_balance:,.2f}")
        print(f"  New Balance: Rs. {new_balance:,.2f}")
        print(f"  Change: Rs. {(new_balance - old_balance):,.2f}\n")
    
    print("=" * 80)
    print("BALANCE RECALCULATION COMPLETE")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print(" PURCHASE SYSTEM TRANSACTION SYNCHRONIZATION ")
    print("=" * 80 + "\n")
    print("This script will create CompanyTransaction records for:")
    print("  1. All received GRNs (Purchases)")
    print("  2. All approved Purchase Returns")
    print("  3. Recalculate all company account balances")
    print("\n" + "=" * 80 + "\n")
    
    response = input("Do you want to continue? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("\nOperation cancelled.")
        exit()
    
    print("\n")
    
    # Sync purchases
    purchase_count = sync_purchase_transactions()
    
    # Sync returns
    return_count = sync_return_transactions()
    
    # Recalculate balances
    recalculate_all_balances()
    
    print("\n" + "=" * 80)
    print(" SYNCHRONIZATION COMPLETE ")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  - Purchase transactions created: {purchase_count}")
    print(f"  - Return transactions created: {return_count}")
    print(f"  - Total new transactions: {purchase_count + return_count}")
    print("\nAll company account balances have been recalculated.")
    print("=" * 80 + "\n")
