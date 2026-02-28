"""
Fix GRN totals - recalculate discount_amount, subtotal, and total_amount
for all existing Purchase records
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Purchase

def fix_grn_totals():
    """Recalculate totals for all GRNs"""
    purchases = Purchase.objects.all()
    fixed_count = 0
    
    for purchase in purchases:
        old_discount = purchase.discount_amount
        old_subtotal = purchase.subtotal
        old_total = purchase.total_amount
        
        # Recalculate using the new logic
        purchase.calculate_totals()
        
        if (old_discount != purchase.discount_amount or 
            old_subtotal != purchase.subtotal or 
            old_total != purchase.total_amount):
            print(f"Fixed {purchase.grn_number}:")
            print(f"  Discount: {old_discount} -> {purchase.discount_amount}")
            print(f"  Subtotal: {old_subtotal} -> {purchase.subtotal}")
            print(f"  Total: {old_total} -> {purchase.total_amount}")
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} GRN(s)")

if __name__ == '__main__':
    fix_grn_totals()
