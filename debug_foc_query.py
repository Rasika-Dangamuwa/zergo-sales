"""Check what transactions exist for each sales rep with dates"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import FOCValueTransaction
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

# Simulate the report query
start_date = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
end_date = timezone.now().strftime('%Y-%m-%d')

print(f"Date range being used: {start_date} to {end_date}")
print()

query = FOCValueTransaction.objects.filter(
    transaction_type__in=['foc_given', 'implicit_foc'],
    transaction_date__range=[start_date, end_date],
    is_archived=False,
    sales_rep__isnull=False
)

print(f"Total transactions matching filter: {query.count()}")
print()

# Group by rep
for rep_id in query.values_list('sales_rep_id', flat=True).distinct():
    rep_txns = query.filter(sales_rep_id=rep_id)
    first_txn = rep_txns.first()
    rep_name = f"{first_txn.sales_rep.first_name} {first_txn.sales_rep.last_name}"
    
    print(f"Rep: {rep_name}")
    print(f"  Transactions: {rep_txns.count()}")
    print(f"  Date range: {rep_txns.earliest('transaction_date').transaction_date} to {rep_txns.latest('transaction_date').transaction_date}")
    
    foc_given = rep_txns.filter(transaction_type='foc_given')
    implicit = rep_txns.filter(transaction_type='implicit_foc')
    
    print(f"  FOC Given: {foc_given.count()} transactions")
    print(f"  Implicit FOC: {implicit.count()} transactions")
    print()
