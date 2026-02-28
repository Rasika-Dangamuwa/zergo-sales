"""
Full Investigation of Bill #213
URL: https://192.168.1.4:8000/sales/213/
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill, BillItem
from payments.models import SalesAccountSettlement, BadDebtWriteOff
from products.models import StockMovement

def investigate_bill_213():
    print("=" * 100)
    print("COMPREHENSIVE INVESTIGATION: BILL #213")
    print("URL: https://192.168.1.4:8000/sales/213/")
    print("=" * 100)
    
    bill = Bill.objects.get(pk=213)
    
    # Basic Information
    print(f"\n📋 BASIC INFORMATION:")
    print(f"   ID: {bill.pk}")
    print(f"   Bill Number: {bill.bill_number}")
    print(f"   Bill Date: {bill.bill_date}")
    print(f"   Status: {bill.bill_status}")
    print(f"   Settlement Status: {bill.settlement_status}")
    print(f"   Created At: {bill.created_at}")
    print(f"   Updated At: {bill.updated_at}")
    
    # Customer Information
    print(f"\n👤 CUSTOMER INFORMATION:")
    print(f"   Shop: {bill.shop or 'None'}")
    if bill.shop:
        print(f"   Shop ID: {bill.shop.pk}")
        print(f"   Shop Code: {bill.shop.shop_code}")
        print(f"   Shop Name: {bill.shop.shop_name}")
        print(f"   Owner: {bill.shop.owner_name}")
        print(f"   Current Balance: Rs. {bill.shop.current_balance:,.2f}")
    else:
        print(f"   ⚠️  NO SHOP - This is an UNREGISTERED CUSTOMER bill")
        print(f"   Customer Name: {bill.customer_name or 'NOT SET'}")
        print(f"   Type: Unregistered/Walk-in Customer")
    
    # Sales Rep
    print(f"\n👨‍💼 SALES REPRESENTATIVE:")
    print(f"   Rep: {bill.sales_rep.get_full_name()}")
    print(f"   Username: {bill.sales_rep.username}")
    print(f"   User Type: {bill.sales_rep.user_type}")
    
    # Financial Summary
    print(f"\n💰 FINANCIAL SUMMARY:")
    print(f"   Subtotal: Rs. {bill.subtotal:,.2f}")
    print(f"   Discount %: {bill.discount_percentage}%")
    print(f"   Discount Amount: Rs. {bill.discount_amount:,.2f}")
    print(f"   Tax Amount: Rs. {bill.tax_amount:,.2f}")
    print(f"   Total Amount: Rs. {bill.total_amount:,.2f}")
    print(f"   Paid Amount: Rs. {bill.paid_amount:,.2f}")
    print(f"   Balance Amount: Rs. {bill.balance_amount:,.2f}")
    
    # Bill Items
    items = bill.items.all().order_by('id')
    print(f"\n📦 BILL ITEMS ({items.count()}):")
    total_qty = Decimal('0')
    total_foc = Decimal('0')
    total_value = Decimal('0')
    
    for idx, item in enumerate(items, 1):
        print(f"\n   {idx}. {item.product.product_name}")
        print(f"      Product ID: {item.product.pk}")
        print(f"      Quantity: {item.quantity}")
        print(f"      FOC Quantity: {item.foc_quantity}")
        print(f"      Unit Price: Rs. {item.unit_price:,.2f}")
        print(f"      Discount %: {item.discount_percentage}%")
        print(f"      Discount Amount: Rs. {item.discount_amount:,.2f}")
        print(f"      Tax %: {item.tax_percentage}%")
        print(f"      Tax Amount: Rs. {item.tax_amount:,.2f}")
        print(f"      Line Total: Rs. {item.line_total:,.2f}")
        
        total_qty += item.quantity
        total_foc += item.foc_quantity
        total_value += item.line_total
    
    print(f"\n   TOTALS:")
    print(f"   Total Quantity: {total_qty}")
    print(f"   Total FOC: {total_foc}")
    print(f"   Total Value: Rs. {total_value:,.2f}")
    
    # Stock Movements
    print(f"\n📊 STOCK MOVEMENTS:")
    # Note: StockMovement uses reference_number, not direct bill FK
    movements = StockMovement.objects.filter(reference_number=bill.bill_number).order_by('created_at')
    if movements.exists():
        print(f"   Found {movements.count()} stock movements:")
        for idx, mv in enumerate(movements, 1):
            print(f"\n   {idx}. Movement #{mv.pk}")
            print(f"      Product: {mv.product.product_name}")
            print(f"      Type: {mv.movement_type}")
            print(f"      Quantity: {mv.quantity}")
            if hasattr(mv, 'foc_quantity'):
                print(f"      FOC Quantity: {mv.foc_quantity}")
            print(f"      Reference: {mv.reference_number}")
            print(f"      Previous Stock: {mv.previous_quantity}")
            print(f"      New Stock: {mv.new_quantity}")
            print(f"      Created: {mv.created_at}")
    else:
        print(f"   ⚠️  NO STOCK MOVEMENTS FOUND for reference {bill.bill_number}")
    
    # Payments/Settlements
    print(f"\n💳 PAYMENT SETTLEMENTS:")
    settlements = bill.settlements.all().order_by('settlement_date')
    if settlements.exists():
        print(f"   Found {settlements.count()} settlements:")
        total_completed = Decimal('0')
        total_pending = Decimal('0')
        total_cancelled = Decimal('0')
        
        for idx, s in enumerate(settlements, 1):
            status_icon = "✅" if s.settlement_status == 'completed' else "⏳" if s.settlement_status == 'pending_verification' else "❌"
            print(f"\n   {idx}. {status_icon} {s.settlement_number}")
            print(f"      Amount: Rs. {s.amount:,.2f}")
            print(f"      Method: {s.get_settlement_method_display()}")
            print(f"      Status: {s.get_settlement_status_display()}")
            print(f"      Date: {s.settlement_date}")
            
            if s.settlement_method == 'cheque':
                print(f"      Cheque/Reference No: {s.reference_number}")
                print(f"      Bank: {s.bank_name}")
                print(f"      Cheque Date: {s.cheque_date}")
                print(f"      Collected: {'Yes' if s.cheque_collected else 'No'}")
            
            if s.settlement_status == 'completed':
                total_completed += s.amount
            elif s.settlement_status in ['pending', 'pending_verification']:
                total_pending += s.amount
            elif s.settlement_status == 'cancelled':
                total_cancelled += s.amount
        
        print(f"\n   SETTLEMENT SUMMARY:")
        print(f"   ✅ Completed: Rs. {total_completed:,.2f}")
        print(f"   ⏳ Pending: Rs. {total_pending:,.2f}")
        print(f"   ❌ Cancelled: Rs. {total_cancelled:,.2f}")
        
        # Verify paid amount
        print(f"\n   VERIFICATION:")
        print(f"   Bill.paid_amount: Rs. {bill.paid_amount:,.2f}")
        print(f"   Completed Settlements: Rs. {total_completed:,.2f}")
        print(f"   Match: {'✅ YES' if bill.paid_amount == total_completed else '❌ NO - DISCREPANCY!'}")
    else:
        print(f"   ⚠️  NO SETTLEMENTS/PAYMENTS")
    
    # Write-Offs
    print(f"\n💸 BAD DEBT WRITE-OFFS:")
    writeoffs = BadDebtWriteOff.objects.filter(bill=bill).order_by('created_at')
    if writeoffs.exists():
        print(f"   Found {writeoffs.count()} write-offs:")
        total_executed_writeoff = Decimal('0')
        
        for idx, wo in enumerate(writeoffs, 1):
            status_icon = "✅" if wo.executed else "⏳" if wo.approval_status == 'pending' else "❌"
            print(f"\n   {idx}. {status_icon} {wo.write_off_number}")
            print(f"      Amount: Rs. {wo.write_off_amount:,.2f}")
            print(f"      Approval Status: {wo.approval_status}")
            print(f"      Executed: {'Yes' if wo.executed else 'No'}")
            print(f"      Reason: {wo.get_reason_display()}")
            print(f"      Requested By: {wo.requested_by.get_full_name()}")
            print(f"      Requested Date: {wo.created_at}")
            if wo.approved_by:
                print(f"      Approved By: {wo.approved_by.get_full_name()}")
                print(f"      Approval Date: {wo.approval_date}")
            print(f"      Bill Updated: {'Yes' if wo.bill_updated else 'No'}")
            print(f"      Shop Balance Updated: {'Yes' if wo.shop_balance_updated else 'No'}")
            if wo.customer_name:
                print(f"      Customer Name: {wo.customer_name}")
            if wo.detailed_notes:
                print(f"      Notes: {wo.detailed_notes[:100]}...")
            
            if wo.executed and wo.approval_status == 'approved':
                total_executed_writeoff += wo.write_off_amount
        
        if total_executed_writeoff > 0:
            print(f"\n   TOTAL EXECUTED WRITE-OFFS: Rs. {total_executed_writeoff:,.2f}")
    else:
        print(f"   ⚠️  NO WRITE-OFFS")
    
    # Notes
    if bill.notes:
        print(f"\n📝 BILL NOTES:")
        print(f"   {bill.notes}")
    
    # Analysis
    print(f"\n🔍 ANALYSIS:")
    
    # Check if unregistered customer properly set
    if not bill.shop:
        if bill.customer_name:
            print(f"   ✅ Unregistered customer properly configured")
            print(f"      Customer Name: '{bill.customer_name}'")
            print(f"      Can write off: Yes (no shop balance to update)")
        else:
            print(f"   ⚠️  WARNING: No shop AND no customer name!")
            print(f"      This bill is incomplete - should have customer_name set")
    
    # Check balance calculation
    expected_balance = bill.total_amount - bill.paid_amount
    if writeoffs.filter(executed=True, approval_status='approved').exists():
        total_writeoff = sum(wo.write_off_amount for wo in writeoffs.filter(executed=True, approval_status='approved'))
        expected_balance -= total_writeoff
        print(f"\n   Balance Calculation:")
        print(f"   Total: Rs. {bill.total_amount:,.2f}")
        print(f"   - Paid: Rs. {bill.paid_amount:,.2f}")
        print(f"   - Written Off: Rs. {total_writeoff:,.2f}")
        print(f"   = Expected: Rs. {expected_balance:,.2f}")
        print(f"   Actual: Rs. {bill.balance_amount:,.2f}")
        print(f"   Match: {'✅ YES' if bill.balance_amount == expected_balance else '❌ NO - DISCREPANCY!'}")
    else:
        print(f"\n   Balance Calculation:")
        print(f"   Rs. {bill.total_amount:,.2f} (total) - Rs. {bill.paid_amount:,.2f} (paid) = Rs. {expected_balance:,.2f}")
        print(f"   Actual Balance: Rs. {bill.balance_amount:,.2f}")
        print(f"   Match: {'✅ YES' if bill.balance_amount == expected_balance else '❌ NO - DISCREPANCY!'}")
    
    # Write-off eligibility
    print(f"\n   Write-Off Eligibility:")
    can_writeoff = True
    reasons = []
    
    if bill.balance_amount <= 0:
        can_writeoff = False
        reasons.append("No outstanding balance")
    
    if bill.bill_status == 'cancelled':
        can_writeoff = False
        reasons.append("Bill is cancelled")
    
    pending_settlements = bill.settlements.filter(settlement_status__in=['pending', 'pending_verification'])
    if pending_settlements.exists():
        can_writeoff = False
        reasons.append(f"{pending_settlements.count()} pending settlements must be verified first")
    
    existing_writeoff = writeoffs.filter(executed=True).first()
    if existing_writeoff:
        can_writeoff = False
        reasons.append(f"Already written off ({existing_writeoff.write_off_number})")
    
    if can_writeoff:
        print(f"   ✅ ELIGIBLE for write-off")
        print(f"      Write-off amount would be: Rs. {bill.balance_amount:,.2f}")
        if bill.shop:
            print(f"      Shop balance would be reduced by: Rs. {bill.balance_amount:,.2f}")
        else:
            print(f"      No shop balance update (unregistered customer)")
    else:
        print(f"   ❌ NOT ELIGIBLE for write-off")
        for reason in reasons:
            print(f"      - {reason}")
    
    print(f"\n" + "=" * 100)

if __name__ == '__main__':
    investigate_bill_213()
