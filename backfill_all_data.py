"""
Comprehensive Data Backfill & Consistency Fix Script
====================================================
Fixes all data inconsistencies found during audit:

1. Fix cancelled bills: set balance/paid to 0, status to 'settled'
2. Fix $0-total confirmed test bills: items with line_total=0 → recalculate or mark cancelled
3. Fix settlement_status typo: 'partially_settled' → 'partial_settled'
4. Recalculate bill paid_amount/balance from actual settlements
5. Fix bill settlement_status based on paid vs total
6. Recalculate product stock from StockMovement records
7. Rebuild FIFO layers from purchase/return/exchange movements
8. Recalculate BillItem costs from rebuilt FIFO layers
9. Fix commission running_balance per sales rep
10. Fix shop current_balance from confirmed bill balances

Run: python backfill_all_data.py
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, F, Q
from products.models import Product, StockMovement, FIFOCostLayer
from sales.models import Bill, BillItem, Return, ReturnItem, CommissionTransaction
from payments.models import SalesAccountSettlement
from shops.models import Shop
from accounts.models import User


def log(msg):
    print(f"  {msg}")


def fix_cancelled_bills():
    """Step 1: Cancelled bills should have 0 balance, 0 paid, status='settled'"""
    print("\n=== STEP 1: Fix Cancelled Bills ===")
    cancelled = Bill.objects.filter(bill_status='cancelled')
    fixed = 0
    for b in cancelled:
        changes = []
        if b.balance_amount != Decimal('0'):
            changes.append(f"balance {b.balance_amount}→0")
            b.balance_amount = Decimal('0')
        if b.paid_amount != Decimal('0'):
            changes.append(f"paid {b.paid_amount}→0")
            b.paid_amount = Decimal('0')
        # Cancelled bills shouldn't show as unsettled
        if b.settlement_status != 'cancelled':
            changes.append(f"status {b.settlement_status}→cancelled")
            b.settlement_status = 'cancelled'
        if changes:
            b.save(update_fields=['balance_amount', 'paid_amount', 'settlement_status'])
            fixed += 1
            log(f"Fixed {b.bill_number}: {', '.join(changes)}")
    print(f"  Fixed {fixed}/{cancelled.count()} cancelled bills")


def fix_zero_total_bills():
    """Step 2: Confirmed bills with $0 total whose items also have $0 line_total are test data.
    These are all items with quantity=0 or unit_price=0. Mark them as settled since nothing is owed."""
    print("\n=== STEP 2: Fix $0-Total Confirmed Bills ===")
    zero_bills = Bill.objects.filter(bill_status='confirmed', total_amount=0, subtotal=0)
    fixed = 0
    for b in zero_bills:
        items = BillItem.objects.filter(bill=b)
        items_sum = items.aggregate(s=Sum('line_total'))['s'] or Decimal('0')
        if items_sum == Decimal('0'):
            # All items are $0 too — this is test data, mark as settled
            if b.settlement_status != 'settled':
                b.settlement_status = 'settled'
                b.save(update_fields=['settlement_status'])
                fixed += 1
                log(f"Fixed {b.bill_number}: {items.count()} items, all $0 → settled")
    print(f"  Fixed {fixed} zero-total bills to 'settled'")


def fix_settlement_status_typo():
    """Step 3: Fix 'partially_settled' → 'partial_settled'."""
    print("\n=== STEP 3: Fix Settlement Status Typo ===")
    fixed = Bill.objects.filter(settlement_status='partially_settled').update(
        settlement_status='partial_settled'
    )
    print(f"  Fixed {fixed} bills from 'partially_settled' → 'partial_settled'")


def recalculate_bill_payments():
    """Step 4 & 5: Recalculate paid_amount from actual completed settlements, then fix balance and status."""
    print("\n=== STEP 4: Recalculate Bill Payments & Status ===")
    fixed = 0
    for b in Bill.objects.filter(bill_status='confirmed'):
        settled = SalesAccountSettlement.objects.filter(
            bill=b, settlement_status='completed'
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0')

        old_paid = b.paid_amount
        old_balance = b.balance_amount
        old_status = b.settlement_status

        b.paid_amount = settled
        b.balance_amount = b.total_amount - settled

        if b.total_amount <= 0:
            b.settlement_status = 'settled'
        elif b.paid_amount >= b.total_amount:
            b.settlement_status = 'settled'
            b.balance_amount = Decimal('0')
        elif b.paid_amount > 0:
            b.settlement_status = 'partial_settled'
        else:
            b.settlement_status = 'unsettled'

        if (old_paid != b.paid_amount or old_balance != b.balance_amount
                or old_status != b.settlement_status):
            b.save(update_fields=['paid_amount', 'balance_amount', 'settlement_status'])
            fixed += 1
            changes = []
            if old_paid != b.paid_amount:
                changes.append(f"paid {old_paid}→{b.paid_amount}")
            if old_balance != b.balance_amount:
                changes.append(f"balance {old_balance}→{b.balance_amount}")
            if old_status != b.settlement_status:
                changes.append(f"status {old_status}→{b.settlement_status}")
            log(f"Fixed {b.bill_number}: {', '.join(changes)}")
    print(f"  Fixed {fixed} bills")


def recalculate_product_stock():
    """Step 6: Recalculate product stock from StockMovement records."""
    print("\n=== STEP 6: Recalculate Product Stock from Movements ===")
    fixed = 0
    for p in Product.objects.all():
        net_resaleable = StockMovement.objects.filter(
            product=p, stock_type='resaleable'
        ).aggregate(s=Sum('quantity'))['s'] or 0

        net_non_resaleable = StockMovement.objects.filter(
            product=p, stock_type='non_resaleable'
        ).aggregate(s=Sum('quantity'))['s'] or 0

        old_stock = p.quantity_in_stock
        old_nr = p.non_resaleable_stock

        changes = []
        if p.quantity_in_stock != net_resaleable:
            changes.append(f"resaleable {old_stock}→{net_resaleable}")
            p.quantity_in_stock = max(net_resaleable, 0)  # Don't go negative

        if p.non_resaleable_stock != net_non_resaleable:
            changes.append(f"non_resaleable {old_nr}→{net_non_resaleable}")
            p.non_resaleable_stock = max(net_non_resaleable, 0)

        if changes:
            p.save(update_fields=['quantity_in_stock', 'non_resaleable_stock'])
            fixed += 1
            log(f"Fixed {p.product_code} ({p.product_name}): {', '.join(changes)}")
    print(f"  Fixed {fixed} products")


def rebuild_fifo_layers():
    """Step 7: Delete all FIFO layers and rebuild from stock-in movements.
    Step 8: Re-consume for all confirmed bill items and recost them."""
    print("\n=== STEP 7: Rebuild FIFO Cost Layers ===")

    # Delete all existing layers
    old_count = FIFOCostLayer.objects.count()
    FIFOCostLayer.objects.all().delete()
    print(f"  Deleted {old_count} existing layers")

    # Rebuild layers from stock-in movements (positive quantity, specific types)
    stock_in_types = ['opening_balance', 'purchase', 'return', 'exchange', 'adjustment', 'foc_in']

    movements_in = StockMovement.objects.filter(
        movement_type__in=stock_in_types,
        stock_type='resaleable',
        quantity__gt=0
    ).order_by('created_at')

    layer_count = 0
    for mv in movements_in:
        cost = mv.unit_cost or mv.product.company_price
        if cost and cost > 0 and mv.quantity > 0:
            FIFOCostLayer.objects.create(
                product=mv.product,
                unit_cost=cost,
                original_quantity=mv.quantity,
                remaining_quantity=mv.quantity,
                layer_source=mv.movement_type if mv.movement_type in ['purchase', 'opening_balance', 'return'] else 'adjustment',
                reference_number=mv.reference_number or '',
                is_exhausted=False,
                created_at=mv.created_at,
            )
            layer_count += 1

    # Also create layers for return stock-in movements
    return_movements = StockMovement.objects.filter(
        movement_type='return',
        stock_type='resaleable',
        quantity__gt=0
    ).exclude(id__in=movements_in.values_list('id', flat=True))

    for mv in return_movements:
        cost = mv.unit_cost or mv.product.company_price
        if cost and cost > 0:
            FIFOCostLayer.objects.create(
                product=mv.product,
                unit_cost=cost,
                original_quantity=mv.quantity,
                remaining_quantity=mv.quantity,
                layer_source='return',
                reference_number=mv.reference_number or '',
                is_exhausted=False,
                created_at=mv.created_at,
            )
            layer_count += 1

    print(f"  Created {layer_count} FIFO layers from stock-in movements")

    # Step 8: Consume layers for all confirmed bill items (in chronological order)
    print("\n=== STEP 8: Recost Bill Items via FIFO ===")
    bills = Bill.objects.filter(bill_status='confirmed').order_by('bill_date', 'id')
    items_costed = 0
    items_failed = 0

    for bill in bills:
        for item in BillItem.objects.filter(bill=bill).order_by('id'):
            total_qty = int(item.quantity + (item.foc_quantity or 0))
            if total_qty <= 0:
                item.unit_cost = Decimal('0')
                item.total_cost = Decimal('0')
                item.save(update_fields=['unit_cost', 'total_cost'])
                items_costed += 1
                continue

            try:
                # Consume FIFO layers
                layers = FIFOCostLayer.objects.filter(
                    product=item.product,
                    is_exhausted=False,
                    remaining_quantity__gt=0
                ).order_by('created_at')

                remaining = total_qty
                total_cost = Decimal('0')
                for layer in layers:
                    if remaining <= 0:
                        break
                    take = min(remaining, layer.remaining_quantity)
                    total_cost += Decimal(str(take)) * layer.unit_cost
                    layer.remaining_quantity -= take
                    layer.is_exhausted = (layer.remaining_quantity <= 0)
                    layer.save(update_fields=['remaining_quantity', 'is_exhausted'])
                    remaining -= take

                if remaining > 0:
                    # Not enough layers — use company_price for remainder
                    fallback_cost = item.product.company_price or Decimal('0')
                    total_cost += Decimal(str(remaining)) * fallback_cost

                unit_cost = total_cost / Decimal(str(total_qty))
                item.unit_cost = round(unit_cost, 4)
                item.total_cost = round(total_cost, 2)
                item.save(update_fields=['unit_cost', 'total_cost'])
                items_costed += 1
            except Exception as e:
                items_failed += 1
                log(f"FAILED costing {bill.bill_number} item {item.product.product_code}: {e}")

    # Also consume for exchange OUT movements (just mark layers as consumed, no item to update)
    exchange_out = StockMovement.objects.filter(
        movement_type='exchange',
        stock_type='resaleable',
        quantity__lt=0
    ).order_by('created_at')

    for mv in exchange_out:
        qty = abs(mv.quantity)
        layers = FIFOCostLayer.objects.filter(
            product=mv.product,
            is_exhausted=False,
            remaining_quantity__gt=0
        ).order_by('created_at')
        remaining = qty
        for layer in layers:
            if remaining <= 0:
                break
            take = min(remaining, layer.remaining_quantity)
            layer.remaining_quantity -= take
            layer.is_exhausted = (layer.remaining_quantity <= 0)
            layer.save(update_fields=['remaining_quantity', 'is_exhausted'])
            remaining -= take

    print(f"  Costed {items_costed} bill items, {items_failed} failures")

    # Verify FIFO vs stock
    fifo_mismatch = 0
    for p in Product.objects.filter(quantity_in_stock__gt=0):
        fifo_rem = FIFOCostLayer.objects.filter(
            product=p, is_exhausted=False
        ).aggregate(s=Sum('remaining_quantity'))['s'] or 0
        if p.quantity_in_stock != fifo_rem:
            fifo_mismatch += 1
    print(f"  FIFO vs stock mismatches remaining: {fifo_mismatch}")


def fix_commission_running_balance():
    """Step 9: Fix commission running_balance for all sales reps."""
    print("\n=== STEP 9: Fix Commission Running Balances ===")
    reps = User.objects.filter(user_type='sales_rep')
    fixed = 0
    for rep in reps:
        txns = CommissionTransaction.objects.filter(sales_rep=rep).order_by('created_at', 'id')
        running = Decimal('0')
        rep_fixes = 0
        for t in txns:
            running += t.commission_earned
            if abs(t.running_balance - running) > Decimal('0.01'):
                t.running_balance = running
                t.save(update_fields=['running_balance'])
                rep_fixes += 1
        if rep_fixes > 0:
            fixed += rep_fixes
            log(f"Fixed {rep_fixes} running_balance entries for {rep.get_full_name()} (final balance: {running})")
    print(f"  Fixed {fixed} commission entries total")


def fix_shop_balances():
    """Step 10: Recalculate shop current_balance from confirmed bill balances."""
    print("\n=== STEP 10: Fix Shop Outstanding Balances ===")
    fixed = 0
    for shop in Shop.objects.filter(is_active=True):
        outstanding = Bill.objects.filter(
            shop=shop, bill_status='confirmed'
        ).aggregate(s=Sum('balance_amount'))['s'] or Decimal('0')

        if abs(shop.current_balance - outstanding) > Decimal('0.01'):
            old = shop.current_balance
            shop.current_balance = outstanding
            shop.save(update_fields=['current_balance'])
            fixed += 1
            log(f"Fixed {shop.shop_name} ({shop.shop_code}): {old} → {outstanding}")
    print(f"  Fixed {fixed} shop balances")


def verify_all():
    """Final verification pass."""
    print("\n" + "=" * 60)
    print("FINAL VERIFICATION")
    print("=" * 60)

    # 1. Stock
    stock_ok = 0
    stock_bad = 0
    for p in Product.objects.all():
        net = StockMovement.objects.filter(product=p, stock_type='resaleable').aggregate(s=Sum('quantity'))['s'] or 0
        expected = max(net, 0)
        if p.quantity_in_stock == expected:
            stock_ok += 1
        else:
            stock_bad += 1
            log(f"STILL BAD: {p.product_code} stock={p.quantity_in_stock}, expected={expected}")
    print(f"  Product stock: {stock_ok} OK, {stock_bad} bad")

    # 2. Bill payments
    bill_ok = 0
    bill_bad = 0
    for b in Bill.objects.filter(bill_status='confirmed'):
        settled = SalesAccountSettlement.objects.filter(
            bill=b, settlement_status='completed'
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        if abs(b.paid_amount - settled) > Decimal('0.01'):
            bill_bad += 1
        else:
            bill_ok += 1
    print(f"  Bill paid_amount: {bill_ok} OK, {bill_bad} bad")

    # 3. Settlement status
    status_ok = 0
    status_bad = 0
    for b in Bill.objects.filter(bill_status='confirmed'):
        if b.total_amount <= 0:
            expected = 'settled'
        elif b.paid_amount >= b.total_amount:
            expected = 'settled'
        elif b.paid_amount > 0:
            expected = 'partial_settled'
        else:
            expected = 'unsettled'
        if b.settlement_status == expected:
            status_ok += 1
        else:
            status_bad += 1
    print(f"  Bill settlement_status: {status_ok} OK, {status_bad} bad")

    # 4. Cancelled bills
    cancel_bad = Bill.objects.filter(bill_status='cancelled').exclude(
        balance_amount=0, settlement_status='cancelled'
    ).count()
    print(f"  Cancelled bills still bad: {cancel_bad}")

    # 5. Shop balances
    shop_ok = 0
    shop_bad = 0
    for shop in Shop.objects.filter(is_active=True):
        outstanding = Bill.objects.filter(
            shop=shop, bill_status='confirmed'
        ).aggregate(s=Sum('balance_amount'))['s'] or Decimal('0')
        if abs(shop.current_balance - outstanding) > Decimal('0.01'):
            shop_bad += 1
        else:
            shop_ok += 1
    print(f"  Shop balances: {shop_ok} OK, {shop_bad} bad")

    # 6. FIFO layers
    fifo_bad = 0
    for p in Product.objects.filter(quantity_in_stock__gt=0):
        fifo_rem = FIFOCostLayer.objects.filter(
            product=p, is_exhausted=False
        ).aggregate(s=Sum('remaining_quantity'))['s'] or 0
        if p.quantity_in_stock != fifo_rem:
            fifo_bad += 1
    print(f"  FIFO vs stock mismatches: {fifo_bad}")

    # 7. BillItem costs
    missing = BillItem.objects.filter(bill__bill_status='confirmed', unit_cost__isnull=True).count()
    print(f"  BillItems missing cost: {missing}")

    # 8. Commission
    comm_bad = 0
    for rep in User.objects.filter(user_type='sales_rep'):
        txns = CommissionTransaction.objects.filter(sales_rep=rep).order_by('created_at', 'id')
        running = Decimal('0')
        for t in txns:
            running += t.commission_earned
            if abs(t.running_balance - running) > Decimal('0.01'):
                comm_bad += 1
                break
    print(f"  Commission reps with bad running_balance: {comm_bad}")


if __name__ == '__main__':
    print("=" * 60)
    print("COMPREHENSIVE DATA BACKFILL & CONSISTENCY FIX")
    print("=" * 60)

    with transaction.atomic():
        fix_cancelled_bills()
        fix_zero_total_bills()
        fix_settlement_status_typo()
        recalculate_bill_payments()
        recalculate_product_stock()
        rebuild_fifo_layers()
        fix_commission_running_balance()
        fix_shop_balances()
        verify_all()

    print("\n✓ All fixes applied successfully within a single transaction!")
