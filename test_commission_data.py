import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from payments.models import OldPayment
from sales.models import CommissionRecord
from accounts.models import User

# Get all sales reps
reps = User.objects.filter(user_type='sales_rep')
print(f'Total sales reps: {reps.count()}')
for rep in reps:
    print(f'  - {rep.username} ({rep.get_full_name()})')

# Check which rep has payments
print('\nPayments per sales rep:')
for rep in reps:
    count = OldPayment.objects.filter(bill__sales_rep=rep, status='completed').count()
    if count > 0:
        print(f'  {rep.username}: {count} completed payments')

# Get the rep with payments
active_rep = User.objects.get(username='rep')
print(f'\nActive sales rep: {active_rep.get_full_name()}')

# Check their payments
payments = OldPayment.objects.filter(bill__sales_rep=active_rep, status='completed')
print(f'Completed payments: {payments.count()}')

# Show payment details grouped by month
from collections import defaultdict
by_month = defaultdict(list)
for p in payments:
    month = p.payment_date.strftime('%Y-%m')
    by_month[month].append(p)

print('\nPayments by month:')
for month in sorted(by_month.keys()):
    total = sum(p.amount for p in by_month[month])
    print(f'  {month}: {len(by_month[month])} payments, Rs.{total}')
