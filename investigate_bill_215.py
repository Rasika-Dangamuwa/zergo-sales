"""
Investigate Bill #215
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill, BillItem, Return
from payments.models import SalesAccountSettlement, BadDebtWriteOff
from decimal import Decimal

print("\n" + "="*100)
print("INVESTIGATING BILL #215")
print("="*100)

try:
    bill = Bill.objects.get(pk=215)
    
    print(f"\n📋 BILL DETAILS:")
    print(f"   ID: {bill.pk}")
    print(f"   Bill Number: {bill.bill_number}")
    print(f"   Shop: {bill.shop.shop_name if bill.shop else bill.customer_name}")
    print(f"   Sales Rep: {bill.sales_rep.get_full_name()}")
    print(f"   Bill Date: {bill.bill_date}")
    print(f"   Status: {bill.bill_status}")
    print(f"   Settlement Status: {bill.settlement_status}")
    
    print(f"\n💰 FINANCIAL SUMMARY:")
    print(f"   Subtotal: Rs. {bill.subtotal:,.2f}")
    print(f"   Discount Amount: Rs. {bill.discount_amount:,.2f}")
    print(f"   Total Amount: Rs. {bill.total_amount:,.2f}")
    print(f"   Paid Amount: Rs. {bill.paid_amount:,.2f}")
    print(f"   Balance Amount: Rs. {bill.balance_amount:,.2f}")
    
    # Get bill items
    items = bill.items.all()
    print(f"\n📦 BILL ITEMS ({items.count()}):")
    for item in items:
        print(f"\n   • {item.product.product_name}")
        print(f"     Quantity: {item.quantity}")
        print(f"     FOC Qty: {item.foc_quantity}")
        print(f"     Unit Price: Rs. {item.unit_price:,.2f}")
        print(f"     Line Total: Rs. {item.line_total:,.2f}")
    
    # Get settlements
    settlements = bill.settlements.all().order_by('created_at')
    print(f"\n💳 SETTLEMENTS ({settlements.count()}):")
    
    total_completed = Decimal('0')
    total_pending = Decimal('0')
    total_cancelled = Decimal('0')
    
    for s in settlements:
        status_icon = "✅" if s.settlement_status == 'completed' else "⏳" if s.settlement_status == 'pending' else "❌"
        print(f"\n   {status_icon} {s.settlement_number}")
        print(f"      Amount: Rs. {s.amount:,.2f}")
        print(f"      Method: {s.get_settlement_method_display()}")
        print(f"      Status: {s.settlement_status}")
        print(f"      Date: {s.settlement_date}")
        print(f"      Received By: {s.received_by.get_full_name()}")
        
        if s.settlement_method == 'cheque':
            print(f"      Cheque No: {s.reference_number}")
            print(f"      Bank: {s.bank_name}")
            print(f"      Cheque Date: {s.cheque_date}")
            print(f"      Collected: {'Yes' if s.cheque_collected else 'No'}")
        
        if s.settlement_method == 'bank_transfer':
            print(f"      Reference: {s.reference_number}")
            print(f"      Bank: {s.bank_name}")
        
        if s.return_ref:
            print(f"      Return: {s.return_ref.return_number}")
        
        if s.settlement_status == 'completed':
            total_completed += s.amount
        elif s.settlement_status == 'pending':
            total_pending += s.amount
        elif s.settlement_status == 'cancelled':
            total_cancelled += s.amount
    
    print(f"\n   SETTLEMENT TOTALS:")
    print(f"   ✅ Completed: Rs. {total_completed:,.2f}")
    print(f"   ⏳ Pending: Rs. {total_pending:,.2f}")
    print(f"   ❌ Cancelled: Rs. {total_cancelled:,.2f}")
    
    # Verify paid amount
    print(f"\n🔍 VERIFICATION:")
    print(f"   Bill.paid_amount: Rs. {bill.paid_amount:,.2f}")
    print(f"   Completed Settlements: Rs. {total_completed:,.2f}")
    print(f"   Match: {'✅ YES' if bill.paid_amount == total_completed else '❌ NO'}")
    
    # Check for bad debt write-offs
    writeoffs = BadDebtWriteOff.objects.filter(bill=bill).order_by('created_at')
    if writeoffs.exists():
        print(f"\n💸 BAD DEBT WRITE-OFFS ({writeoffs.count()}):")
        total_writeoff = Decimal('0')
        for wo in writeoffs:
            status_icon = "✅" if wo.approval_status == 'approved' else "⏳" if wo.approval_status == 'pending' else "❌"
            print(f"\n   {status_icon} Write-Off #{wo.pk}")
            print(f"      Write-Off Number: {wo.write_off_number}")
            print(f"      Amount: Rs. {wo.write_off_amount:,.2f}")
            print(f"      Approval Status: {wo.approval_status}")
            print(f"      Executed: {'Yes' if wo.executed else 'No'}")
            print(f"      Reason: {wo.get_reason_display()}")
            print(f"      Requested By: {wo.requested_by.get_full_name()}")
            print(f"      Requested Date: {wo.created_at}")
            if wo.approved_by:
                print(f"      Approved By: {wo.approved_by.get_full_name()}")
                print(f"      Approval Date: {wo.approval_date}")
            if wo.executed_at:
                print(f"      Executed At: {wo.executed_at}")
            if wo.detailed_notes:
                print(f"      Notes: {wo.detailed_notes}")
            print(f"      Bill Updated: {'Yes' if wo.bill_updated else 'No'}")
            print(f"      Shop Balance Updated: {'Yes' if wo.shop_balance_updated else 'No'}")
            
            if wo.approval_status == 'approved' and wo.executed:
                total_writeoff += wo.write_off_amount
        
        print(f"\n   TOTAL APPROVED & EXECUTED WRITE-OFFS: Rs. {total_writeoff:,.2f}")
        
        # Calculate what should be the actual balance
        expected_balance = bill.total_amount - bill.paid_amount - total_writeoff
        print(f"\n   BALANCE CALCULATION:")
        print(f"   Total Amount: Rs. {bill.total_amount:,.2f}")
        print(f"   - Paid Amount: Rs. {bill.paid_amount:,.2f}")
        print(f"   - Write-Offs: Rs. {total_writeoff:,.2f}")
        print(f"   = Expected Balance: Rs. {expected_balance:,.2f}")
        print(f"   Actual Balance: Rs. {bill.balance_amount:,.2f}")
        print(f"   Match: {'✅ YES' if abs(expected_balance - bill.balance_amount) < Decimal('0.01') else '❌ NO'}")
    
    
    
    # Check returns
    returns = Return.objects.filter(bill=bill).order_by('created_at')
    if returns.exists():
        print(f"\n🔄 RELATED RETURNS ({returns.count()}):")
        for r in returns:
            print(f"\n   • {r.return_number}")
            print(f"     Total: Rs. {r.total_amount:,.2f}")
            print(f"     Status: {r.return_status}")
            print(f"     Settlement Method: {r.get_settlement_method_display()}")
            print(f"     Settlement Status: {r.get_settlement_status_display()}")
    
except Bill.DoesNotExist:
    print("\n❌ Bill #215 not found in database")

print("\n" + "="*100)
