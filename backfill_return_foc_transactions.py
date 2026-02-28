"""
Backfill FOC Transactions for Historical Returns
Creates FOC restoration transactions for returns with FOC that were created before FOC system
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, ReturnItem
from products.models import FOCValueTransaction, FOCValueAccount
from django.utils import timezone
from decimal import Decimal

def backfill_return_foc_transactions():
    """Create FOC transactions for historical returns with FOC"""
    print("\n" + "="*80)
    print("BACKFILLING FOC TRANSACTIONS FOR HISTORICAL RETURNS")
    print("="*80 + "\n")
    
    # Find returns with FOC but no FOC transactions
    all_returns_with_foc = Return.objects.filter(
        items__foc_quantity__gt=0
    ).distinct()
    
    print(f"Total returns with FOC: {all_returns_with_foc.count()}")
    
    missing_foc_returns = []
    
    for ret in all_returns_with_foc:
        # Check if FOC transactions exist
        foc_txns = FOCValueTransaction.objects.filter(
            return_item__return_ref=ret
        )
        
        if not foc_txns.exists():
            missing_foc_returns.append(ret)
    
    print(f"Returns missing FOC transactions: {len(missing_foc_returns)}\n")
    
    if not missing_foc_returns:
        print("✅ All returns with FOC already have FOC transactions!")
        return
    
    created_count = 0
    
    for ret in missing_foc_returns:
        print(f"\n📦 Processing Return: {ret.return_number} (ID: {ret.pk})")
        print(f"   Date: {ret.return_date}")
        print(f"   Shop: {ret.shop.shop_name}")
        print(f"   Status: {ret.settlement_status}")
        
        # Process each item with FOC
        for item in ret.items.filter(foc_quantity__gt=0):
            product = item.product
            
            if not product.company:
                print(f"   ⚠️  Skipping {product.product_name} - No company assigned")
                continue
            
            # Get or create FOC account
            foc_account, created = FOCValueAccount.objects.get_or_create(
                company=product.company,
                defaults={'created_by_id': 1}  # Default to admin user
            )
            
            if created:
                print(f"   ✅ Created FOC account for {product.company.company_name}")
            
            # Create FOC restoration transaction
            txn = FOCValueTransaction.objects.create(
                foc_account=foc_account,
                transaction_type='return_foc_restored',
                transaction_date=ret.return_date,
                product=product,
                foc_quantity=item.foc_quantity,
                shop_price_at_time=product.shop_price,
                reference_number=ret.return_number,
                return_item=item,
                shop=ret.shop,
                notes=f'[BACKFILLED] FOC restored from return by {ret.shop.shop_name}',
                created_by_id=1  # Admin user
            )
            
            print(f"   ✅ Created {txn.transaction_number}: Rs. {txn.foc_value:,.2f}")
            print(f"      Product: {product.product_name}")
            print(f"      FOC Qty: {item.foc_quantity}")
            
            created_count += 1
            
            # Check if return is cancelled - archive transaction
            if ret.settlement_status == 'cancelled':
                txn.is_archived = True
                txn.notes += f"\\n[AUTO-CANCELLED] Return {ret.return_number} was cancelled"
                txn.save()
                print(f"      ⚠️  Return is cancelled - transaction archived")
    
    print(f"\n{'='*80}")
    print(f"✅ Backfill complete: Created {created_count} FOC transactions")
    print(f"{'='*80}")
    
    # Update all FOC account balances
    print(f"\nRecalculating FOC account balances...")
    for account in FOCValueAccount.objects.all():
        account.update_balance()
        print(f"   ✅ Updated {account.company.company_name}")
    
    print(f"\n✅ All FOC account balances updated")


def verify_backfill():
    """Verify the backfill was successful"""
    print("\n" + "="*80)
    print("VERIFICATION: CHECKING ALL RETURNS WITH FOC")
    print("="*80 + "\n")
    
    returns_with_foc = Return.objects.filter(
        items__foc_quantity__gt=0
    ).distinct()
    
    print(f"Total returns with FOC: {returns_with_foc.count()}\n")
    
    missing_count = 0
    
    for ret in returns_with_foc:
        foc_txns = FOCValueTransaction.objects.filter(
            return_item__return_ref=ret
        )
        
        if not foc_txns.exists():
            print(f"❌ Return {ret.return_number} (ID: {ret.pk}) still missing FOC transactions")
            missing_count += 1
    
    if missing_count == 0:
        print("✅ All returns with FOC now have FOC transactions!")
    else:
        print(f"\n⚠️  {missing_count} returns still missing FOC transactions")


if __name__ == '__main__':
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  FOC TRANSACTION BACKFILL FOR HISTORICAL RETURNS".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    backfill_return_foc_transactions()
    verify_backfill()
    
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  BACKFILL COMPLETE".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80 + "\n")
