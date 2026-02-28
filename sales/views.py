from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db import transaction, models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid
from .models import Bill, BillItem, Return, Sale, SaleItem, PrintManager
from shops.models import Shop, ShopAccess
from products.models import Product
import json


@login_required
def bill_list(request):
    """List all bills"""
    from datetime import datetime, timedelta
    from django.utils import timezone
    from django.db.models import Sum, Count, Q
    from payments.models import SalesAccountSettlement
    
    if request.user.is_sales_rep:
        bills = Bill.objects.filter(sales_rep=request.user).select_related('shop', 'sales_rep')
    else:
        bills = Bill.objects.all().select_related('shop', 'sales_rep')
    
    # Filter by date - default to all (show all bills)
    date_filter = request.GET.get('date', 'all')
    # Get today's date in the configured timezone (Asia/Colombo)
    import pytz
    local_tz = pytz.timezone(settings.TIME_ZONE)
    today = timezone.now().astimezone(local_tz).date()
    
    if date_filter == 'today':
        bills = bills.filter(bill_date__date=today)
    elif date_filter == 'yesterday':
        yesterday = today - timedelta(days=1)
        bills = bills.filter(bill_date__date=yesterday)
    elif date_filter == 'this_week':
        start_of_week = today - timedelta(days=today.weekday())
        bills = bills.filter(bill_date__date__gte=start_of_week)
    elif date_filter == 'this_month':
        bills = bills.filter(bill_date__year=today.year, bill_date__month=today.month)
    elif date_filter == 'all':
        pass  # No date filtering
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        bills = bills.filter(bill_status=status)
    
    # Filter by settlement status
    settlement_status = request.GET.get('settlement_status')
    if settlement_status:
        bills = bills.filter(settlement_status=settlement_status)
    
    # Custom date range filter
    from_date = request.GET.get('from_date', '').strip()
    to_date = request.GET.get('to_date', '').strip()
    
    if from_date:
        try:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d')
            bills = bills.filter(bill_date__date__gte=from_date_obj.date())
        except ValueError:
            pass
    
    if to_date:
        try:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d')
            bills = bills.filter(bill_date__date__lte=to_date_obj.date())
        except ValueError:
            pass
    
    # Filter by shop
    shop_id = request.GET.get('shop')
    if shop_id:
        bills = bills.filter(shop_id=shop_id)
    
    # Filter by sales rep (managers only)
    sales_rep_id = request.GET.get('sales_rep')
    if sales_rep_id and not request.user.is_sales_rep:
        bills = bills.filter(sales_rep_id=sales_rep_id)
    
    # Search filter (bill number, shop name, owner)
    search_query = request.GET.get('search', '').strip()
    if search_query:
        bills = bills.filter(
            Q(bill_number__icontains=search_query) |
            Q(shop__shop_name__icontains=search_query) |
            Q(shop__owner_name__icontains=search_query)
        )
    
    # Order by date descending
    bills = bills.order_by('-bill_date', '-created_at')
    
    # Calculate statistics (confirmed bills only - exclude draft & cancelled)
    active_bills = bills.filter(bill_status='confirmed')
    
    # Basic stats
    total_bills_count = active_bills.count()
    # Total sales = sum of total_amount (which is already after discount)
    total_sales = active_bills.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    # Get all bill IDs for payment queries
    bill_ids = list(active_bills.values_list('id', flat=True))
    
    # Cash sales
    cash_total = SalesAccountSettlement.objects.filter(
        bill_id__in=bill_ids,
        settlement_method='cash',
        settlement_status='completed'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Credit = total balance amount from unsettled and partially settled bills
    credit_total = active_bills.filter(
        settlement_status__in=['unsettled', 'partial_settled']
    ).aggregate(total=Sum('balance_amount'))['total'] or Decimal('0')
    
    # Cheques (pending + completed)
    cheque_pending = SalesAccountSettlement.objects.filter(
        bill_id__in=bill_ids,
        settlement_method='cheque',
        settlement_status='pending'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    cheque_completed = SalesAccountSettlement.objects.filter(
        bill_id__in=bill_ids,
        settlement_method='cheque',
        settlement_status='completed'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Bank transfers (pending + completed)
    bank_pending = SalesAccountSettlement.objects.filter(
        bill_id__in=bill_ids,
        settlement_method='bank_transfer',
        settlement_status='pending'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    bank_completed = SalesAccountSettlement.objects.filter(
        bill_id__in=bill_ids,
        settlement_method='bank_transfer',
        settlement_status='completed'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Calculate totals
    cheque_total = cheque_pending + cheque_completed
    bank_total = bank_pending + bank_completed
    
    # Get all shops and sales reps for filter dropdowns
    from shops.models import Shop
    from accounts.models import User
    
    # For sales reps, only show shops with Level 2+ access
    if request.user.is_sales_rep:
        all_shops_query = Shop.objects.filter(is_active=True)
        all_shops = [shop for shop in all_shops_query if ShopAccess.get_rep_access_level(shop, request.user) >= 2]
    else:
        all_shops = Shop.objects.filter(is_active=True).order_by('shop_name')
    
    from accounts.tenant_utils import get_tenant_users
    all_sales_reps = get_tenant_users().filter(user_type='sales_rep', is_active_employee=True).order_by('first_name', 'last_name')
    
    context = {
        'bills': bills,
        'date_filter': date_filter,
        
        # Summary statistics
        'total_bills': total_bills_count,
        'total_sales': total_sales,
        'cash_total': cash_total,
        'credit_total': credit_total,
        'cheque_pending': cheque_pending,
        'cheque_completed': cheque_completed,
        'cheque_total': cheque_total,
        'bank_pending': bank_pending,
        'bank_completed': bank_completed,
        'bank_total': bank_total,
        
        # Filter options
        'all_shops': all_shops,
        'all_sales_reps': all_sales_reps,
        
        # Current filter values
        'from_date': from_date,
        'to_date': to_date,
        'selected_shop': shop_id,
        'selected_sales_rep': sales_rep_id,
        'search_query': search_query,
    }
    return render(request, 'sales/bill_list.html', context)


@login_required
@transaction.atomic
def create_bill(request):
    """Create new bill or update existing draft bill"""
    if request.method == 'POST':
        try:
            # Prevent duplicate submissions via session token
            submission_token = request.POST.get('submission_token', '')
            session_token = request.session.pop('bill_submission_token', None)
            if not submission_token or submission_token != session_token:
                messages.warning(request, 'This bill was already submitted. Please create a new one if needed.')
                return redirect('sales:list')

            # Get shop or customer name
            shop_id = request.POST.get('shop_id')
            customer_name = request.POST.get('customer_name', '').strip()
            
            # Validate: Either shop_id OR customer_name must be provided
            if not shop_id and not customer_name:
                messages.error(request, 'Please select a shop or enter a customer name.')
                return redirect('sales:create')
            
            if shop_id and customer_name:
                messages.error(request, 'Please select either a shop OR enter a customer name, not both.')
                return redirect('sales:create')
            
            # Get shop object if shop_id provided
            shop = None
            if shop_id:
                shop = Shop.objects.get(pk=shop_id)
                
                # Check if sales rep has Level 2+ access to create bills for this shop
                if request.user.is_sales_rep:
                    access_level = ShopAccess.get_rep_access_level(shop, request.user)
                    if access_level < 2:
                        messages.error(request, 'You need Level 2+ access to create bills for this shop.')
                        return redirect('sales:create')
            
            # Check if saving as draft or confirming
            save_as_draft = request.POST.get('save_as_draft') == 'true'
            
            # Check if updating existing bill
            bill_id = request.POST.get('bill_id')
            
            if bill_id:
                # Update existing bill
                bill = get_object_or_404(Bill, pk=bill_id)
                
                # Verify permissions
                if request.user.is_sales_rep and bill.sales_rep != request.user:
                    messages.error(request, 'You do not have permission to edit this bill.')
                    return redirect('sales:detail', pk=bill.pk)
                
                if bill.bill_status != 'draft':
                    messages.error(request, 'Only draft bills can be edited.')
                    return redirect('sales:detail', pk=bill.pk)
                
                # Reverse previous stock changes
                for item in bill.items.all():
                    product = item.product
                    total_qty = item.quantity + item.foc_quantity
                    product.quantity_in_stock += total_qty
                    product.save()
                    
                    # Restore FIFO layers: create a new layer with the cost that was consumed
                    if item.unit_cost:
                        from products.models import FIFOCostLayer
                        FIFOCostLayer.create_layer(
                            product=product,
                            qty=int(total_qty),
                            unit_cost=item.unit_cost,
                            source='adjustment',
                            reference=f'{bill.bill_number}-EDIT',
                        )
                
                # Delete old items (and their associated stock movements)
                from products.models import StockMovement as SM
                SM.objects.filter(
                    movement_type='sale',
                    reference_number=bill.bill_number
                ).delete()
                
                # Delete old items
                bill.items.all().delete()
                
                # Update bill details
                bill.shop = shop
                bill.customer_name = customer_name if customer_name else None
                bill.discount_percentage = Decimal(str(request.POST.get('discount_percentage', 0)))
                bill.notes = request.POST.get('notes', '')
                bill.save()
                
            else:
                # Create new bill
                bill = Bill.objects.create(
                    shop=shop,
                    customer_name=customer_name if customer_name else None,
                    sales_rep=request.user,
                    discount_percentage=Decimal(str(request.POST.get('discount_percentage', 0))),
                    notes=request.POST.get('notes', ''),
                    bill_status='draft'
                )
                
                # Generate bill number
                bill.generate_bill_number()
                bill.save()
            
            # Get items data from JSON
            items_data = json.loads(request.POST.get('items', '[]'))
            
            # Create bill items
            for item_data in items_data:
                product = Product.objects.get(pk=item_data['product_id'])
                
                quantity = Decimal(str(item_data['quantity']))
                foc_quantity = Decimal(str(item_data.get('foc_quantity', 0)))
                unit_price = Decimal(str(item_data['unit_price']))
                
                bill_item = BillItem.objects.create(
                    bill=bill,
                    product=product,
                    quantity=quantity,
                    foc_quantity=foc_quantity,
                    unit_price=unit_price,
                    discount_percentage=Decimal(str(item_data.get('discount_percentage', 0))),
                    tax_percentage=0
                )
                
                # Update product stock (both paid and FOC quantities)
                total_qty = quantity + foc_quantity
                product.quantity_in_stock -= total_qty
                product.save()
                
                # FIFO: consume cost layers and record COGS on bill item
                from products.models import FIFOCostLayer, StockMovement
                fifo_cost, cost_breakdown = FIFOCostLayer.consume_fifo(product, int(total_qty))
                bill_item.unit_cost = fifo_cost
                bill_item.total_cost = fifo_cost * total_qty
                bill_item.cost_breakdown = cost_breakdown
                bill_item.save(update_fields=['unit_cost', 'total_cost', 'cost_breakdown'])
                
                # Create sale stock movement
                previous_qty = int(product.quantity_in_stock + total_qty)
                StockMovement.objects.create(
                    product=product,
                    movement_type='sale',
                    quantity=-int(total_qty),
                    previous_quantity=previous_qty,
                    new_quantity=product.quantity_in_stock,
                    reference_number=bill.bill_number,
                    notes=f'Bill: {bill.bill_number} - Qty: {int(quantity)}, FOC: {int(foc_quantity)}',
                    created_by=request.user,
                    unit_cost=fifo_cost,
                    total_cost=fifo_cost * total_qty,
                )
                
                # Track FOC value (only after bill is confirmed, not draft)
                if not save_as_draft and product.company:
                    from products.models import FOCValueAccount, FOCValueTransaction
                    
                    # Get or create FOC account for product's company
                    foc_account, created = FOCValueAccount.objects.get_or_create(
                        company=product.company,
                        defaults={'created_by': request.user}
                    )
                    
                    # Determine customer name for FOC notes
                    customer_label = shop.shop_name if shop else (customer_name or "Unregistered Customer")
                    
                    # Track explicit FOC given
                    if foc_quantity > 0:
                        FOCValueTransaction.objects.create(
                            foc_account=foc_account,
                            transaction_type='foc_given',
                            transaction_date=bill.bill_date,
                            product=product,
                            foc_quantity=foc_quantity,
                            shop_price_at_time=product.shop_price,
                            reference_number=bill.bill_number,
                            bill_item=bill_item,
                            shop=shop,  # Can be None for unregistered customers
                            sales_rep=request.user,
                            notes=f'FOC given to {customer_label}',
                            created_by=request.user
                        )
                    
                    # Track implicit FOC (selling below shop_price)
                    if quantity > 0 and unit_price < product.shop_price:
                        implicit_foc_per_unit = product.shop_price - unit_price
                        implicit_foc_value = quantity * implicit_foc_per_unit
                        
                        FOCValueTransaction.objects.create(
                            foc_account=foc_account,
                            transaction_type='implicit_foc',
                            transaction_date=bill.bill_date,
                            product=product,
                            foc_quantity=quantity,
                            shop_price_at_time=product.shop_price,
                            foc_value=implicit_foc_value,  # Manually set for implicit FOC
                            reference_number=bill.bill_number,
                            bill_item=bill_item,
                            shop=shop,  # Can be None for unregistered customers
                            sales_rep=request.user,
                            notes=f'Sold at Rs.{unit_price} (shop_price: Rs.{product.shop_price}) - Discount: Rs.{implicit_foc_per_unit}/unit',
                            created_by=request.user
                        )
            
            # Calculate totals
            bill.calculate_totals()
            
            # Update bill status and shop balance only if confirming
            if not save_as_draft:
                bill.bill_status = 'confirmed'
                bill.save()
                
                # Update shop balance (only if shop exists)
                if shop:
                    shop.current_balance += bill.balance_amount
                    shop.save()
                
                if bill_id:
                    messages.success(request, f'Bill {bill.bill_number} updated and confirmed successfully!')
                else:
                    messages.success(request, f'Bill {bill.bill_number} created and confirmed successfully!')
            else:
                if bill_id:
                    messages.success(request, f'Bill {bill.bill_number} updated successfully.')
                else:
                    messages.success(request, f'Bill {bill.bill_number} saved as draft. You can edit it later.')
            
            # Auto-mark shop visit (if nearby)
            if shop and not save_as_draft:
                try:
                    from shops.visit_utils import auto_mark_visit
                    auto_mark_visit(shop, request.user, 'auto_bill', bill.bill_number)
                except Exception:
                    pass  # Never block bill creation for visit tracking
            
            return redirect('sales:detail', pk=bill.pk)
            
        except Exception as e:
            messages.error(request, f'Error processing bill: {str(e)}')
            return redirect('sales:create')
    
    # GET request
    if request.user.is_sales_rep:
        # Only show shops where sales rep has Level 2+ access (can do activities)
        # Level 1 is view-only, cannot create bills
        all_shops = Shop.objects.filter(is_active=True)
        shops = []
        for shop in all_shops:
            access_level = ShopAccess.get_rep_access_level(shop, request.user)
            if access_level >= 2:  # Level 2 (Standard) or Level 3 (Full Access)
                shop.user_access_level = access_level
                
                # Calculate 4-tier balance for shop
                from django.db.models import Sum, Q
                from payments.models import SalesAccountSettlement
                
                # Tier 1: Total Debt (freshly calculated from actual bill balances)
                tier1_total_debt = Bill.objects.filter(
                    shop=shop, balance_amount__gt=0
                ).aggregate(total=Sum('balance_amount'))['total'] or Decimal('0.00')
                
                # Tier 2: Pending Verification (settlements awaiting approval)
                pending_settlements = SalesAccountSettlement.objects.filter(
                    shop=shop,
                    settlement_status__in=['pending', 'pending_verification']
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                # Tier 3: Cash Due Now (Total Debt - Pending)
                tier3_cash_due = tier1_total_debt - pending_settlements
                
                # Tier 4: Total Paid (Cleared) - Completed settlements
                total_cleared = SalesAccountSettlement.objects.filter(
                    shop=shop,
                    settlement_status='completed'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                # Attach balance tiers to shop object
                shop.tier1_total_debt = tier1_total_debt
                shop.tier2_pending = pending_settlements
                shop.tier3_cash_due = tier3_cash_due
                shop.tier4_total_cleared = total_cleared
                
                shops.append(shop)
    else:
        # Office/Admin users see all shops with full balance calculation
        shops = []
        from django.db.models import Sum, Q
        from payments.models import SalesAccountSettlement
        
        for shop in Shop.objects.filter(is_active=True):
            # Calculate 4-tier balance for shop
            # Tier 1: Total Debt (freshly calculated from actual bill balances)
            tier1_total_debt = Bill.objects.filter(
                shop=shop, balance_amount__gt=0
            ).aggregate(total=Sum('balance_amount'))['total'] or Decimal('0.00')
            
            # Tier 2: Pending Verification (settlements awaiting approval)
            pending_settlements = SalesAccountSettlement.objects.filter(
                shop=shop,
                settlement_status__in=['pending', 'pending_verification']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            # Tier 3: Cash Due Now (Total Debt - Pending)
            tier3_cash_due = tier1_total_debt - pending_settlements
            
            # Tier 4: Total Paid (Cleared) - Completed settlements
            total_cleared = SalesAccountSettlement.objects.filter(
                shop=shop,
                settlement_status='completed'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            # Attach balance tiers to shop object
            shop.tier1_total_debt = tier1_total_debt
            shop.tier2_pending = pending_settlements
            shop.tier3_cash_due = tier3_cash_due
            shop.tier4_total_cleared = total_cleared
            
            shops.append(shop)
    
    # Get preselected shop from query parameter
    preselected_shop_id = request.GET.get('shop')
    
    # Get all products grouped by size AND marked_price
    products = Product.objects.filter(is_active=True).select_related('company').order_by('size', 'marked_price', 'display_order', 'product_name')
    
    # Group products by size + marked_price combination
    from collections import defaultdict, OrderedDict
    products_by_category = defaultdict(list)
    
    for product in products:
        # Create category key as "SIZE - PRICE"
        category_key = f"{product.size} - Rs. {product.marked_price}"
        products_by_category[category_key].append(product)
    
    # Sort categories by size order and price
    size_order = ['250ML', '500ML', '750ML', '1000ML', '1500ML', '2200ML']
    
    def get_sort_key(category):
        size = category.split(' - ')[0]
        price_str = category.split('Rs. ')[1]
        price = float(price_str)
        size_index = size_order.index(size) if size in size_order else 999
        return (size_index, price)
    
    sorted_categories = OrderedDict(sorted(products_by_category.items(), key=lambda x: get_sort_key(x[0])))
    
    # Generate one-time submission token to prevent double-submit
    submission_token = str(uuid.uuid4())
    request.session['bill_submission_token'] = submission_token

    context = {
        'shops': shops,
        'products_by_category': sorted_categories,
        'preselected_shop_id': preselected_shop_id,
        'submission_token': submission_token,
    }
    return render(request, 'sales/create_bill.html', context)


@login_required
def bill_detail(request, pk):
    """Bill detail view"""
    bill = get_object_or_404(Bill, pk=pk)
    
    # Check permissions for sales reps
    if request.user.is_sales_rep:
        from shops.models import ShopAccess
        
        # Allow if rep created the bill
        if bill.sales_rep == request.user:
            pass  # Allowed
        else:
            # Check shop access level
            access_level = ShopAccess.get_rep_access_level(bill.shop, request.user)
            
            # Level 3 (Full Access): Can view all bills for the shop
            # Level 2 (Standard): Cannot view others' bills
            # Level 1 (View Only): Cannot view bills
            if access_level != 3:
                messages.error(request, 'You do not have permission to view this bill.')
                return redirect('sales:list')
    
    items = bill.items.all().select_related('product', 'product__category', 'product__company')
    
    # Get payment history from old payment system
    settlements = bill.settlements.all().select_related('received_by').order_by('-settlement_date')
    
    # Group items by category (size - price)
    from collections import defaultdict, OrderedDict
    items_by_category = defaultdict(lambda: {
        'regular': [],
        'foc': [],
        'category_display': '',
        'bottles_per_pack': 24,
        'total_bottles': 0,
        'foc_bottles': 0,
        'total_value': Decimal('0')
    })
    
    for item in items:
        # Create category key as "SIZE - PRICE"
        category_key = f"{item.product.size} - Rs. {item.product.marked_price}"
        category_data = items_by_category[category_key]
        
        # Set category display name and bottles per pack
        if not category_data['category_display']:
            category_data['category_display'] = category_key
            category_data['bottles_per_pack'] = item.product.bottles_per_pack or 24
        
        # Add to appropriate list based on whether it's FOC or regular sale
        if item.quantity > 0:
            category_data['regular'].append({
                'name': item.product.product_name,
                'qty': int(item.quantity),
                'price': item.unit_price,
                'line_total': item.line_total,
                'discount_percentage': item.discount_percentage
            })
            category_data['total_bottles'] += int(item.quantity)
            category_data['total_value'] += item.line_total
        
        if item.foc_quantity > 0:
            category_data['foc'].append({
                'name': item.product.product_name,
                'qty': int(item.foc_quantity)
            })
            category_data['foc_bottles'] += int(item.foc_quantity)
    
    # Calculate pack/loose breakdown for each category
    for category_key, category_data in items_by_category.items():
        bottles_per_pack = category_data['bottles_per_pack']
        
        # Sales breakdown
        total_bottles = category_data['total_bottles']
        category_data['sales_packs'] = total_bottles // bottles_per_pack
        category_data['sales_loose'] = total_bottles % bottles_per_pack
        
        # FOC breakdown
        foc_bottles = category_data['foc_bottles']
        category_data['foc_packs'] = foc_bottles // bottles_per_pack
        category_data['foc_loose'] = foc_bottles % bottles_per_pack
        
        # Total breakdown
        total_all_bottles = total_bottles + foc_bottles
        category_data['total_all_bottles'] = total_all_bottles
        category_data['total_packs'] = total_all_bottles // bottles_per_pack
        category_data['total_loose'] = total_all_bottles % bottles_per_pack
    
    # Convert to ordered dict for template
    items_by_category = OrderedDict(sorted(items_by_category.items()))
    
    # Get user's print profile
    print_profile = PrintManager.get_user_default(request.user, 'bill')
    
    # Check if bill has ANY settlements (including pending)
    has_settlements = bill.settlements.exists()
    
    # Calculate FOC Analysis (Standard vs Actual)
    from products.models import FOCValueTransaction
    foc_analysis = {
        'standard_foc_qty': Decimal('0'),
        'standard_foc_value': Decimal('0'),
        'actual_explicit_foc_qty': Decimal('0'),
        'actual_explicit_foc_value': Decimal('0'),
        'actual_implicit_foc_value': Decimal('0'),
        'actual_total_foc_value': Decimal('0'),
        'variance_qty': Decimal('0'),
        'variance_value': Decimal('0'),
        'variance_qty_abs': Decimal('0'),
        'variance_value_abs': Decimal('0'),
        'explicit_variance_value': Decimal('0'),  # Explicit FOC impact (bottles)
        'explicit_variance_value_abs': Decimal('0'),  # Absolute value
        'implicit_variance_value': Decimal('0'),  # Implicit FOC impact (price discount)
        'items_detail': []
    }
    
    for item in items:
        product = item.product
        
        # Calculate standard FOC based on shop_foc_buy/shop_foc_free ratio
        standard_foc_qty = Decimal('0')
        if product.shop_foc_buy and product.shop_foc_buy > 0:
            # Standard FOC = (sales_qty / shop_foc_buy) * shop_foc_free
            standard_foc_qty = (item.quantity / Decimal(str(product.shop_foc_buy))) * Decimal(str(product.shop_foc_free))
        
        standard_foc_value = standard_foc_qty * product.shop_price
        
        # Actual explicit FOC (free bottles given)
        actual_explicit_foc_qty = item.foc_quantity
        actual_explicit_foc_value = actual_explicit_foc_qty * product.shop_price
        
        # Actual implicit FOC (selling below shop price)
        actual_implicit_foc_value = Decimal('0')
        if item.unit_price < product.shop_price:
            price_difference = product.shop_price - item.unit_price
            actual_implicit_foc_value = price_difference * item.quantity
        
        # Total actual FOC value
        actual_total_foc_value = actual_explicit_foc_value + actual_implicit_foc_value
        
        # Variance (actual - standard)
        variance_qty = actual_explicit_foc_qty - standard_foc_qty
        variance_value = actual_total_foc_value - standard_foc_value
        
        # Separate explicit and implicit variance
        explicit_variance_value = actual_explicit_foc_value - standard_foc_value
        implicit_variance_value = actual_implicit_foc_value  # This is always additional cost
        
        # Add to totals
        foc_analysis['standard_foc_qty'] += standard_foc_qty
        foc_analysis['standard_foc_value'] += standard_foc_value
        foc_analysis['actual_explicit_foc_qty'] += actual_explicit_foc_qty
        foc_analysis['actual_explicit_foc_value'] += actual_explicit_foc_value
        foc_analysis['actual_implicit_foc_value'] += actual_implicit_foc_value
        foc_analysis['actual_total_foc_value'] += actual_total_foc_value
        foc_analysis['variance_qty'] += variance_qty
        foc_analysis['variance_value'] += variance_value
        foc_analysis['explicit_variance_value'] += explicit_variance_value
        foc_analysis['implicit_variance_value'] += implicit_variance_value
        
        # Store item detail
        foc_analysis['items_detail'].append({
            'product_name': product.product_name,
            'sales_qty': item.quantity,
            'shop_foc_ratio': f"{product.shop_foc_buy}+{product.shop_foc_free}" if product.shop_foc_buy else "N/A",
            'standard_foc_qty': standard_foc_qty,
            'standard_foc_value': standard_foc_value,
            'actual_explicit_foc_qty': actual_explicit_foc_qty,
            'actual_explicit_foc_value': actual_explicit_foc_value,
            'actual_implicit_foc_value': actual_implicit_foc_value,
            'actual_total_foc_value': actual_total_foc_value,
            'variance_qty': variance_qty,
            'variance_value': variance_value,
            'variance_qty_abs': abs(variance_qty),
            'variance_value_abs': abs(variance_value),
            'explicit_variance_value': explicit_variance_value,
            'implicit_variance_value': implicit_variance_value,
            'shop_price': product.shop_price,
            'unit_price': item.unit_price,
        })
    
    # Calculate absolute values for totals
    foc_analysis['variance_qty_abs'] = abs(foc_analysis['variance_qty'])
    foc_analysis['variance_value_abs'] = abs(foc_analysis['variance_value'])
    foc_analysis['explicit_variance_value_abs'] = abs(foc_analysis['explicit_variance_value'])
    
    # Smart back button: detect where user came from
    from django.urls import reverse
    referrer = request.META.get('HTTP_REFERER', '')
    back_url = None
    back_label = 'Back'
    
    # Priority 1: Check if coming from shop detail page
    if '/shops/' in referrer and bill.shop:
        back_url = reverse('shops:detail', kwargs={'pk': bill.shop.pk})
        back_label = f'Back to {bill.shop.shop_name}'
    
    # Priority 2: Check if coming from dashboard
    elif '/dashboard/' in referrer:
        if request.user.is_sales_rep:
            back_url = reverse('dashboard:sales_rep')
        else:
            back_url = reverse('dashboard:office')
        back_label = 'Back to Dashboard'
    
    # Priority 3: Check if coming from sales list
    elif '/sales/' in referrer and '/sales/' + str(pk) not in referrer:
        back_url = reverse('sales:list')
        back_label = 'Back to Bills'
    
    # Default fallback
    else:
        if bill.shop:
            back_url = reverse('shops:detail', kwargs={'pk': bill.shop.pk})
            back_label = f'Back to {bill.shop.shop_name}'
        else:
            back_url = reverse('sales:list')
            back_label = 'Back to Bills'
    
    context = {
        'sale': bill,  # Use 'sale' to match bill_summary.html template
        'items': items,
        'items_by_category': items_by_category,
        'settlements': settlements,
        'bill_settings': print_profile,  # Backward compatibility
        'print_profile': print_profile,
        'has_settlements': has_settlements,  # Flag to disable discount editing
        'foc_analysis': foc_analysis,  # FOC Standard vs Actual analysis
        'page_title': f'Bill {bill.bill_number}',
        'back_url': back_url,
        'back_label': back_label,
    }
    return render(request, 'sales/bill_summary.html', context)


@login_required
def update_discount(request, pk):
    """Update bill discount"""
    bill = get_object_or_404(Bill, pk=pk)
    
    # Check permissions
    if request.user.is_sales_rep and bill.sales_rep != request.user:
        messages.error(request, 'You do not have permission to update this bill.')
        return redirect('sales:detail', pk=pk)
    
    # Check if ANY payments exist (including pending)
    settlements_exist = bill.settlements.exists()
    if settlements_exist:
        # Count pending and completed payments separately
        from django.db.models import Q, Sum
        pending_count = bill.settlements.filter(settlement_status='pending').count()
        completed_sum = bill.settlements.filter(settlement_status='completed').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        if pending_count > 0 and completed_sum == 0:
            messages.error(request, f'Cannot update discount when bill has pending payments ({pending_count} pending). Please cancel pending payments first if discount change is necessary.')
        else:
            messages.error(request, f'Cannot update discount when bill has payments (Rs. {bill.paid_amount} paid). Please reverse payments first if discount change is necessary.')
        return redirect('sales:detail', pk=pk)
    
    # Prevent discount update if bill is fully settled
    if bill.settlement_status == 'settled':
        messages.error(request, 'Cannot update discount for a fully settled bill. Please reverse payments first if needed.')
        return redirect('sales:detail', pk=pk)
    
    # Prevent discount update if there are any payments (even partial)
    if bill.paid_amount > 0:
        messages.error(request, f'Cannot update discount when bill has payments (Rs. {bill.paid_amount} paid). Please reverse payments first if discount change is necessary.')
        return redirect('sales:detail', pk=pk)
    
    if request.method == 'POST':
        try:
            discount_percentage = Decimal(str(request.POST.get('discount_percentage', 0)))
            discount_amount = Decimal(str(request.POST.get('discount_amount', 0)))
            
            # Update discount - prefer amount if both are provided
            if discount_amount > 0:
                bill.discount_amount = discount_amount
                bill.discount_percentage = Decimal('0')  # Will be recalculated in calculate_totals
            else:
                bill.discount_percentage = discount_percentage
                bill.discount_amount = Decimal('0')  # Will be recalculated in calculate_totals
            
            bill.calculate_totals()
            
            messages.success(request, 'Discount updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating discount: {str(e)}')
    
    return redirect('sales:detail', pk=pk)


@login_required
@transaction.atomic
def cancel_bill(request, pk):
    """Cancel a bill and reverse all transactions"""
    bill = get_object_or_404(Bill, pk=pk)
    
    # Check permissions
    if request.user.is_sales_rep and bill.sales_rep != request.user:
        messages.error(request, 'You do not have permission to cancel this bill.')
        return redirect('sales:detail', pk=pk)
    
    # Check if bill can be cancelled
    if bill.bill_status == 'cancelled':
        messages.warning(request, 'This bill is already cancelled.')
        return redirect('sales:detail', pk=pk)
    
    if bill.paid_amount > 0:
        messages.error(request, 'Cannot cancel bill with payments. Please refund payments first.')
        return redirect('sales:detail', pk=pk)
    
    try:
        # Reverse inventory - Add products back to stock
        from products.models import FIFOCostLayer, StockMovement
        affected_products = []
        for item in bill.items.all():
            product = item.product
            total_qty = item.quantity + item.foc_quantity
            previous_qty = product.quantity_in_stock
            product.quantity_in_stock += total_qty
            product.save()
            
            # Restore FIFO layers that were consumed by this sale
            # Re-create a layer with the cost that was recorded on the BillItem
            if item.unit_cost and total_qty > 0:
                FIFOCostLayer.create_layer(
                    product=product,
                    qty=int(total_qty),
                    unit_cost=item.unit_cost,
                    source='adjustment',
                    reference=f'{bill.bill_number}-CANCEL',
                )
            
            # Create reversal stock movement for audit trail
            cost_per_unit = item.unit_cost if item.unit_cost else (product.cost_after_foc or Decimal('0'))
            StockMovement.objects.create(
                product=product,
                movement_type='adjustment',
                quantity=int(total_qty),
                previous_quantity=previous_qty,
                new_quantity=product.quantity_in_stock,
                reference_number=f'{bill.bill_number}-CANCEL',
                notes=f'Bill {bill.bill_number} cancelled - stock reversed',
                created_by=request.user,
                unit_cost=cost_per_unit,
                total_cost=cost_per_unit * total_qty,
            )
            affected_products.append(product)
        
        # Reverse FOC transactions for this bill
        from products.models import FOCValueTransaction
        foc_transactions = FOCValueTransaction.objects.filter(
            bill_item__bill=bill,
            is_archived=False
        )
        for foc_txn in foc_transactions:
            foc_txn.is_archived = True
            foc_txn.notes = f"{foc_txn.notes or ''}\n[CANCELLED] Bill {bill.bill_number} cancelled on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            foc_txn.save()
            # Update account balance
            if hasattr(foc_txn, 'foc_account') and foc_txn.foc_account:
                foc_txn.foc_account.update_balance()
        
        # Reverse shop balance
        bill.shop.current_balance -= bill.balance_amount
        bill.shop.save()
        
        # Mark bill as cancelled
        bill.bill_status = 'cancelled'
        bill.save()
        
        # Re-replay FIFO for affected products to reassign cost layers
        for product in affected_products:
            FIFOCostLayer.replay_product_fifo(product)
        
        messages.success(request, f'Bill {bill.bill_number} has been cancelled successfully. Inventory and shop balance have been reversed.')
        return redirect('sales:detail', pk=pk)
        
    except Exception as e:
        messages.error(request, f'Error cancelling bill: {str(e)}')
        return redirect('sales:detail', pk=pk)


@login_required
@transaction.atomic
def delete_bill(request, pk):
    """Delete a bill (only draft bills with no payments)"""
    bill = get_object_or_404(Bill, pk=pk)
    
    # Check permissions
    if request.user.is_sales_rep and bill.sales_rep != request.user:
        messages.error(request, 'You do not have permission to delete this bill.')
        return redirect('sales:list')
    
    # Check if bill can be deleted
    if bill.bill_status != 'draft':
        messages.error(request, 'Only draft bills can be deleted. Use cancel for confirmed bills.')
        return redirect('sales:detail', pk=pk)
    
    if bill.paid_amount > 0:
        messages.error(request, 'Cannot delete bill with payments.')
        return redirect('sales:detail', pk=pk)
    
    try:
        # Reverse inventory and FIFO layers
        from products.models import FIFOCostLayer, StockMovement
        affected_products = []
        for item in bill.items.all():
            product = item.product
            total_qty = item.quantity + item.foc_quantity
            previous_qty = product.quantity_in_stock
            product.quantity_in_stock += total_qty
            product.save()
            
            # Restore FIFO layers
            cost_per_unit = item.unit_cost if item.unit_cost else (product.cost_after_foc or Decimal('0'))
            if total_qty > 0:
                FIFOCostLayer.create_layer(
                    product=product,
                    qty=int(total_qty),
                    unit_cost=cost_per_unit,
                    source='adjustment',
                    reference=f'{bill.bill_number}-DELETE',
                )
            affected_products.append(product)
        
        # Delete the sale stock movements for this bill
        StockMovement.objects.filter(
            reference_number=bill.bill_number,
            movement_type='sale',
        ).delete()
        
        # Reverse shop balance
        bill.shop.current_balance -= bill.balance_amount
        bill.shop.save()
        
        bill_number = bill.bill_number
        bill.delete()
        
        # Re-replay FIFO for affected products to reassign cost layers
        for product in affected_products:
            FIFOCostLayer.replay_product_fifo(product)
        
        messages.success(request, f'Bill {bill_number} has been deleted successfully.')
        return redirect('sales:list')
        
    except Exception as e:
        messages.error(request, f'Error deleting bill: {str(e)}')
        return redirect('sales:detail', pk=pk)


@login_required
def mobile_print(request, pk):
    """Mobile-friendly print page with Bluetooth printer support - World-class optimized"""
    from .print_engine import UnifiedPrintEngine
    import time
    
    bill = get_object_or_404(Bill, pk=pk)
    
    # Check permissions
    if request.user.is_sales_rep and bill.sales_rep != request.user:
        messages.error(request, 'You do not have permission to view this bill.')
        return redirect('sales:list')
    
    items = bill.items.all().select_related('product', 'product__category', 'product__company').order_by('product__display_order', 'product__product_name')
    
    # Separate regular items and FOC-only items for display order matching bill detail
    regular_items = []
    foc_items = []
    for item in items:
        if item.quantity > 0:
            regular_items.append(item)
        if item.foc_quantity > 0:
            foc_items.append(item)
    # Combined: regular items first, then FOC-only (items that ONLY have FOC, no sales qty)
    # Items with both qty and foc_quantity show in regular list with FOC inline
    ordered_items = regular_items + [i for i in foc_items if i.quantity == 0]
    
    # Get payment/settlement breakdown for the bill
    from payments.models import SalesAccountSettlement
    from decimal import Decimal
    
    settlements = bill.settlements.all()
    
    # Cash paid (completed)
    cash_paid = sum(s.amount for s in settlements if s.settlement_method == 'cash' and s.settlement_status == 'completed')
    # Cheques
    cheque_completed = sum(s.amount for s in settlements if s.settlement_method == 'cheque' and s.settlement_status == 'completed')
    cheque_pending = sum(s.amount for s in settlements if s.settlement_method == 'cheque' and s.settlement_status == 'pending')
    # Bank transfers
    bank_completed = sum(s.amount for s in settlements if s.settlement_method == 'bank_transfer' and s.settlement_status == 'completed')
    bank_pending = sum(s.amount for s in settlements if s.settlement_method == 'bank_transfer' and s.settlement_status == 'pending')
    # Return adjustments
    return_adj = sum(s.amount for s in settlements if s.settlement_method == 'return_adjustment' and s.settlement_status == 'completed')
    
    total_paid = cash_paid + cheque_completed + bank_completed + return_adj
    total_pending = cheque_pending + bank_pending
    credit_balance = bill.total_amount - total_paid - total_pending
    if credit_balance < 0:
        credit_balance = Decimal('0')
    has_payment_info = total_paid > 0 or total_pending > 0 or credit_balance > 0
    
    # Use unified print engine for optimized context
    engine = UnifiedPrintEngine(request.user, receipt_type='bill')
    context = engine.get_print_context({
        'sale': bill,
        'items': ordered_items,
    })
    
    # Add payment breakdown to context
    context['cash_paid'] = cash_paid
    context['cheque_completed'] = cheque_completed
    context['cheque_pending'] = cheque_pending
    context['bank_completed'] = bank_completed
    context['bank_pending'] = bank_pending
    context['return_adj'] = return_adj
    context['total_paid'] = total_paid
    context['total_pending'] = total_pending
    context['credit_balance'] = credit_balance
    context['has_payment_info'] = has_payment_info
    
    # Add cache buster
    context['cache_buster'] = str(int(time.time()))
    
    response = render(request, 'sales/mobile_print.html', context)
    # Aggressive no-cache headers
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


@login_required
def edit_bill(request, pk):
    """Edit bill (only draft bills)"""
    bill = get_object_or_404(Bill, pk=pk)
    
    # Check permissions
    if request.user.is_sales_rep and bill.sales_rep != request.user:
        messages.error(request, 'You do not have permission to edit this bill.')
        return redirect('sales:detail', pk=pk)
    
    if bill.bill_status != 'draft':
        messages.error(request, 'Only draft bills can be edited.')
        return redirect('sales:detail', pk=pk)
    
    if bill.paid_amount > 0:
        messages.error(request, 'Cannot edit bill with payments.')
        return redirect('sales:detail', pk=pk)
    
    # GET request - show form with existing data
    if request.user.is_sales_rep:
        shops = Shop.objects.filter(assigned_sales_rep=request.user, is_active=True)
    else:
        shops = Shop.objects.filter(is_active=True)
    
    products = Product.objects.filter(is_active=True).select_related('company').order_by('size', 'marked_price', 'display_order', 'product_name')
    
    # Get existing items
    existing_items = bill.items.all().select_related('product')
    
    # Group products by size + marked_price combination
    from collections import defaultdict, OrderedDict
    products_by_category = defaultdict(list)
    
    for product in products:
        category_key = f"{product.size} - Rs. {product.marked_price}"
        products_by_category[category_key].append(product)
    
    products_by_category = OrderedDict(sorted(products_by_category.items()))
    
    context = {
        'shops': shops,
        'products_by_category': products_by_category,
        'bill': bill,
        'existing_items': existing_items,
        'is_edit': True
    }
    
    return render(request, 'sales/edit_bill.html', context)


@login_required
def return_list(request):
    """List all returns - DEPRECATED: Use sales/return_views.py instead"""
    if request.user.is_sales_rep:
        returns = Return.objects.filter(created_by=request.user).select_related('shop', 'bill')
    else:
        returns = Return.objects.all().select_related('shop', 'bill')
    
    context = {
        'returns': returns
    }
    return render(request, 'sales/return_list.html', context)


# ==================== NEW ENHANCED BILL SYSTEM ====================
@login_required
def bill_summary(request, pk):
    """Mobile-friendly bill summary with print button"""
    sale = get_object_or_404(Sale, pk=pk)
    
    # Check permissions
    if request.user.is_sales_rep and sale.sales_rep != request.user:
        messages.error(request, 'You can only view your own bills.')
        return redirect('sales:bill_list')
    
    items = sale.items.all().select_related('product', 'product__category')
    
    # Get payment history (new Payment model)
    payments = sale.payments.all().select_related('collected_by').order_by('-payment_date')
    
    # Also get old settlements if any
    from payments.models import SalesAccountSettlement
    settlements = SalesAccountSettlement.objects.filter(bill=sale).select_related('received_by').order_by('-settlement_date')
    
    # Combine both payment lists for display
    all_payments = list(payments) + list(settlements)
    all_payments.sort(key=lambda x: getattr(x, 'payment_date', None) or getattr(x, 'settlement_date', None), reverse=True)
    
    # Calculate category totals
    from collections import defaultdict
    category_totals = defaultdict(lambda: {'count': 0, 'total': Decimal('0')})
    for item in items:
        category_name = item.product.category.name if item.product.category else 'Uncategorized'
        category_totals[category_name]['count'] += 1
        category_totals[category_name]['total'] += item.line_total
    
    # Sort by category name
    category_totals = dict(sorted(category_totals.items()))
    
    # Calculate payment method breakdown (ONLY COMPLETED/COLLECTED PAYMENTS)
    cash_paid = Decimal('0')
    cheque_paid = Decimal('0')
    bank_paid = Decimal('0')
    
    # Process new payments (only collected ones)
    for payment in payments:
        if payment.collection_status == 'collected':
            if payment.payment_type == 'cash':
                cash_paid += payment.amount
            elif payment.payment_type == 'cheque':
                cheque_paid += payment.amount
            elif payment.payment_type == 'bank_transfer':
                bank_paid += payment.amount
    
    # Process old settlements (only completed ones)
    for settlement in settlements:
        if settlement.settlement_status == 'completed':
            if settlement.settlement_method == 'cash':
                cash_paid += settlement.amount
            elif settlement.settlement_method == 'cheque':
                cheque_paid += settlement.amount
            elif settlement.settlement_method == 'bank_transfer':
                bank_paid += settlement.amount
    
    # Credit balance is the remaining unpaid amount
    credit_balance = sale.balance_amount
    
    # Check if there are any payments
    has_payments = len(all_payments) > 0
    
    # Get user's print profile
    print_profile = PrintManager.get_user_default(request.user, 'bill')
    
    context = {
        'sale': sale,
        'items': items,
        'payments': all_payments,
        'bill_settings': print_profile,  # Backward compatibility
        'print_profile': print_profile,
        'page_title': f'Bill {sale.sale_number}',
        'category_totals': category_totals,
        'cash_paid': cash_paid,
        'cheque_paid': cheque_paid,
        'bank_paid': bank_paid,
        'credit_balance': credit_balance,
        'has_payments': has_payments,
    }
    return render(request, 'sales/bill_summary.html', context)


@login_required
def bill_print_preview(request, pk):
    """Print preview page - shows bill ready for printing"""
    from sales.print_engine import UnifiedPrintEngine
    import time
    
    sale = get_object_or_404(Sale, pk=pk)
    
    # Check permissions
    if request.user.is_sales_rep and sale.sales_rep != request.user:
        messages.error(request, 'You can only print your own bills.')
        return redirect('sales:bill_list')
    
    items = sale.items.all().select_related('product')
    
    # Use unified print engine (same pattern as mobile_print)
    engine = UnifiedPrintEngine(request.user, receipt_type='bill')
    context = engine.get_print_context({
        'sale': sale,
        'items': items,
    })
    
    # Determine which print template to use based on paper size
    print_profile = context['print_profile']
    paper_size = print_profile.paper_size
    
    if paper_size in ['thermal_48mm', 'thermal_58mm', 'thermal_80mm']:
        print_template = 'sales/print_thermal.html'
    else:
        print_template = 'sales/print_a4.html'
    
    # Add extra context
    context['bill_settings'] = print_profile  # Backward compatibility
    context['template'] = print_profile  # Backward compatibility
    context['print_template'] = print_template
    context['page_title'] = f'Print Bill {sale.sale_number}'
    context['cache_buster'] = str(int(time.time()))
    
    response = render(request, 'sales/bill_print_preview.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@login_required
def printer_settings(request):
    """Unified printer settings page using PrintManager"""
    from .paper_config import PaperSizeConfig
    from .receipt_optimizer import ReceiptOptimizer
    from products.models import Company
    from business.models import DistributorProfile
    import json
    
    # Get or create print profile for user (default: bill type)
    receipt_type = request.GET.get('receipt_type', 'bill')
    print_profile = PrintManager.get_user_default(request.user, receipt_type)
    
    if request.method == 'POST':
        try:
            # Profile Information
            print_profile.profile_name = request.POST.get('profile_name', f'{request.user.username} - {receipt_type}')
            print_profile.receipt_type = request.POST.get('receipt_type', receipt_type)
            
            # Ensure only THIS profile is default for this user+receipt_type
            # First, set all other profiles to is_default=False
            PrintManager.objects.filter(
                user=request.user,
                receipt_type=receipt_type,
                is_active=True
            ).exclude(id=print_profile.id).update(is_default=False)
            
            # Now set this profile as the default
            print_profile.is_default = True
            
            # Company/Distributor Selection
            print_profile.use_distributor_profile = request.POST.get('use_distributor_profile') == 'on'
            company_id = request.POST.get('company_id')
            if company_id and company_id != '':
                print_profile.company_id = int(company_id)
            else:
                print_profile.company_id = None
            
            # Branding Display Toggles
            print_profile.show_logo = request.POST.get('show_logo') == 'on'
            print_profile.show_tagline = request.POST.get('show_tagline') == 'on'
            print_profile.show_address = request.POST.get('show_address') == 'on'
            print_profile.show_contact = request.POST.get('show_contact') == 'on'
            print_profile.show_website = request.POST.get('show_website') == 'on'
            
            # Receipt Footer Messages
            print_profile.footer_line1 = request.POST.get('footer_line1', 'Thank you for your business!')
            print_profile.footer_line2 = request.POST.get('footer_line2', '') or None
            print_profile.footer_line3 = request.POST.get('footer_line3', '') or None
            
            # Receipt Template Settings
            print_profile.show_barcode = request.POST.get('show_barcode') == 'on'
            print_profile.show_qr_code = request.POST.get('show_qr_code') == 'on'
            print_profile.show_tax_breakdown = request.POST.get('show_tax_breakdown') == 'on'
            print_profile.language = request.POST.get('language', 'en')
            
            # Printer Hardware Settings
            print_profile.printer_name = request.POST.get('printer_name', '')
            print_profile.paper_size = request.POST.get('paper_size', '80mm')
            print_profile.bluetooth_address = request.POST.get('bluetooth_address', '')
            print_profile.print_density = int(request.POST.get('print_density', 50))
            print_profile.print_speed = int(request.POST.get('print_speed', 50))
            
            # Print Copies
            print_profile.bill_print_copies = int(request.POST.get('bill_print_copies', 1))
            print_profile.payment_print_copies = int(request.POST.get('payment_print_copies', 1))
            print_profile.return_print_copies = int(request.POST.get('return_print_copies', 1))
            print_profile.field_receipt_print_copies = int(request.POST.get('field_receipt_print_copies', 1))
            
            # Auto Print Setting
            print_profile.auto_print = request.POST.get('auto_print') == 'on'
            
            # Save footer lines for ALL receipt types (each gets its own footer)
            for rt_code, rt_label in PrintManager.RECEIPT_TYPE_CHOICES:
                if rt_code == receipt_type:
                    # Current profile footer already set above
                    continue
                rt_profile = PrintManager.get_user_default(request.user, rt_code)
                rt_f1 = request.POST.get(f'footer_line1_{rt_code}')
                rt_f2 = request.POST.get(f'footer_line2_{rt_code}')
                rt_f3 = request.POST.get(f'footer_line3_{rt_code}')
                if rt_f1 is not None:  # Only save if fields were submitted
                    rt_profile.footer_line1 = rt_f1 or 'Thank you for your business!'
                    rt_profile.footer_line2 = rt_f2 or None
                    rt_profile.footer_line3 = rt_f3 or None
                    rt_profile.save()
            
            print_profile.save()
            
            # ======================================================
            # GLOBAL PROPAGATION: Apply settings to ALL users
            # Only admin/office staff can propagate settings
            # ======================================================
            if request.user.user_type != 'sales_rep':
                # These settings should be consistent across all users:
                # - Branding source (company/distributor)
                # - Display toggles (logo, tagline, address, etc.)
                # - Paper size
                # - Print copies per receipt type
                # - Footer messages (per receipt type)
                # Hardware settings (bluetooth_address, printer_name) stay per-user.
                
                from accounts.models import User as AppUser
                from accounts.tenant_utils import get_tenant_users
                all_users = get_tenant_users().filter(is_active=True)
                
                # Shared settings to propagate (NOT hardware-specific)
                shared_fields = {
                    'use_distributor_profile': print_profile.use_distributor_profile,
                    'company_id': print_profile.company_id,
                    'show_logo': print_profile.show_logo,
                    'show_tagline': print_profile.show_tagline,
                    'show_address': print_profile.show_address,
                    'show_contact': print_profile.show_contact,
                    'show_website': print_profile.show_website,
                    'paper_size': print_profile.paper_size,
                    'print_density': print_profile.print_density,
                    'print_speed': print_profile.print_speed,
                    'bill_print_copies': print_profile.bill_print_copies,
                    'payment_print_copies': print_profile.payment_print_copies,
                    'return_print_copies': print_profile.return_print_copies,
                    'field_receipt_print_copies': print_profile.field_receipt_print_copies,
                    'show_barcode': print_profile.show_barcode,
                    'show_qr_code': print_profile.show_qr_code,
                    'show_tax_breakdown': print_profile.show_tax_breakdown,
                    'language': print_profile.language,
                    'auto_print': print_profile.auto_print,
                }
                
                # Collect footer settings per receipt type (from current user's profiles)
                footer_per_type = {}
                for rt_code, rt_label in PrintManager.RECEIPT_TYPE_CHOICES:
                    rt_prof = PrintManager.get_user_default(request.user, rt_code)
                    footer_per_type[rt_code] = {
                        'footer_line1': rt_prof.footer_line1,
                        'footer_line2': rt_prof.footer_line2,
                        'footer_line3': rt_prof.footer_line3,
                    }
                
                updated_count = 0
                for target_user in all_users:
                    for rt_code, rt_label in PrintManager.RECEIPT_TYPE_CHOICES:
                        # Skip the exact profile we just saved above (already has correct values)
                        if target_user.id == request.user.id and rt_code == receipt_type:
                            continue
                        
                        target_profile = PrintManager.get_user_default(target_user, rt_code)
                        
                        # Apply shared settings
                        for field, value in shared_fields.items():
                            setattr(target_profile, field, value)
                        
                        # Apply footer for this receipt type
                        ft = footer_per_type[rt_code]
                        target_profile.footer_line1 = ft['footer_line1']
                        target_profile.footer_line2 = ft['footer_line2']
                        target_profile.footer_line3 = ft['footer_line3']
                        
                        # Preserve per-user hardware settings
                        target_profile.save()
                        updated_count += 1
                
                messages.success(request, f'Print settings saved and applied to all users ({updated_count} profiles updated)!')
            else:
                messages.success(request, 'Print settings saved for your profile!')
            return redirect('sales:printer_settings')
            
        except Exception as e:
            messages.error(request, f'Error saving settings: {str(e)}')
    
    # Refresh profile from database to get latest values
    print_profile.refresh_from_db()
    
    # Get all profiles for this user
    user_profiles = PrintManager.objects.filter(user=request.user).order_by('-is_default', 'receipt_type', 'profile_name')
    
    # Get paper size specifications
    paper_sizes = []
    for code, name in PaperSizeConfig.PAPER_SIZE_CHOICES:
        specs = PaperSizeConfig.get_specs(code)
        if specs:
            paper_sizes.append({
                'code': code,
                'name': name,
                'category': specs.category,
                'width_mm': specs.width_mm,
                'width_inch': specs.width_inch,
                'chars_per_line': specs.chars_per_line_normal,
                'is_thermal': specs.category == 'thermal',
                'optimal_fonts': PaperSizeConfig.get_optimal_fonts(code),
            })
    
    # Get optimization settings for current paper size
    optimizer = ReceiptOptimizer(print_profile.paper_size)
    optimization_settings = optimizer.get_optimized_settings(item_count=10)
    
    # Get companies and distributor profile for branding selection
    companies = Company.objects.filter(is_active=True).order_by('company_name')
    try:
        distributor_profile = DistributorProfile.objects.filter(is_active=True).first()
    except:
        distributor_profile = None
    
    # Load footer profiles for all receipt types
    footer_profiles = {}
    for rt_code, rt_label in PrintManager.RECEIPT_TYPE_CHOICES:
        if rt_code == receipt_type:
            footer_profiles[rt_code] = {
                'label': rt_label,
                'footer_line1': print_profile.footer_line1 or '',
                'footer_line2': print_profile.footer_line2 or '',
                'footer_line3': print_profile.footer_line3 or '',
            }
        else:
            rt_profile = PrintManager.get_user_default(request.user, rt_code)
            footer_profiles[rt_code] = {
                'label': rt_label,
                'footer_line1': rt_profile.footer_line1 or '',
                'footer_line2': rt_profile.footer_line2 or '',
                'footer_line3': rt_profile.footer_line3 or '',
            }
    
    context = {
        'print_profile': print_profile,
        'user_profiles': user_profiles,
        'paper_sizes': paper_sizes,
        'paper_sizes_json': json.dumps(paper_sizes),
        'optimization_settings': json.dumps(optimization_settings),
        'receipt_types': PrintManager.RECEIPT_TYPE_CHOICES,
        'footer_profiles': footer_profiles,
        'companies': companies,
        'distributor_profile': distributor_profile,
        'page_title': 'Printer Settings',
        # Backward compatibility
        'bill_settings': print_profile,
    }
    return render(request, 'sales/printer_settings.html', context)


@login_required
def bill_templates_list(request):
    """List all print profiles (formerly bill templates)"""
    profiles = PrintManager.objects.filter(user=request.user, is_active=True).order_by('-is_default', 'receipt_type', 'profile_name')
    
    context = {
        'templates': profiles,  # Keep template name for backward compatibility
        'profiles': profiles,
        'page_title': 'Print Profiles'
    }
    return render(request, 'sales/bill_templates_list.html', context)


@login_required
def bill_template_create(request):
    """Create new print profile (formerly bill template)"""
    if request.method == 'POST':
        try:
            profile = PrintManager.objects.create(
                user=request.user,
                profile_name=request.POST.get('name'),
                receipt_type=request.POST.get('receipt_type', 'bill'),
                paper_size=request.POST.get('paper_size', '80mm'),
                company_name=request.POST.get('company_name', 'Zergo Distributors'),
                company_address=request.POST.get('company_address', ''),
                company_phone=request.POST.get('company_phone', ''),
                company_email=request.POST.get('company_email', ''),
                header_text=request.POST.get('header_text', ''),
                footer_line_1=request.POST.get('footer_text', ''),
                show_barcode=request.POST.get('show_barcode') == 'on',
                show_qr_code=request.POST.get('show_qr_code') == 'on',
                show_tax_breakdown=request.POST.get('show_tax_breakdown') == 'on',
                font_size_header=int(request.POST.get('font_size_header', 14)),
                font_size_body=int(request.POST.get('font_size_body', 10)),
                font_size_footer=int(request.POST.get('font_size_footer', 8)),
                is_default=request.POST.get('is_default') == 'on'
            )
            
            messages.success(request, f'Print profile "{profile.profile_name}" created successfully!')
            return redirect('sales:bill_templates_list')
            
        except Exception as e:
            messages.error(request, f'Error creating profile: {str(e)}')
    
    context = {
        'page_title': 'Create Print Profile'
    }
    return render(request, 'sales/bill_template_form.html', context)


@login_required
def bill_template_edit(request, pk):
    """Edit print profile (formerly bill template)"""
    profile = get_object_or_404(PrintManager, pk=pk, user=request.user)
    
    if request.method == 'POST':
        try:
            profile.profile_name = request.POST.get('name')
            profile.receipt_type = request.POST.get('receipt_type', profile.receipt_type)
            profile.paper_size = request.POST.get('paper_size')
            profile.company_name = request.POST.get('company_name', 'Zergo Distributors')
            profile.company_address = request.POST.get('company_address', '')
            profile.company_phone = request.POST.get('company_phone', '')
            profile.company_email = request.POST.get('company_email', '')
            profile.header_text = request.POST.get('header_text', '')
            profile.footer_line_1 = request.POST.get('footer_text', '')
            profile.show_barcode = request.POST.get('show_barcode') == 'on'
            profile.show_qr_code = request.POST.get('show_qr_code') == 'on'
            profile.show_tax_breakdown = request.POST.get('show_tax_breakdown') == 'on'
            profile.font_size_header = int(request.POST.get('font_size_header', 14))
            profile.font_size_body = int(request.POST.get('font_size_body', 10))
            profile.font_size_footer = int(request.POST.get('font_size_footer', 8))
            profile.is_default = request.POST.get('is_default') == 'on'
            profile.save()
            
            messages.success(request, f'Print profile "{profile.profile_name}" updated successfully!')
            return redirect('sales:bill_templates_list')
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    context = {
        'template': profile,  # Keep template name for backward compatibility
        'profile': profile,
        'page_title': f'Edit Print Profile: {profile.profile_name}'
    }
    return render(request, 'sales/bill_template_form.html', context)


@login_required
def bill_template_delete(request, pk):
    """Delete print profile (formerly bill template)"""
    profile = get_object_or_404(PrintManager, pk=pk, user=request.user)
    
    if request.method == 'POST':
        profile_name = profile.profile_name
        profile.delete()
        messages.success(request, f'Print profile "{profile_name}" deleted successfully!')
        return redirect('sales:bill_templates_list')
    
    context = {
        'template': profile,  # Keep template name for backward compatibility
        'profile': profile,
        'page_title': f'Delete Print Profile: {profile.profile_name}'
    }
    return render(request, 'sales/bill_template_delete.html', context)


# ========================================
# PAYMENT MANAGEMENT VIEWS
# ========================================

@login_required
@transaction.atomic
def add_payment(request, pk):
    """Add payment to a bill"""
    from payments.models import SalesAccountSettlement, SettlementAttachment
    from django.utils import timezone
    from django.db import models
    
    bill = get_object_or_404(Bill, pk=pk)
    
    # Check permissions for sales reps
    if request.user.is_sales_rep:
        from shops.models import ShopAccess
        
        # Allow if rep created the bill
        if bill.sales_rep == request.user:
            pass  # Allowed
        else:
            # Check shop access level (need Level 2+ for activities)
            access_level = ShopAccess.get_rep_access_level(bill.shop, request.user)
            
            if not access_level or access_level < 2:
                messages.error(request, 'You do not have permission to add payments to this bill.')
                return redirect('sales:detail', pk=pk)
    
    if bill.bill_status == 'cancelled':
        messages.error(request, 'Cannot add payment to cancelled bill.')
        return redirect('sales:detail', pk=pk)
    
    if request.method == 'POST':
        try:
            # Prevent duplicate submissions via session token
            submission_token = request.POST.get('submission_token', '')
            token_key = f'payment_submission_token_{pk}'
            session_token = request.session.pop(token_key, None)
            if not submission_token or submission_token != session_token:
                messages.warning(request, 'This payment was already submitted. Please check payment history.')
                return redirect('sales:detail', pk=pk)

            payment_method = request.POST.get('payment_type')
            amount = Decimal(request.POST.get('amount', 0))
            
            # Validate amount
            if amount <= 0:
                messages.error(request, 'Payment amount must be greater than zero.')
                return redirect('sales:add_settlement', pk=pk)
            
            # Calculate total payments (excluding cancelled/bounced ones)
            total_payments = bill.settlements.filter(
                settlement_status__in=['completed', 'pending']
            ).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0')
            
            # Calculate remaining balance (total - all non-cancelled payments)
            remaining_balance = bill.total_amount - total_payments
            
            if amount > remaining_balance:
                messages.error(request, f'Payment amount Rs. {amount} exceeds remaining balance of Rs. {remaining_balance}. Total bill: Rs. {bill.total_amount}, Total payments (including pending): Rs. {total_payments}')
                return redirect('sales:add_settlement', pk=pk)
            
            # Generate settlement number
            from utils.number_generator import generate_number
            settlement_number = generate_number('SET', SalesAccountSettlement, 'settlement_number')
            
            # Handle return adjustment
            return_ref = None
            if payment_method == 'return_adjustment':
                return_id = request.POST.get('return_id')
                if not return_id:
                    messages.error(request, 'Please select a return to apply.')
                    return redirect('sales:add_settlement', pk=pk)
                
                from sales.models import Return
                return_ref = Return.objects.get(pk=return_id)
                
                # Validate return belongs to same shop
                if return_ref.shop != bill.shop:
                    messages.error(request, 'Return must belong to the same shop as the bill.')
                    return redirect('sales:add_settlement', pk=pk)
                
                # Validate return has available amount
                available_amount = return_ref.total_amount - return_ref.applied_amount
                if available_amount <= 0:
                    messages.error(request, 'This return has already been fully applied.')
                    return redirect('sales:add_settlement', pk=pk)
                
                if amount > available_amount:
                    messages.error(request, f'Amount exceeds available return balance of Rs. {available_amount}')
                    return redirect('sales:add_settlement', pk=pk)
            
            # Create settlement record (NO PROVISIONAL SETTLEMENTS - all returns auto-approved)
            settlement = SalesAccountSettlement(
                settlement_number=settlement_number,
                shop=bill.shop,
                bill=bill,
                settlement_method=payment_method,
                amount=amount,
                received_by=request.user,
                notes=request.POST.get('notes', ''),
                return_ref=return_ref,
                is_provisional=False,  # No provisional settlements - returns are auto-approved
            )
            
            # Set settlement-specific fields and status
            if payment_method == 'return_adjustment':
                # All return adjustments are completed immediately (no pending state)
                settlement.settlement_status = 'completed'
                settlement.verified_by = request.user
                settlement.verified_at = timezone.now()
                
                # Update return's applied amount
                return_ref.applied_amount += amount
                
                # Update return settlement status
                if return_ref.applied_amount >= return_ref.total_amount:
                    return_ref.settlement_status = 'fully_applied'
                    return_ref.is_applied = True
                elif return_ref.applied_amount > 0:
                    return_ref.settlement_status = 'partially_applied'
                
                return_ref.save()
                
            elif payment_method == 'cheque':
                settlement.reference_number = request.POST.get('cheque_number')
                settlement.cheque_date = request.POST.get('cheque_date') or None
                settlement.bank_name = request.POST.get('cheque_bank_name', '')  # Get from cheque-specific field
                settlement.settlement_status = 'pending'  # Cheque needs to clear
            elif payment_method == 'bank_transfer':
                settlement.reference_number = request.POST.get('reference_number')
                settlement.bank_name = request.POST.get('transfer_bank_name', '')  # Get from transfer-specific field
                settlement.settlement_status = 'pending'  # Bank transfer needs office confirmation
            else:  # cash
                settlement.settlement_status = 'completed'  # Cash is immediate
                settlement.verified_by = request.user
                settlement.verified_at = timezone.now()
            
            settlement.save()
            
            # Recalculate bill totals from all settlements (prevents double-counting)
            bill.calculate_totals()
            
            # Handle image attachments for cheque and bank transfer
            if payment_method == 'cheque':
                # Cheque front image
                if 'cheque_front' in request.FILES:
                    SettlementAttachment.objects.create(
                        settlement=settlement,
                        file=request.FILES['cheque_front'],
                        description='Cheque Front'
                    )
                
                # Cheque back image
                if 'cheque_back' in request.FILES:
                    SettlementAttachment.objects.create(
                        settlement=settlement,
                        file=request.FILES['cheque_back'],
                        description='Cheque Back'
                    )
            
            elif payment_method == 'bank_transfer':
                # Bank transfer receipt
                if 'bank_receipt' in request.FILES:
                    SettlementAttachment.objects.create(
                        settlement=settlement,
                        file=request.FILES['bank_receipt'],
                        description='Bank Transfer Receipt'
                    )
            
            # No need to update bill here - the post_save signal on SalesAccountSettlement
            # will automatically call bill.calculate_totals() when the settlement is saved
            
            # Auto-mark shop visit (cash & cheque only — bank transfers are done remotely)
            if bill.shop and payment_method not in ('bank_transfer', 'return_adjustment'):
                try:
                    from shops.visit_utils import auto_mark_visit
                    auto_mark_visit(bill.shop, request.user, 'auto_payment', settlement.settlement_number)
                except Exception:
                    pass  # Never block payment for visit tracking
            
            messages.success(request, f'Payment of Rs. {amount} recorded successfully!')
            # Redirect to unified payment detail page
            return redirect('sales:settlement_detail', pk=settlement.pk)
            
        except Exception as e:
            messages.error(request, f'Error recording payment: {str(e)}')
            return redirect('sales:add_settlement', pk=pk)
    
    # GET request - show form
    # Calculate total payments (excluding cancelled/bounced ones)
    total_payments = bill.settlements.filter(
        settlement_status__in=['completed', 'pending']
    ).aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0')
    
    # Calculate actual remaining balance
    actual_balance = bill.total_amount - total_payments
    
    # Get returns for this shop that can be used for bill adjustment
    # All returns (verified or not) can be used - manager verifies at end of day
    from sales.models import Return
    available_returns = Return.objects.filter(
        shop=bill.shop,
        settlement_method='bill_adjustment'  # Only bill adjustments can be used (NOT cash)
    ).exclude(
        settlement_status__in=['fully_applied', 'cancelled']  # Exclude fully applied and cancelled returns
    ).annotate(
        available_amount=models.F('total_amount') - models.F('applied_amount')
    ).filter(
        available_amount__gt=0  # Only returns with remaining credit
    ).order_by('-return_date')
    
    # Generate one-time submission token to prevent double-submit
    token_key = f'payment_submission_token_{pk}'
    submission_token = str(uuid.uuid4())
    request.session[token_key] = submission_token

    context = {
        'bill': bill,
        'balance_amount': bill.balance_amount,  # Only completed payments
        'actual_balance': actual_balance,  # Including pending payments
        'total_payments': total_payments,
        'available_returns': available_returns,
        'page_title': f'Add Payment - {bill.bill_number}',
        'submission_token': submission_token,
    }
    return render(request, 'sales/add_payment.html', context)


@login_required
def payment_receipt(request, pk):
    """Redirect to unified payment detail page"""
    # Redirect to the new unified payment detail page
    return redirect('sales:settlement_detail', pk=pk)


@login_required
def payment_mobile_print(request, pk):
    """Mobile-friendly print page for payment receipt with Bluetooth printer support - World-class optimized"""
    from payments.models import SalesAccountSettlement
    from .print_engine import UnifiedPrintEngine
    import time
    
    settlement = get_object_or_404(SalesAccountSettlement, pk=pk)
    
    # Check permissions
    if request.user.is_sales_rep:
        if settlement.bill and settlement.bill.sales_rep != request.user:
            messages.error(request, 'You do not have permission to view this receipt.')
            return redirect('sales:list')
    
    # Use unified print engine for optimized context
    engine = UnifiedPrintEngine(request.user, receipt_type='payment')
    context = engine.get_print_context({
        'settlement': settlement,
        'bill': settlement.bill,
        'shop': settlement.shop,
    })
    
    # Add cache buster
    context['cache_buster'] = str(int(time.time()))
    
    response = render(request, 'sales/payment_mobile_print.html', context)
    # Aggressive no-cache headers
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


@login_required
def payment_list(request):
    """List all payments"""
    # Payment model removed - using SalesAccountSettlement from payments app
    from payments.models import SalesAccountSettlement
    
    # Filter payments based on user role
    if request.user.is_sales_rep:
        # For Bill-based payments, we need different approach
        bills = Bill.objects.filter(sales_rep=request.user, paid_amount__gt=0).order_by('-bill_date')
    else:
        bills = Bill.objects.filter(paid_amount__gt=0).order_by('-bill_date')
    
    # Apply filters
    settlement_status = request.GET.get('status')
    if settlement_status:
        bills = bills.filter(settlement_status=settlement_status)
    
    context = {
        'bills': bills,
        'page_title': 'Payment Records'
    }
    return render(request, 'sales/payment_list.html', context)


@login_required
def payment_detail(request, pk):
    """Payment detail view"""
    from payments.models import SalesAccountSettlement
    
    settlement = get_object_or_404(SalesAccountSettlement, pk=pk)
    
    # Check permissions
    if request.user.is_sales_rep:
        if settlement.bill and settlement.bill.sales_rep != request.user:
            messages.error(request, 'You do not have permission to view this settlement.')
            return redirect('sales:payment_list')
    
    context = {
        'payment': settlement,  # Using 'payment' for template compatibility
        'settlement': settlement,  # Keep settlement for backward compatibility
        'page_title': f'Settlement {settlement.settlement_number}'
    }
    return render(request, 'sales/payment_detail.html', context)


@login_required
@transaction.atomic
def mark_payment_collected(request, pk):
    """Mark payment as collected (for cheques and bank transfers)"""
    from payments.models import SalesAccountSettlement
    from django.utils import timezone
    
    if request.user.user_type == 'sales_rep':
        messages.error(request, 'Only office staff can mark payments as collected.')
        return redirect('sales:payment_detail', pk=pk)
    
    settlement = get_object_or_404(SalesAccountSettlement, pk=pk)
    
    if request.method == 'POST':
        if settlement.settlement_method not in ['cheque', 'bank_transfer']:
            messages.error(request, 'Only cheque and bank transfer settlements can be marked as collected.')
            return redirect('sales:payment_detail', pk=pk)
        
        # Mark as collected
        settlement.settlement_status = 'completed'
        settlement.verified_by = request.user
        settlement.verified_at = timezone.now()
        settlement.save()
        
        # Update bill paid amount
        if settlement.bill:
            settlement.bill.paid_amount += settlement.amount
            settlement.bill.balance_amount = settlement.bill.total_amount - settlement.bill.paid_amount
            
            # Update settlement status
            if settlement.bill.paid_amount >= settlement.bill.total_amount:
                settlement.bill.settlement_status = 'settled'
            elif settlement.bill.paid_amount > 0:
                settlement.bill.settlement_status = 'partial_settled'
            else:
                settlement.bill.settlement_status = 'unsettled'
            
            settlement.bill.save()
        
        messages.success(request, f'Settlement {settlement.pk} marked as collected!')
        return redirect('sales:payment_detail', pk=pk)
    
    return redirect('sales:payment_detail', pk=pk)


@login_required
@transaction.atomic
def mark_payment_bounced(request, pk):
    """Mark cheque payment as bounced"""
    from payments.models import SalesAccountSettlement
    
    if request.user.user_type == 'sales_rep':
        messages.error(request, 'Only office staff can mark payments as bounced.')
        return redirect('sales:payment_detail', pk=pk)
    
    settlement = get_object_or_404(SalesAccountSettlement, pk=pk)
    
    if settlement.settlement_method != 'cheque':
        messages.error(request, 'Only cheque settlements can be marked as bounced.')
        return redirect('sales:payment_detail', pk=pk)
    
    if request.method == 'POST':
        settlement.settlement_status = 'bounced'
        settlement.save()
        messages.warning(request, f'Settlement {settlement.settlement_number} marked as bounced!')
        return redirect('sales:payment_detail', pk=pk)
    
    return redirect('sales:payment_detail', pk=pk)


@login_required
@transaction.atomic
def mark_cheque_collected(request, pk):
    """Mark physical cheque as collected from sales rep"""
    from payments.models import SalesAccountSettlement
    from django.utils import timezone
    
    settlement = get_object_or_404(SalesAccountSettlement, pk=pk)
    
    # Only office staff and admin can mark cheques as collected
    if not (request.user.is_office_staff or request.user.is_admin):
        messages.error(request, 'Only office staff can mark cheques as collected.')
        return redirect('sales:settlement_detail', pk=pk)
    
    if settlement.settlement_method != 'cheque':
        messages.error(request, 'Only cheque settlements can be marked as collected.')
        return redirect('sales:settlement_detail', pk=pk)
    
    if settlement.cheque_collected:
        messages.warning(request, 'This cheque has already been marked as collected.')
        return redirect('sales:settlement_detail', pk=pk)
    
    if request.method == 'POST':
        settlement.cheque_collected = True
        settlement.collected_at = timezone.now()
        settlement.collected_by = request.user
        settlement.save()
        
        messages.success(request, f'Cheque {settlement.reference_number or settlement.settlement_number} marked as collected! You can now clear or bounce this cheque.')
        
        # Support redirect back to calling page (validated)
        from django.utils.http import url_has_allowed_host_and_scheme
        next_url = request.POST.get('next', '')
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect('sales:settlement_detail', pk=pk)
    
    return redirect('sales:settlement_detail', pk=pk)
