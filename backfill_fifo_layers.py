"""
Backfill FIFO cost layers and BillItem costs from historical data.

Steps:
1. Create FIFO cost layers from all stock-IN movements (purchase, opening_balance, return)
2. Process confirmed bills chronologically — consume layers oldest-first per product
3. Record unit_cost/total_cost on each BillItem
4. Create sale StockMovements for historical bills

Run: python backfill_fifo_layers.py
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from decimal import Decimal
from django.db import transaction
from products.models import StockMovement, FIFOCostLayer, Product
from sales.models import Bill, BillItem


def backfill():
    print("=" * 60)
    print("FIFO Cost Layer Backfill")
    print("=" * 60)
    
    # Step 1: Clear any existing layers (fresh start)
    existing = FIFOCostLayer.objects.count()
    if existing > 0:
        print(f"\nClearing {existing} existing FIFO layers...")
        FIFOCostLayer.objects.all().delete()
    
    # Step 2: Create layers from all stock-IN movements, ordered chronologically
    in_types = ['purchase', 'opening_balance', 'return', 'exchange']
    in_movements = StockMovement.objects.filter(
        movement_type__in=in_types,
        quantity__gt=0  # Only stock-in (positive quantity)
    ).select_related('product').order_by('created_at')
    
    source_map = {
        'purchase': 'purchase',
        'opening_balance': 'opening_balance',
        'return': 'return',
        'exchange': 'exchange_in',
    }
    
    layers_created = 0
    for mv in in_movements:
        if not mv.product:
            continue
        
        unit_cost = mv.unit_cost
        if not unit_cost or unit_cost <= 0:
            # Fallback to product.company_price
            unit_cost = mv.product.company_price if mv.product.company_price else Decimal('0')
        
        if unit_cost and unit_cost > 0 and mv.quantity > 0:
            FIFOCostLayer.objects.create(
                product=mv.product,
                unit_cost=unit_cost,
                original_quantity=mv.quantity,
                remaining_quantity=mv.quantity,
                layer_source=source_map.get(mv.movement_type, 'adjustment'),
                reference_number=mv.reference_number,
                created_at=mv.created_at,
            )
            layers_created += 1
    
    print(f"\nCreated {layers_created} FIFO cost layers from stock-in movements.")
    
    # Step 3: Process confirmed bills chronologically
    # Consume layers oldest-first for each bill item
    bills = Bill.objects.filter(
        bill_status='confirmed'
    ).prefetch_related('items__product').order_by('bill_date', 'id')
    
    total_bills = bills.count()
    print(f"\nProcessing {total_bills} confirmed bills...")
    
    bills_processed = 0
    items_costed = 0
    items_no_cost = 0
    sale_movements_created = 0
    
    # Delete any existing sale stock movements (we'll recreate them)
    existing_sale_movements = StockMovement.objects.filter(movement_type='sale').count()
    if existing_sale_movements > 0:
        print(f"Cleaning {existing_sale_movements} existing sale stock movements...")
        StockMovement.objects.filter(movement_type='sale').delete()
    
    for bill in bills:
        for item in bill.items.all():
            product = item.product
            total_qty = int(item.quantity + item.foc_quantity)
            
            if total_qty <= 0:
                continue
            
            # Consume FIFO layers
            fifo_cost, _ = FIFOCostLayer.consume_fifo(product, total_qty)
            
            # Update BillItem with cost
            if fifo_cost and fifo_cost > 0:
                item.unit_cost = fifo_cost
                item.total_cost = fifo_cost * Decimal(str(total_qty))
                item.save(update_fields=['unit_cost', 'total_cost'])
                items_costed += 1
            else:
                items_no_cost += 1
            
            # Create sale stock movement
            StockMovement.objects.create(
                product=product,
                movement_type='sale',
                quantity=-total_qty,
                previous_quantity=0,  # Historical — exact previous unknown
                new_quantity=0,       # Historical — exact new unknown
                reference_number=bill.bill_number,
                notes=f'Bill: {bill.bill_number} (backfill)',
                unit_cost=fifo_cost if fifo_cost else Decimal('0'),
                total_cost=(fifo_cost * Decimal(str(total_qty))) if fifo_cost else Decimal('0'),
                created_at=bill.bill_date,
            )
            sale_movements_created += 1
        
        bills_processed += 1
        if bills_processed % 50 == 0:
            print(f"  Processed {bills_processed}/{total_bills} bills...")
    
    # Step 4: Summary
    remaining_layers = FIFOCostLayer.objects.filter(is_exhausted=False, remaining_quantity__gt=0).count()
    exhausted_layers = FIFOCostLayer.objects.filter(is_exhausted=True).count()
    
    print(f"\n{'=' * 60}")
    print(f"Backfill Complete!")
    print(f"{'=' * 60}")
    print(f"  FIFO layers created:      {layers_created}")
    print(f"  Bills processed:          {bills_processed}")
    print(f"  Items costed (FIFO):      {items_costed}")
    print(f"  Items without cost:       {items_no_cost}")
    print(f"  Sale movements created:   {sale_movements_created}")
    print(f"  Layers exhausted:         {exhausted_layers}")
    print(f"  Layers with remaining:    {remaining_layers}")
    print(f"{'=' * 60}\n")


if __name__ == '__main__':
    backfill()
