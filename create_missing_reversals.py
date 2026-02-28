"""
Create missing reversal transactions for cancelled settlements

This will fix:
- SET-20260125-020 (missing reversal)
- SET-20260125-028 (missing reversal)
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from payments.models import SalesAccountSettlement
from django.utils import timezone
from decimal import Decimal

print("=" * 80)
print("CREATING MISSING REVERSAL TRANSACTIONS")
print("=" * 80)
print()

# List of settlements missing reversals
missing_reversals = [
    'SET-20260125-020',
    'SET-20260125-028'
]

created_count = 0

for settlement_number in missing_reversals:
    settlement = SalesAccountSettlement.objects.get(settlement_number=settlement_number)
    
    print(f"Processing: {settlement_number}")
    print(f"  Status: {settlement.settlement_status}")
    print(f"  Amount: Rs. {settlement.amount}")
    
    # Get the original payment_received transaction
    original_txn = CommissionTransaction.objects.filter(
        settlement=settlement,
        transaction_type='payment_received'
    ).first()
    
    if not original_txn:
        print(f"  ❌ ERROR: No payment_received transaction found!")
        print()
        continue
    
    print(f"  Original transaction ID: {original_txn.id}")
    print(f"    Date: {original_txn.transaction_date}")
    print(f"    Sales Rep: {original_txn.sales_rep.username}")
    print(f"    Commission: {original_txn.commission_earned}")
    
    # Calculate new running balance
    # Get the latest transaction for this sales rep
    latest_txn = CommissionTransaction.objects.filter(
        sales_rep=original_txn.sales_rep
    ).order_by('-transaction_date', '-id').first()
    
    new_balance = latest_txn.running_balance - original_txn.commission_earned
    
    print(f"  Creating reversal transaction...")
    print(f"    Reversal amount: {-original_txn.collected_amount}")
    print(f"    Reversal commission: {-original_txn.commission_earned}")
    print(f"    New balance: {new_balance}")
    
    # Create the reversal transaction
    reversal = CommissionTransaction(
        sales_rep=original_txn.sales_rep,
        bill=settlement.bill,
        settlement=settlement,
        transaction_type='payment_cancelled',
        transaction_date=settlement.updated_at,  # Use settlement's updated time
        collected_amount=-original_txn.collected_amount,
        commission_earned=-original_txn.commission_earned,
        running_balance=new_balance,
        notes=f"Reversal for cancelled settlement {settlement_number}"
    )
    
    reversal.save()
    created_count += 1
    
    print(f"  ✓ Created reversal transaction ID: {reversal.id}")
    print()

print("=" * 80)
print(f"SUMMARY: Created {created_count} reversal transactions")
print("=" * 80)
print()
print("These reversals restore the commission balance integrity.")
print("The cancelled settlements will now properly show in the commission dashboard.")
