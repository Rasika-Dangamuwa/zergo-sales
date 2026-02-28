"""
Test Commission Rate Calculation Based on Bill Creation Date
=============================================================

Business Rule: Commission should be calculated using the rate that was 
active when the BILL WAS CREATED, not when payment was received.

Example Scenario:
- Bill created on 26/01/2026 when rate was 5%
- Payment received on 28/01/2026 when rate changed to 7%
- Commission should use 5% rate (from bill creation)
"""

from sales.models import Bill, CommissionTransaction, CommissionRateHistory
from payments.models import SalesAccountSettlement
from datetime import date, datetime
from decimal import Decimal

print("=" * 80)
print("COMMISSION RATE CALCULATION TEST")
print("=" * 80)

# Find a recent bill with payment
bill = Bill.objects.filter(
    settlements__settlement_status='completed'
).select_related('sales_rep').order_by('-id').first()

if not bill:
    print("\n❌ No bills with completed payments found")
    exit()

# Get bill details
print(f"\n📋 BILL DETAILS:")
print(f"   Bill Number: {bill.bill_number}")
print(f"   Bill Date: {bill.bill_date}")
print(f"   Total Amount: Rs. {bill.total_amount}")
print(f"   Sales Rep: {bill.sales_rep.get_full_name()}")

# Get commission rate on bill creation date
bill_date = bill.bill_date.date() if hasattr(bill.bill_date, 'date') else bill.bill_date
rate_on_bill_date = CommissionRateHistory.get_rate_for_date(bill_date)
print(f"\n💰 COMMISSION RATE ON BILL DATE ({bill_date}):")
print(f"   Rate: {rate_on_bill_date}%")

# Get payment details
payment = bill.settlements.filter(settlement_status='completed').first()
if payment:
    payment_date = payment.settlement_date.date() if hasattr(payment.settlement_date, 'date') else payment.settlement_date
    rate_on_payment_date = CommissionRateHistory.get_rate_for_date(payment_date)
    
    print(f"\n💳 PAYMENT DETAILS:")
    print(f"   Settlement Number: {payment.settlement_number}")
    print(f"   Settlement Date: {payment.settlement_date}")
    print(f"   Amount: Rs. {payment.amount}")
    print(f"   Rate on payment date ({payment_date}): {rate_on_payment_date}%")
    
    # Get commission transaction
    commission = CommissionTransaction.objects.filter(
        bill=bill,
        settlement=payment,
        transaction_type='payment_received'
    ).first()
    
    if commission:
        print(f"\n✅ COMMISSION TRANSACTION:")
        print(f"   Transaction ID: {commission.id}")
        print(f"   Applicable Rate: {commission.applicable_rate}%")
        print(f"   Commission Earned: Rs. {commission.commission_earned}")
        
        # Verify correct rate was used
        expected_commission = (payment.amount * rate_on_bill_date) / 100
        
        print(f"\n🔍 VERIFICATION:")
        print(f"   Expected commission (using bill date rate): Rs. {expected_commission}")
        print(f"   Actual commission: Rs. {commission.commission_earned}")
        
        if commission.applicable_rate == rate_on_bill_date:
            print(f"\n✅ SUCCESS! Commission calculated using bill creation date rate ({rate_on_bill_date}%)")
        else:
            print(f"\n⚠️  WARNING! Commission used {commission.applicable_rate}% instead of {rate_on_bill_date}%")
            print(f"   This may be from old data before the fix was applied.")
    else:
        print(f"\n❌ No commission transaction found for this payment")
else:
    print(f"\n❌ No completed payment found for this bill")

print("\n" + "=" * 80)
print("RATE HISTORY:")
print("=" * 80)

rates = CommissionRateHistory.objects.all().order_by('effective_from')
for rate in rates:
    status = "ACTIVE" if rate.is_active else "INACTIVE"
    to_date = rate.effective_to or "Present"
    print(f"{rate.effective_from} to {to_date}: {rate.rate}% [{status}]")

print("\n" + "=" * 80)
