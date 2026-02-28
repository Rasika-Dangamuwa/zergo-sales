"""Check FOC transactions by sales rep"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import FOCValueTransaction
from django.db.models import Count, Sum, Min, Max

print('=== FOC Transactions by Sales Rep ===')
reps = FOCValueTransaction.objects.filter(
    is_archived=False, 
    sales_rep__isnull=False
).values(
    'sales_rep__username', 
    'sales_rep__first_name', 
    'sales_rep__last_name'
).annotate(
    count=Count('id'), 
    total_value=Sum('foc_value')
).order_by('-total_value')

print(f'Total unique reps with FOC: {len(reps)}')
for r in reps:
    print(f"{r['sales_rep__first_name']} {r['sales_rep__last_name']} ({r['sales_rep__username']}): {r['count']} transactions, Total: Rs. {r['total_value']}")

print('\n=== Date Range Check ===')
dates = FOCValueTransaction.objects.filter(
    is_archived=False, 
    sales_rep__isnull=False
).aggregate(
    min_date=Min('transaction_date'), 
    max_date=Max('transaction_date')
)
print(f"Earliest: {dates['min_date']}")
print(f"Latest: {dates['max_date']}")

print('\n=== Transaction Type Breakdown ===')
types = FOCValueTransaction.objects.filter(
    is_archived=False, 
    sales_rep__isnull=False
).values('transaction_type').annotate(
    count=Count('id')
)
for t in types:
    print(f"{t['transaction_type']}: {t['count']} records")
