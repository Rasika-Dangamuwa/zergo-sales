import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, ReturnItem, Bill
from payments.models import OldPayment
from decimal import Decimal

print("=" * 80)
print("INVESTIGATION: Return #43 and Bill #47")
print("=" * 80)

# Check Return #43
try:
    ret = Return.objects.get(id=43)
    print("\n--- RETURN #43 ---")
    print(f"Return Number: {ret.return_number}")
    print(f"Shop: {ret.shop.shop_name}")
    print(f"Date: {ret.return_date}")
    print(f"Total Amount: Rs. {ret.total_amount}")
    print(f"Settlement Method: {ret.settlement_method}")
    print(f"Settlement Status: {ret.settlement_status}")
    print(f"Applied Amount: Rs. {ret.applied_amount}")
    print(f"Cash Receipt Number: {ret.cash_receipt_number}")
    print(f"Return Status: {ret.return_status}")
    
    # Check return items
    print(f"\nReturn Items:")
    items = ReturnItem.objects.filter(return_obj=ret)
    for item in items:
        print(f"  - {item.product.name}: {item.quantity} × Rs. {item.price} = Rs. {item.total_price}")
    
    # Calculate settlement status consistency
    print(f"\n--- Settlement Analysis ---")
    print(f"Total Amount: Rs. {ret.total_amount}")
    print(f"Applied Amount: Rs. {ret.applied_amount}")
    print(f"Remaining: Rs. {ret.total_amount - ret.applied_amount}")
    
    # Check what the settlement status should be
    if ret.settlement_method == 'credit_note':
        if ret.applied_amount == 0:
            expected_status = 'available'
        elif ret.applied_amount < ret.total_amount:
            expected_status = 'partially_applied'
        elif ret.applied_amount == ret.total_amount:
            expected_status = 'fully_applied'
        else:
            expected_status = 'ERROR: Applied > Total'
    elif ret.settlement_method == 'cash':
        if ret.cash_receipt_number:
            expected_status = 'settled_cash'
        else:
            expected_status = 'unsettled'
    else:
        expected_status = 'unknown_method'
    
    print(f"Current Status: {ret.settlement_status}")
    print(f"Expected Status: {expected_status}")
    if ret.settlement_status != expected_status:
        print(f"⚠️ STATUS MISMATCH! Should be '{expected_status}' but is '{ret.settlement_status}'")
    else:
        print(f"✓ Status is correct")
    
except Return.DoesNotExist:
    print("\n❌ Return #43 does not exist")
except Exception as e:
    print(f"\n❌ Error checking Return #43: {e}")

# Check Bill #47
try:
    bill = Bill.objects.get(id=47)
    print("\n\n--- BILL #47 ---")
    print(f"Bill Number: {bill.bill_number}")
    print(f"Shop: {bill.shop.shop_name}")
    print(f"Date: {bill.bill_date}")
    print(f"Total Amount: Rs. {bill.total_amount}")
    print(f"Paid Amount: Rs. {bill.paid_amount}")
    print(f"Balance: Rs. {bill.balance_amount}")
    print(f"Payment Status: {bill.payment_status}")
    
    # Check payments
    print(f"\n--- Payments for Bill #47 ---")
    payments = OldPayment.objects.filter(bill=bill).order_by('payment_date')
    total_payments = Decimal('0.00')
    for payment in payments:
        print(f"  Payment #{payment.id}: Rs. {payment.amount} on {payment.payment_date}")
        print(f"    Method: {payment.payment_method}")
        if payment.return_ref:
            print(f"    ⚠️ Linked to Return: {payment.return_ref.return_number}")
        total_payments += payment.amount
    
    print(f"\nTotal Payments Sum: Rs. {total_payments}")
    
    # Check calculation consistency
    print(f"\n--- Bill Balance Analysis ---")
    calculated_balance = bill.total_amount - bill.paid_amount
    print(f"Total Amount: Rs. {bill.total_amount}")
    print(f"Paid Amount: Rs. {bill.paid_amount}")
    print(f"Stored Balance: Rs. {bill.balance_amount}")
    print(f"Calculated Balance: Rs. {calculated_balance}")
    
    if bill.balance_amount != calculated_balance:
        print(f"⚠️ BALANCE MISMATCH! Stored ({bill.balance_amount}) != Calculated ({calculated_balance})")
    else:
        print(f"✓ Balance is correct")
    
    # Check payment status
    if bill.balance_amount == 0:
        expected_payment_status = 'paid'
    elif bill.paid_amount == 0:
        expected_payment_status = 'unpaid'
    else:
        expected_payment_status = 'partial'
    
    print(f"\nCurrent Payment Status: {bill.payment_status}")
    print(f"Expected Payment Status: {expected_payment_status}")
    if bill.payment_status != expected_payment_status:
        print(f"⚠️ PAYMENT STATUS MISMATCH! Should be '{expected_payment_status}' but is '{bill.payment_status}'")
    else:
        print(f"✓ Payment status is correct")
    
except Bill.DoesNotExist:
    print("\n❌ Bill #47 does not exist")
except Exception as e:
    print(f"\n❌ Error checking Bill #47: {e}")

# Check if Return #43 is linked to Bill #47
print("\n\n--- LINKAGE ANALYSIS ---")
try:
    ret = Return.objects.get(id=43)
    bill = Bill.objects.get(id=47)
    
    # Check if there's a payment linking them
    linked_payments = OldPayment.objects.filter(bill=bill, return_ref=ret)
    if linked_payments.exists():
        print(f"✓ Found {linked_payments.count()} payment(s) linking Return #43 to Bill #47:")
        for payment in linked_payments:
            print(f"  Payment #{payment.id}: Rs. {payment.amount}")
            print(f"    This should reduce Return #43 applied_amount")
            print(f"    This should increase Bill #47 paid_amount")
    else:
        print(f"⚠️ No payments found linking Return #43 to Bill #47")
        print(f"   If return was applied to bill, there should be a Payment record")
    
    # Cross-check
    print(f"\n--- Cross-Verification ---")
    all_payments_using_return = OldPayment.objects.filter(return_ref=ret)
    print(f"Total payments using Return #43 credit: {all_payments_using_return.count()}")
    total_used = sum(p.amount for p in all_payments_using_return)
    print(f"Total amount used from return: Rs. {total_used}")
    print(f"Return's applied_amount field: Rs. {ret.applied_amount}")
    
    if total_used != ret.applied_amount:
        print(f"⚠️ MISMATCH! Sum of payments ({total_used}) != applied_amount ({ret.applied_amount})")
    else:
        print(f"✓ Applied amount matches payment records")
        
except Exception as e:
    print(f"❌ Error in linkage analysis: {e}")

print("\n" + "=" * 80)
print("INVESTIGATION COMPLETE")
print("=" * 80)
