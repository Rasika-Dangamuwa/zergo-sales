"""
Audit: Opening Stock Balance vs FIFO Cost Layers
Checks if OB stock movements match OB FIFO layers in qty and cost.
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from decimal import Decimal
from collections import defaultdict
from products.models import FIFOCostLayer, StockMovement, Product


def audit():
    print("=" * 80)
    print("AUDIT: Opening Stock Balances vs FIFO Cost Layers")
    print("=" * 80)

    # 1. Opening Balance stock movements
    ob_moves = StockMovement.objects.filter(
        movement_type='opening_balance'
    ).select_related('product').order_by('product__product_name', 'created_at')

    print(f"\nTotal OB stock movements: {ob_moves.count()}")

    mv_by_product = defaultdict(list)
    for m in ob_moves:
        mv_by_product[m.product_id].append(m)

    # 2. Opening Balance FIFO layers
    ob_layers = FIFOCostLayer.objects.filter(
        layer_source='opening_balance'
    ).select_related('product').order_by('product__product_name', 'created_at')

    print(f"Total OB FIFO layers: {ob_layers.count()}")

    ly_by_product = defaultdict(list)
    for l in ob_layers:
        ly_by_product[l.product_id].append(l)

    # 3. Compare
    all_pids = set(mv_by_product.keys()) | set(ly_by_product.keys())
    products = {p.id: p for p in Product.objects.filter(id__in=all_pids)}

    print(f"\nProducts with OB data: {len(all_pids)}")
    print()
    print(f"{'Product':<35} {'MV Qty':>8} {'LY Qty':>8} {'MV Cost':>12} {'LY Cost':>12} {'Status'}")
    print("-" * 95)

    mismatches = []
    total_mv_qty = 0
    total_ly_qty = 0
    total_mv_value = Decimal('0')
    total_ly_value = Decimal('0')

    for pid in sorted(all_pids, key=lambda x: products[x].product_name):
        p = products[pid]
        moves = mv_by_product.get(pid, [])
        layers = ly_by_product.get(pid, [])

        mv_qty = sum(m.quantity for m in moves)
        ly_qty = sum(l.original_quantity for l in layers)

        # Get cost - use latest
        mv_cost = moves[-1].unit_cost if moves else Decimal('0')
        ly_cost = layers[-1].unit_cost if layers else Decimal('0')

        mv_value = mv_cost * mv_qty
        ly_value = sum(l.unit_cost * l.original_quantity for l in layers)

        total_mv_qty += mv_qty
        total_ly_qty += ly_qty
        total_mv_value += mv_value
        total_ly_value += ly_value

        qty_match = mv_qty == ly_qty
        cost_match = abs(mv_cost - ly_cost) < Decimal('0.01')

        if qty_match and cost_match:
            status = "OK"
        else:
            problems = []
            if not qty_match:
                problems.append(f"qty diff={ly_qty - mv_qty}")
            if not cost_match:
                problems.append(f"cost diff")
            status = "MISMATCH: " + ", ".join(problems)
            mismatches.append((p, mv_qty, ly_qty, mv_cost, ly_cost))

        name = f"{p.product_code} {p.product_name}"
        if len(name) > 34:
            name = name[:34]
        print(f"{name:<35} {mv_qty:>8} {ly_qty:>8} {mv_cost:>12.4f} {ly_cost:>12.4f} {status}")

    print("-" * 95)
    print(f"{'TOTAL':<35} {total_mv_qty:>8} {total_ly_qty:>8} {total_mv_value:>12.2f} {total_ly_value:>12.2f}")
    print()

    if mismatches:
        print(f"\n!!! {len(mismatches)} MISMATCHES FOUND !!!")
        for p, mq, lq, mc, lc in mismatches:
            print(f"  {p.product_code} {p.product_name}:")
            print(f"    Movement qty={mq}, Layer qty={lq} (diff={lq - mq})")
            print(f"    Movement cost={mc}, Layer cost={lc}")
            # Show details
            moves = mv_by_product.get(p.id, [])
            layers = ly_by_product.get(p.id, [])
            print(f"    Movements:")
            for m in moves:
                print(f"      qty={m.quantity} cost={m.unit_cost} ref={m.reference_number} date={m.created_at.date()}")
            print(f"    Layers:")
            for l in layers:
                c = l.original_quantity - l.remaining_quantity
                print(f"      orig={l.original_quantity} consumed={c} remaining={l.remaining_quantity} cost={l.unit_cost} ref={l.reference_number} date={l.created_at.date()}")
    else:
        print("ALL OK - Opening balance movements match FIFO layers perfectly.")

    # 4. Check for products with NO opening balance layer but that have stock
    print("\n\n=== Products with current stock but NO opening balance layer ===")
    products_with_ob = set(ly_by_product.keys())
    for p in Product.objects.filter(quantity_in_stock__gt=0).order_by('product_name'):
        if p.id not in products_with_ob:
            print(f"  {p.product_code} {p.product_name}: stock={p.quantity_in_stock} (no OB layer)")

    # 5. Check current stock vs FIFO layer balance for OB products
    print("\n\n=== Current Stock vs Total FIFO Remaining (all sources) ===")
    print(f"{'Product':<35} {'DB Stock':>10} {'FIFO Rem':>10} {'Status'}")
    print("-" * 70)
    stock_mismatches = 0
    for pid in sorted(all_pids, key=lambda x: products[x].product_name):
        p = products[pid]
        fifo_remaining = sum(
            l.remaining_quantity
            for l in FIFOCostLayer.objects.filter(product=p)
        )
        match = "OK" if p.quantity_in_stock == fifo_remaining else f"DIFF={fifo_remaining - p.quantity_in_stock}"
        if p.quantity_in_stock != fifo_remaining:
            stock_mismatches += 1
        name = f"{p.product_code} {p.product_name}"
        if len(name) > 34:
            name = name[:34]
        print(f"{name:<35} {p.quantity_in_stock:>10} {fifo_remaining:>10} {match}")

    if stock_mismatches:
        print(f"\n!!! {stock_mismatches} stock vs FIFO mismatches !!!")
    else:
        print(f"\nAll stock quantities match FIFO remaining quantities.")


if __name__ == '__main__':
    audit()
