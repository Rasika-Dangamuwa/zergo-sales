"""
Deep dive into the return_processed transactions causing balance jumps
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from django.utils import timezone

print("=" * 80)
print("RETURN_PROCESSED TRANSACTIONS ANALYSIS")
print("=" * 80)
print()

# Get all return_processed transactions from Jan 25-26
transactions = CommissionTransaction.objects.filter(
    transaction_type='return_processed',
    transaction_date__gte='2026-01-25'
).order_by('transaction_date')

print(f"Found {transactions.count()} return_processed transactions")
print()

for txn in transactions:
    print(f"Transaction ID: {txn.id}")
    print(f"Date: {txn.transaction_date}")
    print(f"Sales Rep: {txn.sales_rep.username if txn.sales_rep else 'None'}")
    print(f"Bill: {txn.bill.bill_number if txn.bill else 'None'}")
    print(f"Settlement: {txn.settlement.settlement_number if txn.settlement else 'None'}")
    print(f"Collected Amount: {txn.collected_amount}")
    print(f"Commission Earned: {txn.commission_earned}")
    print(f"Running Balance: {txn.running_balance}")
    print(f"Notes: {txn.notes[:100] if txn.notes else 'None'}")
    print()
    
    # Check what the running balance should be based on previous transaction
    prev_txn = CommissionTransaction.objects.filter(
        sales_rep=txn.sales_rep,
        transaction_date__lt=txn.transaction_date
    ).order_by('-transaction_date', '-id').first()
    
    if prev_txn:
        expected_balance = prev_txn.running_balance + txn.commission_earned
        print(f"  Previous balance: {prev_txn.running_balance}")
        print(f"  Expected new balance: {expected_balance}")
        print(f"  Actual new balance: {txn.running_balance}")
        
        if abs(expected_balance - txn.running_balance) > 0.01:
            print(f"  ❌ MISMATCH: Difference of {txn.running_balance - expected_balance}")
        else:
            print(f"  ✓ Correct")
    
    print("-" * 80)
    print()

# Check if there are concurrent transactions (same timestamp)
print("=" * 80)
print("CHECKING FOR CONCURRENT TRANSACTIONS")
print("=" * 80)
print()

from django.db.models import Count
duplicates = CommissionTransaction.objects.filter(
    transaction_date__gte='2026-01-25'
).values('transaction_date', 'sales_rep').annotate(
    count=Count('id')
).filter(count__gt=1)

if duplicates.exists():
    print(f"Found {duplicates.count()} timestamps with multiple transactions")
    for dup in duplicates:
        print(f"\n{dup['transaction_date']}: {dup['count']} transactions")
        txns = CommissionTransaction.objects.filter(
            transaction_date=dup['transaction_date'],
            sales_rep=dup['sales_rep']
        ).order_by('id')
        for t in txns:
            print(f"  ID {t.id}: {t.transaction_type}, Balance: {t.running_balance}")
else:
    print("No concurrent transactions found")
