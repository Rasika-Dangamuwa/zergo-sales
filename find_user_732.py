from sales.models import CommissionTransaction
from accounts.models import User
from django.db.models import Sum
from decimal import Decimal

print("=" * 80)
print("FINDING THE USER WITH Rs. 732.00 BALANCE")
print("=" * 80)

# Get all users with commission transactions
users_with_commission = User.objects.filter(
    commission_transactions__isnull=False
).distinct()

print(f"\nFound {users_with_commission.count()} users with commission transactions:")

for user in users_with_commission:
    balance = CommissionTransaction.get_rep_balance(user)
    txn_count = CommissionTransaction.objects.filter(sales_rep=user).count()
    
    print(f"\n{user.get_full_name()} ({user.user_type}):")
    print(f"  Balance: Rs. {balance}")
    print(f"  Transactions: {txn_count}")
    
    if abs(balance - Decimal('732.00')) < Decimal('0.01'):
        print(f"\n  ⭐ THIS IS THE USER WITH Rs. 732.00!")
        
        # Show this month's details
        from datetime import date
        today = date.today()
        month_start = date(today.year, today.month, 1)
        if today.month == 12:
            month_end = date(today.year + 1, 1, 1)
        else:
            month_end = date(today.year, today.month + 1, 1)
        
        month_txns = CommissionTransaction.objects.filter(
            sales_rep=user,
            transaction_date__gte=month_start,
            transaction_date__lt=month_end
        ).exclude(transaction_type='writeoff_executed')
        
        print(f"\n  This Month Transactions: {month_txns.count()}")
        
        # Breakdown
        payments = month_txns.filter(transaction_type='payment_received')
        returns = month_txns.filter(transaction_type='return_processed')
        
        payments_collected = payments.aggregate(total=Sum('collected_amount'))['total'] or 0
        returns_total = returns.aggregate(total=Sum('return_amount'))['total'] or 0
        
        print(f"  Payments Collected: Rs. {payments_collected} ({payments.count()} payments)")
        print(f"  Returns Processed: Rs. {returns_total} ({returns.count()} returns)")
        
        # Check commission calculation
        total_commission = month_txns.aggregate(total=Sum('commission_earned'))['total'] or 0
        print(f"  This Month Commission: Rs. {total_commission}")

print(f"\n{'=' * 80}")
