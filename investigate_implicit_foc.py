"""
Deep Investigation of FOC-20260127-012 (Implicit FOC Transaction)
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import FOCValueTransaction, FOCValueAccount, Product
from sales.models import Bill, BillItem
from django.db.models import Q

def investigate_transaction():
    """Deep investigation of FOC-20260127-012"""
    print("\n" + "="*80)
    print("DEEP INVESTIGATION: FOC-20260127-012 (IMPLICIT FOC)")
    print("="*80 + "\n")
    
    try:
        txn = FOCValueTransaction.objects.get(transaction_number='FOC-20260127-012')
        
        print(f"📊 TRANSACTION DETAILS")
        print(f"   Transaction #: {txn.transaction_number}")
        print(f"   Type: {txn.transaction_type}")
        print(f"   Date: {txn.transaction_date}")
        print(f"   Is Archived: {txn.is_archived}")
        
        print(f"\n💰 FOC VALUES")
        print(f"   FOC Quantity: {txn.foc_quantity}")
        print(f"   Shop Price at Time: Rs. {txn.shop_price_at_time:,.2f}")
        print(f"   FOC Value: Rs. {txn.foc_value:,.2f}")
        print(f"   FOC Value per Unit: Rs. {txn.foc_value / txn.foc_quantity:,.2f}")
        
        print(f"\n📦 PRODUCT INFO")
        print(f"   Product: {txn.product.product_name}")
        print(f"   Company: {txn.foc_account.company.company_name}")
        print(f"   Current Shop Price: Rs. {txn.product.shop_price:,.2f}")
        
        print(f"\n🏪 SHOP & SALES REP")
        print(f"   Shop: {txn.shop.shop_name}")
        if txn.sales_rep:
            print(f"   Sales Rep: {txn.sales_rep.username}")
        
        print(f"\n📝 NOTES")
        print(f"   {txn.notes}")
        
        # Check the bill item
        if txn.bill_item:
            bill_item = txn.bill_item
            bill = bill_item.bill
            
            print(f"\n📋 RELATED BILL DETAILS")
            print(f"   Bill Number: {bill.bill_number}")
            print(f"   Bill Date: {bill.bill_date}")
            print(f"   Bill Status: {bill.bill_status}")
            print(f"   Bill Total: Rs. {bill.total_amount:,.2f}")
            
            print(f"\n📦 BILL ITEM DETAILS")
            print(f"   Product: {bill_item.product.product_name}")
            print(f"   Quantity Sold: {bill_item.quantity}")
            print(f"   FOC Quantity: {bill_item.foc_quantity}")
            print(f"   Unit Price Sold At: Rs. {bill_item.unit_price:,.2f}")
            print(f"   Line Total: Rs. {bill_item.line_total:,.2f}")
            
            # Calculate implicit FOC
            shop_price = txn.shop_price_at_time
            unit_price = bill_item.unit_price
            quantity = bill_item.quantity
            
            print(f"\n🔍 IMPLICIT FOC CALCULATION")
            print(f"   Shop Price: Rs. {shop_price:,.2f}")
            print(f"   Sold At: Rs. {unit_price:,.2f}")
            print(f"   Discount per Unit: Rs. {shop_price - unit_price:,.2f}")
            print(f"   Quantity: {quantity}")
            print(f"   Expected Implicit FOC: {quantity} × Rs. {shop_price - unit_price:,.2f} = Rs. {quantity * (shop_price - unit_price):,.2f}")
            print(f"   Recorded Implicit FOC: Rs. {txn.foc_value:,.2f}")
            
            if abs((quantity * (shop_price - unit_price)) - txn.foc_value) > 0.01:
                print(f"\n   ⚠️  MISMATCH DETECTED!")
                print(f"   Difference: Rs. {abs((quantity * (shop_price - unit_price)) - txn.foc_value):,.2f}")
            else:
                print(f"\n   ✅ Calculation matches!")
            
            # Check if selling at Rs. 0
            if unit_price == 0:
                print(f"\n   🚨 CRITICAL ISSUE: Unit price is Rs. 0!")
                print(f"   This means products were given for FREE")
                print(f"   Should this be explicit FOC instead of implicit FOC?")
            elif unit_price < 0:
                print(f"\n   🚨 CRITICAL ERROR: Negative unit price!")
            
            # Check all items in this bill
            print(f"\n📋 ALL ITEMS IN BILL {bill.bill_number}")
            all_items = bill.items.all()
            for idx, item in enumerate(all_items, 1):
                print(f"\n   Item {idx}:")
                print(f"   • Product: {item.product.product_name}")
                print(f"   • Qty: {item.quantity} | FOC: {item.foc_quantity}")
                print(f"   • Unit Price: Rs. {item.unit_price:,.2f}")
                print(f"   • Shop Price: Rs. {item.product.shop_price:,.2f}")
                print(f"   • Line Total: Rs. {item.line_total:,.2f}")
                
                if item.unit_price == 0 and item.foc_quantity == 0:
                    print(f"   ⚠️  WARNING: Sold at Rs. 0 but NOT marked as FOC!")
        else:
            print(f"\n❌ No bill item associated with this transaction")
        
        # Check related FOC transactions
        print(f"\n🔗 RELATED FOC TRANSACTIONS")
        related_txns = FOCValueTransaction.objects.filter(
            reference_number=txn.reference_number
        ).exclude(transaction_number=txn.transaction_number)
        
        if related_txns.exists():
            print(f"   Found {related_txns.count()} related transactions:")
            for rt in related_txns:
                print(f"   • {rt.transaction_number} - {rt.transaction_type} - Rs. {rt.foc_value:,.2f}")
        else:
            print(f"   No other FOC transactions for this bill")
    
    except FOCValueTransaction.DoesNotExist:
        print("❌ FOC-20260127-012 not found in database")


def check_all_implicit_foc():
    """Check all implicit FOC transactions for issues"""
    print("\n" + "="*80)
    print("ANALYZING ALL IMPLICIT FOC TRANSACTIONS")
    print("="*80 + "\n")
    
    implicit_txns = FOCValueTransaction.objects.filter(
        transaction_type='implicit_foc',
        is_archived=False
    ).select_related('product', 'shop', 'bill_item__bill')
    
    print(f"Found {implicit_txns.count()} active implicit FOC transactions\n")
    
    issues_found = 0
    
    for txn in implicit_txns:
        if txn.bill_item:
            bill_item = txn.bill_item
            shop_price = txn.shop_price_at_time
            unit_price = bill_item.unit_price
            quantity = bill_item.quantity
            
            expected_foc = quantity * (shop_price - unit_price)
            
            # Check for issues
            has_issue = False
            
            if unit_price == 0:
                print(f"🚨 {txn.transaction_number} - Bill {txn.reference_number}")
                print(f"   Product sold at Rs. 0 (should be explicit FOC?)")
                print(f"   Product: {txn.product.product_name}")
                print(f"   FOC Value: Rs. {txn.foc_value:,.2f}")
                has_issue = True
            
            if abs(expected_foc - txn.foc_value) > 0.01:
                print(f"⚠️  {txn.transaction_number} - Bill {txn.reference_number}")
                print(f"   Calculation mismatch!")
                print(f"   Expected: Rs. {expected_foc:,.2f}")
                print(f"   Recorded: Rs. {txn.foc_value:,.2f}")
                has_issue = True
            
            if unit_price >= shop_price:
                print(f"⚠️  {txn.transaction_number} - Bill {txn.reference_number}")
                print(f"   Unit price (Rs. {unit_price}) >= Shop price (Rs. {shop_price})")
                print(f"   This should NOT be implicit FOC!")
                has_issue = True
            
            if has_issue:
                issues_found += 1
                print()
    
    if issues_found == 0:
        print("✅ No issues found in implicit FOC transactions")
    else:
        print(f"\n⚠️  Found {issues_found} transactions with issues")


if __name__ == '__main__':
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  FOC TRANSACTION DEEP INVESTIGATION".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    investigate_transaction()
    check_all_implicit_foc()
    
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  INVESTIGATION COMPLETE".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80 + "\n")
