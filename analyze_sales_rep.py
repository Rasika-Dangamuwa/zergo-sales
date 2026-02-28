from sales.models import CommissionTransaction
from accounts.models import User  
from django.db.models import Sum, Count
from datetime import date
from decimal import Decimal

u = User.objects.get(first_name='Sales', last_name='Representative')
ms = date(2026, 1, 1)
me = date(2026, 2, 1)
txns = CommissionTransaction.objects.filter(
    sales_rep=u,
    transaction_date__gte=ms,
    transaction_date__lt=me
).exclude(transaction_type='writeoff_executed')

print("=" * 80)
print(f"SALES REPRESENTATIVE COMMISSION ANALYSIS")
print("=" * 80)
print(f"\nUser: {u.get_full_name()}")
print(f"Current Balance: Rs. {CommissionTransaction.get_rep_balance(u)}")
print(f"\nThis Month (Jan 2026):")
print(f"Total Transactions: {txns.count()}")

total_commission = txns.aggregate(Sum('commission_earned'))['commission_earned__sum'] or Decimal('0')
print(f"Total Commission: Rs. {total_commission}")

payments = txns.filter(transaction_type='payment_received')
payments_collected = payments.aggregate(Sum('collected_amount'))['collected_amount__sum'] or Decimal('0')
print(f"\nPayments Received: {payments.count()}")
print(f"Amount Collected: Rs. {payments_collected}")

returns = txns.filter(transaction_type='return_processed')
returns_total = returns.aggregate(Sum('return_amount'))['return_amount__sum'] or Decimal('0')
print(f"\nReturns Processed: {returns.count()}")
print(f"Return Amount: Rs. {returns_total}")

print(f"\n{'=' * 80}")
print("ISSUE FOUND:")
print("=" * 80)
print(f"\nDashboard shows:")
print(f"  Payments Collected: Rs. 24,380.00 (74 payments)")
print(f"  Returns Processed: Rs. 2,790.00 (22 returns)")
print(f"\nActual values:")
print(f"  Payments Collected: Rs. {payments_collected} ({payments.count()} payments)")
print(f"  Returns Processed: Rs. {returns_total} ({returns.count()} returns)")
print(f"\n⚠️  The dashboard is showing INCORRECT values!")
print(f"{'=' * 80}")
