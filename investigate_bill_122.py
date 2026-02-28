import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill
from payments.models import SalesAccountSettlement
from decimal import Decimal

# Get Bill #122
bill = Bill.objects.get(pk=122)
print(f'=== BILL #{bill.id} ({bill.bill_number}) ===')
print(f'Total: Rs. {bill.total_amount}')
print(f'Paid: Rs. {bill.paid_amount}')
print(f'Balance: Rs. {bill.balance_amount}')
print(f'Status: {bill.settlement_status}')

print(f'\n=== ALL SETTLEMENTS (chronological) ===')
for s in bill.settlements.all().order_by('created_at'):
    print(f'\n{s.settlement_number}:')
    print(f'  Method: {s.settlement_method}')
    print(f'  Amount: Rs. {s.amount}')
    print(f'  Status: {s.settlement_status}')
    print(f'  Created: {s.created_at}')
    print(f'  Verified: {s.verified_at}')

# Calculate expected
completed_settlements = bill.settlements.filter(settlement_status='completed')
expected_paid = sum(s.amount for s in completed_settlements)

print(f'\n=== ANALYSIS ===')
print(f'Completed settlements total: Rs. {expected_paid}')
print(f'Current paid_amount: Rs. {bill.paid_amount}')
print(f'Difference: Rs. {bill.paid_amount - expected_paid}')

# Group by method and status
print(f'\n=== BY METHOD ===')
for method in ['cash', 'cheque', 'bank_transfer', 'return_adjustment']:
    settlements = bill.settlements.filter(settlement_method=method)
    if settlements.exists():
        for s in settlements:
            print(f'{method.upper()}: {s.settlement_number} - Rs. {s.amount} ({s.settlement_status})')

# Check if signal handler should have fired
print(f'\n=== SIGNAL ANALYSIS ===')
for s in bill.settlements.all().order_by('created_at'):
    if s.settlement_status == 'completed':
        print(f'{s.settlement_number} ({s.settlement_method}):')
        print(f'  Status: completed → Signal SHOULD fire')
        print(f'  Created: {s.created_at}')
        
        # Check if commission was created
        from sales.models import CommissionTransaction
        comm = CommissionTransaction.objects.filter(settlement=s).first()
        if comm:
            print(f'  ✅ Commission created: {comm.transaction_type}')
        else:
            print(f'  ❌ NO COMMISSION FOUND - Signal failed!')
    else:
        print(f'{s.settlement_number} ({s.settlement_method}):')
        print(f'  Status: {s.settlement_status} → Signal should NOT fire yet')

# Fix the bill
print(f'\n=== FIXING BILL ===')
bill.paid_amount = expected_paid
bill.balance_amount = bill.total_amount - expected_paid

if bill.paid_amount == 0:
    bill.settlement_status = 'unsettled'
elif bill.paid_amount >= bill.total_amount:
    bill.settlement_status = 'settled'
else:
    bill.settlement_status = 'partial_settled'

bill.save(update_fields=['paid_amount', 'balance_amount', 'settlement_status'])

print(f'✅ FIXED:')
print(f'  paid_amount: Rs. {bill.paid_amount}')
print(f'  balance: Rs. {bill.balance_amount}')
print(f'  status: {bill.settlement_status}')
