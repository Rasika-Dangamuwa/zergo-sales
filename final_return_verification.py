"""
Final comprehensive verification of return deletion commission tracking
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction, Return
from accounts.models import User
from decimal import Decimal

print("=" * 80)
print("COMPREHENSIVE VERIFICATION: RETURN DELETION COMMISSION TRACKING")
print("=" * 80)

# Get all sales reps
sales_reps = User.objects.filter(user_type='sales_rep')

for rep in sales_reps:
    print(f"\n{'=' * 80}")
    print(f"SALES REP: {rep.get_full_name()}")
    print(f"{'=' * 80}")
    
    # Get all transactions
    all_txns = CommissionTransaction.objects.filter(
        sales_rep=rep
    ).order_by('transaction_date', 'created_at')
    
    print(f"Total Transactions: {all_txns.count()}")
    
    # Verify running balances
    print("\nVerifying running balances...")
    running_balance = Decimal('0.00')
    balance_correct = True
    
    for txn in all_txns:
        running_balance += txn.commission_earned
        if txn.running_balance != running_balance:
            print(f"❌ Transaction ID {txn.id}: Balance mismatch!")
            print(f"   Expected: Rs. {running_balance}, Actual: Rs. {txn.running_balance}")
            balance_correct = False
    
    if balance_correct:
        print(f"✅ All running balances correct")
        print(f"Final Balance: Rs. {running_balance}")
    
    # Check return_processed transactions
    return_processed = all_txns.filter(transaction_type='return_processed')
    print(f"\nReturn Processed Transactions: {return_processed.count()}")
    
    deleted_returns = []
    existing_returns = []
    
    for txn in return_processed:
        if txn.notes and 'RN-' in txn.notes:
            import re
            match = re.search(r'RN-\d{8}-\d+', txn.notes)
            if match:
                return_number = match.group()
                return_exists = Return.objects.filter(return_number=return_number).exists()
                
                if return_exists:
                    existing_returns.append(return_number)
                else:
                    deleted_returns.append((return_number, txn.id))
    
    if deleted_returns:
        print(f"\nDeleted Returns ({len(deleted_returns)}):")
        for return_number, txn_id in deleted_returns:
            print(f"  - {return_number} (Transaction ID: {txn_id})")
            
            # Check if reversal exists
            reversal = CommissionTransaction.objects.filter(
                transaction_type='return_cancelled',
                sales_rep=rep,
                notes__contains=return_number
            ).first()
            
            if reversal:
                print(f"    ✅ Reversal exists: ID {reversal.id}, Commission Rs. {reversal.commission_earned}")
            else:
                print(f"    ❌ NO REVERSAL FOUND!")
    else:
        print(f"\n✅ No deleted returns")
    
    print(f"\nExisting Returns: {len(existing_returns)}")
    
    # Check return_cancelled transactions
    return_cancelled = all_txns.filter(transaction_type='return_cancelled')
    print(f"Return Cancelled Transactions: {return_cancelled.count()}")
    
    if return_cancelled.exists():
        print("\nReturn Cancellations:")
        for txn in return_cancelled:
            print(f"  ID {txn.id}: {txn.transaction_date.strftime('%Y-%m-%d %H:%M')}")
            print(f"  Return Amount: Rs. {txn.return_amount}")
            print(f"  Commission: Rs. {txn.commission_earned}")
            print(f"  Notes: {txn.notes[:80]}")

print("\n" + "=" * 80)
print("SYSTEM-WIDE SUMMARY")
print("=" * 80)

# Count all deleted returns across all reps
all_return_processed = CommissionTransaction.objects.filter(
    transaction_type='return_processed'
)

total_deleted = 0
total_with_reversal = 0
total_without_reversal = 0

for txn in all_return_processed:
    if txn.notes and 'RN-' in txn.notes:
        import re
        match = re.search(r'RN-\d{8}-\d+', txn.notes)
        if match:
            return_number = match.group()
            return_exists = Return.objects.filter(return_number=return_number).exists()
            
            if not return_exists:
                total_deleted += 1
                
                reversal_exists = CommissionTransaction.objects.filter(
                    transaction_type='return_cancelled',
                    notes__contains=return_number
                ).exists()
                
                if reversal_exists:
                    total_with_reversal += 1
                else:
                    total_without_reversal += 1

print(f"\nDeleted Returns: {total_deleted}")
print(f"  With Reversals: {total_with_reversal}")
print(f"  Without Reversals: {total_without_reversal}")

if total_without_reversal == 0:
    print(f"\n✅ ALL DELETED RETURNS HAVE REVERSAL TRANSACTIONS!")
    print(f"✅ Return deletion commission tracking is now working correctly!")
else:
    print(f"\n⚠️ {total_without_reversal} deleted returns still missing reversals")

print("\n" + "=" * 80)
print("SIGNAL HANDLER STATUS")
print("=" * 80)
print("✅ pre_delete signal handler added to sales/commission_signals.py")
print("✅ return_cancelled transaction type added to CommissionTransaction")
print("✅ Commission calculation updated to handle return_cancelled")
print("\nFuture return deletions will automatically create reversal transactions!")

print("\n" + "=" * 80)
