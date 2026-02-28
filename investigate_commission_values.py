from sales.models import CommissionTransaction
from accounts.models import User
from django.db.models import Sum, Count
from datetime import date, datetime
from decimal import Decimal

print("=" * 80)
print("DEEP INVESTIGATION: COMMISSION DASHBOARD VALUES")
print("=" * 80)

# Get Sales Representative
sales_rep = User.objects.filter(user_type='sales_rep').first()
if not sales_rep:
    print("\n❌ No sales rep found!")
    exit()
print(f"\nSales Rep: {sales_rep.get_full_name()}")

# Get current month
today = date.today()
month_start = date(today.year, today.month, 1)
if today.month == 12:
    month_end = date(today.year + 1, 1, 1)
else:
    month_end = date(today.year, today.month + 1, 1)

print(f"Month: {month_start} to {month_end}")

# Get all commission transactions for this month
all_txns = CommissionTransaction.objects.filter(
    sales_rep=sales_rep,
    transaction_date__gte=month_start,
    transaction_date__lt=month_end
).exclude(transaction_type='writeoff_executed')

print(f"\n{'=' * 80}")
print(f"TRANSACTION BREAKDOWN:")
print(f"{'=' * 80}")

# Count by type
bill_created = all_txns.filter(transaction_type='bill_created')
payment_received = all_txns.filter(transaction_type='payment_received')
payment_cancelled = all_txns.filter(transaction_type='payment_cancelled')
return_processed = all_txns.filter(transaction_type='return_processed')
return_cancelled = all_txns.filter(transaction_type='return_cancelled')

print(f"\nBill Created: {bill_created.count()}")
print(f"Payment Received: {payment_received.count()}")
print(f"Payment Cancelled: {payment_cancelled.count()}")
print(f"Return Processed: {return_processed.count()}")
print(f"Return Cancelled: {return_cancelled.count()}")
print(f"TOTAL: {all_txns.count()}")

# Calculate amounts
print(f"\n{'=' * 80}")
print(f"AMOUNT BREAKDOWN:")
print(f"{'=' * 80}")

payments_collected = payment_received.aggregate(
    total=Sum('collected_amount'),
    commission=Sum('commission_earned')
)
print(f"\nPayments Collected:")
print(f"  Amount: Rs. {payments_collected['total'] or 0}")
print(f"  Commission: Rs. {payments_collected['commission'] or 0}")
print(f"  Count: {payment_received.count()}")

returns_total = return_processed.aggregate(
    total=Sum('return_amount'),
    commission=Sum('commission_earned')
)
print(f"\nReturns Processed:")
print(f"  Amount: Rs. {returns_total['total'] or 0}")
print(f"  Commission: Rs. {returns_total['commission'] or 0}")
print(f"  Count: {return_processed.count()}")

# Total commission this month
total_commission = all_txns.aggregate(total=Sum('commission_earned'))['total'] or Decimal('0.00')
print(f"\nTotal Commission This Month: Rs. {total_commission}")

# Get current running balance
current_balance = CommissionTransaction.get_rep_balance(sales_rep)
print(f"Current Running Balance: Rs. {current_balance}")

# Check if balance matches commission
print(f"\n{'=' * 80}")
print(f"VERIFICATION:")
print(f"{'=' * 80}")

if abs(total_commission - current_balance) > Decimal('0.01'):
    print(f"\n⚠️  WARNING: Balance mismatch!")
    print(f"  This month commission: Rs. {total_commission}")
    print(f"  Current balance: Rs. {current_balance}")
    print(f"  Difference: Rs. {current_balance - total_commission}")
    
    # Check if there are transactions from previous months
    all_time = CommissionTransaction.objects.filter(
        sales_rep=sales_rep
    ).exclude(transaction_type='writeoff_executed')
    
    all_time_commission = all_time.aggregate(total=Sum('commission_earned'))['total'] or Decimal('0.00')
    print(f"\n  All-time commission: Rs. {all_time_commission}")
    print(f"  All-time transactions: {all_time.count()}")
else:
    print(f"\n✅ Balance matches this month's commission")

# Show detailed breakdown
print(f"\n{'=' * 80}")
print(f"DETAILED TRANSACTION SUMMARY:")
print(f"{'=' * 80}")

summary = all_txns.values('transaction_type').annotate(
    count=Count('id'),
    total_commission=Sum('commission_earned')
).order_by('-count')

for item in summary:
    print(f"\n{item['transaction_type']}:")
    print(f"  Count: {item['count']}")
    print(f"  Commission: Rs. {item['total_commission']}")

print(f"\n{'=' * 80}")
