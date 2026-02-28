import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionRecord
from accounts.models import User
from payments.models import OldPayment
from decimal import Decimal

# Get the sales rep with data
rep = User.objects.get(username='rep')
print(f'Sales Rep: {rep.get_full_name()}')

# Check existing commission records
existing = CommissionRecord.objects.filter(sales_rep=rep)
print(f'Existing commission records: {existing.count()}')

# Get payments for January 2026
payments = OldPayment.objects.filter(
    bill__sales_rep=rep,
    status='completed',
    payment_date__year=2026,
    payment_date__month=1
)
print(f'\nJanuary 2026 payments: {payments.count()}')
total_amount = sum(p.amount for p in payments)
print(f'Total payment amount: Rs.{total_amount}')

# Create/get commission record for January 2026
record, created = CommissionRecord.objects.get_or_create(
    month='2026-01',
    sales_rep=rep,
    defaults={
        'commission_rate': Decimal('5.00'),
        'collected_amount': Decimal('0'),
        'returns_amount': Decimal('0'),
        'commission_amount': Decimal('0'),
        'payment_status': 'pending'
    }
)

print(f'\nCommission record {"created" if created else "already exists"}')
print(f'Record ID: {record.id}')
print(f'Month: {record.month}')
print(f'Collected: Rs.{record.collected_amount}')
print(f'Commission: Rs.{record.commission_amount}')
print(f'Status: {record.payment_status}')

# Check if CommissionRecord has calculate_commission method
if hasattr(record, 'calculate_commission'):
    print('\nCalculating commission...')
    record.calculate_commission()
    record.refresh_from_db()
    print(f'After calculation:')
    print(f'  Collected: Rs.{record.collected_amount}')
    print(f'  Returns: Rs.{record.returns_amount}')
    print(f'  Commission: Rs.{record.commission_amount}')
else:
    print('\nCommissionRecord does not have calculate_commission method')
    print('Need to manually set values')
    record.collected_amount = total_amount
    record.returns_amount = Decimal('0')
    record.commission_amount = total_amount * record.commission_rate / 100
    record.save()
    print(f'Manual calculation:')
    print(f'  Collected: Rs.{record.collected_amount}')
    print(f'  Commission: Rs.{record.commission_amount}')
