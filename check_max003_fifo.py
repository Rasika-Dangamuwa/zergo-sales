import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from products.models import StockMovement, FIFOCostLayer

print('=== MAX003 FIFO layers ===')
for l in FIFOCostLayer.objects.filter(product__product_code='MAX003').order_by('created_at'):
    print(f'  {l.layer_source:20s} | {l.reference_number or "":25s} | cost={l.unit_cost} | orig={l.original_quantity:4d} | rem={l.remaining_quantity:4d} | created={l.created_at.strftime("%Y-%m-%d %H:%M")}')

print()
print('=== MAX003 stock IN movements (layers created) ===')
for m in StockMovement.objects.filter(product__product_code='MAX003', quantity__gt=0).order_by('created_at'):
    print(f'  {m.movement_type:20s} | {m.reference_number or "":25s} | qty={m.quantity:5d} | created={m.created_at.strftime("%Y-%m-%d %H:%M")}')

print()
print('=== MAX003 stock OUT movements (FIFO consumed) ===')
for m in StockMovement.objects.filter(product__product_code='MAX003', quantity__lt=0).order_by('created_at'):
    print(f'  {m.movement_type:20s} | {m.reference_number or "":25s} | qty={m.quantity:5d} | created={m.created_at.strftime("%Y-%m-%d %H:%M")}')

print()
# Check BILL-20260109-002 specifically
from sales.models import BillItem
bi = BillItem.objects.filter(bill__bill_number='BILL-20260109-002', product__product_code='MAX003').first()
if bi:
    print(f'=== BillItem for BILL-20260109-002 MAX003 ===')
    print(f'  qty={bi.quantity}, foc={bi.foc_quantity}, unit_cost={bi.unit_cost}, total_cost={bi.total_cost}')
    print(f'  cost_breakdown={bi.cost_breakdown}')
