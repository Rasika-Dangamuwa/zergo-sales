import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, Bill
from payments.models import OldPayment
from decimal import Decimal

print("=" * 80)
print("FIXING Return #43 and Bill #47")
print("=" * 80)

# Fix Return #43
try:
    ret = Return.objects.get(id=43)
    print(f"\n--- Return #43 BEFORE Fix ---")
    print(f"Applied Amount: Rs. {ret.applied_amount}")
    print(f"Total Amount: Rs. {ret.total_amount}")
    print(f"Settlement Status: {ret.settlement_status}")
    
    # Determine correct settlement status
    if ret.applied_amount == 0:
        correct_status = 'available'
    elif ret.applied_amount < ret.total_amount:
        correct_status = 'partially_applied'
    elif ret.applied_amount >= ret.total_amount:
        correct_status = 'fully_applied'
    
    if ret.settlement_status != correct_status:
        print(f"\n✓ Updating settlement_status: '{ret.settlement_status}' → '{correct_status}'")
        ret.settlement_status = correct_status
        ret.save()
        print("✓ Return #43 fixed!")
    else:
        print(f"\n✓ Settlement status is already correct: {correct_status}")
        
except Exception as e:
    print(f"\n❌ Error fixing Return #43: {e}")

# Fix Bill #47
try:
    bill = Bill.objects.get(id=47)
    print(f"\n--- Bill #47 BEFORE Fix ---")
    print(f"Total Amount: Rs. {bill.total_amount}")
    print(f"Paid Amount: Rs. {bill.paid_amount}")
    print(f"Balance Amount: Rs. {bill.balance_amount}")
    print(f"Payment Status: {bill.payment_status}")
    
    # Calculate what paid_amount should be from completed payments
    completed_payments = OldPayment.objects.filter(
        bill=bill,
        status='completed'
    ).aggregate(total=django.db.models.Sum('amount'))['total'] or Decimal('0')
    
    print(f"\nTotal Completed Payments from DB: Rs. {completed_payments}")
    
    if bill.paid_amount != completed_payments:
        print(f"\n✓ Updating paid_amount: Rs. {bill.paid_amount} → Rs. {completed_payments}")
        bill.paid_amount = completed_payments
        
        # Recalculate balance
        bill.balance_amount = bill.total_amount - bill.paid_amount
        print(f"✓ Updating balance_amount: Rs. {bill.balance_amount}")
        
        # Recalculate payment status
        if bill.paid_amount >= bill.total_amount:
            bill.payment_status = 'paid'
        elif bill.paid_amount > 0:
            bill.payment_status = 'partial'
        else:
            bill.payment_status = 'unpaid'
        print(f"✓ Updating payment_status: {bill.payment_status}")
        
        bill.save()
        print("\n✓ Bill #47 fixed!")
    else:
        print(f"\n✓ Bill amounts are already correct")
        
    print(f"\n--- Bill #47 AFTER Fix ---")
    bill.refresh_from_db()
    print(f"Total Amount: Rs. {bill.total_amount}")
    print(f"Paid Amount: Rs. {bill.paid_amount}")
    print(f"Balance Amount: Rs. {bill.balance_amount}")
    print(f"Payment Status: {bill.payment_status}")
        
except Exception as e:
    print(f"\n❌ Error fixing Bill #47: {e}")

print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

try:
    ret = Return.objects.get(id=43)
    bill = Bill.objects.get(id=47)
    
    print(f"\nReturn #43:")
    print(f"  Settlement Status: {ret.settlement_status}")
    print(f"  Applied: {ret.applied_amount} / Total: {ret.total_amount}")
    
    print(f"\nBill #47:")
    print(f"  Payment Status: {bill.payment_status}")
    print(f"  Paid: {bill.paid_amount} / Total: {bill.total_amount}")
    print(f"  Balance: {bill.balance_amount}")
    
    # Check if both are correct now
    issues = []
    
    # Check return
    if ret.applied_amount >= ret.total_amount and ret.settlement_status != 'fully_applied':
        issues.append("Return settlement_status should be 'fully_applied'")
    elif ret.applied_amount < ret.total_amount and ret.applied_amount > 0 and ret.settlement_status != 'partially_applied':
        issues.append("Return settlement_status should be 'partially_applied'")
    elif ret.applied_amount == 0 and ret.settlement_status != 'available':
        issues.append("Return settlement_status should be 'available'")
    
    # Check bill
    if bill.paid_amount != (bill.total_amount - bill.balance_amount):
        issues.append("Bill paid_amount doesn't match (total - balance)")
    
    if bill.paid_amount >= bill.total_amount and bill.payment_status != 'paid':
        issues.append("Bill payment_status should be 'paid'")
    elif bill.paid_amount > 0 and bill.paid_amount < bill.total_amount and bill.payment_status != 'partial':
        issues.append("Bill payment_status should be 'partial'")
    elif bill.paid_amount == 0 and bill.payment_status != 'unpaid':
        issues.append("Bill payment_status should be 'unpaid'")
    
    if issues:
        print(f"\n⚠️ REMAINING ISSUES:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"\n✅ ALL ISSUES FIXED! Both records are now consistent.")
    
except Exception as e:
    print(f"\n❌ Error in verification: {e}")

print("\n" + "=" * 80)
