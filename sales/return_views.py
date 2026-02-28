"""
RETURN MANAGEMENT VIEWS - Simplified & Pattern-Matched with Bill System
===========================================================================
Following exact patterns from bill_list, bill_detail, and payment_detail views
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum, Q
from django.http import HttpResponseForbidden, JsonResponse
from decimal import Decimal
import uuid
from functools import wraps
from datetime import timedelta
import time
from .models import Return, ReturnItem, Sale, Bill, PrintManager
from products.models import Product, StockMovement
from shops.models import Shop, ShopAccess
import json


def require_office_staff(view_func):
    """
    Decorator to restrict views to office staff and managers only.
    Sales reps are blocked from accessing these actions.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_sales_rep:
            messages.error(request, 'You do not have permission to perform this action. Only office staff can approve/reject/delete returns.')
            return redirect('sales:return_list')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def return_list(request):
    """
    List all returns with role-based filtering
    Pattern: Matches bill_list exactly
    - Sales Reps: See only their own returns
    - Managers/Office: See all returns with filters
    """
    from datetime import timedelta
    
    # Role-based initial filtering (same pattern as bill_list)
    if request.user.is_sales_rep:
        returns = Return.objects.filter(created_by=request.user).select_related(
            'shop', 'created_by', 'bill', 'cash_paid_by'
        )
    else:
        returns = Return.objects.all().select_related(
            'shop', 'created_by', 'bill', 'cash_paid_by'
        )
    
    # Filter by date - default to all (show all returns)
    date_filter = request.GET.get('date', 'all')
    # Get today's date in the configured timezone (Asia/Colombo)
    import pytz
    local_tz = pytz.timezone(settings.TIME_ZONE)
    today = timezone.now().astimezone(local_tz).date()
    
    if date_filter == 'today':
        returns = returns.filter(return_date__date=today)
    elif date_filter == 'yesterday':
        yesterday = today - timedelta(days=1)
        returns = returns.filter(return_date__date=yesterday)
    elif date_filter == 'this_week':
        start_of_week = today - timedelta(days=today.weekday())
        returns = returns.filter(return_date__date__gte=start_of_week)
    elif date_filter == 'this_month':
        returns = returns.filter(return_date__year=today.year, return_date__month=today.month)
    elif date_filter == 'all':
        pass  # No date filtering
    
    # Custom date range filter
    from_date = request.GET.get('from_date', '').strip()
    to_date = request.GET.get('to_date', '').strip()
    
    if from_date:
        try:
            from datetime import datetime
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d')
            returns = returns.filter(return_date__date__gte=from_date_obj.date())
        except ValueError:
            pass  # Invalid date format, skip
    
    if to_date:
        try:
            from datetime import datetime
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d')
            returns = returns.filter(return_date__date__lte=to_date_obj.date())
        except ValueError:
            pass  # Invalid date format, skip
    
    # Search filter
    search = request.GET.get('search', '').strip()
    if search:
        returns = returns.filter(
            Q(return_number__icontains=search) |
            Q(shop__shop_name__icontains=search) |
            Q(shop__shop_code__icontains=search) |
            Q(cash_receipt_number__icontains=search)
        )
    
    # Filter by shop (managers only)
    shop_id = request.GET.get('shop')
    if shop_id and not request.user.is_sales_rep:
        returns = returns.filter(shop_id=shop_id)
    
    # Filter by settlement status
    settlement_status = request.GET.get('settlement_status')
    if settlement_status:
        returns = returns.filter(settlement_status=settlement_status)
    
    # Filter by return reason
    reason = request.GET.get('reason')
    if reason:
        returns = returns.filter(return_reason=reason)
    
    # Filter by settlement method
    method = request.GET.get('method')
    if method:
        returns = returns.filter(settlement_method=method)
    
    # Filter by verification status (managers only)
    verification_filter = request.GET.get('verification')
    if verification_filter and not request.user.is_sales_rep:
        if verification_filter == 'verified':
            returns = returns.filter(is_verified=True)
        elif verification_filter == 'unverified':
            returns = returns.filter(is_verified=False)
    
    # Order by date descending (same pattern as bill_list)
    returns = returns.order_by('-return_date', '-created_at')
    
    # Get shops for filter dropdown
    if not request.user.is_sales_rep:
        shops = Shop.objects.filter(is_active=True).order_by('shop_name')
    else:
        # Sales reps see shops they have Level 2+ access to
        all_shops_query = Shop.objects.filter(is_active=True)
        shops = [shop for shop in all_shops_query if ShopAccess.get_rep_access_level(shop, request.user) >= 2]
    
    # Calculate statistics (exclude cancelled returns from totals)
    active_returns = returns.exclude(settlement_status='cancelled')
    stats = {
        'total_returns': active_returns.count(),
        'total_amount': active_returns.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0'),
        'cash_settled': returns.filter(settlement_status='settled_cash').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0'),
        'available_credit': returns.filter(settlement_status='available').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0'),
        'partially_applied': returns.filter(settlement_status='partially_applied').aggregate(Sum('applied_amount'))['applied_amount__sum'] or Decimal('0'),
        'fully_applied': returns.filter(settlement_status='fully_applied').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0'),
    }
    
    # Add shops and date_filter to context for template
    context = {
        'returns': returns,
        'stats': stats,
        'shops': shops,
        'date_filter': date_filter,
    }
    
    return render(request, 'sales/return_list.html', context)


