"""
Fix reversal transactions that have 0 commission
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from decimal import Decimal

# Find all payment_cancelled transactions with 0 commission
broken_reversals = CommissionTransaction.objects.filter(
    transaction_type='payment_cancelled',
    commission_earned=Decimal('0.00')
)

print(f"\nFound {broken_reversals.count()} reversal transactions with 0 commission\n")

fixed_count = 0
for txn in broken_reversals:
    # Recalculate commission
    expected_commission = (txn.collected_amount * txn.applicable_rate) / 100
    
    print(f"Transaction ID: {txn.id}")
    print(f"  Settlement: {txn.settlement.settlement_number if txn.settlement else 'N/A'}")
    print(f"  Collected Amount: {txn.collected_amount}")
    print(f"  Rate: {txn.applicable_rate}%")
    print(f"  Current Commission: {txn.commission_earned}")
    print(f"  Expected Commission: {expected_commission}")
    
    # Update commission
    txn.commission_earned = expected_commission
    
    # Recalculate running balance
    previous_txn = CommissionTransaction.objects.filter(
        sales_rep=txn.sales_rep,
        created_at__lt=txn.created_at
    ).order_by('-created_at').first()
    
    if previous_txn:
        old_balance = txn.running_balance
        new_balance = previous_txn.running_balance + expected_commission
        txn.running_balance = new_balance
        print(f"  Old Balance: {old_balance}")
        print(f"  New Balance: {new_balance}")
    
    txn.save(update_fields=['commission_earned', 'running_balance'])
    
    # Now recalculate all subsequent transactions
    subsequent_txns = CommissionTransaction.objects.filter(
        sales_rep=txn.sales_rep,
        created_at__gt=txn.created_at
    ).order_by('created_at')
    
    current_balance = txn.running_balance
    for sub_txn in subsequent_txns:
        current_balance += sub_txn.commission_earned
        if sub_txn.running_balance != current_balance:
            print(f"  └─ Updating subsequent txn ID {sub_txn.id}: {sub_txn.running_balance} → {current_balance}")
            sub_txn.running_balance = current_balance
            sub_txn.save(update_fields=['running_balance'])
    
    fixed_count += 1
    print(f"  ✅ Fixed!\n")

print(f"📊 Summary: Fixed {fixed_count} reversal transactions")
