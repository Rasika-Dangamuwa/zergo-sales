"""
Find returns with FOC quantities and verify FOC transaction creation
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, ReturnItem
from products.models import FOCValueTransaction
from django.db.models import Q, Sum

def find_returns_with_foc():
    """Find returns that have FOC quantities"""
    print("\n" + "="*80)
    print("CHECKING FOC TRANSACTION CREATION FOR RETURNS WITH FOC")
    print("="*80 + "\n")
    
    # Find returns with FOC items
    returns_with_foc = Return.objects.filter(
        items__foc_quantity__gt=0
    ).distinct().order_by('-return_date')[:10]
    
    print(f"Found {returns_with_foc.count()} returns with FOC quantities\n")
    
    for ret in returns_with_foc:
        print(f"\n{'='*80}")
        print(f"📦 Return: {ret.return_number} (ID: {ret.pk})")
        print(f"   Shop: {ret.shop.shop_name}")
        print(f"   Date: {ret.return_date}")
        print(f"   Status: {ret.settlement_status}")
        
        # Check items with FOC
        foc_items = ret.items.filter(foc_quantity__gt=0)
        print(f"\n   Items with FOC: {foc_items.count()}")
        
        total_foc_qty = 0
        for item in foc_items:
            print(f"   • {item.product.product_name}: {item.foc_quantity} FOC units")
            total_foc_qty += item.foc_quantity
        
        print(f"\n   Total FOC Quantity: {total_foc_qty}")
        
        # Check FOC transactions
        foc_txns = FOCValueTransaction.objects.filter(
            return_item__return_ref=ret
        )
        
        print(f"\n   FOC Transactions: {foc_txns.count()}")
        
        if foc_txns.exists():
            for txn in foc_txns:
                status = "✅ Active" if not txn.is_archived else "📦 Archived"
                print(f"   • {txn.transaction_number}: Rs. {txn.foc_value:,.2f} ({status})")
        else:
            print(f"   ❌ NO FOC TRANSACTIONS FOUND!")
            print(f"\n   INVESTIGATING...")
            
            # Check when return was created
            print(f"   Created at: {ret.created_at}")
            
            # Check if product has company
            for item in foc_items:
                if item.product.company:
                    print(f"   ✅ Product {item.product.product_name} has company: {item.product.company.company_name}")
                else:
                    print(f"   ❌ Product {item.product.product_name} has NO company!")


def check_return_121_details():
    """Detailed check of Return 121"""
    print("\n" + "="*80)
    print("DETAILED ANALYSIS: RETURN #121")
    print("="*80 + "\n")
    
    try:
        ret = Return.objects.get(pk=121)
        
        print(f"Return Number: {ret.return_number}")
        print(f"URL: /sales/returns/121/")
        
        items = ret.items.all()
        print(f"\nItems:")
        for item in items:
            print(f"  • {item.product.product_name}")
            print(f"    - Regular Quantity: {item.quantity}")
            print(f"    - FOC Quantity: {item.foc_quantity}")
            print(f"    - Company: {item.product.company.company_name if item.product.company else 'NO COMPANY'}")
        
        foc_items_count = items.filter(foc_quantity__gt=0).count()
        
        if foc_items_count == 0:
            print(f"\n✅ EXPLANATION: Return #121 has NO FOC quantities")
            print(f"   FOC transactions are ONLY created when foc_quantity > 0")
            print(f"   This is CORRECT behavior - no bug here!")
        else:
            print(f"\n⚠️  Return #121 HAS FOC but no transactions - investigating...")
    
    except Return.DoesNotExist:
        print("Return #121 not found")


if __name__ == '__main__':
    check_return_121_details()
    find_returns_with_foc()
