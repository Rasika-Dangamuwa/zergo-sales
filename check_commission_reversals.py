"""
Check commission transactions to verify reversals are working
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from decimal import Decimal

# Get all transactions ordered by date
transactions = CommissionTransaction.objects.filter(
    sales_rep__username='rep'
).select_related('settlement', 'bill').order_by('created_at')

print("\n" + "="*100)
print("COMMISSION TRANSACTIONS FOR rep")
print("="*100)

total_earned = Decimal('0')
for txn in transactions:
    total_earned += txn.commission_earned
    
    ref = ""
    if txn.settlement:
        ref = f"SET-{txn.settlement.settlement_number}"
    elif txn.bill:
        ref = f"BILL-{txn.bill.bill_number}"
    
    status = ""
    if txn.settlement:
        status = f"[{txn.settlement.settlement_status}]"
    
    direction = "+" if txn.commission_earned >= 0 else ""
    
    print(f"{txn.created_at.strftime('%Y-%m-%d %H:%M')} | "
          f"{txn.transaction_type:20} | "
          f"{ref:20} {status:15} | "
          f"Collected: {txn.collected_amount:>10.2f} | "
          f"Rate: {txn.applicable_rate}% | "
          f"Commission: {direction}{txn.commission_earned:>8.2f} | "
          f"Balance: {txn.running_balance:>10.2f}")

print("="*100)
print(f"Total Commission Earned: {total_earned:.2f}")
print(f"Final Balance: {transactions.last().running_balance if transactions.exists() else 0:.2f}")
print("="*100)

# Check specifically for reversal transactions (negative commission)
reversals = CommissionTransaction.objects.filter(
    sales_rep__username='rep',
    commission_earned__lt=0
).select_related('settlement')

print(f"\n📊 Found {reversals.count()} reversal transactions (negative commission):")
for rev in reversals:
    print(f"  ❌ {rev.created_at.strftime('%Y-%m-%d %H:%M')} | "
          f"SET-{rev.settlement.settlement_number if rev.settlement else 'N/A'} | "
          f"Commission: {rev.commission_earned:.2f} | "
          f"Balance after: {rev.running_balance:.2f}")
