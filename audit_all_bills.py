import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill
from payments.models import SalesAccountSettlement
from decimal import Decimal

print('=== AUDITING ALL BILLS FOR PAID_AMOUNT MISMATCHES ===\n')

problematic_bills = []
total_bills = Bill.objects.all().count()
checked = 0

for bill in Bill.objects.all():
    checked += 1
    
    # Calculate what paid_amount SHOULD be
    actual_settlements = bill.settlements.filter(
        settlement_status__in=['completed']
    ).aggregate(total=django.db.models.Sum('amount'))['total'] or Decimal('0')
    
    # Compare with recorded paid_amount
    if bill.paid_amount != actual_settlements:
        difference = bill.paid_amount - actual_settlements
        problematic_bills.append({
            'bill': bill,
            'recorded': bill.paid_amount,
            'actual': actual_settlements,
            'difference': difference
        })

print(f'Checked {checked} bills')
print(f'Found {len(problematic_bills)} bills with mismatches\n')

if problematic_bills:
    print('=== PROBLEMATIC BILLS ===')
    for item in problematic_bills:
        bill = item['bill']
        direction = 'over-counted' if item['difference'] > 0 else 'under-counted'
        print(f"Bill {bill.bill_number}:")
        print(f"  Total: Rs. {bill.total_amount}")
        print(f"  Recorded paid_amount: Rs. {item['recorded']}")
        print(f"  Actual settlements: Rs. {item['actual']}")
        print(f"  DIFFERENCE: Rs. {item['difference']} ({direction})")
        print(f"  Current balance: Rs. {bill.balance_amount}")
        print()
    
    # Offer to fix all
    print(f'\n=== TOTAL IMPACT ===')
    total_over = sum(item['difference'] for item in problematic_bills if item['difference'] > 0)
    total_under = sum(abs(item['difference']) for item in problematic_bills if item['difference'] < 0)
    print(f"Total over-counted: Rs. {total_over}")
    print(f"Total under-counted: Rs. {total_under}")
    print(f"Net difference: Rs. {total_over - total_under}")
    
else:
    print('✅ All bills have correct paid_amount!')
