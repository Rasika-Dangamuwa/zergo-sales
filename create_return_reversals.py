"""
Create reversal commission transactions for deleted returns
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from django.utils import timezone
from decimal import Decimal
from django.db import transaction

print("=" * 80)
print("CREATING REVERSAL TRANSACTIONS FOR DELETED RETURNS")
print("=" * 80)

# Find return_processed transactions with deleted returns
deleted_returns_data = [
    {
        'txn_id': 68,
        'return_number': 'RN-20260125-004',
        'return_amount': Decimal('90.00'),
        'commission': Decimal('-4.50')
    },
    {
        'txn_id': 59,
        'return_number': 'RN-20260125-002',  # First one for Rasika
        'return_amount': Decimal('900.00'),
        'commission': Decimal('-45.00')
    },
    {
        'txn_id': 51,
        'return_number': 'RN-20260125-002',  # Second one for Sales Rep
        'return_amount': Decimal('90.00'),
        'commission': Decimal('-4.50')
    }
]

for data in deleted_returns_data:
    print(f"\n{'-' * 80}")
    print(f"Processing Return: {data['return_number']} (Transaction ID: {data['txn_id']})")
    print(f"Original Commission: Rs. {data['commission']}")
    
    # Get the original transaction
    original_txn = CommissionTransaction.objects.get(id=data['txn_id'])
    
    print(f"Sales Rep: {original_txn.sales_rep.get_full_name()}")
    print(f"Transaction Date: {original_txn.transaction_date}")
    print(f"Running Balance Before: Rs. {original_txn.running_balance}")
    
    # Check if reversal already exists
    reversal_exists = CommissionTransaction.objects.filter(
        transaction_type='return_cancelled',
        sales_rep=original_txn.sales_rep,
        return_amount=-data['return_amount'],
        notes__contains=data['return_number']
    ).exists()
    
    if reversal_exists:
        print(f"⚠️ Reversal already exists for {data['return_number']}")
        continue
    
    try:
        with transaction.atomic():
            # Get current balance
            latest_txn = CommissionTransaction.objects.filter(
                sales_rep=original_txn.sales_rep
            ).order_by('-transaction_date', '-id').select_for_update().first()
            
            current_balance = latest_txn.running_balance if latest_txn else Decimal('0.00')
            
            # Create reversal (positive return_amount to reverse the negative commission)
            reversal = CommissionTransaction.objects.create(
                transaction_type='return_cancelled',
                transaction_date=timezone.now(),
                sales_rep=original_txn.sales_rep,
                bill=original_txn.bill,
                return_amount=-data['return_amount'],  # Opposite sign
                notes=f"REVERSAL: Return {data['return_number']} deleted - Commission restored"
            )
            
            print(f"✅ Created reversal transaction ID: {reversal.id}")
            print(f"Reversal Commission: Rs. {reversal.commission_earned}")
            print(f"New Running Balance: Rs. {reversal.running_balance}")
            
    except Exception as e:
        print(f"❌ Error creating reversal: {e}")

print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

# Verify all return_processed transactions
from sales.models import Return

all_return_processed = CommissionTransaction.objects.filter(
    transaction_type='return_processed'
).order_by('-transaction_date')

print(f"\nTotal return_processed transactions: {all_return_processed.count()}")

orphaned = 0
for txn in all_return_processed:
    if txn.notes and 'RN-' in txn.notes:
        import re
        match = re.search(r'RN-\d{8}-\d+', txn.notes)
        if match:
            return_number = match.group()
            return_exists = Return.objects.filter(return_number=return_number).exists()
            
            if not return_exists:
                # Check if reversal exists
                reversal_exists = CommissionTransaction.objects.filter(
                    transaction_type='return_cancelled',
                    notes__contains=return_number
                ).exists()
                
                if reversal_exists:
                    print(f"✅ {return_number} deleted but has reversal")
                else:
                    print(f"❌ {return_number} deleted WITHOUT reversal")
                    orphaned += 1

if orphaned == 0:
    print(f"\n✅ ALL deleted returns now have reversals!")
else:
    print(f"\n⚠️ {orphaned} deleted returns still missing reversals")

print("\n" + "=" * 80)
