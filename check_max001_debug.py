"""Deep investigation: what SHOULD the FIFO layers be for MAX001 & MAX003?
Compare layer totals with stock movements that create layers."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from decimal import Decimal
from collections import defaultdict
from products.models import FIFOCostLayer, StockMovement, Product
from sales.models import Return

cancelled_rns = set(Return.objects.filter(settlement_status='cancelled').values_list('return_number', flat=True))

for code in ['MAX001', 'MAX003']:
    p = Product.objects.get(product_code=code)
    print(f"\n{'='*70}")
    print(f"{code} - DB stock: {p.quantity_in_stock}")
    print(f"{'='*70}")
    
    # Current FIFO layers
    layers = FIFOCostLayer.objects.filter(product=p).order_by('created_at')
    fifo_orig = sum(l.original_quantity for l in layers)
    fifo_rem = sum(l.remaining_quantity for l in layers)
    fifo_consumed = fifo_orig - fifo_rem
    
    print(f"\nCurrent FIFO: orig={fifo_orig}, consumed={fifo_consumed}, remaining={fifo_rem}")
    print(f"DB stock: {p.quantity_in_stock}, diff(FIFO-DB): {fifo_rem - p.quantity_in_stock}")
    
    # Layer breakdown
    by_src = defaultdict(lambda: [0, 0])  # [orig, count]
    for l in layers:
        by_src[l.layer_source][0] += l.original_quantity
        by_src[l.layer_source][1] += 1
    print(f"\nFIFO layers by source:")
    for src in sorted(by_src.keys()):
        print(f"  {src:20s}: {by_src[src][1]:4d} layers, orig_qty={by_src[src][0]:6d}")
    
    # Compare: positive stock movements that SHOULD have corresponding layers
    print(f"\nPositive stock movements (layer-creating):")
    pos_moves = StockMovement.objects.filter(product=p, quantity__gt=0).order_by('movement_type', 'created_at')
    pos_by_type = defaultdict(int)
    for m in pos_moves:
        pos_by_type[m.movement_type] += m.quantity
    for t, qty in sorted(pos_by_type.items()):
        print(f"  {t:25s}: +{qty}")
    
    print(f"\nNegative stock movements (should consume layers):")
    neg_moves = StockMovement.objects.filter(product=p, quantity__lt=0).order_by('movement_type', 'created_at')
    neg_by_type = defaultdict(int)
    for m in neg_moves:
        neg_by_type[m.movement_type] += abs(m.quantity)
    for t, qty in sorted(neg_by_type.items()):
        print(f"  {t:25s}: -{qty}")
    
    # Expected: FIFO original = sum of positive movements that create layers
    # These are: opening_balance, sale (NO - that's negative), purchase/GRN, return, exchange(positive)
    # Wait - not all positive movements correspond to a FIFO layer creation
    # FIFO layers are only from: purchase, opening_balance, return, exchange_in, adjustment
    # Let's match them
    
    print(f"\n--- FIFO layer-creating events vs actual layers ---")
    
    # Positive stock movements that should create layers
    layer_creating_types = ['opening_balance', 'return', 'exchange']  # exchange positive = exchange_in
    # purchase is handled via GRN (movement_type might differ)
    
    # Actually, let me just check: for each FIFO layer, does a corresponding positive movement exist?
    print(f"\nOrphan check - layers without matching positive movement:")
    orphans = 0
    for l in layers:
        ref = l.reference_number or ''
        src = l.layer_source
        # Find matching positive movement
        if src == 'purchase':
            match = StockMovement.objects.filter(
                product=p, reference_number=ref, quantity__gt=0
            ).exists()
        elif src == 'return':
            match = StockMovement.objects.filter(
                product=p, reference_number=ref, movement_type='return', quantity__gt=0
            ).exists()
            if not match:
                # Check old format
                match = StockMovement.objects.filter(
                    product=p, reference_number=ref, quantity__gt=0
                ).exists()
        elif src == 'exchange_in':
            match = StockMovement.objects.filter(
                product=p, reference_number=ref, movement_type='exchange', quantity__gt=0
            ).exists()
        elif src == 'opening_balance':
            match = StockMovement.objects.filter(
                product=p, reference_number=ref, movement_type='opening_balance'
            ).exists()
        elif src == 'adjustment':
            match = StockMovement.objects.filter(
                product=p, reference_number=ref, quantity__gt=0
            ).exists()
        else:
            match = False
        
        if not match:
            orphans += 1
            if orphans <= 10:
                print(f"  ORPHAN Layer {l.id}: {src} ref={ref} orig={l.original_quantity}")
    
    if orphans > 10:
        print(f"  ... and {orphans - 10} more orphans")
    if orphans == 0:
        print(f"  None - all layers have matching movements")
    
    # Check: are there duplicate positive movements for the same ref?
    print(f"\nDuplicate positive movements (same ref, same type):")
    from django.db.models import Count
    dupes = StockMovement.objects.filter(
        product=p, quantity__gt=0
    ).values('movement_type', 'reference_number').annotate(
        cnt=Count('id')
    ).filter(cnt__gt=1)
    for d in dupes:
        print(f"  {d['movement_type']} ref={d['reference_number']}: {d['cnt']} times")
    if not dupes:
        print("  None found")
