"""
Create cash receipt transactions for existing settled returns
This fixes the balance to be 0 when all returns are settled via cash refund
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import (
    PurchaseReturn, PurchaseReturnSettlement, CompanyTransaction, CompanyAccount
)
from decimal import Decimal as D
from django.utils import timezone

print("=" * 120)
print("CREATE CASH RECEIPT TRANSACTIONS FOR EXISTING SETTLED RETURNS")
print("=" * 120)

# Find all cash refund settlements that don't have corresponding cash receipt transactions
cash_refund_settlements = PurchaseReturnSettlement.objects.filter(
    settlement_method='refund'
).select_related('purchase_return', 'purchase_return__company', 'created_by')

print(f"\nFound {cash_refund_settlements.count()} cash refund settlements")

created_count = 0
total_amount = D('0.00')

for settlement in cash_refund_settlements:
    pr = settlement.purchase_return
    
    # Check if cash receipt transaction already exists
    existing_txn = CompanyTransaction.objects.filter(
        purchase_return=pr,
        transaction_type='settlement',
        reference_number__icontains='REFUND'
    ).exists()
    
    if existing_txn:
        print(f"\n⏭️  {pr.pr_number}: Cash receipt transaction already exists, skipping")
        continue
    
    print(f"\n📝 {pr.pr_number}: Creating cash receipt transaction")
    print(f"   Settlement Amount: Rs. {settlement.settlement_amount:,.2f}")
    
    # Get or create company account
    account, acc_created = CompanyAccount.objects.get_or_create(
        company=pr.company,
        defaults={
            'opening_balance': D('0'),
            'opening_date': timezone.now().date(),
            'created_by': settlement.created_by or pr.created_by
        }
    )
    
    if acc_created:
        print(f"   ✅ Created company account for {pr.company.company_name}")
    
    # Create cash receipt transaction
    txn_date = settlement.cash_received_date or pr.return_date
    txn = CompanyTransaction.objects.create(
        company_account=account,
        transaction_type='settlement',
        transaction_date=txn_date,
        reference_number=f'{pr.pr_number}-REFUND',
        amount=settlement.settlement_amount,  # POSITIVE - we received cash
        settlement_method='refund',
        purchase_return=pr,
        description=f'Cash refund received for {pr.pr_number}',
        created_by=settlement.created_by or pr.created_by
    )
    
    print(f"   ✅ Created transaction: {txn.reference_number}")
    print(f"   Amount: +Rs. {txn.amount:,.2f} (cash received)")
    
    created_count += 1
    total_amount += settlement.settlement_amount

print("\n" + "=" * 120)
print("SUMMARY")
print("=" * 120)
print(f"\n✅ Created {created_count} cash receipt transactions")
print(f"💰 Total Cash Receipts: Rs. {total_amount:,.2f}")

if created_count > 0:
    print("\n🔄 Updating all company account balances...")
    for account in CompanyAccount.objects.all():
        old_balance = account.current_balance
        account.update_balance()
        new_balance = account.current_balance
        
        if old_balance != new_balance:
            print(f"   {account.company.company_name}:")
            print(f"      Old Balance: Rs. {old_balance:,.2f}")
            print(f"      New Balance: Rs. {new_balance:,.2f}")
            print(f"      Change: Rs. {new_balance - old_balance:+,.2f}")

print("\n" + "=" * 120)
print("FINAL VERIFICATION")
print("=" * 120)

for account in CompanyAccount.objects.all():
    print(f"\n{account.company.company_name}:")
    print(f"  Current Balance: Rs. {account.current_balance:,.2f}")
    
    if abs(account.current_balance) < D('0.01'):
        print(f"  Status: ✅ SETTLED (balance = 0)")
    elif account.current_balance < 0:
        print(f"  Status: ⚠️  RECEIVABLE - They owe us Rs. {abs(account.current_balance):,.2f}")
    else:
        print(f"  Status: ⚠️  PAYABLE - We owe them Rs. {account.current_balance:,.2f}")
    
    # Check for unsettled returns
    unsettled = PurchaseReturn.objects.filter(
        company=account.company,
        settlement_status='pending'
    )
    
    if unsettled.exists():
        total_unsettled = sum(pr.total_amount for pr in unsettled)
        print(f"  Unsettled Returns: {unsettled.count()} (Rs. {total_unsettled:,.2f})")
    else:
        print(f"  Unsettled Returns: None")

print("\n" + "=" * 120)
print("DONE! 🎉")
print("=" * 120)
