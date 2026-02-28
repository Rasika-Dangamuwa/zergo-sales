"""
Investigation: Bill #61
URL: https://192.168.1.4:8000/sales/61/
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import models
from sales.models import Bill
from payments.models import SalesAccountSettlement, BadDebtWriteOff

bill = Bill.objects.get(pk=61)

print("=" * 100)
print(f"BILL #{bill.pk}: {bill.bill_number}")
print("URL: https://192.168.1.4:8000/sales/61/")
print("=" * 100)

# Customer
print(f"\n👤 CUSTOMER:")
if bill.shop:
    print(f"   Shop: {bill.shop.shop_name}")
    print(f"   Shop Code: {bill.shop.shop_code}")
    print(f"   Current Balance: Rs. {bill.shop.current_balance:,.2f}")
else:
    print(f"   Type: Unregistered Customer")
    print(f"   Name: {bill.customer_name or 'Not Set'}")

# Basic Info
print(f"\n📋 BILL INFO:")
print(f"   Date: {bill.bill_date}")
print(f"   Status: {bill.bill_status}")
print(f"   Settlement Status: {bill.settlement_status}")
print(f"   Sales Rep: {bill.sales_rep.get_full_name()}")

# Financial (from bill fields)
print(f"\n💰 BILL FIELDS:")
print(f"   Total: Rs. {bill.total_amount:,.2f}")
print(f"   Paid: Rs. {bill.paid_amount:,.2f}")
print(f"   Balance: Rs. {bill.balance_amount:,.2f}")

# Actual settlements
print(f"\n💳 ACTUAL SETTLEMENTS:")
settlements = bill.settlements.all()
print(f"   Total Settlements: {settlements.count()}")

completed = bill.settlements.filter(settlement_status='completed').aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
pending = bill.settlements.filter(settlement_status__in=['pending', 'pending_verification']).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
cancelled = bill.settlements.filter(settlement_status='cancelled').aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

print(f"   ✅ Completed: Rs. {completed:,.2f}")
print(f"   ⏳ Pending: Rs. {pending:,.2f}")
print(f"   ❌ Cancelled: Rs. {cancelled:,.2f}")

for s in settlements.order_by('settlement_date'):
    icon = "✅" if s.settlement_status == 'completed' else "⏳" if s.settlement_status in ['pending', 'pending_verification'] else "❌"
    print(f"\n   {icon} {s.settlement_number}")
    print(f"      Amount: Rs. {s.amount:,.2f}")
    print(f"      Method: {s.get_settlement_method_display()}")
    print(f"      Status: {s.get_settlement_status_display()}")
    print(f"      Date: {s.settlement_date}")

# Recalculated amounts
actual_balance = bill.total_amount - completed
print(f"\n🔢 RECALCULATED AMOUNTS:")
print(f"   Total: Rs. {bill.total_amount:,.2f}")
print(f"   - Completed Settlements: Rs. {completed:,.2f}")
print(f"   = Actual Balance: Rs. {actual_balance:,.2f}")

# Write-offs
writeoffs = BadDebtWriteOff.objects.filter(bill=bill)
if writeoffs.exists():
    print(f"\n💸 WRITE-OFFS ({writeoffs.count()}):")
    for wo in writeoffs:
        print(f"\n   {wo.write_off_number}")
        print(f"   Amount: Rs. {wo.write_off_amount:,.2f}")
        print(f"   Status: {wo.approval_status}")
        print(f"   Executed: {'Yes' if wo.executed else 'No'}")
        print(f"   Reason: {wo.get_reason_display()}")
else:
    print(f"\n💸 WRITE-OFFS: None")

# Validation
print(f"\n🔍 VALIDATION:")

mismatch = bill.paid_amount != completed or bill.balance_amount != actual_balance
if mismatch:
    print(f"   ⚠️  MISMATCH DETECTED!")
    if bill.paid_amount != completed:
        print(f"      Paid: Bill={bill.paid_amount:,.2f} vs Actual={completed:,.2f} (diff: {completed - bill.paid_amount:,.2f})")
    if bill.balance_amount != actual_balance:
        print(f"      Balance: Bill={bill.balance_amount:,.2f} vs Actual={actual_balance:,.2f} (diff: {actual_balance - bill.balance_amount:,.2f})")
else:
    print(f"   ✅ All amounts match")

if pending > 0:
    print(f"   ⚠️  Has pending settlements: Rs. {pending:,.2f}")
    print(f"      Write-off blocked until verified/cancelled")

if actual_balance > 0:
    print(f"   ✅ Can write off: Rs. {actual_balance:,.2f}")
elif actual_balance == 0:
    print(f"   ℹ️  Fully settled - no write-off needed")
else:
    print(f"   ⚠️  Negative balance: Rs. {actual_balance:,.2f}")

print("\n" + "=" * 100)
