"""
Verify Company Account Balance is Actually 0
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import CompanyAccount, CompanyTransaction, Purchase, PurchaseReturn, PurchaseReturnSettlement
from decimal import Decimal as D

print("=" * 120)
print("COMPANY ACCOUNT BALANCE VERIFICATION")
print("=" * 120)

account = CompanyAccount.objects.get(pk=1)

print(f"\n🏢 Company: {account.company.company_name}")
print(f"💰 Stored Balance: Rs. {account.current_balance:,.2f}")

# Recalculate from scratch
balance = account.opening_balance
print(f"\n📊 Opening Balance: Rs. {balance:,.2f}")

print("\n" + "=" * 120)
print("TRANSACTION LEDGER")
print("=" * 120)
print(f"\n{'Date':<12} {'Type':<15} {'Reference':<25} {'Amount':<15} {'Balance':<15}")
print("-" * 120)

for txn in account.transactions.all().order_by('transaction_date', 'id'):
    balance += txn.amount
    print(f"{txn.transaction_date.strftime('%Y-%m-%d'):<12} {txn.transaction_type:<15} {txn.reference_number:<25} {txn.amount:>13,.2f} {balance:>13,.2f}")

print("-" * 120)
print(f"{'FINAL CALCULATED BALANCE':<67} {balance:>13,.2f}")
print(f"{'STORED BALANCE':<67} {account.current_balance:>13,.2f}")
print(f"{'MATCH':<67} {'✅ YES' if balance == account.current_balance else '❌ NO'}")

print("\n" + "=" * 120)
print("DETAILED ANALYSIS")
print("=" * 120)

# Count transactions by type
from django.db.models import Count, Sum

txn_summary = account.transactions.values('transaction_type').annotate(
    count=Count('id'),
    total=Sum('amount')
).order_by('transaction_type')

print("\nTransaction Summary:")
for item in txn_summary:
    print(f"  {item['transaction_type']:<20} Count: {item['count']:<5} Total: Rs. {item['total']:>12,.2f}")

print("\n" + "=" * 120)
print("GRN vs PAYMENT VERIFICATION")
print("=" * 120)

grns = Purchase.objects.filter(company=account.company)
total_grn = sum(grn.total_amount for grn in grns)
total_paid_grn = sum(grn.total_paid for grn in grns)

print(f"\nTotal GRN Amount: Rs. {total_grn:,.2f}")
print(f"Total Paid for GRNs: Rs. {total_paid_grn:,.2f}")
print(f"GRN Outstanding: Rs. {total_grn - total_paid_grn:,.2f}")

print("\n" + "=" * 120)
print("RETURN vs SETTLEMENT VERIFICATION")
print("=" * 120)

returns = PurchaseReturn.objects.filter(company=account.company)
total_returned = sum(pr.total_amount for pr in returns)
total_settled = sum(pr.total_settled_amount for pr in returns)

print(f"\nTotal Returned: Rs. {total_returned:,.2f}")
print(f"Total Settled: Rs. {total_settled:,.2f}")
print(f"Unsettled Returns: Rs. {total_returned - total_settled:,.2f}")

# Check settlement breakdown
settlements = PurchaseReturnSettlement.objects.filter(
    purchase_return__company=account.company
)
refund_total = sum(s.settlement_amount for s in settlements.filter(settlement_method='refund'))
replacement_total = sum(s.settlement_amount for s in settlements.filter(settlement_method='replacement'))

print(f"\nSettlement Breakdown:")
print(f"  Cash Refunds: Rs. {refund_total:,.2f}")
print(f"  Replacements: Rs. {replacement_total:,.2f}")

print("\n" + "=" * 120)
print("EXPECTED BALANCE CALCULATION")
print("=" * 120)

print(f"""
Method 1: Direct Calculation
─────────────────────────────
Total Paid:        Rs. {total_paid_grn:>12,.2f}
Total Purchased:   Rs. {total_grn:>12,.2f}
Total Returned:    Rs. {total_returned:>12,.2f}
Cash Refund Got:   Rs. {refund_total:>12,.2f}

Net Purchase = Purchased - Returned
             = {total_grn:,.2f} - {total_returned:,.2f}
             = Rs. {total_grn - total_returned:,.2f}

We Paid:       Rs. {total_paid_grn:,.2f}
We Should Pay: Rs. {total_grn - total_returned:,.2f}
We Got Back:   Rs. {refund_total:,.2f}

Balance = Paid - Should Pay - Got Back
        = {total_paid_grn:,.2f} - {total_grn - total_returned:,.2f} - {refund_total:,.2f}
        = Rs. {total_paid_grn - (total_grn - total_returned) - refund_total:,.2f}

Wait, that's not right. Let me recalculate...

Correct Calculation:
────────────────────
What we gave them:  Rs. {total_paid_grn:,.2f} (payments)
What we got:        Rs. {total_grn:,.2f} (goods via GRN)
What we returned:   Rs. {total_returned:,.2f} (goods back)
What they gave us:  Rs. {refund_total:,.2f} (cash back)

Net goods we kept: {total_grn:,.2f} - {total_returned:,.2f} = Rs. {total_grn - total_returned:,.2f}

Cash flow:
  We gave:  {total_paid_grn:,.2f}
  We got:   {refund_total:,.2f}
  Net cash paid: {total_paid_grn - refund_total:,.2f}

Expected Balance = Net goods cost - Net cash paid
                 = {total_grn - total_returned:,.2f} - {total_paid_grn - refund_total:,.2f}
                 = Rs. {(total_grn - total_returned) - (total_paid_grn - refund_total):,.2f}
""")

print("\n" + "=" * 120)
print("ACTUAL vs EXPECTED")
print("=" * 120)

expected = (total_grn - total_returned) - (total_paid_grn - refund_total)
actual = account.current_balance

print(f"\nExpected Balance: Rs. {expected:,.2f}")
print(f"Actual Balance:   Rs. {actual:,.2f}")
print(f"Match: {'✅ CORRECT' if abs(expected - actual) < D('0.01') else f'❌ DIFFERENCE: Rs. {expected - actual:,.2f}'}")

if abs(expected) < D('0.01'):
    print("\n✅ Balance should be 0 - All transactions balanced!")
else:
    print(f"\n⚠️  Expected balance is NOT 0: Rs. {expected:,.2f}")
    if expected > 0:
        print(f"   We owe them Rs. {expected:,.2f}")
    else:
        print(f"   They owe us Rs. {abs(expected):,.2f}")

if abs(actual) < D('0.01'):
    print("✅ Actual balance IS 0 - Perfect!")
else:
    print(f"⚠️  Actual balance is NOT 0: Rs. {actual:,.2f}")

print("\n" + "=" * 120)
