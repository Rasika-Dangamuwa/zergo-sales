"""
Fix FOC Transaction FOC-20260127-003
Archive FOC transactions for cancelled returns and recalculate balances
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import FOCValueAccount, FOCValueTransaction
from sales.models import Return
from django.utils import timezone
from django.db.models import Q

def fix_cancelled_return_foc_transactions():
    """Archive FOC transactions for cancelled returns"""
    print("\n" + "="*80)
    print("FIXING FOC TRANSACTIONS FOR CANCELLED RETURNS")
    print("="*80 + "\n")
    
    # Find all cancelled returns
    cancelled_returns = Return.objects.filter(settlement_status='cancelled')
    
    print(f"Found {cancelled_returns.count()} cancelled returns\n")
    
    fixed_count = 0
    
    for ret in cancelled_returns:
        # Find active FOC transactions for this return
        foc_txns = FOCValueTransaction.objects.filter(
            return_item__return_ref=ret,
            is_archived=False
        )
        
        if foc_txns.exists():
            print(f"📦 Return: {ret.return_number}")
            print(f"   Found {foc_txns.count()} active FOC transactions:")
            
            for txn in foc_txns:
                print(f"   • {txn.transaction_number} ({txn.transaction_type}): Rs. {txn.foc_value:,.2f}")
                
                # Archive the transaction
                txn.is_archived = True
                txn.notes = f"{txn.notes or ''}\\n[AUTO-CANCELLED] Return {ret.return_number} was cancelled on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                txn.save()
                
                fixed_count += 1
                print(f"      ✅ Archived")
                
                # Update account balance
                if hasattr(txn, 'foc_account') and txn.foc_account:
                    txn.foc_account.update_balance()
                    print(f"      ✅ Updated account balance for {txn.foc_account.company.company_name}")
            
            print()
    
    print(f"\n✅ Fixed {fixed_count} FOC transactions")
    return fixed_count


def verify_fix():
    """Verify the fix worked"""
    print("\n" + "="*80)
    print("VERIFYING FIX")
    print("="*80 + "\n")
    
    # Check FOC-20260127-003 specifically
    try:
        txn = FOCValueTransaction.objects.get(transaction_number='FOC-20260127-003')
        print(f"📊 FOC-20260127-003:")
        print(f"   Is Archived: {'✅ Yes' if txn.is_archived else '❌ No (Still Active)'}")
        
        if txn.return_item:
            ret = txn.return_item.return_ref
            print(f"   Return: {ret.return_number} (Status: {ret.settlement_status})")
        
        if txn.foc_account:
            account = txn.foc_account
            print(f"\n   Account: {account.company.company_name}")
            print(f"   FOC Received: Rs. {account.total_foc_received_value:,.2f}")
            print(f"   FOC Given: Rs. {account.total_foc_given_value:,.2f}")
            print(f"   Net FOC: Rs. {account.net_foc_value:,.2f}")
    
    except FOCValueTransaction.DoesNotExist:
        print("❌ FOC-20260127-003 not found")
    
    # Check for any remaining active FOC transactions on cancelled returns
    print("\n" + "-"*80)
    print("Checking for remaining issues...")
    print("-"*80 + "\n")
    
    cancelled_returns = Return.objects.filter(settlement_status='cancelled')
    active_foc_count = 0
    
    for ret in cancelled_returns:
        foc_txns = FOCValueTransaction.objects.filter(
            return_item__return_ref=ret,
            is_archived=False
        )
        
        if foc_txns.exists():
            active_foc_count += foc_txns.count()
            print(f"⚠️  Return {ret.return_number} still has {foc_txns.count()} active FOC transactions")
    
    if active_foc_count == 0:
        print("✅ No active FOC transactions found on cancelled returns")
    else:
        print(f"\n❌ Found {active_foc_count} active FOC transactions on cancelled returns")


if __name__ == '__main__':
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  FOC TRANSACTION CANCELLATION FIX".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    fixed_count = fix_cancelled_return_foc_transactions()
    verify_fix()
    
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  FIX COMPLETE".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80 + "\n")
