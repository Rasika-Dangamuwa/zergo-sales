import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from accounts.models import User
from accounts.money_account_models import UserMoneyAccount, MoneyTransaction

print("\n" + "="*80)
print("FIXING BALANCE - Recalculating from transactions")
print("="*80 + "\n")

rep = User.objects.get(username='rep')
acc = rep.money_account

print(f"BEFORE:")
print(f"  Balance: Rs. {acc.current_balance:,.2f}")
print(f"  Total Advances Taken: Rs. {acc.total_advance_given:,.2f}")

# Delete legacy advance_recovery transactions
legacy_recovery = MoneyTransaction.objects.filter(
    account=acc,
    transaction_type='advance_recovery'
)

if legacy_recovery.exists():
    count = legacy_recovery.count()
    total = sum(t.amount for t in legacy_recovery)
    print(f"\n⚠️  Deleting {count} legacy 'advance_recovery' transactions totaling Rs. {total:,.2f}")
    legacy_recovery.delete()
    print("✅ Deleted")

# Recalculate balance
print("\nRecalculating balance...")
acc.update_balance()
acc.refresh_from_db()

print(f"\nAFTER:")
print(f"  Balance: Rs. {acc.current_balance:,.2f}")
print(f"  Total Credited: Rs. {acc.total_credited:,.2f}")
print(f"  Total Debited: Rs. {acc.total_debited:,.2f}")
print(f"  Total Advances Taken: Rs. {acc.total_advance_given:,.2f}")

print("\n" + "="*80)
print("✅ Balance fixed successfully!")
print("="*80 + "\n")
