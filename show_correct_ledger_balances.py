"""
Show what the correct ledger balances should be after fix
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import CompanyAccount
from decimal import Decimal

account = CompanyAccount.objects.first()
transactions = account.transactions.all().order_by('transaction_date', 'id')

print("=" * 120)
print("CORRECT LEDGER BALANCES - After View Fix")
print("=" * 120)
print(f"\nCompany: {account.company.company_name}")
print(f"Opening Balance: Rs. {account.opening_balance:,.2f}")
print(f"Current Balance: Rs. {account.current_balance:,.2f}")

print("\n" + "=" * 120)
print("Date       | Type       | Reference            | Debit         | Credit        | Balance       | Status")
print("-" * 120)

balance = account.opening_balance
print(f"01 Jan 2026 | Opening    | -                    | -             | Rs. {balance:>10,.2f} | Rs. {balance:>10,.2f} | -")

for txn in transactions:
    balance += txn.amount  # Correct calculation - all amounts added
    
    # Determine debit/credit display
    if txn.transaction_type in ['purchase', 'debit']:
        debit = f"Rs. {txn.amount:>10,.2f}"
        credit = "-"
    else:  # return, payment, credit
        debit = "-"
        credit = f"Rs. {abs(txn.amount):>10,.2f}"
    
    date_str = txn.transaction_date.strftime('%d %b %Y')
    type_str = txn.transaction_type.capitalize()
    ref = txn.reference_number[:20]
    
    status = "Settled" if hasattr(txn, 'purchase') and txn.purchase and txn.purchase.amount_outstanding == 0 else "-"
    
    print(f"{date_str} | {type_str:10} | {ref:20} | {debit:13} | {credit:13} | Rs. {balance:>10,.2f} | {status}")

print("-" * 120)
print(f"Final Balance: Rs. {balance:,.2f}")
print(f"Stored Balance: Rs. {account.current_balance:,.2f}")
print(f"Match: {'✅ CORRECT' if balance == account.current_balance else '❌ ERROR'}")

print("\n" + "=" * 120)
print("KEY CHANGES FROM OLD VIEW")
print("=" * 120)
print("""
OLD CALCULATION (WRONG):
  if transaction_type in ['purchase', 'debit']:
      balance += amount
  elif transaction_type in ['return', 'payment']:
      balance -= amount  # ❌ Wrong! Amount is already negative

  Result: Returns/payments INCREASED balance instead of reducing it
  Final: Rs. 128,690.10 ❌

NEW CALCULATION (CORRECT):
  balance += amount  # For ALL transaction types
  
  Why? Transaction amounts already have correct signs:
  - Purchase: +39,916.80 (we owe more)
  - Return: -693.00 (we owe less)
  - Payment: -21,552.30 (we paid them)
  
  Result: All transactions correctly affect balance
  Final: Rs. -2,979.90 ✅
""")

print("\n" + "=" * 120)
print("BALANCE INTERPRETATION")
print("=" * 120)
if account.current_balance < 0:
    print(f"✅ Balance: Rs. {account.current_balance:,.2f} (NEGATIVE)")
    print(f"   Meaning: RECEIVABLE - Company owes us Rs. {abs(account.current_balance):,.2f}")
    print(f"   Why negative? They returned less goods than we paid them")
    print(f"   Action: They should pay us cash or send goods worth Rs. {abs(account.current_balance):,.2f}")
elif account.current_balance > 0:
    print(f"⚠️  Balance: Rs. {account.current_balance:,.2f} (POSITIVE)")
    print(f"   Meaning: PAYABLE - We owe company Rs. {account.current_balance:,.2f}")
    print(f"   Why positive? We bought more than we've paid")
    print(f"   Action: We should pay them Rs. {account.current_balance:,.2f}")
else:
    print(f"✅ Balance: Rs. 0.00")
    print(f"   Meaning: SETTLED - Account is balanced")

print("\n" + "=" * 120)
