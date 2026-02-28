import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from accounts.models import User
from accounts.money_account_models import UserMoneyAccount, MoneyTransaction
from django.db.models import Sum
from decimal import Decimal

rep = User.objects.get(username='rep')
acc = rep.money_account

print("\n" + "="*80)
print("CURRENT DATABASE STATE")
print("="*80)

print("\nStored Account Totals:")
print(f"  opening_balance: Rs. {acc.opening_balance:,.2f}")
print(f"  total_credited: Rs. {acc.total_credited:,.2f}")
print(f"  total_debited: Rs. {acc.total_debited:,.2f}")
print(f"  total_advance_given: Rs. {acc.total_advance_given:,.2f}")
print(f"  total_advance_recovered: Rs. {acc.total_advance_recovered:,.2f}")
print(f"  current_balance: Rs. {acc.current_balance:,.2f}")

print("\n" + "="*80)
print("ALL TRANSACTIONS")
print("="*80)

txns = MoneyTransaction.objects.filter(account=acc).order_by('transaction_date', 'id')
for t in txns:
    sign = "+" if t.transaction_type in ['credit', 'commission_payment', 'bonus', 'adjustment_credit', 'advance_recovery'] else "-"
    print(f"{t.transaction_number}: {t.transaction_type:20s} {sign}Rs. {t.amount:8,.2f}")

print("\n" + "="*80)
print("RECALCULATION")
print("="*80)

credits = txns.filter(
    transaction_type__in=['credit', 'commission_payment', 'bonus', 'adjustment_credit']
).aggregate(t=Sum('amount'))['t'] or Decimal('0')

debits = txns.filter(
    transaction_type__in=['debit', 'payment', 'adjustment_debit']
).aggregate(t=Sum('amount'))['t'] or Decimal('0')

advances_given = txns.filter(
    transaction_type='advance_given'
).aggregate(t=Sum('amount'))['t'] or Decimal('0')

advances_recovered = txns.filter(
    transaction_type='advance_recovery'
).aggregate(t=Sum('amount'))['t'] or Decimal('0')

print(f"Credits (commission/bonus): Rs. {credits:,.2f}")
print(f"Debits (payments): Rs. {debits:,.2f}")
print(f"Advances Given: Rs. {advances_given:,.2f}")
print(f"Advances Recovered (LEGACY): Rs. {advances_recovered:,.2f}")

correct_balance = credits - debits - advances_given
print(f"\nCorrect Balance = {credits:,.2f} - {debits:,.2f} - {advances_given:,.2f}")
print(f"Correct Balance = Rs. {correct_balance:,.2f}")
print(f"Stored Balance = Rs. {acc.current_balance:,.2f}")
print(f"Match: {'✅ YES' if correct_balance == acc.current_balance else '❌ NO'}")

if advances_recovered > 0:
    print(f"\n⚠️  WARNING: Found {advances_recovered:,.2f} in legacy 'advance_recovery' transactions!")
    print("   These should be deleted as they don't fit the new business model.")

print("="*80 + "\n")
