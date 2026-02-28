from sales.models import Bill, CommissionTransaction, CommissionRateHistory
from payments.models import SalesAccountSettlement

print("=" * 80)
print("COMMISSION RATE CALCULATION TEST")
print("=" * 80)

bill = Bill.objects.filter(settlements__settlement_status='completed').select_related('sales_rep').order_by('-id').first()

if not bill:
    print("No bills with payments found")
else:
    print(f"\nBill: {bill.bill_number}")
    print(f"Bill Date: {bill.bill_date}")
    print(f"Total: Rs. {bill.total_amount}")
    print(f"Sales Rep: {bill.sales_rep.get_full_name()}")
    
    bill_date = bill.bill_date.date() if hasattr(bill.bill_date, 'date') else bill.bill_date
    rate_on_bill_date = CommissionRateHistory.get_rate_for_date(bill_date)
    print(f"\nRate on bill date ({bill_date}): {rate_on_bill_date}%")
    
    payment = bill.settlements.filter(settlement_status='completed').first()
    if payment:
        payment_date = payment.settlement_date.date() if hasattr(payment.settlement_date, 'date') else payment.settlement_date
        rate_on_payment_date = CommissionRateHistory.get_rate_for_date(payment_date)
        
        print(f"\nPayment: {payment.settlement_number}")
        print(f"Payment Date: {payment.settlement_date}")
        print(f"Amount: Rs. {payment.amount}")
        print(f"Rate on payment date ({payment_date}): {rate_on_payment_date}%")
        
        commission = CommissionTransaction.objects.filter(bill=bill, settlement=payment, transaction_type='payment_received').first()
        
        if commission:
            print(f"\nCommission ID: {commission.id}")
            print(f"Applicable Rate: {commission.applicable_rate}%")
            print(f"Commission Earned: Rs. {commission.commission_earned}")
            
            expected_commission = (payment.amount * rate_on_bill_date) / 100
            print(f"\nExpected (bill date rate): Rs. {expected_commission}")
            print(f"Actual: Rs. {commission.commission_earned}")
            
            if commission.applicable_rate == rate_on_bill_date:
                print(f"\nSUCCESS! Using bill creation date rate ({rate_on_bill_date}%)")
            else:
                print(f"\nWARNING! Using {commission.applicable_rate}% instead of {rate_on_bill_date}%")
                print("This is old data before fix. New transactions will use correct rate.")

print("\n" + "=" * 80)
print("RATE HISTORY:")
print("=" * 80)

rates = CommissionRateHistory.objects.all().order_by('effective_from')
for rate in rates:
    status = "ACTIVE" if rate.is_active else "INACTIVE"
    to_date = rate.effective_to or "Present"
    print(f"{rate.effective_from} to {to_date}: {rate.rate}% [{status}]")

print("=" * 80)