@login_required
@transaction.atomic
def return_detail(request, pk):
    """
    Return detail view with inline actions
    Pattern: Matches bill_detail with POST action handling
    Actions: approve, reject, delete, settle_cash
    """
    return_obj = get_object_or_404(
        Return.objects.select_related('shop', 'created_by', 'cash_paid_by', 'verified_by', 'bill'),
        pk=pk
    )
    
    # Check permissions (same pattern as bill_detail)
    if request.user.is_sales_rep and return_obj.created_by != request.user:
        messages.error(request, 'You do not have permission to view this return.')
        return redirect('sales:return_list')
    
    # Handle POST actions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # CANCEL ACTION (same-day corrections only - creator or manager, not if verified)
        if action == 'cancel':
            # Check if return is verified (verified returns cannot be cancelled)
            if return_obj.is_verified:
                messages.error(request, f'This return has been verified and cannot be cancelled.')
                return redirect('sales:return_detail', pk=pk)
            
            # Check if already cancelled
            if return_obj.settlement_status == 'cancelled':
                messages.warning(request, 'This return is already cancelled.')
                return redirect('sales:return_detail', pk=pk)
            
            # Check if return was created today (same-day correction window for sales reps)
            import pytz
            local_tz = pytz.timezone(settings.TIME_ZONE)
            return_created_date = return_obj.return_date.astimezone(local_tz).date()
            today = timezone.now().astimezone(local_tz).date()
            
            # Sales reps can only cancel same-day returns; office/admin can cancel any unverified return
            if request.user.is_sales_rep and return_created_date != today:
                messages.error(request, 'Sales reps can only cancel returns created today. Please contact office staff for older returns.')
                return redirect('sales:return_detail', pk=pk)
            
            # Check permissions: creator can cancel own returns, managers can cancel any
            if request.user.is_sales_rep and return_obj.created_by != request.user:
                messages.error(request, 'You do not have permission to cancel this return.')
                return redirect('sales:return_detail', pk=pk)
            
            # Check if return has been used for bill settlements (excluding auto-created return_adjustment settlements)
            from payments.models import SalesAccountSettlement
            non_adjustment_settlements = SalesAccountSettlement.objects.filter(
                return_ref=return_obj
            ).exclude(settlement_method='return_adjustment')
            
            if non_adjustment_settlements.exists():
                messages.error(request, 'Cannot delete return that has been used for bill settlements (cash/cheque/bank transfer).')
                return redirect('sales:return_detail', pk=pk)
            
            try:
                # Auto-cancel any return_adjustment settlements linked to this return
                adjustment_settlements = SalesAccountSettlement.objects.filter(
                    return_ref=return_obj,
                    settlement_method='return_adjustment'
                )
                
                cancelled_settlements = []
                for settlement in adjustment_settlements:
                    # Mark settlement as cancelled
                    settlement.settlement_status = 'cancelled'
                    settlement.notes = f"{settlement.notes or ''}\n[AUTO-CANCELLED] Return {return_obj.return_number} cancelled on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                    settlement.save()
                    cancelled_settlements.append(settlement.settlement_number)
                    
                    # Recalculate bill totals to reflect cancelled settlement
                    if settlement.bill:
                        # Use new method if available (after server restart), fallback to manual update
                        if hasattr(settlement.bill, 'calculate_payment_totals'):
                            settlement.bill.calculate_payment_totals()
                        else:
                            # Manual fallback for old server code
                            bill = settlement.bill
                            bill.paid_amount = sum(
                                s.amount for s in bill.settlements.filter(settlement_status='completed')
                            )
                            bill.balance_amount = bill.total_amount - bill.paid_amount
                            
                            # Update settlement status
                            if bill.paid_amount == 0:
                                bill.settlement_status = 'unsettled'
                            elif bill.paid_amount >= bill.total_amount:
                                bill.settlement_status = 'settled'
                            else:
                                bill.settlement_status = 'partial_settled'
                            
                            bill.save()
                
                # Get CPV number before cancelling
                cpv_number = return_obj.cash_receipt_number
                
                # Reverse FOC transactions for this return
                from products.models import FOCValueTransaction
                foc_transactions = FOCValueTransaction.objects.filter(
                    return_item__return_ref=return_obj,
                    is_archived=False
                )
                for foc_txn in foc_transactions:
                    foc_txn.is_archived = True
                    foc_txn.notes = f"{foc_txn.notes or ''}\n[CANCELLED] Return {return_obj.return_number} cancelled on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                    foc_txn.save()
                    # Update account balance
                    if hasattr(foc_txn, 'foc_account') and foc_txn.foc_account:
                        foc_txn.foc_account.update_balance()
                
                # Reverse stock movements and delete FIFO layers
                from products.models import StockMovement, FIFOCostLayer
                affected_products = []
                for item in return_obj.items.all():
                    product = item.product
                    total_returned = item.quantity + item.foc_quantity
                    
                    previous_qty = product.quantity_in_stock
                    product.quantity_in_stock -= total_returned
                    product.save()
                    
                    # Delete FIFO cost layer created by this return
                    FIFOCostLayer.objects.filter(
                        product=product,
                        layer_source='return',
                        reference_number=return_obj.return_number,
                    ).delete()
                    
                    # Create reversal stock movement record
                    cost_per_unit = product.cost_after_foc if product.cost_after_foc else Decimal('0')
                    StockMovement.objects.create(
                        product=product,
                        movement_type='adjustment',
                        quantity=-total_returned,
                        previous_quantity=previous_qty,
                        new_quantity=product.quantity_in_stock,
                        reference_number=return_obj.return_number,
                        notes=f"Return {return_obj.return_number} cancelled - Stock reversal",
                        unit_cost=cost_per_unit,
                        total_cost=cost_per_unit * total_returned,
                    )
                    
                    affected_products.append(product)
                
                # Cancel the return (soft delete - just change status)
                return_obj.settlement_status = 'cancelled'
                return_obj.applied_amount = 0  # Reset applied amount
                return_obj.notes = f"{return_obj.notes or ''}\n[CANCELLED] by {request.user.get_full_name()} on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                return_obj.save()  # This triggers post_save signal for commission reversal
                
                # Re-replay FIFO for affected products so consumed layers
                # are reassigned to the next available stock-in layers
                for product in affected_products:
                    FIFOCostLayer.replay_product_fifo(product)
                
                # Build success message
                success_msg = f'Return {return_obj.return_number} cancelled successfully. Stock reversed.'
                
                if cancelled_settlements:
                    success_msg += f' Settlements auto-cancelled: {", ".join(cancelled_settlements)}.'
                
                if cpv_number:
                    success_msg += f' CPV {cpv_number} auto-cancelled.'
                
                messages.success(request, success_msg)
                    
                return redirect('sales:return_detail', pk=pk)
            except Exception as e:
                messages.error(request, f'Error cancelling return: {str(e)}')
                return redirect('sales:return_detail', pk=pk)
        
        # UPDATE SETTLEMENT METHOD ACTION (unverified returns only)
        elif action == 'update_settlement_method':
            # Check if return can be updated
            if return_obj.is_verified:
                messages.error(request, 'Cannot update settlement method for verified returns.')
                return redirect('sales:return_detail', pk=pk)
            
            if return_obj.settlement_status == 'cancelled':
                messages.error(request, 'Cannot update settlement method for cancelled returns.')
                return redirect('sales:return_detail', pk=pk)
            
            if return_obj.settlement_status != 'unsettled':
                messages.error(request, 'Cannot update settlement method after payment has been processed.')
                return redirect('sales:return_detail', pk=pk)
            
            # Get new settlement method
            new_method = request.POST.get('settlement_method')
            valid_methods = ['cash', 'bill_adjustment']
            
            if new_method not in valid_methods:
                messages.error(request, 'Invalid settlement method selected.')
                return redirect('sales:return_detail', pk=pk)
            
            # Update settlement method
            old_method = return_obj.get_settlement_method_display()
            return_obj.settlement_method = new_method
            return_obj.save()
            
            new_method_display = return_obj.get_settlement_method_display()
            messages.success(request, f'Settlement method changed from "{old_method}" to "{new_method_display}"')
            return redirect('sales:return_detail', pk=pk)
        
        # VERIFY RETURN ACTION (managers only - verifies return at end of day, locks from changes)
        elif action == 'verify_return':
            # Permission check
            if request.user.is_sales_rep:
                messages.error(request, 'Only office staff/managers can verify returns.')
                return redirect('sales:return_detail', pk=pk)
            
            # Check if already verified
            if return_obj.is_verified:
                messages.warning(request, 'This return is already verified.')
                return redirect('sales:return_detail', pk=pk)
            
            try:
                # Mark as verified
                return_obj.is_verified = True
                return_obj.verified_by = request.user
                return_obj.verified_at = timezone.now()
                return_obj.save()
                
                messages.success(
                    request,
                    f'Return {return_obj.return_number} verified successfully. This return is now locked from changes.'
                )
                return redirect('sales:return_detail', pk=pk)
            except Exception as e:
                messages.error(request, f'Error verifying return: {str(e)}')
                return redirect('sales:return_detail', pk=pk)
        
        # SETTLE CASH ACTION (office staff - issue cash payment voucher if not already done)
        elif action == 'settle_cash':
            # Validate settlement method
            if return_obj.settlement_method != 'cash':
                messages.error(request, 'This return is not marked for cash settlement.')
                return redirect('sales:return_detail', pk=pk)
            
            # Check if already settled
            if return_obj.settlement_status == 'settled_cash' or return_obj.cash_receipt_number:
                messages.warning(request, 'Cash has already been paid for this return.')
                return redirect('sales:return_detail', pk=pk)
            
            try:
                # Generate cash payment voucher number (CPV)
                from utils.number_generator import generate_number
                cash_receipt_number = generate_number('CPV', Return, 'cash_receipt_number')
                
                # Mark as cash settled (return is already approved at creation)
                return_obj.settlement_status = 'settled_cash'
                return_obj.is_applied = True
                return_obj.applied_amount = return_obj.total_amount
                return_obj.cash_paid_by = request.user
                return_obj.cash_paid_at = timezone.now()
                return_obj.cash_receipt_number = cash_receipt_number
                return_obj.save()
                
                messages.success(
                    request,
                    f'Cash payment voucher {cash_receipt_number} issued for Rs. {return_obj.total_amount}'
                )
                
            except Exception as e:
                messages.error(request, f'Error processing cash payment: {str(e)}')
        
        # Reload page to show updated data
        return redirect('sales:return_detail', pk=pk)
    
    # GET request - display return details
    items = return_obj.items.all().select_related('product', 'product__category', 'product__company')
    
    # Get settlement applications (bills where this return was used)
    from payments.models import SalesAccountSettlement
    settlement_applications = SalesAccountSettlement.objects.filter(
        return_ref=return_obj
    ).select_related('bill', 'bill__shop').order_by('-settlement_date')
    
    # Group items by category (same pattern as bill_detail)
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
        
        # Add to appropriate list
        if item.quantity > 0:
            category_data['regular'].append({
                'name': item.product.product_name,
                'qty': int(item.quantity),
                'price': item.unit_price,
                'line_total': item.total_price
            })
            category_data['total_bottles'] += int(item.quantity)
            category_data['total_value'] += item.total_price
        
        if item.foc_quantity > 0:
            category_data['foc'].append({
                'name': item.product.product_name,
                'qty': int(item.foc_quantity)
            })
            category_data['foc_bottles'] += int(item.foc_quantity)
    
    # Calculate pack/loose breakdown
    for category_key, category_data in items_by_category.items():
        bottles_per_pack = category_data['bottles_per_pack']
        
        total_bottles = category_data['total_bottles']
        category_data['sales_packs'] = total_bottles // bottles_per_pack
        category_data['sales_loose'] = total_bottles % bottles_per_pack
        
        foc_bottles = category_data['foc_bottles']
        category_data['foc_packs'] = foc_bottles // bottles_per_pack
        category_data['foc_loose'] = foc_bottles % bottles_per_pack
        
        total_all_bottles = total_bottles + foc_bottles
        category_data['total_all_bottles'] = total_all_bottles
        category_data['total_packs'] = total_all_bottles // bottles_per_pack
        category_data['total_loose'] = total_all_bottles % bottles_per_pack
    
    items_by_category = OrderedDict(sorted(items_by_category.items()))
    
    # Calculate remaining amount for display
    remaining_amount = return_obj.total_amount - return_obj.applied_amount
    
    # Check if return is same-day (for sales rep cancel permission)
    import pytz
    local_tz = pytz.timezone(settings.TIME_ZONE)
    return_created_date = return_obj.return_date.astimezone(local_tz).date()
    today = timezone.now().astimezone(local_tz).date()
    is_same_day_return = (return_created_date == today)
    
    # Smart back button: detect where user came from
    from django.urls import reverse
    referrer = request.META.get('HTTP_REFERER', '')
    back_url = None
    back_label = 'Back'

    if '/shops/' in referrer and return_obj.shop:
        back_url = reverse('shops:detail', kwargs={'pk': return_obj.shop.pk})
        back_label = f'Back to {return_obj.shop.shop_name}'
    elif '/dashboard/' in referrer:
        back_url = reverse('dashboard:home')
        back_label = 'Back to Dashboard'
    elif '/sales/returns/' in referrer and '/sales/returns/' + str(pk) not in referrer:
        back_url = reverse('sales:return_list')
        back_label = 'Back to Returns'
    elif '/sales/' in referrer and '/sales/returns/' not in referrer:
        # Coming from a bill detail page
        back_url = referrer
        back_label = 'Back to Bill'
    else:
        back_url = reverse('sales:return_list')
        back_label = 'Back to Returns'

    context = {
        'return': return_obj,
        'items': items,
        'items_by_category': items_by_category,
        'settlement_applications': settlement_applications,
        'remaining_amount': remaining_amount,
        'is_same_day_return': is_same_day_return,
        'page_title': f'Return {return_obj.return_number}',
        'back_url': back_url,
        'back_label': back_label,
    }
    
    return render(request, 'sales/return_detail.html', context)


