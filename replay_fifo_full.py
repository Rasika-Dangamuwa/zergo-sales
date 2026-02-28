"""
Proper FIFO Replay: Replays ALL stock-out events that consume FIFO layers
in chronological order, not just sales.

Stock-out events that consume FIFO:
1. Sales (bill creation) → updates BillItem.unit_cost/total_cost
2. Exchange OUT → just consumes layers (no BillItem)

This ensures layers are consumed in the correct order and BillItem COGS
reflects the actual cost at the time of sale.
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from decimal import Decimal
from django.db.models import Sum, F, Q
from products.models import FIFOCostLayer, StockMovement
from sales.models import Bill, BillItem


def run_full_fifo_replay():
    print("=" * 70)
    print("FULL FIFO REPLAY: All stock-out events in chronological order")
    print("=" * 70)

    # Step 1: Reset all FIFO layers to full capacity
    print("\n1. Resetting all FIFO layers to full capacity...")
    reset_count = FIFOCostLayer.objects.all().update(
        remaining_quantity=django.db.models.F('original_quantity'),
        is_exhausted=False,
    )
    print(f"   Reset {reset_count} layers")

    # Step 2: Gather all stock-out events that consume FIFO
    print("\n2. Gathering stock-out events...")

    # 2a. Sale stock movements (movement_type='sale')
    sale_movements = list(StockMovement.objects.filter(
        movement_type='sale'
    ).select_related('product').order_by('created_at', 'id').values_list(
        'id', 'product_id', 'quantity', 'reference_number', 'created_at'
    ))
    print(f"   Sale movements: {len(sale_movements)}")

    # 2b. Exchange OUT movements (movement_type='exchange', quantity < 0, NOT cancellations)
    exchange_out_movements = list(StockMovement.objects.filter(
        movement_type='exchange',
        quantity__lt=0,
    ).exclude(
        reference_number__icontains='CANCEL'
    ).select_related('product').order_by('created_at', 'id').values_list(
        'id', 'product_id', 'quantity', 'reference_number', 'created_at'
    ))
    print(f"   Exchange OUT movements: {len(exchange_out_movements)}")

    # Merge and sort all events chronologically
    all_events = []
    for mv in sale_movements:
        all_events.append({
            'type': 'sale',
            'movement_id': mv[0],
            'product_id': mv[1],
            'qty': abs(mv[2]),  # make positive
            'reference': mv[3],
            'created_at': mv[4],
        })
    for mv in exchange_out_movements:
        all_events.append({
            'type': 'exchange_out',
            'movement_id': mv[0],
            'product_id': mv[1],
            'qty': abs(mv[2]),
            'reference': mv[3],
            'created_at': mv[4],
        })

    all_events.sort(key=lambda x: (x['created_at'], x['movement_id']))
    print(f"   Total events to replay: {len(all_events)}")

    # Step 3: Build BillItem lookup for sales
    # Map (bill_number, product_id) → BillItem for updating COGS
    print("\n3. Building BillItem lookup...")
    bill_items_map = {}
    for item in BillItem.objects.filter(
        bill__bill_status='confirmed'
    ).select_related('bill', 'product'):
        key = (item.bill.bill_number, item.product_id)
        bill_items_map[key] = item
    print(f"   BillItems mapped: {len(bill_items_map)}")

    # Step 4: Replay all events
    print("\n4. Replaying FIFO consumption...")
    sales_updated = 0
    exchanges_consumed = 0
    fallback_count = 0
    total_cogs = Decimal('0')
    total_consumed_from_layers = 0
    total_fallback_qty = 0

    for event in all_events:
        product_id = event['product_id']
        qty = int(event['qty'])

        if qty <= 0:
            continue

        # Consume FIFO layers
        weighted_avg, breakdown = FIFOCostLayer.consume_fifo_by_id(product_id, qty)

        if event['type'] == 'sale':
            # Find and update BillItem
            key = (event['reference'], product_id)
            bill_item = bill_items_map.get(key)
            if bill_item:
                total_qty = bill_item.quantity + (bill_item.foc_quantity or 0)
                bill_item.unit_cost = weighted_avg
                bill_item.total_cost = weighted_avg * total_qty
                bill_item.cost_breakdown = breakdown
                bill_item.save(update_fields=['unit_cost', 'total_cost', 'cost_breakdown'])
                total_cogs += bill_item.total_cost
                sales_updated += 1
            else:
                # Sale movement without matching BillItem - might be cancelled bill
                pass
        else:
            exchanges_consumed += 1

    print(f"   Sales BillItems updated: {sales_updated}")
    print(f"   Exchange OUTs consumed: {exchanges_consumed}")
    print(f"   Total COGS: Rs.{total_cogs:,.2f}")

    # Step 5: Mark exhausted layers
    print("\n5. Updating exhausted status...")
    exhausted = FIFOCostLayer.objects.filter(remaining_quantity__lte=0).update(is_exhausted=True)
    active = FIFOCostLayer.objects.filter(remaining_quantity__gt=0).update(is_exhausted=False)
    print(f"   Exhausted: {exhausted}, Active: {active}")

    # Step 6: Verification
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)

    final_cogs = BillItem.objects.filter(
        bill__bill_status='confirmed'
    ).aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
    print(f"   Final COGS from BillItems: Rs.{final_cogs:,.2f}")

    layer_stats = FIFOCostLayer.objects.aggregate(
        orig=Sum('original_quantity'),
        rem=Sum('remaining_quantity'),
    )
    consumed_qty = layer_stats['orig'] - layer_stats['rem']
    total_events_qty = sum(e['qty'] for e in all_events)
    print(f"   Total events qty: {total_events_qty}")
    print(f"   FIFO layers consumed qty: {consumed_qty}")
    print(f"   FIFO remaining: {layer_stats['rem']}")

    if total_events_qty != consumed_qty:
        fallback = total_events_qty - consumed_qty
        print(f"   Fallback qty (insufficient layers): {fallback}")

    consumed_value = Decimal('0')
    for layer in FIFOCostLayer.objects.all():
        c = layer.original_quantity - layer.remaining_quantity
        if c > 0:
            consumed_value += layer.unit_cost * c
    print(f"   Value consumed from layers: Rs.{consumed_value:,.2f}")

    active_value = Decimal('0')
    for layer in FIFOCostLayer.objects.filter(is_exhausted=False):
        active_value += layer.unit_cost * layer.remaining_quantity
    print(f"   Active inventory value: Rs.{active_value:,.2f}")

    # Layer breakdown
    print(f"\n   Layer breakdown by source:")
    for src in FIFOCostLayer.objects.values('layer_source').annotate(
        cnt=django.db.models.Count('id'),
        orig=Sum('original_quantity'),
        rem=Sum('remaining_quantity'),
    ).order_by('layer_source'):
        consumed = src['orig'] - src['rem']
        print(f"     {src['layer_source']:20s} | {src['cnt']:4d} layers | orig: {src['orig']:6d} | consumed: {consumed:6d} | remaining: {src['rem']:6d}")


# We need consume_fifo_by_id - a variant that takes product_id instead of product object
# to avoid N+1 queries. Let's just add it as a wrapper.
# Actually, the existing consume_fifo already works with product objects.
# Let's preload products and use the existing method.

def run():
    """Wrapper that patches consume_fifo to work efficiently."""
    from products.models import Product

    print("=" * 70)
    print("FULL FIFO REPLAY")
    print("=" * 70)

    # Step 0a: Delete FIFO layers from cancelled returns
    print("\n0a. Removing FIFO layers from cancelled returns...")
    from sales.models import Return
    cancelled_return_numbers = list(
        Return.objects.filter(settlement_status='cancelled').values_list('return_number', flat=True)
    )
    if cancelled_return_numbers:
        deleted_count, _ = FIFOCostLayer.objects.filter(
            layer_source='return',
            reference_number__in=cancelled_return_numbers,
        ).delete()
        print(f"    Deleted {deleted_count} layers from {len(cancelled_return_numbers)} cancelled returns")
    else:
        print(f"    No cancelled returns found")

    # Step 0b: Ensure exactly ONE OB layer per product
    # Delete all duplicate OB layers, keeping only the oldest per product
    print("\n0b. Deduplicating OB layers (keep exactly 1 per product)...")
    from django.db.models import Min
    ob_layers = FIFOCostLayer.objects.filter(layer_source='opening_balance')
    # Get the oldest (lowest id) OB layer per product
    keep_ids = (
        ob_layers.values('product_id')
        .annotate(keep_id=Min('id'))
        .values_list('keep_id', flat=True)
    )
    keep_ids_list = list(keep_ids)
    ob_dupes_deleted, _ = ob_layers.exclude(id__in=keep_ids_list).delete()
    print(f"    Kept {len(keep_ids_list)} OB layers, deleted {ob_dupes_deleted} duplicates")

    # Also deduplicate OB StockMovements (keep oldest per product)
    ob_movements = StockMovement.objects.filter(movement_type='opening_balance')
    keep_mv_ids = (
        ob_movements.values('product_id')
        .annotate(keep_id=Min('id'))
        .values_list('keep_id', flat=True)
    )
    keep_mv_ids_list = list(keep_mv_ids)
    ob_mv_dupes_deleted, _ = ob_movements.exclude(id__in=keep_mv_ids_list).delete()
    print(f"    Kept {len(keep_mv_ids_list)} OB movements, deleted {ob_mv_dupes_deleted} duplicates")

    # Step 1: Reset all remaining FIFO layers to full capacity
    print("\n1. Resetting all FIFO layers to full capacity...")
    reset_count = FIFOCostLayer.objects.all().update(
        remaining_quantity=django.db.models.F('original_quantity'),
        is_exhausted=False,
    )
    print(f"   Reset {reset_count} layers")

    # Step 2: Gather ALL stock-out events (not just sales + exchange OUTs)
    # Any movement that reduces stock should consume FIFO layers
    print("\n2. Gathering ALL stock-out events...")

    # 2a. Sale movements
    sale_movements = list(StockMovement.objects.filter(
        movement_type='sale'
    ).order_by('created_at', 'id'))
    print(f"   Sale movements: {len(sale_movements)}")

    # 2b. Exchange OUT movements (exchange with negative qty, not cancellations)
    exchange_out_movements = list(StockMovement.objects.filter(
        movement_type='exchange',
        quantity__lt=0,
    ).exclude(
        reference_number__icontains='CANCEL'
    ).order_by('created_at', 'id'))
    print(f"   Exchange OUT movements: {len(exchange_out_movements)}")

    # 2c. ALL other stock-reducing movements (damage, purchase_return,
    # non_resaleable, status_adjustment, adjustments, etc.)
    # These reduce physical stock and should consume FIFO layers so
    # FIFO remaining matches DB stock.
    other_out_types = [
        'damage', 'purchase_return', 'return_to_company',
        'non_resaleable_in', 'non_resaleable_out',
        'status_adjustment', 'disposal',
    ]
    other_out_movements = list(StockMovement.objects.filter(
        movement_type__in=other_out_types,
        quantity__lt=0,
    ).order_by('created_at', 'id'))
    print(f"   Other stock-out movements: {len(other_out_movements)}")

    # 2d. Negative adjustments (qty < 0) that are NOT cancelled return reversals
    # Cancelled return reversals have reference_number matching RN-* or RET* and
    # their FIFO layer was already deleted in step 0a, so they should not consume
    # additional layers.
    adj_movements = list(StockMovement.objects.filter(
        movement_type='adjustment',
        quantity__lt=0,
    ).exclude(
        # Exclude cancelled return stock reversals (already handled by layer deletion)
        reference_number__in=cancelled_return_numbers
    ).exclude(
        # Also exclude old-format cancelled return reversals
        reference_number__startswith='RET'
    ).order_by('created_at', 'id'))
    print(f"   Adjustment (negative) movements: {len(adj_movements)}")

    # Merge ALL events chronologically
    all_events = []
    for mv in sale_movements:
        all_events.append(('sale', mv))
    for mv in exchange_out_movements:
        all_events.append(('exchange_out', mv))
    for mv in other_out_movements:
        all_events.append(('other_out', mv))
    for mv in adj_movements:
        all_events.append(('adjustment_out', mv))

    all_events.sort(key=lambda x: (x[1].created_at, x[1].id))
    print(f"   Total events to replay: {len(all_events)}")

    # Preload products
    product_cache = {p.id: p for p in Product.objects.all()}

    # Build BillItem lookup: (bill_number, product_id) → [BillItem, ...]
    print("\n3. Building BillItem lookup...")
    bill_items_map = {}
    for item in BillItem.objects.filter(
        bill__bill_status='confirmed'
    ).select_related('bill'):
        key = (item.bill.bill_number, item.product_id)
        if key not in bill_items_map:
            bill_items_map[key] = []
        bill_items_map[key].append(item)
    print(f"   BillItem keys mapped: {len(bill_items_map)}")

    # Step 4: Replay
    print("\n4. Replaying FIFO consumption in chronological order...")
    sales_updated = 0
    sales_not_found = 0
    exchanges_consumed = 0
    other_consumed = 0
    adj_consumed = 0
    total_cogs = Decimal('0')

    for event_type, mv in all_events:
        product = product_cache.get(mv.product_id)
        if not product:
            continue

        qty = abs(mv.quantity)
        if qty <= 0:
            continue

        # Consume FIFO layers
        weighted_avg, breakdown = FIFOCostLayer.consume_fifo(product, int(qty))

        if event_type == 'sale':
            key = (mv.reference_number, mv.product_id)
            items = bill_items_map.get(key, [])
            if items:
                bill_item = items.pop(0)
                total_qty = bill_item.quantity + (bill_item.foc_quantity or 0)
                bill_item.unit_cost = weighted_avg
                bill_item.total_cost = weighted_avg * total_qty
                bill_item.cost_breakdown = breakdown
                bill_item.save(update_fields=['unit_cost', 'total_cost', 'cost_breakdown'])
                total_cogs += bill_item.total_cost
                sales_updated += 1
            else:
                sales_not_found += 1
        elif event_type == 'exchange_out':
            exchanges_consumed += 1
        elif event_type == 'other_out':
            other_consumed += 1
        else:
            adj_consumed += 1

    print(f"   Sales BillItems updated: {sales_updated}")
    print(f"   Sales not found (cancelled?): {sales_not_found}")
    print(f"   Exchange OUTs consumed: {exchanges_consumed}")
    print(f"   Other stock-outs consumed: {other_consumed}")
    print(f"   Adjustments consumed: {adj_consumed}")

    # Step 5: Reconcile FIFO remaining with actual DB stock
    # Some edge cases (non-resaleable moves, cancelled return reversals) can
    # leave FIFO remaining != DB stock. Fix by consuming excess or creating
    # adjustment layers for shortfall.
    print("\n5. Reconciling FIFO remaining with DB stock...")
    reconciled = 0
    for p in Product.objects.all():
        fifo_rem = sum(
            l.remaining_quantity
            for l in FIFOCostLayer.objects.filter(product=p)
        )
        diff = fifo_rem - p.quantity_in_stock

        if diff > 0:
            # FIFO has more than DB stock — consume excess from oldest layers
            excess = diff
            for layer in FIFOCostLayer.objects.filter(
                product=p, remaining_quantity__gt=0
            ).order_by('created_at'):
                if excess <= 0:
                    break
                take = min(excess, layer.remaining_quantity)
                layer.remaining_quantity -= take
                if layer.remaining_quantity <= 0:
                    layer.is_exhausted = True
                layer.save()
                excess -= take
            reconciled += 1
            print(f"   {p.product_code}: consumed {diff} excess (FIFO was {fifo_rem}, DB={p.quantity_in_stock})")

        elif diff < 0:
            # FIFO has less than DB stock — create adjustment layer
            shortfall = abs(diff)
            FIFOCostLayer.objects.create(
                product=p,
                unit_cost=p.cost_after_foc or Decimal('0'),
                original_quantity=shortfall,
                remaining_quantity=shortfall,
                layer_source='adjustment',
                reference_number='RECONCILE-FIFO',
                is_exhausted=False,
            )
            reconciled += 1
            print(f"   {p.product_code}: created adjustment layer +{shortfall} (FIFO was {fifo_rem}, DB={p.quantity_in_stock})")

    if reconciled == 0:
        print("   All products already balanced!")
    else:
        print(f"   Reconciled {reconciled} products")

    # Step 6: Fix exhausted status
    print("\n6. Updating exhausted status...")
    FIFOCostLayer.objects.filter(remaining_quantity__lte=0).update(is_exhausted=True)
    FIFOCostLayer.objects.filter(remaining_quantity__gt=0).update(is_exhausted=False)

    # Step 7: Verification
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)

    final_cogs = BillItem.objects.filter(
        bill__bill_status='confirmed'
    ).aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
    print(f"\n   COGS from BillItems: Rs.{final_cogs:,.2f}")

    layer_stats = FIFOCostLayer.objects.aggregate(
        orig=Sum('original_quantity'),
        rem=Sum('remaining_quantity'),
    )
    consumed_qty = (layer_stats['orig'] or 0) - (layer_stats['rem'] or 0)
    total_event_qty = sum(abs(e[1].quantity) for e in all_events)

    print(f"   Total event qty (all outflows): {total_event_qty}")
    print(f"   FIFO layers consumed qty: {consumed_qty}")
    print(f"   Fallback qty: {total_event_qty - consumed_qty}")
    print(f"   Layers remaining qty: {layer_stats['rem']}")

    consumed_value = Decimal('0')
    for layer in FIFOCostLayer.objects.all():
        c = layer.original_quantity - layer.remaining_quantity
        if c > 0:
            consumed_value += layer.unit_cost * c
    print(f"   Layer consumed value: Rs.{consumed_value:,.2f}")

    active_val = Decimal('0')
    active_count = 0
    for layer in FIFOCostLayer.objects.filter(is_exhausted=False):
        active_val += layer.unit_cost * layer.remaining_quantity
        active_count += 1
    print(f"   Active layers: {active_count}, Value: Rs.{active_val:,.2f}")

    print(f"\n   Layer breakdown:")
    for src in FIFOCostLayer.objects.values('layer_source').annotate(
        cnt=django.db.models.Count('id'),
        orig=Sum('original_quantity'),
        rem=Sum('remaining_quantity'),
    ).order_by('layer_source'):
        consumed = src['orig'] - src['rem']
        print(f"     {src['layer_source']:20s} | {src['cnt']:4d} layers | "
              f"orig: {src['orig']:6d} | consumed: {consumed:6d} | remaining: {src['rem']:6d}")

    # Stock vs FIFO check
    print(f"\n   Stock vs FIFO remaining:")
    mismatches = 0
    for p in Product.objects.all().order_by('product_name'):
        fifo_rem = sum(l.remaining_quantity for l in FIFOCostLayer.objects.filter(product=p))
        if p.quantity_in_stock != fifo_rem:
            mismatches += 1
            print(f"     MISMATCH {p.product_code} {p.product_name}: DB={p.quantity_in_stock} FIFO={fifo_rem} diff={fifo_rem - p.quantity_in_stock:+d}")
    if mismatches == 0:
        print(f"     ALL {Product.objects.count()} products match!")
    else:
        print(f"     {mismatches} mismatches found")

    # Revenue for reference
    revenue = Bill.objects.filter(bill_status='confirmed').aggregate(
        t=Sum('total_amount'))['t'] or 0
    print(f"\n   Gross Sales: Rs.{revenue:,.2f}")
    print(f"   COGS: Rs.{final_cogs:,.2f}")
    print(f"   Gross Profit: Rs.{revenue - final_cogs:,.2f}")
    gm = ((revenue - final_cogs) / revenue * 100) if revenue > 0 else 0
    print(f"   Gross Margin: {gm:.1f}%")


if __name__ == '__main__':
    run()
