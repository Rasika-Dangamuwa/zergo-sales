"""
List all sales reps with commission transactions
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from django.db.models import Count, Sum

# Get sales reps with transactions
reps_with_commissions = CommissionTransaction.objects.values(
    'sales_rep__username',
    'sales_rep__first_name',
    'sales_rep__last_name'
).annotate(
    total_transactions=Count('id'),
    total_commission=Sum('commission_earned'),
    final_balance=Sum('commission_earned')  # This is approximate
).order_by('-total_transactions')

print("\n" + "="*80)
print("SALES REPS WITH COMMISSION TRANSACTIONS")
print("="*80)

for rep in reps_with_commissions:
    username = rep['sales_rep__username']
    name = f"{rep['sales_rep__first_name']} {rep['sales_rep__last_name']}"
    txn_count = rep['total_transactions']
    commission = rep['total_commission'] or 0
    
    print(f"👤 {username:15} | {name:25} | "
          f"Transactions: {txn_count:3} | "
          f"Commission: Rs. {commission:>10.2f}")

print("="*80)

# Also check for reversals across all reps
from decimal import Decimal
reversals = CommissionTransaction.objects.filter(
    commission_earned__lt=Decimal('0')
).select_related('sales_rep', 'settlement')

print(f"\n📊 Total Reversal Transactions (negative commission): {reversals.count()}")
for rev in reversals:
    print(f"  ❌ {rev.sales_rep.username:15} | "
          f"SET-{rev.settlement.settlement_number if rev.settlement else 'N/A':20} | "
          f"Commission: {rev.commission_earned:>8.2f} | "
          f"Date: {rev.created_at.strftime('%Y-%m-%d %H:%M')}")
