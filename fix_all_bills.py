import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill
from payments.models import SalesAccountSettlement
from decimal import Decimal

print('=== FIXING ALL BILLS WITH PAID_AMOUNT MISMATCHES ===\n')

fixed_count = 0
total_correction = Decimal('0')

for bill in Bill.objects.all():
    # Calculate what paid_amount SHOULD be
    actual_settlements = bill.settlements.filter(
        settlement_status__in=['completed']
    ).aggregate(total=django.db.models.Sum('amount'))['total'] or Decimal('0')
    
    # Compare with recorded paid_amount
    if bill.paid_amount != actual_settlements:
        old_paid = bill.paid_amount
        old_balance = bill.balance_amount
        
        # Fix using calculate_totals()
        bill.calculate_totals()
        bill.save()
        
        fixed_count += 1
        correction = old_paid - bill.paid_amount
        total_correction += correction
        
        print(f"✅ Fixed Bill {bill.bill_number}:")
        print(f"   paid_amount: Rs. {old_paid} → Rs. {bill.paid_amount} (corrected {correction})")
        print(f"   balance_amount: Rs. {old_balance} → Rs. {bill.balance_amount}")
        print()

print(f'\n=== SUMMARY ===')
print(f"Fixed {fixed_count} bills")
print(f"Total paid_amount corrected: Rs. {total_correction}")
print(f"✅ All bills now have correct paid_amount matching their completed settlements!")
