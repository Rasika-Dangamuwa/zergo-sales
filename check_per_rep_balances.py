"""
Check if the balance mismatch is due to mixing transactions from different sales reps
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 80)
print("SALES REP COMMISSION BALANCE ANALYSIS")
print("=" * 80)
print()

# Get all sales reps with transactions
sales_reps = User.objects.filter(
    commission_transactions__transaction_date__gte='2026-01-25'
).distinct()

for rep in sales_reps:
    print(f"\nSALES REP: {rep.username} ({rep.get_full_name()})")
    print("=" * 80)
    
    transactions = CommissionTransaction.objects.filter(
        sales_rep=rep,
        transaction_date__gte='2026-01-25'
    ).order_by('transaction_date', 'id')
    
    print(f"Total transactions: {transactions.count()}")
    print()
    
    prev_balance = None
    errors = []
    
    for txn in transactions:
        expected = prev_balance + txn.commission_earned if prev_balance is not None else txn.running_balance
        actual = txn.running_balance
        status = "✓" if prev_balance is None or abs(expected - actual) < 0.01 else "❌"
        
        if status == "❌":
            errors.append({
                'id': txn.id,
                'date': txn.transaction_date,
                'type': txn.transaction_type,
                'expected': expected,
                'actual': actual,
                'diff': actual - expected
            })
        
        print(f"{status} {txn.transaction_date.strftime('%H:%M:%S')} | "
              f"{txn.transaction_type:20s} | "
              f"Comm: {str(txn.commission_earned):>7s} | "
              f"Bal: {str(actual):>8s}", end="")
        
        if status == "❌":
            print(f" | Expected: {expected} | Diff: {actual - expected}")
        else:
            print()
        
        prev_balance = actual
    
    if errors:
        print(f"\n⚠️  Found {len(errors)} balance mismatches for {rep.username}:")
        for err in errors:
            print(f"  Transaction {err['id']} at {err['date']}: {err['type']}")
            print(f"    Expected: {err['expected']}, Actual: {err['actual']}, Diff: {err['diff']}")
    else:
        print(f"\n✓ All balances correct for {rep.username}")
    
    print()