@login_required
def return_receipt_print(request, pk):
    """
    Unified receipt print for returns
    Pattern: Matches mobile_print pattern with UnifiedPrintEngine
    Handles BOTH cash receipts AND field receipts based on flags
    """
    from sales.print_engine import UnifiedPrintEngine
    
    return_obj = get_object_or_404(Return, pk=pk)
    
    # Check if cash payment voucher exists (regardless of approval status)
    if not return_obj.cash_receipt_number:
        messages.error(request, 'No cash payment voucher available for this return.')
        return redirect('sales:return_detail', pk=pk)
    
    # Check if voucher was cancelled (return was rejected after payment)
    if return_obj.settlement_status == 'cancelled':
        messages.warning(
            request,
            f'This voucher ({return_obj.cash_receipt_number}) has been CANCELLED because the return was rejected.'
        )
    
    receipt_type = 'return_cash'
    receipt_number = return_obj.cash_receipt_number
    receipt_title = 'Cash Payment Voucher'
    
    # Get items
    items = return_obj.items.all().select_related('product', 'product__company')
    
    # Use unified print engine (same pattern as bill system)
    engine = UnifiedPrintEngine(request.user, receipt_type=receipt_type)
    context = engine.get_print_context({
        'return': return_obj,
        'items': items,
        'receipt_number': receipt_number,
        'receipt_title': receipt_title,
    })
    
    # Add cache buster
    context['cache_buster'] = str(int(time.time()))
    
    response = render(request, 'sales/return_cash_receipt_mobile_print.html', context)
    # Aggressive no-cache headers
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


