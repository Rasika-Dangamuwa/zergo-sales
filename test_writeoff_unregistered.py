"""
Test write-off for Bill #213 (Unregistered Customer)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill
from payments.models import BadDebtWriteOff

bill = Bill.objects.get(pk=213)

print("=" * 80)
print("BILL #213 - UNREGISTERED CUSTOMER WRITE-OFF TEST")
print("=" * 80)

print(f"\n📋 BILL DETAILS:")
print(f"   Bill Number: {bill.bill_number}")
print(f"   Shop: {bill.shop}")
print(f"   Customer Name: {bill.customer_name or 'None'}")
print(f"   Customer Type: {'Registered Shop' if bill.shop else 'Unregistered Customer'}")
print(f"   Total: Rs. {bill.total_amount:,.2f}")
print(f"   Paid: Rs. {bill.paid_amount:,.2f}")
print(f"   Balance: Rs. {bill.balance_amount:,.2f}")

print(f"\n✅ VALIDATION CHECKS:")
print(f"   Has outstanding balance? {'✅ Yes' if bill.balance_amount > 0 else '❌ No'}")
print(f"   Bill confirmed? {'✅ Yes' if bill.bill_status == 'confirmed' else f'❌ No ({bill.bill_status})'}")
print(f"   Any pending settlements? ", end="")
pending = bill.settlements.filter(settlement_status='pending_verification')
if pending.exists():
    print(f"❌ Yes ({pending.count()} pending)")
else:
    print("✅ No")

print(f"   Already written off? ", end="")
existing = BadDebtWriteOff.objects.filter(bill=bill, executed=True)
if existing.exists():
    print(f"❌ Yes ({existing.first().write_off_number})")
else:
    print("✅ No")

print(f"\n✅ WRITE-OFF ELIGIBILITY:")
can_write_off = (
    bill.balance_amount > 0 and 
    bill.bill_status == 'confirmed' and 
    not pending.exists() and 
    not existing.exists()
)

if can_write_off:
    print("   ✅ ELIGIBLE FOR WRITE-OFF")
    print(f"\n   Write-off amount would be: Rs. {bill.balance_amount:,.2f}")
    print(f"   Customer: {bill.customer_name or 'Unregistered Customer'}")
    print(f"   Shop balance update: {'Yes' if bill.shop else 'No (unregistered customer)'}")
else:
    print("   ❌ NOT ELIGIBLE FOR WRITE-OFF")
    if bill.balance_amount <= 0:
        print("      Reason: No outstanding balance")
    if bill.bill_status != 'confirmed':
        print(f"      Reason: Bill not confirmed ({bill.bill_status})")
    if pending.exists():
        print(f"      Reason: Has {pending.count()} pending settlements")
    if existing.exists():
        print(f"      Reason: Already written off ({existing.first().write_off_number})")

print("\n" + "=" * 80)
