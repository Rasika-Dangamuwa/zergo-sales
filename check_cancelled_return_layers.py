import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'zergo_sales.settings'
django.setup()

from products.models import FIFOCostLayer
from sales.models import Return

# Check these specific layers
print('=== Layers for RN-20260201-001 and RN-20260201-002 ===')
layers = FIFOCostLayer.objects.filter(reference_number__in=['RN-20260201-001', 'RN-20260201-002'])
for l in layers:
    consumed = l.original_quantity - l.remaining_quantity
    print(f'  Layer {l.id}: {l.product.product_name} | ref={l.reference_number} | source={l.layer_source} | orig={l.original_quantity} | consumed={consumed} | remaining={l.remaining_quantity} | exhausted={l.is_exhausted} | unit_cost={l.unit_cost}')

print()

# Check if those returns are cancelled
print('=== Return statuses ===')
returns = Return.objects.filter(return_number__in=['RN-20260201-001', 'RN-20260201-002'])
for r in returns:
    print(f'  {r.return_number}: return_status={r.return_status} | settlement_status={r.settlement_status}')

print()

# Check ALL cancelled returns and their FIFO layers
cancelled_returns = Return.objects.filter(return_status='cancelled')
print(f'Total cancelled returns: {cancelled_returns.count()}')
for r in cancelled_returns:
    print(f'  {r.return_number}: status={r.return_status}')
    rn_layers = FIFOCostLayer.objects.filter(reference_number=r.return_number)
    if rn_layers.exists():
        for l in rn_layers:
            consumed = l.original_quantity - l.remaining_quantity
            print(f'    Layer {l.id}: orig={l.original_quantity} remaining={l.remaining_quantity} consumed={consumed} exhausted={l.is_exhausted}')
    else:
        print(f'    No FIFO layers (good)')

print()

# Full scan: Return layers where the return is cancelled
print('=== ALL return-source layers where return is cancelled ===')
all_return_layers = FIFOCostLayer.objects.filter(layer_source='return')
problem_layers = []
for l in all_return_layers:
    try:
        ret = Return.objects.get(return_number=l.reference_number)
        if ret.return_status == 'cancelled':
            consumed = l.original_quantity - l.remaining_quantity
            print(f'  PROBLEM Layer {l.id}: ref={l.reference_number} | product={l.product.product_code} | orig={l.original_quantity} consumed={consumed} remaining={l.remaining_quantity} | exhausted={l.is_exhausted}')
            problem_layers.append(l)
    except Return.DoesNotExist:
        print(f'  ORPHAN Layer {l.id}: ref={l.reference_number} - Return not found!')

print(f'\nTotal problem layers (return cancelled but layer exists): {len(problem_layers)}')
if problem_layers:
    total_orig = sum(l.original_quantity for l in problem_layers)
    total_consumed = sum(l.original_quantity - l.remaining_quantity for l in problem_layers)
    total_remaining = sum(l.remaining_quantity for l in problem_layers)
    print(f'  Total original qty: {total_orig}')
    print(f'  Total consumed qty: {total_consumed}')
    print(f'  Total remaining qty: {total_remaining}')
