import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill
from payments.models import SalesAccountSettlement
from decimal import Decimal

# Get the bill
bill = Bill.objects.get(bill_number='BILL20260126022')
print(f'=== BILL {bill.bill_number} ===')
print(f'Total: Rs. {bill.total_amount}')
print(f'Paid: Rs. {bill.paid_amount}')
print(f'Balance: Rs. {bill.balance_amount}')
print(f'Status: {bill.settlement_status}')
print(f'Created: {bill.created_at}')

print(f'\n=== SETTLEMENTS ===')
settlements = bill.settlements.all().order_by('created_at')
for s in settlements:
    print(f'{s.settlement_number}:')
    print(f'  Status: {s.settlement_status}')
    print(f'  Amount: Rs. {s.amount}')
    print(f'  Created: {s.created_at}')

# Calculate what the paid amount SHOULD be
completed_settlements = bill.settlements.filter(settlement_status='completed')
expected_paid = sum(s.amount for s in completed_settlements)
print(f'\n=== VERIFICATION ===')
print(f'Expected paid_amount: Rs. {expected_paid}')
print(f'Actual paid_amount: Rs. {bill.paid_amount}')
print(f'Expected balance: Rs. {bill.total_amount - expected_paid}')
print(f'Actual balance: Rs. {bill.balance_amount}')

if bill.paid_amount != expected_paid:
    print(f'\n❌ MISMATCH DETECTED!')
    print(f'Difference: Rs. {bill.paid_amount - expected_paid}')
    
    # Check if calculate_payment_totals exists
    if hasattr(bill, 'calculate_payment_totals'):
        print(f'\n✅ calculate_payment_totals() method exists')
        print(f'Fixing bill...')
        bill.calculate_payment_totals()
        print(f'AFTER FIX:')
        print(f'  paid_amount: Rs. {bill.paid_amount}')
        print(f'  balance: Rs. {bill.balance_amount}')
        print(f'  status: {bill.settlement_status}')
    else:
        print(f'\n⚠️  calculate_payment_totals() method NOT FOUND!')
        print(f'Server needs to be restarted to load the new method')
        
        # Manual fix
        print(f'\nApplying manual fix...')
        bill.paid_amount = expected_paid
        bill.balance_amount = bill.total_amount - expected_paid
        
        if bill.paid_amount == 0:
            bill.settlement_status = 'unsettled'
        elif bill.paid_amount >= bill.total_amount:
            bill.settlement_status = 'settled'
        else:
            bill.settlement_status = 'partial_settled'
        
        bill.save(update_fields=['paid_amount', 'balance_amount', 'settlement_status'])
        
        print(f'AFTER MANUAL FIX:')
        print(f'  paid_amount: Rs. {bill.paid_amount}')
        print(f'  balance: Rs. {bill.balance_amount}')
        print(f'  status: {bill.settlement_status}')
else:
    print(f'\n✅ Bill totals are CORRECT!')