@login_required
def mobile_return_print(request, pk):
    """
    Mobile thermal print for returns - all settlement methods
    Pattern: Matches mobile_print pattern for bills
    Prints return acknowledgment receipt for customer
    """
    from sales.print_engine import UnifiedPrintEngine
    
    return_obj = get_object_or_404(Return, pk=pk)
    
    # Permission check
    if request.user.is_sales_rep and return_obj.created_by != request.user:
        messages.error(request, 'You do not have permission to print this return.')
        return redirect('sales:return_detail', pk=pk)
    
    # Get items
    items = return_obj.items.all().select_related('product', 'product__company')
    
    # Determine receipt type based on settlement method
    if return_obj.cash_receipt_number:
        receipt_type = 'return_cash'  # Cash payment voucher
        receipt_number = return_obj.cash_receipt_number
        receipt_title = 'Cash Payment Voucher'
    else:
        receipt_type = 'return_cash'  # Use same template, just different title
        receipt_number = return_obj.return_number
        receipt_title = 'Return Acknowledgment'
    
    # Use unified print engine (same pattern as bill system)
    engine = UnifiedPrintEngine(request.user, receipt_type=receipt_type)
    context = engine.get_print_context({
        'return': return_obj,
        'items': items,
        'receipt_number': receipt_number,
        'receipt_title': receipt_title,
        'is_mobile_print': True,  # Flag for mobile-specific layout
    })
    
    # Add cache buster
    context['cache_buster'] = str(int(time.time()))
    
    response = render(request, 'sales/mobile_return_print.html', context)
    # Aggressive no-cache headers
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


