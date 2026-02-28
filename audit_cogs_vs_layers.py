"""Audit COGS vs FIFO layers to find discrepancies."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from decimal import Decimal
from django.db.models import Sum, F, Q, Count
from products.models import FIFOCostLayer, Product
from sales.models import Bill, BillItem

print("=" * 70)
print("COGS vs FIFO LAYERS AUDIT")
print("=" * 70)

# 1. COGS from BillItems
cogs = BillItem.objects.filter(bill__bill_status='confirmed').aggregate(
    total_cost=Sum('total_cost'),
    total_qty=Sum('quantity'),
    total_foc=Sum('foc_quantity'),
    count=Count('id'),
)
print(f"\n1. COGS from BillItems (confirmed bills):")
print(f"   Items: {cogs['count']}")
print(f"   Qty sold: {cogs['total_qty']}, FOC: {cogs['total_foc']}")
total_units_sold = (cogs['total_qty'] or 0) + (cogs['total_foc'] or 0)
print(f"   Total units (sold+FOC): {total_units_sold}")
print(f"   COGS total: Rs.{cogs['total_cost']:,.2f}")

# 2. FIFO layers summary
print(f"\n2. FIFO Layers by Source:")
for src in FIFOCostLayer.objects.values('layer_source').annotate(
    cnt=Count('id'),
    orig_qty=Sum('original_quantity'),
    rem_qty=Sum('remaining_quantity'),
).order_by('layer_source'):
    consumed = src['orig_qty'] - src['rem_qty']
    print(f"   {src['layer_source']:20s} | {src['cnt']:4d} layers | orig: {src['orig_qty']:6d} | consumed: {consumed:6d} | remaining: {src['rem_qty']:6d}")

total_layers = FIFOCostLayer.objects.aggregate(
    orig=Sum('original_quantity'),
    rem=Sum('remaining_quantity'),
)
total_consumed_qty = total_layers['orig'] - total_layers['rem']
print(f"\n   TOTAL: orig={total_layers['orig']}, consumed={total_consumed_qty}, remaining={total_layers['rem']}")

# 3. Compare consumed qty vs sold qty
print(f"\n3. Qty Comparison:")
print(f"   Units sold+FOC (BillItems): {total_units_sold}")
print(f"   Units consumed (FIFO layers): {total_consumed_qty}")
print(f"   Difference: {total_units_sold - total_consumed_qty}")
if total_units_sold != total_consumed_qty:
    print(f"   *** MISMATCH: FIFO consumed ({total_consumed_qty}) != sold ({total_units_sold}) ***")

# 4. Check COGS calculation - is it using weighted avg from FIFO correctly?
print(f"\n4. COGS value comparison:")
# Calculate what COGS should be from the actual FIFO consumption
# The backfill replayed all BillItems through consume_fifo, so let's check
# what the layers show as consumed value
consumed_value = Decimal('0')
for layer in FIFOCostLayer.objects.all():
    consumed_qty = layer.original_quantity - layer.remaining_quantity
    if consumed_qty > 0:
        consumed_value += layer.unit_cost * consumed_qty

print(f"   COGS on P&L (BillItem.total_cost sum): Rs.{cogs['total_cost']:,.2f}")
print(f"   Value consumed from FIFO layers:        Rs.{consumed_value:,.2f}")
print(f"   Difference: Rs.{cogs['total_cost'] - consumed_value:,.2f}")

# 5. Check for non-sale consumption of layers
# Stock movements that consume stock but aren't sales
print(f"\n5. Non-sale stock-out movements (also consume FIFO):")
from products.models import StockMovement
non_sale_out = StockMovement.objects.filter(quantity__lt=0).exclude(
    movement_type='sale'
).values('movement_type').annotate(
    cnt=Count('id'),
    total_qty=Sum('quantity'),
).order_by('movement_type')
for mv in non_sale_out:
    print(f"   {mv['movement_type']:25s} | {mv['cnt']:4d} movements | qty: {mv['total_qty']}")

# 6. Check if exchange OUT and other outflows consumed FIFO layers but aren't in BillItems
print(f"\n6. Layer consumption sources:")
print(f"   FIFO layers are consumed by: sales (BillItems), exchanges OUT, purchase returns")
print(f"   But only BillItems contribute to COGS on P&L")
print(f"   So consumed_from_layers > COGS is expected if exchanges/returns also consumed layers")

# 7. Check exchange FIFO consumption
# In exchange_views.py, exchange OUT calls FIFOCostLayer.consume_fifo()
# This means exchange outs consume layers but don't create BillItems
print(f"\n7. Stock-out events that consume FIFO layers:")
# Sales (from confirmed bills)
print(f"   Sales (BillItems qty+foc):     {total_units_sold}")

# Exchange outs
exchange_out = StockMovement.objects.filter(
    movement_type='exchange', quantity__lt=0
).aggregate(q=Sum('quantity'))
exchange_out_qty = abs(exchange_out['q'] or 0)
print(f"   Exchange OUT (from movements): {exchange_out_qty}")

# Purchase returns (sent to supplier) - these also call consume_fifo? Let me check
pr_out = StockMovement.objects.filter(
    movement_type='purchase_return', quantity__lt=0
).aggregate(q=Sum('quantity'))
pr_out_qty = abs(pr_out['q'] or 0)
print(f"   Purchase Returns:              {pr_out_qty}")

# Status adjustments OUT 
adj_out = StockMovement.objects.filter(
    movement_type__in=['adjustment', 'status_adjustment', 'non_resaleable_in', 'non_resaleable_out'],
    quantity__lt=0
).aggregate(q=Sum('quantity'))
adj_out_qty = abs(adj_out['q'] or 0)
print(f"   Adjustments/Status (out):      {adj_out_qty}")

# Return cancellations (take stock back out)
cancel_out = StockMovement.objects.filter(
    reference_number__icontains='cancel', 
    movement_type='exchange',
    quantity__lt=0
).aggregate(q=Sum('quantity'))
cancel_out_qty = abs(cancel_out['q'] or 0)
print(f"   Exchange cancel reversals:     {cancel_out_qty}")

expected_consumed = total_units_sold + exchange_out_qty
print(f"\n   Expected total consumed: {total_units_sold} (sales) + {exchange_out_qty} (exch) = {expected_consumed}")
print(f"   Actual FIFO consumed:    {total_consumed_qty}")
print(f"   Gap: {total_consumed_qty - expected_consumed}")

# 8. Per-product COGS check (top 10 by COGS)
print(f"\n8. Top 10 Products by COGS:")
product_cogs = BillItem.objects.filter(
    bill__bill_status='confirmed'
).values(
    'product__product_name', 'product__product_code'
).annotate(
    total_cogs=Sum('total_cost'),
    total_qty=Sum('quantity'),
    total_foc=Sum('foc_quantity'),
).order_by('-total_cogs')[:10]

for p in product_cogs:
    qty = (p['total_qty'] or 0) + (p['total_foc'] or 0)
    avg = p['total_cogs'] / qty if qty > 0 else 0
    print(f"   {p['product__product_name']:35s} | qty: {qty:5d} | COGS: Rs.{p['total_cogs']:>10,.2f} | avg: Rs.{avg:.4f}")

# 9. Cross-check: sum of per-product COGS
total_product_cogs = BillItem.objects.filter(
    bill__bill_status='confirmed'
).values('product').annotate(t=Sum('total_cost')).aggregate(grand=Sum('t'))
print(f"\n   Sum of all product COGS: Rs.{total_product_cogs['grand']:,.2f}")

# 10. Check BillItems with zero or null cost
zero_cost = BillItem.objects.filter(
    bill__bill_status='confirmed',
    total_cost__lte=0
).count()
null_cost = BillItem.objects.filter(
    bill__bill_status='confirmed',
    total_cost__isnull=True
).count()
print(f"\n9. BillItems with zero/null cost:")
print(f"   Zero cost: {zero_cost}")
print(f"   Null cost: {null_cost}")

if zero_cost > 0:
    print(f"   Zero cost items:")
    for item in BillItem.objects.filter(bill__bill_status='confirmed', total_cost__lte=0).select_related('product', 'bill')[:10]:
        print(f"     Bill {item.bill.bill_number} | {item.product.product_name} | qty: {item.quantity} | foc: {item.foc_quantity} | unit_cost: {item.unit_cost} | total_cost: {item.total_cost}")
