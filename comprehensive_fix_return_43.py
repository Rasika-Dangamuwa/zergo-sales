import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, Bill
from payments.models import OldPayment
from decimal import Decimal

print("=" * 80)
print("COMPREHENSIVE FIX: Return #43 and Bill #47")
print("=" * 80)

# Step 1: Fix Payment #47 status
try:
    payment = OldPayment.objects.get(id=47)
    print(f"\n--- Payment #47 ---")
    print(f"Current Status: {payment.status}")
    print(f"Is Provisional: {payment.is_provisional}")
    print(f"Return Status: {payment.return_ref.return_status}")
    
    # If return is approved but payment is still pending, update it
    if payment.return_ref.return_status == 'approved' and payment.status == 'pending':
        print(f"\n✓ Return is approved → Updating payment status to 'completed'")
        payment.status = 'completed'
        payment.save()
        print("✓ Payment #47 status updated!")
    else:
        print(f"\n✓ Payment status is already correct")
        
except Exception as e:
    print(f"\n❌ Error fixing Payment #47: {e}")

# Step 2: Recalculate Bill #47 amounts
try:
    bill = Bill.objects.get(id=47)
    print(f"\n--- Bill #47 ---")
    print(f"Before Fix:")
    print(f"  Paid Amount: Rs. {bill.paid_amount}")
    print(f"  Balance: Rs. {bill.balance_amount}")
    print(f"  Payment Status: {bill.payment_status}")
    
    # Calculate total from completed payments
    completed_payments = OldPayment.objects.filter(
        bill=bill,
        status='completed'
    ).aggregate(total=django.db.models.Sum('amount'))['total'] or Decimal('0')
    
    print(f"\nCompleted Payments Total: Rs. {completed_payments}")
    
    # Update bill amounts
    bill.paid_amount = completed_payments
    bill.balance_amount = bill.total_amount - bill.paid_amount
    
    # Update payment status
    if bill.paid_amount >= bill.total_amount:
        bill.payment_status = 'paid'
    elif bill.paid_amount > 0:
        bill.payment_status = 'partial'
    else:
        bill.payment_status = 'unpaid'
    
    bill.save()
    
    print(f"\nAfter Fix:")
    print(f"  Paid Amount: Rs. {bill.paid_amount}")
    print(f"  Balance: Rs. {bill.balance_amount}")
    print(f"  Payment Status: {bill.payment_status}")
    print("\n✓ Bill #47 updated!")
    
except Exception as e:
    print(f"\n❌ Error fixing Bill #47: {e}")

# Step 3: Update Return #43 settlement status
try:
    ret = Return.objects.get(id=43)
    print(f"\n--- Return #43 ---")
    print(f"Before Fix:")
    print(f"  Applied: Rs. {ret.applied_amount} / Total: Rs. {ret.total_amount}")
    print(f"  Settlement Status: {ret.settlement_status}")
    
    # Determine correct settlement status
    if ret.applied_amount >= ret.total_amount:
        correct_status = 'fully_applied'
    elif ret.applied_amount > 0:
        correct_status = 'partially_applied'
    else:
        correct_status = 'available'
    
    if ret.settlement_status != correct_status:
        print(f"\n✓ Updating settlement status to '{correct_status}'")
        ret.settlement_status = correct_status
        ret.save()
    
    print(f"\nAfter Fix:")
    print(f"  Applied: Rs. {ret.applied_amount} / Total: Rs. {ret.total_amount}")
    print(f"  Settlement Status: {ret.settlement_status}")
    print("\n✓ Return #43 updated!")
    
except Exception as e:
    print(f"\n❌ Error fixing Return #43: {e}")

# Final Verification
print("\n" + "=" * 80)
print("FINAL VERIFICATION")
print("=" * 80)

try:
    payment = OldPayment.objects.get(id=47)
    bill = Bill.objects.get(id=47)
    ret = Return.objects.get(id=43)
    
    issues = []
    
    # Check payment
    if payment.return_ref.return_status == 'approved' and payment.status != 'completed':
        issues.append(f"Payment #47: Status is '{payment.status}' but return is approved (should be 'completed')")
    
    # Check bill
    completed_total = OldPayment.objects.filter(bill=bill, status='completed').aggregate(
        total=django.db.models.Sum('amount'))['total'] or Decimal('0')
    
    if bill.paid_amount != completed_total:
        issues.append(f"Bill #47: paid_amount ({bill.paid_amount}) doesn't match completed payments ({completed_total})")
    
    if bill.balance_amount != (bill.total_amount - bill.paid_amount):
        issues.append(f"Bill #47: balance_amount calculation error")
    
    if bill.paid_amount >= bill.total_amount and bill.payment_status != 'paid':
        issues.append(f"Bill #47: Should be 'paid' but is '{bill.payment_status}'")
    
    # Check return
    if ret.applied_amount >= ret.total_amount and ret.settlement_status != 'fully_applied':
        issues.append(f"Return #43: Should be 'fully_applied' but is '{ret.settlement_status}'")
    
    if issues:
        print("\n⚠️ REMAINING ISSUES:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ SUCCESS! All records are now consistent:")
        print(f"\n  Payment #47: {payment.status} (Rs. {payment.amount})")
        print(f"  Bill #47: {bill.payment_status} (Paid: {bill.paid_amount}/{bill.total_amount})")
        print(f"  Return #43: {ret.settlement_status} (Applied: {ret.applied_amount}/{ret.total_amount})")
    
except Exception as e:
    print(f"\n❌ Verification error: {e}")

print("\n" + "=" * 80)
