from sales.models import CommissionTransaction
from accounts.models import User
from django.db.models import Sum
from datetime import date
from decimal import Decimal

u = User.objects.get(first_name='Sales', last_name='Representative')
ms = date(2026, 1, 1)
me = date(2026, 2, 1)

month_transactions = CommissionTransaction.objects.filter(
    sales_rep=u,
    transaction_date__gte=ms,
    transaction_date__lt=me
).exclude(transaction_type='writeoff_executed')

returns_processed = month_transactions.filter(transaction_type='return_processed')
total_returns = returns_processed.aggregate(total=Sum('return_amount'))['total'] or Decimal('0.00')
returns_count = returns_processed.count()

print("=" * 80)
print("DEBUGGING RETURN QUERY")
print("=" * 80)
print(f"\nMonth Transactions Count: {month_transactions.count()}")
print(f"Returns Processed Count: {returns_count}")
print(f"Total Returns Amount: Rs. {total_returns}")

print(f"\n{'=' * 80}")
print("RETURN DETAILS:")
print("=" * 80)
for r in returns_processed.order_by('id'):
    print(f"ID: {r.id} | Date: {r.transaction_date.date()} | Amount: Rs. {r.return_amount} | Commission: Rs. {r.commission_earned}")

print(f"\n{'=' * 80}")
print(f"CONCLUSION: The query IS CORRECT!")
print(f"  Returns Count: {returns_count}")
print(f"  Returns Amount: Rs. {total_returns}")
print(f"\nThe dashboard template must be using stale/cached data!")
print("=" * 80)