@login_required
def create_return_mobile(request):
    """
    Mobile-friendly create return for sales reps
    Pattern: Follows create_bill pattern
    """
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Prevent duplicate submissions via session token
                submission_token = request.POST.get('submission_token', '')
                session_token = request.session.pop('return_submission_token', None)
                if not submission_token or submission_token != session_token:
                    messages.warning(request, 'This return was already submitted. Please check return history.')
                    return redirect('sales:return_list')

                # Get form data
                shop_id = request.POST.get('shop')
                customer_name = request.POST.get('customer_name', '').strip()
                return_reason = request.POST.get('return_reason')
                settlement_method = request.POST.get('settlement_method', 'cash')  # Default to cash
                total_amount = request.POST.get('total_amount', 0)
                notes = request.POST.get('notes', '')
                sale_id = request.POST.get('sale_id')
                bill_id = request.POST.get('bill_id')
                
                # Validate: Either shop_id OR customer_name must be provided
                if not shop_id and not customer_name:
                    messages.error(request, 'Please select a shop or enter a customer name.')
                    return redirect('sales:create_return')
                
                if shop_id and customer_name:
                    messages.error(request, 'Please select either a shop OR enter a customer name, not both.')
                    return redirect('sales:create_return')
                
                # Get shop object if shop_id provided
                shop = None
                if shop_id:
                    shop = get_object_or_404(Shop, pk=shop_id)
                
                # Cash payment handling
                cash_given = request.POST.get('cash_given') == 'true'
                
                # Generate cash payment voucher (CPV) if cash given immediately
                cash_receipt_number = None
                if cash_given and settlement_method == 'cash':
                    from utils.number_generator import generate_number
                    cash_receipt_number = generate_number('CPV', Return, 'cash_receipt_number')
                
                # Create return - AUTO-PROCESSED (stock updated immediately)
                return_obj = Return.objects.create(
                    shop=shop,
                    customer_name=customer_name if customer_name else None,
                    created_by=request.user,
                    return_reason=return_reason,
                    settlement_method=settlement_method,
                    total_amount=Decimal(total_amount),
                    notes=notes,
                    sale_id=sale_id if sale_id else None,
                    bill_id=bill_id if bill_id else None,
                    cash_receipt_number=cash_receipt_number,
                    cash_paid_by=request.user if cash_given else None,
                    cash_paid_at=timezone.now() if cash_given else None,
                    # Set settlement status based on method and cash payment
                    settlement_status='settled_cash' if cash_given else (
                        'unsettled' if settlement_method == 'cash' else 'available'
                    )
                    # NOTE: is_verified=False by default - manager verifies at end of day
                )
                
                # Create return items
                items_data = json.loads(request.POST.get('items', '[]'))
                for item_data in items_data:
                    product = get_object_or_404(Product, pk=item_data['product_id'])
                    
                    ReturnItem.objects.create(
                        return_ref=return_obj,
                        product=product,
                        quantity=Decimal(item_data['quantity']),
                        foc_quantity=Decimal(item_data.get('foc_quantity', 0)),
                        unit_price=Decimal(item_data['unit_price'])
                    )
                
                # Calculate totals
                return_obj.calculate_totals()
                
                # UPDATE STOCK IMMEDIATELY (no waiting for approval)
                from products.models import StockMovement, FOCValueAccount, FOCValueTransaction, FIFOCostLayer
                from sales.models import BillItem
                for item in return_obj.items.all():
                    product = item.product
                    total_returned = item.quantity + item.foc_quantity
                    
                    # Store previous quantity before update
                    previous_qty = product.quantity_in_stock
                    product.quantity_in_stock += total_returned
                    product.save()
                    
                    # Create stock movement record
                    customer_label = return_obj.shop.shop_name if return_obj.shop else (return_obj.customer_name or "Unregistered Customer")
                    
                    # Determine cost per unit using best available source:
                    # 1. If bill linked → use BillItem's FIFO cost (most accurate)
                    # 2. Else → use FIFO weighted average from active layers
                    # 3. Fallback → use product.cost_after_foc
                    cost_per_unit = Decimal('0')
                    if return_obj.bill:
                        bill_item = BillItem.objects.filter(
                            bill=return_obj.bill, product=product
                        ).first()
                        if bill_item and bill_item.unit_cost and bill_item.unit_cost > 0:
                            cost_per_unit = bill_item.unit_cost
                    
                    if not cost_per_unit:
                        # FIFO weighted average from active layers
                        active_layers = FIFOCostLayer.objects.filter(
                            product=product, is_exhausted=False
                        ).order_by('created_at')
                        total_val = sum(l.unit_cost * l.remaining_quantity for l in active_layers)
                        total_qty = sum(l.remaining_quantity for l in active_layers)
                        if total_qty > 0:
                            cost_per_unit = total_val / total_qty
                    
                    if not cost_per_unit:
                        cost_per_unit = product.cost_after_foc if product.cost_after_foc else Decimal('0')
                    StockMovement.objects.create(
                        product=product,
                        movement_type='return',
                        quantity=total_returned,
                        previous_quantity=previous_qty,
                        new_quantity=product.quantity_in_stock,
                        reference_number=return_obj.return_number,
                        notes=f"Return from {customer_label}",
                        unit_cost=cost_per_unit,
                        total_cost=cost_per_unit * total_returned,
                    )
                    
                    # Create FIFO cost layer for returned stock
                    from products.models import FIFOCostLayer
                    FIFOCostLayer.create_layer(
                        product=product,
                        qty=int(total_returned),
                        unit_cost=cost_per_unit,
                        source='return',
                        reference=return_obj.return_number,
                    )
                    
                    # Track FOC restoration (explicit and implicit)
                    if product.company:
                        # Get or create FOC account
                        foc_account, created = FOCValueAccount.objects.get_or_create(
                            company=product.company,
                            defaults={'created_by': request.user}
                        )
                        
                        # Track explicit FOC restoration
                        if item.foc_quantity > 0:
                            customer_label = return_obj.shop.shop_name if return_obj.shop else (return_obj.customer_name or "Unregistered Customer")
                            FOCValueTransaction.objects.create(
                                foc_account=foc_account,
                                transaction_type='return_foc_restored',
                                transaction_date=return_obj.return_date,
                                product=product,
                                foc_quantity=item.foc_quantity,
                                foc_value=item.foc_quantity * product.shop_price,
                                shop_price_at_time=product.shop_price,
                                reference_number=return_obj.return_number,
                                return_item=item,
                                shop=return_obj.shop,  # Can be None for unregistered
                                sales_rep=return_obj.created_by,
                                notes=f'Explicit FOC restored from return by {customer_label}',
                                created_by=request.user
                            )
                        
                        # Track implicit FOC restoration (discount restored)
                        if item.quantity > 0 and item.unit_price < product.shop_price:
                            implicit_foc_per_unit = product.shop_price - item.unit_price
                            implicit_foc_value = item.quantity * implicit_foc_per_unit
                            
                            FOCValueTransaction.objects.create(
                                foc_account=foc_account,
                                transaction_type='return_foc_restored',
                                transaction_date=return_obj.return_date,
                                product=product,
                                foc_quantity=item.quantity,
                                foc_value=implicit_foc_value,
                                shop_price_at_time=product.shop_price,
                                reference_number=return_obj.return_number,
                                return_item=item,
                                shop=return_obj.shop,  # Can be None for unregistered
                                sales_rep=return_obj.created_by,
                                notes=f'Implicit FOC restored - sold at Rs.{item.unit_price} (shop_price: Rs.{product.shop_price})',
                                created_by=request.user
                            )
                
                if cash_given and cash_receipt_number:
                    messages.success(
                        request,
                        f'Return {return_obj.return_number} created. Cash voucher {cash_receipt_number} issued. Stock updated.'
                    )
                else:
                    messages.success(
                        request,
                        f'Return {return_obj.return_number} created. Stock updated.'
                    )
                
                # Auto-mark shop visit (if nearby)
                if return_obj.shop:
                    try:
                        from shops.visit_utils import auto_mark_visit
                        auto_mark_visit(return_obj.shop, request.user, 'auto_return', return_obj.return_number)
                    except Exception:
                        pass  # Never block return for visit tracking
                
                return redirect('sales:return_detail', pk=return_obj.pk)
                
        except Exception as e:
            messages.error(request, f'Error creating return: {str(e)}')
            return redirect('sales:create_return')
    
    # GET request
    if request.user.is_sales_rep:
        # Only show shops where sales rep has Level 2+ access (can do activities)
        all_shops = Shop.objects.filter(is_active=True).order_by('shop_name')
        shops = []
        for shop in all_shops:
            if ShopAccess.get_rep_access_level(shop, request.user) >= 2:
                shops.append(shop)
    else:
        shops = Shop.objects.filter(is_active=True).order_by('shop_name')
    
    # Get all products grouped by size AND marked_price (same pattern as create_bill)
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
    
    # Get preselected shop from query parameter
    preselected_shop_id = request.GET.get('shop')
    
    # Generate one-time submission token to prevent double-submit
    submission_token = str(uuid.uuid4())
    request.session['return_submission_token'] = submission_token

    context = {
        'shops': shops,
        'products_by_category': sorted_categories,
        'page_title': 'Create Return',
        'preselected_shop_id': preselected_shop_id,
        'submission_token': submission_token,
    }
    
    return render(request, 'sales/create_return_mobile.html', context)


@login_required
def get_return_id_by_number(request, return_number):
    """
    API endpoint to get return ID from return number
    Used by commission dashboard to create clickable return links
    """
    try:
        return_obj = Return.objects.get(return_number=return_number)
        return JsonResponse({'id': return_obj.id, 'return_number': return_obj.return_number})
    except Return.DoesNotExist:
        return JsonResponse({'error': 'Return not found'}, status=404)
