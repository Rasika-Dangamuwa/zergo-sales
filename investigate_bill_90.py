"""
Investigate Bill #90 and its settlements
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill
from payments.models import SalesAccountSettlement
from decimal import Decimal

# Get bill 90
bill = Bill.objects.filter(pk=90).select_related('shop', 'sales_rep').first()

if bill:
    print(f"\n{'='*100}")
    print(f"BILL #{bill.pk}: {bill.bill_number}")
    print(f"{'='*100}")
    print(f"Shop: {bill.shop.shop_name} ({bill.shop.shop_code})")
    print(f"Sales Rep: {bill.sales_rep.username} - {bill.sales_rep.get_full_name()}")
    print(f"Bill Date: {bill.bill_date}")
    print(f"Bill Status: {bill.bill_status}")
    print(f"Settlement Status: {bill.settlement_status}")
    print()
    print(f"Subtotal: Rs. {bill.subtotal:,.2f}")
    print(f"Discount: Rs. {bill.discount_amount:,.2f} ({bill.discount_percentage}%)")
    print(f"Tax: Rs. {bill.tax_amount:,.2f}")
    print(f"Total Amount: Rs. {bill.total_amount:,.2f}")
    print(f"Paid Amount: Rs. {bill.paid_amount:,.2f}")
    print(f"Balance Amount: Rs. {bill.balance_amount:,.2f}")
    
    # Get all settlements
    settlements = SalesAccountSettlement.objects.filter(bill=bill).order_by('settlement_date')
    
    print(f"\n{'='*100}")
    print(f"SETTLEMENTS ({settlements.count()})")
    print(f"{'='*100}")
    
    total_settlements = Decimal('0')
    for i, settlement in enumerate(settlements, 1):
        print(f"\n{i}. Settlement ID: {settlement.pk}")
        print(f"   Number: {settlement.settlement_number}")
        print(f"   Date: {settlement.settlement_date}")
        print(f"   Method: {settlement.settlement_method}")
        print(f"   Status: {settlement.settlement_status}")
        print(f"   Amount: Rs. {settlement.amount:,.2f}")
        print(f"   Received By: {settlement.received_by.username if settlement.received_by else 'N/A'}")
        
        if settlement.return_ref:
            print(f"   Return Ref: {settlement.return_ref.return_number}")
        
        if settlement.settlement_status != 'cancelled':
            total_settlements += settlement.amount
        else:
            print(f"   ❌ CANCELLED")
    
    print(f"\n{'='*100}")
    print(f"FINANCIAL SUMMARY")
    print(f"{'='*100}")
    print(f"Bill Total: Rs. {bill.total_amount:,.2f}")
    print(f"Total Settlements (non-cancelled): Rs. {total_settlements:,.2f}")
    print(f"Bill Paid Amount: Rs. {bill.paid_amount:,.2f}")
    print(f"Bill Balance: Rs. {bill.balance_amount:,.2f}")
    
    # Check for discrepancies
    if bill.paid_amount != total_settlements:
        print(f"\n⚠️  DISCREPANCY DETECTED!")
        print(f"   Bill paid_amount ({bill.paid_amount}) != Sum of non-cancelled settlements ({total_settlements})")
        print(f"   Difference: Rs. {bill.paid_amount - total_settlements:,.2f}")
    
    # Get bill items
    items = bill.items.all()
    print(f"\n{'='*100}")
    print(f"BILL ITEMS ({items.count()})")
    print(f"{'='*100}")
    
    for i, item in enumerate(items, 1):
        print(f"{i}. {item.product.product_name}")
        print(f"   Qty: {item.quantity} + FOC: {item.foc_quantity} = Total: {item.total_quantity}")
        print(f"   Unit Price: Rs. {item.unit_price:,.2f}")
        print(f"   Line Total: Rs. {item.line_total:,.2f}")
    
    # Check commission transactions
    from sales.models import CommissionTransaction
    comm_txns = CommissionTransaction.objects.filter(bill=bill).order_by('created_at')
    
    if comm_txns.exists():
        print(f"\n{'='*100}")
        print(f"COMMISSION TRANSACTIONS ({comm_txns.count()})")
        print(f"{'='*100}")
        
        for i, txn in enumerate(comm_txns, 1):
            direction = "+" if txn.commission_earned >= 0 else ""
            print(f"{i}. Type: {txn.transaction_type}")
            print(f"   Date: {txn.transaction_date}")
            if txn.settlement:
                print(f"   Settlement: {txn.settlement.settlement_number} ({txn.settlement.settlement_status})")
            print(f"   Amount: {txn.collected_amount}")
            print(f"   Commission: {direction}{txn.commission_earned}")
            print(f"   Balance: {txn.running_balance}")
    
else:
    print("Bill #90 not found!")
