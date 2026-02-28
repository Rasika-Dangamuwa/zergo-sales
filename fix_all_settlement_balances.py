import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill
from decimal import Decimal

print('=== FINDING ALL BILLS WITH SETTLEMENT MISMATCHES ===\n')

affected_bills = []

for bill in Bill.objects.all():
    # Calculate expected paid amount
    expected_paid = bill.settlements.filter(
        settlement_status='completed'
    ).aggregate(total=django.db.models.Sum('amount'))['total'] or Decimal('0')
    
    # Check if there's a mismatch
    if bill.paid_amount != expected_paid:
        affected_bills.append({
            'bill': bill,
            'expected': expected_paid,
            'actual': bill.paid_amount,
            'difference': bill.paid_amount - expected_paid
        })

print(f'Found {len(affected_bills)} bills with mismatches\n')

if affected_bills:
    print('=== AFFECTED BILLS ===')
    for item in affected_bills:
        bill = item['bill']
        print(f"Bill {bill.bill_number}:")
        print(f"  Total: Rs. {bill.total_amount}")
        print(f"  Current paid_amount: Rs. {item['actual']}")
        print(f"  Expected paid_amount: Rs. {item['expected']}")
        print(f"  Difference: Rs. {item['difference']}")
        print(f"  Current status: {bill.settlement_status}")
        print()
    
    # Fix all
    print(f'\n=== FIXING ALL {len(affected_bills)} BILLS ===\n')
    for item in affected_bills:
        bill = item['bill']
        expected = item['expected']
        
        bill.paid_amount = expected
        bill.balance_amount = bill.total_amount - expected
        
        if bill.paid_amount == 0:
            bill.settlement_status = 'unsettled'
        elif bill.paid_amount >= bill.total_amount:
            bill.settlement_status = 'settled'
        else:
            bill.settlement_status = 'partial_settled'
        
        bill.save(update_fields=['paid_amount', 'balance_amount', 'settlement_status'])
        
        print(f"✅ Fixed {bill.bill_number}: paid={bill.paid_amount}, balance={bill.balance_amount}, status={bill.settlement_status}")
    
    print(f'\n✅ ALL {len(affected_bills)} BILLS FIXED!')
else:
    print('✅ All bills have correct paid_amount!')

print('\n⚠️  CRITICAL: RESTART THE DJANGO SERVER NOW!')
print('The server is running old code without calculate_payment_totals() method')
