"""
Investigate Return #121 - Why no FOC transactions?
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, ReturnItem
from products.models import FOCValueTransaction, FOCValueAccount
from django.db.models import Q

def investigate_return_121():
    """Deep investigation of Return #121"""
    print("\n" + "="*80)
    print("INVESTIGATING RETURN #121 - FOC TRANSACTION CREATION")
    print("="*80 + "\n")
    
    try:
        ret = Return.objects.get(pk=121)
        
        print(f"📦 Return Details:")
        print(f"   Return Number: {ret.return_number}")
        print(f"   Shop: {ret.shop.shop_name}")
        print(f"   Date: {ret.return_date}")
        print(f"   Settlement Status: {ret.settlement_status}")
        print(f"   Settlement Method: {ret.settlement_method}")
        print(f"   Total Amount: Rs. {ret.total_amount:,.2f}")
        print(f"   Is Verified: {ret.is_verified}")
        
        # Check return items
        print(f"\n📋 Return Items:")
        items = ret.items.all()
        print(f"   Total Items: {items.count()}")
        
        has_foc = False
        for item in items:
            print(f"\n   Item: {item.product.product_name}")
            print(f"   ├─ Company: {item.product.company.company_name}")
            print(f"   ├─ Quantity: {item.quantity}")
            print(f"   ├─ FOC Quantity: {item.foc_quantity}")
            print(f"   └─ Unit Price: Rs. {item.unit_price:,.2f}")
            
            if item.foc_quantity > 0:
                has_foc = True
                
                # Check if product has FOC account
                try:
                    foc_account = FOCValueAccount.objects.get(company=item.product.company)
                    print(f"   └─ ✅ FOC Account exists for {item.product.company.company_name}")
                except FOCValueAccount.DoesNotExist:
                    print(f"   └─ ❌ NO FOC Account for {item.product.company.company_name}")
        
        if not has_foc:
            print(f"\n⚠️  REASON: This return has NO FOC quantities!")
            print(f"   FOC transactions are only created when foc_quantity > 0")
            return
        
        # Check for FOC transactions
        print(f"\n💰 FOC Transactions:")
        foc_txns = FOCValueTransaction.objects.filter(
            return_item__return_ref=ret
        )
        
        if foc_txns.exists():
            print(f"   Found {foc_txns.count()} FOC transactions:")
            for txn in foc_txns:
                print(f"\n   • {txn.transaction_number}")
                print(f"     ├─ Type: {txn.transaction_type}")
                print(f"     ├─ Value: Rs. {txn.foc_value:,.2f}")
                print(f"     ├─ Product: {txn.product.product_name}")
                print(f"     ├─ Is Archived: {txn.is_archived}")
                print(f"     └─ Date: {txn.transaction_date}")
        else:
            print(f"   ❌ NO FOC transactions found!")
            print(f"\n   INVESTIGATING WHY...")
            
            # Check if return was created before FOC system
            from django.utils import timezone
            foc_system_start = timezone.datetime(2026, 1, 27, tzinfo=timezone.utc)
            
            if ret.created_at < foc_system_start:
                print(f"   ⚠️  Return created BEFORE FOC system ({ret.created_at})")
            
            # Check return item save/create logic
            print(f"\n   Checking return creation logic...")
            print(f"   Settlement Status: {ret.settlement_status}")
            print(f"   Has FOC items: {has_foc}")
            
    except Return.DoesNotExist:
        print("❌ Return #121 not found in database")


if __name__ == '__main__':
    investigate_return_121()
