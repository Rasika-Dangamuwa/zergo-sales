"""Check what FIFO remaining would be after removing OB-20260218 duplicates."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from decimal import Decimal
from products.models import FIFOCostLayer, Product, StockMovement

print("=" * 90)
print("ANALYSIS: OB-20260218 duplicates and stock vs FIFO balance")
print("=" * 90)

# For each product, compare: DB stock vs FIFO remaining vs FIFO remaining without OB-20260218
products = Product.objects.all().order_by('product_name')

print(f"\n{'Product':<35} {'DB Stock':>9} {'FIFO Rem':>9} {'No OB218':>9} {'Diff':>9}")
print("-" * 80)

total_db = 0
total_fifo = 0
total_no_ob = 0
problems = []

for p in products:
    all_layers = FIFOCostLayer.objects.filter(product=p)
    fifo_remaining = sum(l.remaining_quantity for l in all_layers)
    
    # Without OB-20260218
    ob218_layers = all_layers.filter(layer_source='opening_balance', reference_number='OB-20260218')
    ob218_qty = sum(l.remaining_quantity for l in ob218_layers)
    fifo_no_ob = fifo_remaining - ob218_qty
    
    diff = fifo_no_ob - p.quantity_in_stock
    
    total_db += p.quantity_in_stock
    total_fifo += fifo_remaining
    total_no_ob += fifo_no_ob
    
    status = "OK" if diff == 0 else f"{diff:+d}"
    name = f"{p.product_code} {p.product_name}"[:34]
    
    if diff != 0:
        problems.append((p, p.quantity_in_stock, fifo_remaining, fifo_no_ob, diff))
    
    print(f"{name:<35} {p.quantity_in_stock:>9} {fifo_remaining:>9} {fifo_no_ob:>9} {status:>9}")

print("-" * 80)
print(f"{'TOTALS':<35} {total_db:>9} {total_fifo:>9} {total_no_ob:>9} {total_no_ob - total_db:>+9}")

# Check non-sale stock reductions that might explain remaining differences
print(f"\n\nProducts with diff after removing OB-20260218: {len(problems)}")
if problems:
    print("\nChecking stock movements for unexplained differences:")
    for p, db, fifo, no_ob, diff in problems:
        print(f"\n  {p.product_code} {p.product_name}: DB={db}, FIFO(no OB218)={no_ob}, diff={diff:+d}")
        # Find stock-reducing movements that aren't sale/exchange_out
        adj_moves = StockMovement.objects.filter(
            product=p,
            quantity__lt=0
        ).exclude(
            movement_type__in=['sale']
        ).exclude(
            movement_type='exchange', quantity__lt=0
        )
        for m in adj_moves:
            print(f"    {m.movement_type}: qty={m.quantity} ref={m.reference_number} date={m.created_at.date()}")
