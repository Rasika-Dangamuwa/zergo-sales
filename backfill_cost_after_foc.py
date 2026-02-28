"""
Backfill script: Update all non-GRN FIFO layers and stock movements
to use cost_after_foc instead of company_price.

GRN/purchase layers already have correct effective_unit_cost from actual quantities,
so they are NOT touched.

After updating layers, re-consume FIFO on all BillItems to recalculate COGS.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from decimal import Decimal
from products.models import Product, FIFOCostLayer, StockMovement
from sales.models import BillItem

def backfill_fifo_layers():
    """Update non-purchase FIFO layers to use cost_after_foc."""
    # Sources that should use cost_after_foc (NOT 'purchase' which uses GRN effective cost)
    non_purchase_sources = ['return', 'exchange_in', 'opening_balance', 'adjustment']
    
    layers = FIFOCostLayer.objects.filter(
        layer_source__in=non_purchase_sources
    ).select_related('product')
    
    total = layers.count()
    updated = 0
    skipped = 0
    changes = []
    
    print(f"\n{'='*70}")
    print(f"STEP 1: Update FIFO Cost Layers ({total} non-purchase layers)")
    print(f"{'='*70}")
    
    for layer in layers:
        product = layer.product
        new_cost = product.cost_after_foc if product.cost_after_foc else Decimal('0')
        
        if new_cost == Decimal('0'):
            skipped += 1
            continue
        
        old_cost = layer.unit_cost
        if old_cost != new_cost:
            old_total_calc = old_cost * layer.original_quantity
            new_total_calc = new_cost * layer.original_quantity
            
            changes.append({
                'layer_id': layer.id,
                'product': product.product_name,
                'source': layer.layer_source,
                'old_unit': old_cost,
                'new_unit': new_cost,
                'old_total': old_total_calc,
                'new_total': new_total_calc,
                'qty': layer.original_quantity,
            })
            
            layer.unit_cost = new_cost
            layer.save(update_fields=['unit_cost'])
            updated += 1
        else:
            skipped += 1
    
    print(f"  Updated: {updated}")
    print(f"  Skipped (already correct or zero): {skipped}")
    
    if changes:
        print(f"\n  Sample changes (first 10):")
        for c in changes[:10]:
            print(f"    Layer #{c['layer_id']} [{c['source']}] {c['product']}: "
                  f"Rs.{c['old_unit']:.4f} → Rs.{c['new_unit']:.4f} "
                  f"(total: Rs.{c['old_total']:.2f} → Rs.{c['new_total']:.2f}, qty={c['qty']})")
    
    return updated


def backfill_stock_movements():
    """Update non-purchase stock movements to use cost_after_foc."""
    # Movement types that should use cost_after_foc
    non_purchase_types = [
        'return', 'exchange', 'adjustment', 'opening_balance',
        'non_resaleable_in', 'non_resaleable_out', 'status_adjustment',
        'return_to_company', 'purchase_return',
    ]
    
    movements = StockMovement.objects.filter(
        movement_type__in=non_purchase_types
    ).select_related('product')
    
    total = movements.count()
    updated = 0
    skipped = 0
    
    print(f"\n{'='*70}")
    print(f"STEP 2: Update Stock Movements ({total} non-purchase movements)")
    print(f"{'='*70}")
    
    for mv in movements:
        if not mv.product:
            skipped += 1
            continue
            
        new_cost = mv.product.cost_after_foc if mv.product.cost_after_foc else Decimal('0')
        
        if new_cost == Decimal('0'):
            skipped += 1
            continue
        
        old_cost = mv.unit_cost
        if old_cost != new_cost:
            qty = abs(mv.quantity)
            mv.unit_cost = new_cost
            mv.total_cost = new_cost * qty
            mv.save(update_fields=['unit_cost', 'total_cost'])
            updated += 1
        else:
            skipped += 1
    
    print(f"  Updated: {updated}")
    print(f"  Skipped (already correct or zero): {skipped}")
    return updated


def rebuild_bill_item_cogs():
    """Re-consume FIFO for all BillItems to recalculate COGS with new layer costs.
    
    This replays the FIFO consumption from scratch:
    1. Reset all FIFO layers to full (remaining_quantity = original_quantity)
    2. Process all BillItems in chronological order
    3. Re-consume layers oldest-first
    """
    print(f"\n{'='*70}")
    print(f"STEP 3: Rebuild BillItem COGS via FIFO re-consumption")
    print(f"{'='*70}")
    
    # Step 3a: Reset all FIFO layers to full capacity
    all_layers = FIFOCostLayer.objects.all()
    reset_count = all_layers.update(remaining_quantity=django.db.models.F('original_quantity'))
    print(f"  Reset {reset_count} FIFO layers to full capacity")
    
    # Step 3b: Get all confirmed bill items in chronological order
    from sales.models import Bill
    bill_items = BillItem.objects.filter(
        bill__bill_status='confirmed'
    ).select_related('product', 'bill').order_by('bill__bill_date', 'bill__id', 'id')
    
    total_items = bill_items.count()
    updated = 0
    
    print(f"  Processing {total_items} BillItems...")
    
    for item in bill_items:
        if not item.product or item.quantity <= 0:
            continue
        
        # Consume FIFO layers for this item
        total_qty = item.quantity + (item.foc_quantity or 0)
        if total_qty <= 0:
            continue
            
        weighted_avg, breakdown = FIFOCostLayer.consume_fifo(item.product, total_qty)
        
        old_unit = item.unit_cost
        old_total = item.total_cost
        
        item.unit_cost = weighted_avg
        item.total_cost = weighted_avg * total_qty
        item.save(update_fields=['unit_cost', 'total_cost'])
        updated += 1
    
    print(f"  Updated: {updated} BillItems with new FIFO COGS")
    return updated


def print_summary():
    """Print verification summary."""
    print(f"\n{'='*70}")
    print(f"VERIFICATION SUMMARY")
    print(f"{'='*70}")
    
    # Show some sample products with old vs new costs
    products = Product.objects.filter(quantity_in_stock__gt=0).order_by('product_name')[:10]
    print(f"\n  Sample Products (company_price vs cost_after_foc):")
    for p in products:
        foc_ratio = f"{p.company_foc_buy}+{p.company_foc_free}"
        print(f"    {p.product_name}: company_price=Rs.{p.company_price:.2f}, "
              f"FOC={foc_ratio}, cost_after_foc=Rs.{p.cost_after_foc:.4f}")
    
    # Layer stats
    from django.db.models import Sum, F
    purchase_layers = FIFOCostLayer.objects.filter(layer_source='purchase')
    non_purchase_layers = FIFOCostLayer.objects.exclude(layer_source='purchase')
    
    p_total = purchase_layers.aggregate(t=Sum(F('unit_cost') * F('original_quantity')))['t'] or 0
    np_total = non_purchase_layers.aggregate(t=Sum(F('unit_cost') * F('original_quantity')))['t'] or 0
    
    print(f"\n  FIFO Layer Totals:")
    print(f"    Purchase layers: Rs.{p_total:,.2f} (unchanged)")
    print(f"    Non-purchase layers: Rs.{np_total:,.2f} (updated)")
    
    # COGS total
    cogs = BillItem.objects.filter(
        bill__bill_status='confirmed'
    ).aggregate(t=Sum('total_cost'))['t'] or 0
    print(f"\n  Total COGS (confirmed bills): Rs.{cogs:,.2f}")


if __name__ == '__main__':
    print("=" * 70)
    print("BACKFILL: cost_after_foc for all non-GRN stock entries")
    print("=" * 70)
    
    layer_count = backfill_fifo_layers()
    movement_count = backfill_stock_movements()
    item_count = rebuild_bill_item_cogs()
    
    print_summary()
    
    print(f"\n{'='*70}")
    print(f"COMPLETE: {layer_count} layers, {movement_count} movements, {item_count} bill items updated")
    print(f"{'='*70}")
