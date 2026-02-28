"""
ITEM EXCHANGE MANAGEMENT VIEWS
================================
Handles direct product exchanges for damaged/expired items
No approval required - immediate exchange process
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Q
from decimal import Decimal
import uuid
from .models import ItemExchange, ExchangeItem, PrintManager
from products.models import Product, StockMovement
from shops.models import Shop, ShopAccess
import json


@login_required
def exchange_list(request):
    """List all item exchanges"""
    from datetime import timedelta
    
    # Role-based filtering
    if request.user.is_sales_rep:
        exchanges = ItemExchange.objects.filter(created_by=request.user).select_related(
            'shop', 'created_by'
        )
    else:
        exchanges = ItemExchange.objects.all().select_related(
            'shop', 'created_by'
        )
    
    # Filter by date
    date_filter = request.GET.get('date', 'all')
    today = timezone.localdate()
    
    if date_filter == 'today':
        exchanges = exchanges.filter(exchange_date__date=today)
    elif date_filter == 'yesterday':
        yesterday = today - timedelta(days=1)
        exchanges = exchanges.filter(exchange_date__date=yesterday)
    elif date_filter == 'this_week':
        start_of_week = today - timedelta(days=today.weekday())
        exchanges = exchanges.filter(exchange_date__date__gte=start_of_week)
    elif date_filter == 'this_month':
        exchanges = exchanges.filter(exchange_date__year=today.year, exchange_date__month=today.month)
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        exchanges = exchanges.filter(exchange_status=status)
    
    # Filter by shop
    shop_id = request.GET.get('shop')
    if shop_id and not request.user.is_sales_rep:
        exchanges = exchanges.filter(shop_id=shop_id)
    
    # Order by date
    exchanges = exchanges.order_by('-exchange_date', '-created_at')
    
    # Calculate statistics
    stats = {
        'total_exchanges': exchanges.count(),
        'pending': exchanges.filter(exchange_status='pending').count(),
        'completed': exchanges.filter(exchange_status='completed').count(),
        'cancelled': exchanges.filter(exchange_status='cancelled').count(),
    }
    
    # Get shops for filter (managers only)
    shops = Shop.objects.all() if not request.user.is_sales_rep else []
    
    context = {
        'exchanges': exchanges,
        'stats': stats,
        'shops': shops,
        'date_filter': date_filter,
    }
    
    return render(request, 'sales/exchange_list.html', context)


@login_required
def create_exchange(request):
    """Create new item exchange"""
    
    # Get shops based on user role
    if request.user.is_sales_rep:
        # Only show shops where sales rep has Level 2+ access (can do activities)
        all_shops = Shop.objects.all()
        shops = [shop for shop in all_shops if ShopAccess.get_rep_access_level(shop, request.user) >= 2]
    else:
        shops = Shop.objects.all()
    
    # Get all products for the exchange
    products = Product.objects.filter(is_active=True).select_related('company', 'category')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Prevent duplicate submissions via session token
                submission_token = request.POST.get('submission_token', '')
                session_token = request.session.pop('exchange_submission_token', None)
                if not submission_token or submission_token != session_token:
                    messages.warning(request, 'This exchange was already submitted. Please check exchange history.')
                    return redirect('sales:exchange_list')

                # Get shop
                shop_id = request.POST.get('shop')
                shop = get_object_or_404(Shop, id=shop_id)
                
                # Check permissions
                if request.user.is_sales_rep:
                    access_level = ShopAccess.get_rep_access_level(shop, request.user)
                    if access_level < 2:
                        messages.error(request, 'You need Level 2+ access to create exchanges for this shop.')
                        return redirect('sales:exchange_list')
                
                # Get exchange reason (default to 'damaged' if not provided)
                exchange_reason = request.POST.get('exchange_reason', 'damaged')
                if not exchange_reason:
                    exchange_reason = 'damaged'
                
                # Create exchange
                exchange = ItemExchange.objects.create(
                    shop=shop,
                    created_by=request.user,
                    exchange_reason=exchange_reason,
                    notes=request.POST.get('notes', ''),
                    exchange_status='pending'
                )
                
                # Parse exchange items
                items_data = json.loads(request.POST.get('items', '[]'))
                
                if not items_data:
                    raise ValueError('Please add at least one item to exchange')
                
                for item_data in items_data:
                    returned_product = get_object_or_404(Product, id=item_data['returned_product_id'])
                    replacement_product = get_object_or_404(Product, id=item_data['replacement_product_id'])
                    returned_qty = Decimal(str(item_data['returned_quantity']))
                    replacement_qty = Decimal(str(item_data['replacement_quantity']))
                    is_resellable = item_data.get('is_resellable', False)
                    
                    # Create exchange item
                    ExchangeItem.objects.create(
                        exchange=exchange,
                        returned_product=returned_product,
                        returned_quantity=returned_qty,
                        replacement_product=replacement_product,
                        replacement_quantity=replacement_qty,
                        is_resellable=is_resellable,
                        notes=item_data.get('notes', '')
                    )
                    
                    # Create stock movements
                    # 1. First consume FIFO for the replacement (OUT) product
                    #    so we know the actual cost to value the returned (IN) product
                    prev_qty_replacement = replacement_product.quantity_in_stock
                    replacement_product.quantity_in_stock -= int(replacement_qty)
                    replacement_product.save()
                    
                    from products.models import FIFOCostLayer
                    fifo_cost, cost_breakdown = FIFOCostLayer.consume_fifo(replacement_product, int(replacement_qty))
                    
                    StockMovement.objects.create(
                        product=replacement_product,
                        movement_type='exchange',
                        stock_type='resaleable',
                        quantity=-int(replacement_qty),
                        previous_quantity=prev_qty_replacement,
                        new_quantity=replacement_product.quantity_in_stock,
                        reference_number=exchange.exchange_number,
                        created_by=request.user,
                        notes=f'Exchange OUT - Replacement for {returned_product.product_name} - Shop: {shop.shop_name}',
                        unit_cost=fifo_cost,
                        total_cost=fifo_cost * int(replacement_qty),
                    )
                    
                    # 2. Receive returned item (add to stock)
                    #    Use the FIFO cost from the OUT item so the exchange is value-neutral
                    prev_qty_returned = returned_product.quantity_in_stock
                    returned_product.quantity_in_stock += int(returned_qty)
                    returned_product.save()
                    
                    StockMovement.objects.create(
                        product=returned_product,
                        movement_type='exchange',
                        stock_type='resaleable' if is_resellable else 'non_resaleable',
                        quantity=int(returned_qty),
                        previous_quantity=prev_qty_returned,
                        new_quantity=returned_product.quantity_in_stock,
                        reference_number=exchange.exchange_number,
                        created_by=request.user,
                        notes=f'Exchange IN - {exchange.get_exchange_reason_display()} - Shop: {shop.shop_name}',
                        unit_cost=fifo_cost,
                        total_cost=fifo_cost * int(returned_qty),
                    )
                    
                    # Create FIFO cost layer for exchanged-in stock at the OUT cost
                    FIFOCostLayer.create_layer(
                        product=returned_product,
                        qty=int(returned_qty),
                        unit_cost=fifo_cost,
                        source='exchange_in',
                        reference=exchange.exchange_number,
                    )
                
                # Mark as completed immediately
                exchange.mark_as_completed()
                
                # Auto-mark shop visit (if nearby)
                try:
                    from shops.visit_utils import auto_mark_visit
                    auto_mark_visit(shop, request.user, 'auto_exchange', exchange.exchange_number)
                except Exception:
                    pass  # Never block exchange for visit tracking
                
                messages.success(request, f'Item exchange {exchange.exchange_number} created successfully!')
                return redirect('sales:exchange_detail', pk=exchange.pk)
                
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error creating exchange: {str(e)}')
    
    # Group products by category, size, and price for exchange matching
    from collections import defaultdict
    exchange_groups = {}
    groups_dict = defaultdict(list)
    
    for product in products:
        # Group key: category-size-price
        category = product.category.name if product.category else 'Unknown'
        size = product.size if product.size else 'N/A'
        price = product.marked_price
        
        group_key = f"{category}-{size}-{price}"
        groups_dict[group_key].append(product)
    
    # Convert to exchange_groups format
    for group_key, group_products in groups_dict.items():
        if len(group_products) > 1:  # Only include groups with multiple products
            parts = group_key.split('-')
            category = parts[0] if len(parts) > 0 else 'Unknown'
            size = parts[1] if len(parts) > 1 else 'N/A'
            price = parts[2] if len(parts) > 2 else '0'
            
            exchange_groups[group_key] = {
                'key': group_key,
                'label': f"{category} - {size} - Rs. {price}",
                'products': group_products
            }
    
    # Get preselected shop from query parameter
    preselected_shop_id = request.GET.get('shop')
    
    # Generate one-time submission token to prevent double-submit
    submission_token = str(uuid.uuid4())
    request.session['exchange_submission_token'] = submission_token

    context = {
        'shops': shops,
        'products': products,
        'exchange_groups': exchange_groups,
        'preselected_shop_id': preselected_shop_id,
        'submission_token': submission_token,
    }
    
    return render(request, 'sales/create_exchange.html', context)


@login_required
def exchange_detail(request, pk):
    """View exchange details"""
    exchange = get_object_or_404(ItemExchange.objects.select_related(
        'shop', 'created_by'
    ).prefetch_related('items__returned_product', 'items__replacement_product'), pk=pk)
    
    # Check permissions
    if request.user.is_sales_rep and exchange.created_by != request.user:
        messages.error(request, 'You can only view your own exchanges.')
        return redirect('sales:exchange_list')
    
    context = {
        'exchange': exchange,
    }
    
    return render(request, 'sales/exchange_detail.html', context)


@login_required
def cancel_exchange(request, pk):
    """Cancel an exchange"""
    exchange = get_object_or_404(ItemExchange, pk=pk)
    
    # Check permissions
    if request.user.is_sales_rep:
        messages.error(request, 'Only managers can cancel exchanges.')
        return redirect('sales:exchange_detail', pk=pk)
    
    if exchange.exchange_status == 'completed':
        messages.error(request, 'Cannot cancel completed exchange.')
        return redirect('sales:exchange_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                from products.models import FIFOCostLayer
                # Reverse stock movements and FIFO layers
                affected_products = set()
                for item in exchange.items.all():
                    # Look up original exchange cost from the OUT movement
                    original_out_mv = StockMovement.objects.filter(
                        reference_number=exchange.exchange_number,
                        product=item.replacement_product,
                        movement_type='exchange',
                        quantity__lt=0,
                    ).first()
                    exchange_cost = original_out_mv.unit_cost if original_out_mv else (
                        item.replacement_product.cost_after_foc or Decimal('0')
                    )
                    
                    # Reverse the exchange IN (remove from stock)
                    prev_qty_returned = item.returned_product.quantity_in_stock
                    item.returned_product.quantity_in_stock -= int(item.returned_quantity)
                    item.returned_product.save()
                    
                    # Delete FIFO layer created by the exchange IN
                    FIFOCostLayer.objects.filter(
                        product=item.returned_product,
                        layer_source='exchange_in',
                        reference_number=exchange.exchange_number,
                    ).delete()
                    
                    StockMovement.objects.create(
                        product=item.returned_product,
                        movement_type='exchange',
                        stock_type='resaleable',
                        quantity=-int(item.returned_quantity),
                        previous_quantity=prev_qty_returned,
                        new_quantity=item.returned_product.quantity_in_stock,
                        reference_number=f"{exchange.exchange_number}-CANCEL",
                        created_by=request.user,
                        notes=f'Cancelled exchange {exchange.exchange_number} - Reverse IN',
                        unit_cost=exchange_cost,
                        total_cost=exchange_cost * int(item.returned_quantity),
                    )
                    affected_products.add(item.returned_product)
                    
                    # Reverse the exchange OUT (add back to stock)
                    prev_qty_replacement = item.replacement_product.quantity_in_stock
                    item.replacement_product.quantity_in_stock += int(item.replacement_quantity)
                    item.replacement_product.save()
                    
                    # Restore FIFO layer for the exchange OUT reversal at original cost
                    FIFOCostLayer.create_layer(
                        product=item.replacement_product,
                        qty=int(item.replacement_quantity),
                        unit_cost=exchange_cost,
                        source='adjustment',
                        reference=f'{exchange.exchange_number}-CANCEL',
                    )
                    
                    StockMovement.objects.create(
                        product=item.replacement_product,
                        movement_type='exchange',
                        stock_type='resaleable',
                        quantity=int(item.replacement_quantity),
                        previous_quantity=prev_qty_replacement,
                        new_quantity=item.replacement_product.quantity_in_stock,
                        reference_number=f"{exchange.exchange_number}-CANCEL",
                        created_by=request.user,
                        notes=f'Cancelled exchange {exchange.exchange_number} - Reverse OUT',
                        unit_cost=exchange_cost,
                        total_cost=exchange_cost * int(item.replacement_quantity),
                    )
                    affected_products.add(item.replacement_product)
                
                exchange.exchange_status = 'cancelled'
                exchange.save()
                
                # Re-replay FIFO for all affected products
                for product in affected_products:
                    FIFOCostLayer.replay_product_fifo(product)
                
                messages.success(request, f'Exchange {exchange.exchange_number} cancelled successfully!')
        except Exception as e:
            messages.error(request, f'Error cancelling exchange: {str(e)}')
    
    return redirect('sales:exchange_detail', pk=pk)


@login_required
def exchange_print(request, pk):
    """Print exchange receipt - uses UnifiedPrintEngine for consistent branding"""
    from sales.print_engine import UnifiedPrintEngine
    import time
    
    exchange = get_object_or_404(ItemExchange.objects.select_related(
        'shop', 'created_by'
    ).prefetch_related('items__returned_product', 'items__replacement_product'), pk=pk)
    
    # Check permissions
    if request.user.is_sales_rep and exchange.created_by != request.user:
        messages.error(request, 'You can only print your own exchanges.')
        return redirect('sales:exchange_list')
    
    # Use unified print engine for consistent branding/footer
    engine = UnifiedPrintEngine(request.user, receipt_type='field_receipt')
    context = engine.get_print_context({
        'exchange': exchange,
    })
    
    context['cache_buster'] = str(int(time.time()))
    
    response = render(request, 'sales/exchange_print.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
