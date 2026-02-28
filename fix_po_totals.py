"""
Fix Purchase Order totals - recalculate discount and totals for all POs
Run this after fixing the calculate_totals() method
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import PurchaseOrder

def fix_po_totals():
    """Recalculate totals for all purchase orders"""
    pos = PurchaseOrder.objects.all()
    fixed_count = 0
    
    print(f"Found {pos.count()} purchase orders to check...")
    
    for po in pos:
        # Get current values
        old_subtotal = po.subtotal
        old_discount = po.discount
        old_total = po.total
        
        # Recalculate from items
        items = po.items.all()
        new_subtotal = sum(item.value_before_discount for item in items)
        new_discount = sum(item.discount_amount for item in items)
        new_total = sum(item.line_total for item in items)
        
        # Check if update needed
        if (old_subtotal != new_subtotal or 
            old_discount != new_discount or 
            old_total != new_total):
            
            print(f"\nPO {po.po_number}:")
            print(f"  Old: Subtotal={old_subtotal}, Discount={old_discount}, Total={old_total}")
            print(f"  New: Subtotal={new_subtotal}, Discount={new_discount}, Total={new_total}")
            
            # Update
            po.subtotal = new_subtotal
            po.discount = new_discount
            po.total = new_total
            po.save()
            
            fixed_count += 1
    
    print(f"\n✅ Fixed {fixed_count} purchase orders")
    print(f"✅ {pos.count() - fixed_count} purchase orders were already correct")

if __name__ == '__main__':
    fix_po_totals()
