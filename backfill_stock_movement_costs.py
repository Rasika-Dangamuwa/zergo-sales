"""
Backfill unit_cost and total_cost for all existing StockMovement records.

Logic:
- Purchase movements: Look up PurchaseItem via GRN reference to get actual cost
  Formula: (unit_price * quantity) / (quantity + foc_quantity)
- All other movements: Use product.company_price at current time
  (best approximation since historical prices aren't tracked)

Run: python manage.py shell < backfill_stock_movement_costs.py
Or:  python backfill_stock_movement_costs.py
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from decimal import Decimal
from products.models import StockMovement, Purchase, PurchaseItem


def backfill_costs():
    """Backfill cost data for all stock movements that don't have it."""
    
    movements = StockMovement.objects.filter(unit_cost__isnull=True)
    total = movements.count()
    print(f"\nFound {total} stock movements without cost data.\n")
    
    if total == 0:
        print("Nothing to backfill!")
        return
    
    updated = 0
    skipped = 0
    errors = 0
    
    # Pre-load purchase items indexed by GRN + product for fast lookup
    purchase_item_cache = {}
    for pi in PurchaseItem.objects.select_related('purchase', 'product').all():
        if pi.purchase and pi.purchase.grn_number:
            key = (pi.purchase.grn_number, pi.product_id)
            purchase_item_cache[key] = pi
    
    print(f"Loaded {len(purchase_item_cache)} purchase items into cache.\n")
    
    for mv in movements.select_related('product').iterator():
        try:
            unit_cost = None
            
            if mv.movement_type == 'purchase' and mv.reference_number:
                # Look up actual purchase item cost
                key = (mv.reference_number, mv.product_id)
                pi = purchase_item_cache.get(key)
                
                if pi and pi.unit_price:
                    total_bottles = (pi.quantity or 0) + (pi.foc_quantity or 0)
                    if total_bottles > 0:
                        # Spread cost across qty + FOC
                        unit_cost = (pi.unit_price * pi.quantity) / Decimal(str(total_bottles))
                    else:
                        unit_cost = pi.unit_price
                elif mv.product and mv.product.company_price:
                    # Fallback to current company_price
                    unit_cost = mv.product.company_price
                    
            else:
                # All other movement types: use product.company_price
                if mv.product and mv.product.company_price:
                    unit_cost = mv.product.company_price
            
            if unit_cost is not None and unit_cost > 0:
                abs_qty = abs(mv.quantity) if mv.quantity else 0
                mv.unit_cost = unit_cost
                mv.total_cost = unit_cost * abs_qty
                mv.save(update_fields=['unit_cost', 'total_cost'])
                updated += 1
            else:
                skipped += 1
                
        except Exception as e:
            errors += 1
            print(f"  Error on movement #{mv.id} ({mv.movement_type}): {e}")
    
    print(f"\n{'='*50}")
    print(f"Backfill Complete!")
    print(f"  Updated: {updated}")
    print(f"  Skipped (no cost data available): {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Total processed: {updated + skipped + errors}")
    print(f"{'='*50}\n")


if __name__ == '__main__':
    backfill_costs()
