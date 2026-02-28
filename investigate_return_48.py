import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, ReturnItem
from payments.models import OldPayment
from decimal import Decimal

# Get Return 48
try:
    return_obj = Return.objects.get(pk=48)
    
    print("=" * 80)
    print(f"RETURN #{return_obj.pk} - {return_obj.return_number}")
    print("=" * 80)
    
    print(f"\nBasic Information:")
    print(f"  Shop: {return_obj.shop.shop_name}")
    print(f"  Return Date: {return_obj.return_date}")
    print(f"  Created By: {return_obj.created_by.username}")
    print(f"  Return Reason: {return_obj.get_return_reason_display()}")
    
    print(f"\nStatus Information:")
    print(f"  Return Status: {return_obj.return_status} ({return_obj.get_return_status_display()})")
    print(f"  Settlement Method: {return_obj.settlement_method} ({return_obj.get_settlement_method_display()})")
    print(f"  Settlement Status: {return_obj.settlement_status} ({return_obj.get_settlement_status_display()})")
    
    print(f"\nFinancial Information:")
    print(f"  Total Amount: Rs. {return_obj.total_amount}")
    print(f"  Applied Amount: Rs. {return_obj.applied_amount}")
    print(f"  Remaining: Rs. {return_obj.total_amount - return_obj.applied_amount}")
    
    if return_obj.cash_receipt_number:
        print(f"\nCash Payment:")
        print(f"  Voucher Number: {return_obj.cash_receipt_number}")
        print(f"  Paid By: {return_obj.cash_paid_by.username if return_obj.cash_paid_by else 'N/A'}")
        print(f"  Paid At: {return_obj.cash_paid_at}")
    
    print(f"\nApproval Information:")
    print(f"  Approved By: {return_obj.approved_by.username if return_obj.approved_by else 'N/A'}")
    print(f"  Approved At: {return_obj.approved_at}")
    
    # Get return items
    items = return_obj.items.all()
    print(f"\nReturn Items ({items.count()} items):")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item.product.product_name}")
        print(f"     Qty: {item.quantity}, FOC: {item.foc_quantity}")
        print(f"     Price: Rs. {item.unit_price}, Total: Rs. {item.total_price}")
    
    # Get payment applications
    payments = OldPayment.objects.filter(return_ref=return_obj)
    print(f"\nPayment Applications ({payments.count()} payments):")
    if payments.exists():
        for i, payment in enumerate(payments, 1):
            print(f"  {i}. Bill: {payment.bill.bill_number}")
            print(f"     Amount: Rs. {payment.amount}")
            print(f"     Date: {payment.payment_date}")
            print(f"     Status: {payment.status}")
    else:
        print("  No payments applied yet")
    
    # Check for any issues
    print(f"\n" + "=" * 80)
    print("POTENTIAL ISSUES:")
    print("=" * 80)
    
    issues_found = False
    
    # Issue 1: Settlement status vs applied amount mismatch
    if return_obj.settlement_status == 'fully_applied' and return_obj.applied_amount < return_obj.total_amount:
        print(f"❌ Status is 'fully_applied' but applied amount (Rs. {return_obj.applied_amount}) < total (Rs. {return_obj.total_amount})")
        issues_found = True
    
    if return_obj.settlement_status == 'available' and return_obj.applied_amount > 0:
        print(f"❌ Status is 'available' but applied amount is Rs. {return_obj.applied_amount} (should be 0)")
        issues_found = True
    
    if return_obj.settlement_status == 'partially_applied' and return_obj.applied_amount == return_obj.total_amount:
        print(f"❌ Status is 'partially_applied' but entire amount has been used")
        issues_found = True
    
    # Issue 2: Cash settlement inconsistencies
    if return_obj.settlement_method == 'cash':
        if return_obj.settlement_status == 'settled_cash' and not return_obj.cash_receipt_number:
            print(f"❌ Cash settled but no voucher number")
            issues_found = True
        
        if return_obj.cash_receipt_number and return_obj.settlement_status == 'unsettled':
            print(f"❌ Has cash voucher {return_obj.cash_receipt_number} but status is 'unsettled'")
            issues_found = True
    
    # Issue 3: Payment total mismatch
    total_payments = sum(p.amount for p in payments)
    if total_payments != return_obj.applied_amount:
        print(f"❌ Payment total (Rs. {total_payments}) doesn't match applied_amount (Rs. {return_obj.applied_amount})")
        issues_found = True
    
    # Issue 4: Approval status check
    if return_obj.return_status != 'approved':
        print(f"❌ Return status is '{return_obj.return_status}' instead of 'approved'")
        issues_found = True
    
    if not issues_found:
        print("✅ No issues detected")
    
    print("\n" + "=" * 80)
    
except Return.DoesNotExist:
    print(f"❌ Return #48 not found in database")
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
