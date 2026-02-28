from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, models
from django.utils import timezone
from django.db.models import Sum, Q, Count
from django.urls import reverse
from decimal import Decimal
from .models import SalesAccountSettlement, SettlementAttachment
from shops.models import Shop
from sales.models import Bill


@login_required
def payment_list(request):
    """World-class settlement list with advanced features"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.http import HttpResponse
    import csv
    from datetime import datetime, timedelta
    
    # Base queryset with permissions
    if request.user.is_sales_rep:
        settlements = SalesAccountSettlement.objects.filter(received_by=request.user).select_related('shop', 'bill', 'received_by', 'verified_by')
    else:
        settlements = SalesAccountSettlement.objects.all().select_related('shop', 'bill', 'received_by', 'verified_by')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        settlements = settlements.filter(
            Q(settlement_number__icontains=search_query) |
            Q(shop__shop_name__icontains=search_query) |
            Q(bill__bill_number__icontains=search_query) |
            Q(reference_number__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # Filter by shop
    shop_id = request.GET.get('shop')
    if shop_id:
        settlements = settlements.filter(shop_id=shop_id)
    
    # Filter by settlement method
    method = request.GET.get('method')
    if method:
        settlements = settlements.filter(settlement_method=method)
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        settlements = settlements.filter(settlement_status=status)
    
    # Filter by date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        settlements = settlements.filter(settlement_date__gte=date_from)
    if date_to:
        settlements = settlements.filter(settlement_date__lte=date_to + ' 23:59:59')
    
    # Quick date filters
    quick_filter = request.GET.get('quick_date')
    today = timezone.localdate()
    if quick_filter == 'today':
        settlements = settlements.filter(settlement_date__date=today)
    elif quick_filter == 'yesterday':
        yesterday = today - timedelta(days=1)
        settlements = settlements.filter(settlement_date__date=yesterday)
    elif quick_filter == 'this_week':
        week_start = today - timedelta(days=today.weekday())
        settlements = settlements.filter(settlement_date__date__gte=week_start)
    elif quick_filter == 'this_month':
        settlements = settlements.filter(settlement_date__year=today.year, settlement_date__month=today.month)
    elif quick_filter == 'last_month':
        last_month = today.replace(day=1) - timedelta(days=1)
        settlements = settlements.filter(settlement_date__year=last_month.year, settlement_date__month=last_month.month)
    
    # Sorting
    sort_by = request.GET.get('sort', '-settlement_date')
    if sort_by:
        settlements = settlements.order_by(sort_by)
    
    # Calculate comprehensive statistics (before pagination)
    all_stats = settlements.aggregate(
        total_amount=Sum('amount'),
        total_count=Count('id'),
        pending_count=Count('id', filter=Q(settlement_status='pending')),
        completed_count=Count('id', filter=Q(settlement_status='completed')),
        bounced_count=Count('id', filter=Q(settlement_status='bounced')),
        cancelled_count=Count('id', filter=Q(settlement_status='cancelled')),
        pending_amount=Sum('amount', filter=Q(settlement_status='pending')),
        completed_amount=Sum('amount', filter=Q(settlement_status='completed')),
        bounced_amount=Sum('amount', filter=Q(settlement_status='bounced')),
        cancelled_amount=Sum('amount', filter=Q(settlement_status='cancelled')),
        cash_amount=Sum('amount', filter=Q(settlement_method='cash')),
        cheque_amount=Sum('amount', filter=Q(settlement_method='cheque')),
        transfer_amount=Sum('amount', filter=Q(settlement_method='bank_transfer')),
    )
    
    # Method breakdown
    method_stats = list(settlements.values('settlement_method').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total'))
    
    # Status breakdown
    status_stats = list(settlements.values('settlement_status').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total'))
    
    # Export to CSV
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="settlements_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Settlement Number', 'Date', 'Shop', 'Bill Number', 'Method', 'Status', 'Amount', 'Reference', 'Received By', 'Verified By'])
        
        for settlement in settlements:
            writer.writerow([
                settlement.settlement_number,
                timezone.localtime(settlement.settlement_date).strftime('%Y-%m-%d %H:%M') if settlement.settlement_date else '',
                settlement.shop.shop_name if settlement.shop else 'N/A',
                settlement.bill.bill_number if settlement.bill else 'N/A',
                settlement.get_settlement_method_display(),
                settlement.get_settlement_status_display(),
                float(settlement.amount),
                settlement.reference_number or '',
                settlement.received_by.get_full_name() if settlement.received_by else 'System',
                settlement.verified_by.get_full_name() if settlement.verified_by else ''
            ])
        
        return response
    
    # Pagination
    per_page = request.GET.get('per_page', '20')
    try:
        per_page = int(per_page)
        if per_page not in [10, 20, 50, 100]:
            per_page = 20
    except ValueError:
        per_page = 20
    
    paginator = Paginator(settlements, per_page)
    page = request.GET.get('page', 1)
    
    try:
        settlements_page = paginator.page(page)
    except PageNotAnInteger:
        settlements_page = paginator.page(1)
    except EmptyPage:
        settlements_page = paginator.page(paginator.num_pages)
    
    # Get all shops for filter dropdown
    if request.user.is_sales_rep:
        shops = Shop.objects.filter(settlements__received_by=request.user).distinct().order_by('shop_name')
    else:
        shops = Shop.objects.filter(settlements__isnull=False).distinct().order_by('shop_name')
    
    context = {
        'settlements': settlements_page,
        'stats': all_stats,
        'method_stats': method_stats,
        'status_stats': status_stats,
        'shops': shops,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': settlements_page,
    }
    
    return render(request, 'payments/payment_list.html', context)


@login_required
def add_payment(request):
    """Add a new payment"""
    # Implementation placeholder
    messages.info(request, 'Payment addition feature - use sales bill payment instead')
    return redirect('sales:list')


@login_required
def payment_detail(request, pk):
    """View settlement details"""
    settlement = get_object_or_404(SalesAccountSettlement, pk=pk)
    
    # Smart back button: detect where user came from with enhanced logic
    referrer = request.META.get('HTTP_REFERER', '')
    back_url = None
    back_label = 'Back'
    
    # Priority 1: Check if coming from pending settlements
    if 'settlements/pending' in referrer or 'payments/pending' in referrer:
        back_url = reverse('sales:pending')
        back_label = 'Back to Pending Settlements'
    
    # Priority 2: Check if coming from write-off pages
    elif 'write-off' in referrer or 'write_off' in referrer:
        back_url = reverse('sales:write_off_list')
        back_label = 'Back to Write-Offs'
    
    # Priority 3: Check if coming from settlement list (not the detail page itself)
    elif ('settlements/' in referrer or 'payments/' in referrer) and '/settlements/' + str(pk) not in referrer:
        back_url = reverse('sales:settlement_list')
        back_label = 'Back to Settlements'
    
    # Priority 4: Check if coming from shop detail page
    elif '/shops/' in referrer and 'shop' in referrer.lower():
        if settlement.shop:
            back_url = reverse('shops:detail', kwargs={'pk': settlement.shop.pk})
            back_label = f'Back to {settlement.shop.shop_name}'
        else:
            back_url = reverse('shops:list')
            back_label = 'Back to Shops'
    
    # Priority 5: Check if coming from dashboard/reports
    elif '/dashboard/' in referrer:
        # Check specific dashboard pages
        if 'payment-report' in referrer or 'payment_report' in referrer:
            back_url = reverse('dashboard:payment_report')
            back_label = 'Back to Payment Report'
        elif 'commission' in referrer:
            back_url = reverse('dashboard:home')
            back_label = 'Back to Dashboard'
        else:
            back_url = reverse('dashboard:home')
            back_label = 'Back to Dashboard'
    
    # Priority 6: Check if coming from bill detail or bill summary
    elif '/sales/' in referrer and settlement.bill:
        # Check if coming from bill summary or bill detail
        if 'summary' in referrer:
            back_url = reverse('sales:bill_summary', kwargs={'pk': settlement.bill.pk})
            back_label = f'Back to Bill {settlement.bill.bill_number} Summary'
        else:
            back_url = reverse('sales:detail', kwargs={'pk': settlement.bill.pk})
            back_label = f'Back to Bill {settlement.bill.bill_number}'
    
    # Priority 7: Check if coming from any sales page
    elif '/sales/' in referrer:
        if settlement.bill:
            back_url = reverse('sales:detail', kwargs={'pk': settlement.bill.pk})
            back_label = f'Back to Bill {settlement.bill.bill_number}'
        else:
            back_url = reverse('sales:list')
            back_label = 'Back to Sales'
    
    # Default fallback
    else:
        back_url = reverse('sales:settlement_list')
        back_label = 'Back to Settlements'
    
    context = {
        'settlement': settlement,
        'back_url': back_url,
        'back_label': back_label,
    }
    return render(request, 'payments/payment_detail.html', context)


@login_required
@transaction.atomic
def cancel_payment(request, pk):
    """
    Cancel a settlement - Sales rep can cancel their own settlements (same day only), Office/Admin can cancel any
    """
    settlement = get_object_or_404(SalesAccountSettlement, pk=pk)
    
    # Permission check
    if request.user.is_sales_rep:
        # Sales rep can only cancel their own settlements
        if settlement.received_by != request.user:
            messages.error(request, 'You can only cancel your own settlements.')
            return redirect('sales:settlement_detail', pk=settlement.pk)
        
        # Sales rep can only cancel same-day settlements
        from django.utils.timezone import now
        settlement_date = settlement.settlement_date.date()
        today = now().date()
        if settlement_date != today:
            messages.error(request, 'You can only cancel settlements made today. Please contact office staff for older settlements.')
            return redirect('sales:settlement_detail', pk=settlement.pk)
    # Office and Admin can cancel any settlement
    
    # Check if settlement can be cancelled
    if settlement.settlement_status == 'cancelled':
        messages.warning(request, 'This settlement is already cancelled.')
        return redirect('sales:settlement_detail', pk=settlement.pk)
    
    # Check if settlement is linked to a return adjustment (cannot cancel)
    if settlement.settlement_method == 'return_adjustment' and settlement.return_ref:
        messages.error(request, 'Cannot cancel return adjustment settlements. Please cancel the return instead.')
        return redirect('sales:settlement_detail', pk=settlement.pk)
    
    if request.method == 'POST':
        # Get cancellation reason
        cancellation_reason = request.POST.get('cancellation_reason', '').strip()
        
        # Store old status for logging
        old_status = settlement.settlement_status
        old_bill_balance = settlement.bill.balance_amount if settlement.bill else None
        
        # Cancel the settlement
        settlement.settlement_status = 'cancelled'
        
        # Add cancellation note
        if cancellation_reason:
            if settlement.notes:
                settlement.notes += f"\n\n[CANCELLED] {timezone.now().strftime('%Y-%m-%d %H:%M')} by {request.user.get_full_name()}: {cancellation_reason}"
            else:
                settlement.notes = f"[CANCELLED] {timezone.now().strftime('%Y-%m-%d %H:%M')} by {request.user.get_full_name()}: {cancellation_reason}"
        else:
            if settlement.notes:
                settlement.notes += f"\n\n[CANCELLED] {timezone.now().strftime('%Y-%m-%d %H:%M')} by {request.user.get_full_name()}"
            else:
                settlement.notes = f"[CANCELLED] {timezone.now().strftime('%Y-%m-%d %H:%M')} by {request.user.get_full_name()}"
        
        settlement.save()
        
        # Recalculate bill totals if settlement was linked to a bill
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
            
            new_bill_balance = settlement.bill.balance_amount
            
            messages.success(
                request, 
                f'Settlement {settlement.settlement_number} cancelled successfully. '
                f'Bill {settlement.bill.bill_number} balance updated from Rs. {old_bill_balance:,.2f} to Rs. {new_bill_balance:,.2f}'
            )
        else:
            messages.success(request, f'Settlement {settlement.settlement_number} cancelled successfully.')
        
        return redirect('sales:settlement_detail', pk=settlement.pk)
    
    # Calculate what will happen
    context = {
        'settlement': settlement,
    }
    
    # Calculate bill impact if applicable
    if settlement.bill:
        # Only include non-cancelled settlements in calculation
        other_settlements = settlement.bill.settlements.exclude(pk=settlement.pk).exclude(settlement_status='cancelled')
        new_paid_amount = sum(s.amount for s in other_settlements)
        new_balance = settlement.bill.total_amount - new_paid_amount
        
        context['current_bill_balance'] = settlement.bill.balance_amount
        context['new_bill_balance'] = new_balance
        context['balance_increase'] = new_balance - settlement.bill.balance_amount
    
    return render(request, 'payments/cancel_payment.html', context)


@login_required
def verify_payment(request, pk):
    """Redirect to payment detail - use specific verification methods instead"""
    settlement = get_object_or_404(SalesAccountSettlement, pk=pk)
    
    # Determine which specific action to use based on payment method
    if settlement.settlement_method == 'cheque':
        messages.info(request, 'Please use "Clear Cheque" button to verify cheque payments.')
    elif settlement.settlement_method == 'bank_transfer':
        messages.info(request, 'Please use "Confirm Bank Transfer" button to verify bank transfer payments.')
    elif settlement.settlement_method == 'cash':
        messages.info(request, 'Cash payments are automatically verified.')
    else:
        messages.info(request, 'Please use the appropriate verification method for this payment type.')
    
    return redirect('sales:settlement_detail', pk=settlement.pk)


@login_required
def pending_payments(request):
    """List pending settlements"""
    settlements = SalesAccountSettlement.objects.filter(settlement_status='pending').select_related('shop', 'bill', 'received_by').order_by('-settlement_date')
    
    # Calculate statistics
    stats = settlements.aggregate(
        total_amount=Sum('amount'),
        total_count=Count('id')
    )
    
    context = {
        'settlements': settlements,
        'stats': stats,
    }
    
    return render(request, 'payments/pending_payments.html', context)


@login_required
@transaction.atomic
def clear_cheque(request, pk):
    """Mark cheque settlement as cleared (Office only)"""
    # Office/Admin only
    if request.user.is_sales_rep:
        messages.error(request, 'Access denied. Only office staff can clear cheques.')
        return redirect('sales:settlement_detail', pk=pk)
    
    settlement = get_object_or_404(SalesAccountSettlement, pk=pk)
    
    # Validate settlement method
    if settlement.settlement_method != 'cheque':
        messages.error(request, 'This action is only for cheque settlements.')
        return redirect('sales:settlement_detail', pk=pk)
    
    # Validate status
    if settlement.settlement_status != 'pending':
        messages.warning(request, f'Cheque is already {settlement.get_settlement_status_display()}.')
        return redirect('sales:settlement_detail', pk=pk)
    
    if request.method == 'POST':
        cleared_date = request.POST.get('cleared_date')
        
        # Update settlement status
        settlement.settlement_status = 'completed'
        settlement.verified_by = request.user
        settlement.verified_at = timezone.now()
        
        if cleared_date:
            settlement.notes = (settlement.notes or '') + f"\nCleared on {cleared_date} by {request.user.get_full_name()}"
        else:
            settlement.notes = (settlement.notes or '') + f"\nCleared by {request.user.get_full_name()} on {timezone.now().strftime('%Y-%m-%d')}"
        
        settlement.save()
        
        # Recalculate bill totals from all settlements (prevents double-counting)
        if settlement.bill:
            settlement.bill.calculate_totals()
        
        messages.success(request, f'Cheque {settlement.reference_number} marked as cleared! Bill amount updated.')
        return redirect('sales:settlement_detail', pk=pk)
    
    # Calculate what will happen for preview
    new_paid_amount = settlement.bill.paid_amount + settlement.amount if settlement.bill else 0
    new_balance = settlement.bill.total_amount - new_paid_amount if settlement.bill else 0
    
    context = {
        'settlement': settlement,
        'today': timezone.localdate(),
        'new_paid_amount': new_paid_amount,
        'new_balance': new_balance,
    }
    return render(request, 'payments/clear_cheque.html', context)


@login_required
@transaction.atomic
def bounce_cheque(request, pk):
    """Mark cheque settlement as bounced (Office only)"""
    # Office/Admin only
    if request.user.is_sales_rep:
        messages.error(request, 'Access denied. Only office staff can bounce cheques.')
        return redirect('sales:settlement_detail', pk=pk)
    
    settlement = get_object_or_404(SalesAccountSettlement, pk=pk)
    
    # Validate settlement method
    if settlement.settlement_method != 'cheque':
        messages.error(request, 'This action is only for cheque settlements.')
        return redirect('sales:settlement_detail', pk=pk)
    
    # Validate status
    if settlement.settlement_status != 'pending':
        messages.warning(request, f'Cheque is already {settlement.get_settlement_status_display()}.')
        return redirect('sales:settlement_detail', pk=pk)
    
    if request.method == 'POST':
        bounce_reason = request.POST.get('bounce_reason')
        
        # Update settlement status
        settlement.settlement_status = 'bounced'
        settlement.verified_by = request.user
        settlement.verified_at = timezone.now()
        
        # Add bounce reason to notes
        bounce_note = f"\nCheque bounced on {timezone.now().strftime('%Y-%m-%d')} by {request.user.get_full_name()}"
        if bounce_reason:
            bounce_note += f"\nReason: {bounce_reason}"
        settlement.notes = (settlement.notes or '') + bounce_note
        
        settlement.save()
        
        # DO NOT update bill amounts - settlement failed
        
        messages.warning(request, f'Cheque {settlement.reference_number} marked as bounced. Bill amounts NOT updated.')
        return redirect('sales:settlement_detail', pk=pk)
    
    context = {
        'settlement': settlement,
    }
    return render(request, 'payments/bounce_cheque.html', context)


@login_required
@transaction.atomic
def confirm_bank_transfer(request, pk):
    """Confirm bank transfer settlement (Office only)"""
    # Office/Admin only
    if request.user.is_sales_rep:
        messages.error(request, 'Access denied. Only office staff can confirm bank transfers.')
        return redirect('sales:settlement_detail', pk=pk)
    
    settlement = get_object_or_404(SalesAccountSettlement, pk=pk)
    
    # Validate settlement method
    if settlement.settlement_method != 'bank_transfer':
        messages.error(request, 'This action is only for bank transfer settlements.')
        return redirect('sales:settlement_detail', pk=pk)
    
    # Validate status
    if settlement.settlement_status != 'pending':
        messages.warning(request, f'Bank transfer is already {settlement.get_settlement_status_display()}.')
        return redirect('sales:settlement_detail', pk=pk)
    
    if request.method == 'POST':
        # Update settlement status
        settlement.settlement_status = 'completed'
        settlement.verified_by = request.user
        settlement.verified_at = timezone.now()
        settlement.notes = (settlement.notes or '') + f"\nBank transfer confirmed by {request.user.get_full_name()} on {timezone.now().strftime('%Y-%m-%d')}"
        settlement.save()
        
        # Recalculate bill totals from all settlements (prevents double-counting)
        if settlement.bill:
            settlement.bill.calculate_totals()
        
        messages.success(request, f'Bank transfer {settlement.reference_number} confirmed! Bill amount updated.')
        return redirect('sales:settlement_detail', pk=pk)
    
    # Calculate what will happen for preview
    new_paid_amount = settlement.bill.paid_amount + settlement.amount if settlement.bill else 0
    new_balance = settlement.bill.total_amount - new_paid_amount if settlement.bill else 0
    
    context = {
        'settlement': settlement,
        'new_paid_amount': new_paid_amount,
        'new_balance': new_balance,
    }
    return render(request, 'payments/confirm_bank_transfer.html', context)


@login_required
@transaction.atomic
def reject_bank_transfer(request, pk):
    """Reject/bounce bank transfer settlement (Office only)"""
    # Office/Admin only
    if request.user.is_sales_rep:
        messages.error(request, 'Access denied. Only office staff can reject bank transfers.')
        return redirect('sales:settlement_detail', pk=pk)
    
    settlement = get_object_or_404(SalesAccountSettlement, pk=pk)
    
    # Validate settlement method
    if settlement.settlement_method != 'bank_transfer':
        messages.error(request, 'This action is only for bank transfer settlements.')
        return redirect('sales:settlement_detail', pk=pk)
    
    # Validate status
    if settlement.settlement_status != 'pending':
        messages.warning(request, f'Bank transfer is already {settlement.get_settlement_status_display()}.')
        return redirect('sales:settlement_detail', pk=pk)
    
    if request.method == 'POST':
        reject_reason = request.POST.get('reject_reason')
        
        # Update settlement status
        settlement.settlement_status = 'bounced'
        settlement.verified_by = request.user
        settlement.verified_at = timezone.now()
        settlement.notes = (settlement.notes or '') + f"\nBank transfer rejected: {reject_reason}. Rejected by {request.user.get_full_name()} on {timezone.now().strftime('%Y-%m-%d')}"
        settlement.save()
        
        messages.warning(request, f'Bank transfer {settlement.reference_number} rejected. Settlement marked as bounced.')
        return redirect('sales:settlement_detail', pk=pk)
    
    context = {
        'settlement': settlement,
    }
    return render(request, 'payments/reject_bank_transfer.html', context)


# ========================================
# BAD DEBT WRITE-OFF SYSTEM
# ========================================

@login_required
def write_off_confirm(request, bill_pk):
    """
    Confirmation page for writing off bad debt
    Manager/Office only - Sales reps cannot write off
    """
    # Permission check - Only office/admin
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied. Only managers can write off bad debts.')
        return redirect('sales:detail', pk=bill_pk)
    
    bill = get_object_or_404(Bill, pk=bill_pk)
    
    # Validate bill can be written off
    if bill.balance_amount <= 0:
        messages.error(request, 'This bill has no outstanding balance to write off.')
        return redirect('sales:detail', pk=bill_pk)
    
    if bill.bill_status == 'cancelled':
        messages.error(request, 'Cannot write off cancelled bills.')
        return redirect('sales:detail', pk=bill_pk)
    
    # Check if already written off
    from .models import BadDebtWriteOff
    existing_write_off = BadDebtWriteOff.objects.filter(bill=bill, executed=True).first()
    if existing_write_off:
        messages.warning(request, f'This bill has already been written off: {existing_write_off.write_off_number}')
        return redirect('sales:write_off_detail', pk=existing_write_off.pk)
    
    # CRITICAL: Check for pending settlements that haven't been verified yet
    pending_settlements = bill.settlements.filter(settlement_status__in=['pending', 'pending_verification'])
    if pending_settlements.exists():
        total_pending = sum(s.amount for s in pending_settlements)
        messages.error(
            request,
            f'Cannot write off this bill. There are pending settlements totaling Rs. {total_pending:,.2f} that must be verified or cancelled first. '
            f'Please approve or reject these settlements before writing off the debt.'
        )
        return redirect('sales:detail', pk=bill_pk)
    
    # Calculate age of debt
    from django.utils import timezone
    days_overdue = (timezone.now() - bill.bill_date).days
    
    # Get settlement history
    settlements = bill.settlements.filter(settlement_status='completed').order_by('-settlement_date')
    
    # Calculate actual amounts (same logic as execution to show user accurate numbers)
    completed_settlements_total = bill.settlements.filter(
        settlement_status='completed'
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
    
    actual_balance = bill.total_amount - completed_settlements_total
    
    # Warning if bill amounts don't match settlements
    amount_mismatch = bill.paid_amount != completed_settlements_total or bill.balance_amount != actual_balance
    
    context = {
        'bill': bill,
        'days_overdue': days_overdue,
        'settlements': settlements,
        'actual_paid_amount': completed_settlements_total,
        'actual_balance_amount': actual_balance,
        'amount_mismatch': amount_mismatch,
    }
    return render(request, 'payments/write_off_confirm.html', context)


@login_required
@transaction.atomic
def write_off_execute(request, bill_pk):
    """
    Execute the bad debt write-off
    Manager/Office only
    """
    # Permission check
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied. Only managers can write off bad debts.')
        return redirect('sales:detail', pk=bill_pk)
    
    if request.method != 'POST':
        return redirect('sales:write_off_confirm', bill_pk=bill_pk)
    
    bill = get_object_or_404(Bill, pk=bill_pk)
    
    # Validate
    if bill.balance_amount <= 0:
        messages.error(request, 'This bill has no outstanding balance to write off.')
        return redirect('sales:detail', pk=bill_pk)
    
    # Check if already written off
    from .models import BadDebtWriteOff
    existing_write_off = BadDebtWriteOff.objects.filter(bill=bill, executed=True).first()
    if existing_write_off:
        messages.warning(request, f'This bill has already been written off: {existing_write_off.write_off_number}')
        return redirect('sales:write_off_detail', pk=existing_write_off.pk)
    
    # CRITICAL: Check for pending settlements that haven't been verified yet
    pending_settlements = bill.settlements.filter(settlement_status__in=['pending', 'pending_verification'])
    if pending_settlements.exists():
        total_pending = sum(s.amount for s in pending_settlements)
        messages.error(
            request,
            f'Cannot write off this bill. There are pending settlements totaling Rs. {total_pending:,.2f} that must be verified or cancelled first. '
            f'Approve or reject these settlements before writing off the debt.'
        )
        return redirect('sales:detail', pk=bill_pk)
    
    # Get form data
    reason = request.POST.get('reason')
    detailed_notes = request.POST.get('detailed_notes', '').strip()
    
    if not reason:
        messages.error(request, 'Please select a reason for the write-off.')
        return redirect('sales:write_off_confirm', bill_pk=bill_pk)
    
    if not detailed_notes:
        messages.error(request, 'Please provide detailed notes explaining the write-off.')
        return redirect('sales:write_off_confirm', bill_pk=bill_pk)
    
    try:
        # CRITICAL: Recalculate actual amounts from database (don't trust bill.paid_amount/balance_amount)
        # This prevents issues where bill fields are out of sync with settlements
        completed_settlements_total = bill.settlements.filter(
            settlement_status='completed'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        
        actual_balance = bill.total_amount - completed_settlements_total
        
        # Validation: Ensure we're writing off the correct amount
        if actual_balance <= 0:
            messages.error(
                request, 
                f'Cannot write off this bill. The actual balance is Rs. {actual_balance:,.2f} (Total: Rs. {bill.total_amount:,.2f}, Paid: Rs. {completed_settlements_total:,.2f}). '
                f'There is no outstanding debt to write off.'
            )
            return redirect('sales:detail', pk=bill_pk)
        
        # Double-check: If bill.paid_amount doesn't match settlements, warn but proceed
        if bill.paid_amount != completed_settlements_total:
            # Log the discrepancy in the write-off notes
            detailed_notes += f"\n\n[SYSTEM NOTE: Bill paid_amount (Rs. {bill.paid_amount:,.2f}) did not match completed settlements (Rs. {completed_settlements_total:,.2f}). Using actual settlement total for write-off calculation.]"
        
        # Create write-off record with ACTUAL calculated amounts
        write_off = BadDebtWriteOff.objects.create(
            bill=bill,
            shop=bill.shop,  # Can be None for unregistered customers
            customer_name=bill.customer_name,  # For unregistered customers
            original_amount=bill.total_amount,
            paid_amount=completed_settlements_total,  # Use ACTUAL completed settlements, not bill.paid_amount
            write_off_amount=actual_balance,  # Use ACTUAL calculated balance, not bill.balance_amount
            reason=reason,
            detailed_notes=detailed_notes,
            requested_by=request.user,
            approved_by=request.user,  # Auto-approve for managers
            approval_status='approved',
            approval_date=timezone.now(),
            executed=True,
            executed_at=timezone.now()
        )
        
        # Update bill - Add note, but keep status as confirmed (for audit trail)
        bill.notes = (bill.notes or '') + f"\n\n=== BAD DEBT WRITE-OFF ===\nWrite-Off Number: {write_off.write_off_number}\nDate: {timezone.now().strftime('%Y-%m-%d %H:%M')}\nAmount: Rs. {write_off.write_off_amount:,.2f}\nReason: {write_off.get_reason_display()}\nApproved by: {request.user.get_full_name()}\n========================"
        
        # Mark bill as fully settled (write-off counts as settlement for accounting purposes)
        bill.paid_amount = bill.total_amount
        bill.balance_amount = Decimal('0')
        bill.settlement_status = 'settled'
        bill.save()
        
        write_off.bill_updated = True
        
        # Update shop balance - Only if bill has a shop (skip for unregistered customers)
        if bill.shop:
            bill.shop.current_balance -= write_off.write_off_amount
            if bill.shop.current_balance < 0:
                bill.shop.current_balance = Decimal('0')  # Safety check
            bill.shop.notes = (bill.shop.notes or '') + f"\n\nBad debt write-off: Rs. {write_off.write_off_amount:,.2f} on {timezone.now().strftime('%Y-%m-%d')} ({write_off.write_off_number})"
            bill.shop.save()
            write_off.shop_balance_updated = True
        else:
            # Unregistered customer - no shop balance to update
            write_off.shop_balance_updated = False
        
        write_off.save()
        
        messages.success(
            request,
            f'Bad debt write-off completed successfully!\n'
            f'Write-Off Number: {write_off.write_off_number}\n'
            f'Amount: Rs. {write_off.write_off_amount:,.2f}\n'
            f'Bill {bill.bill_number} marked as fully settled.'
        )
        
        return redirect('sales:write_off_detail', pk=write_off.pk)
        
    except Exception as e:
        messages.error(request, f'Error creating write-off: {str(e)}')
        return redirect('sales:write_off_confirm', bill_pk=bill_pk)


@login_required
def write_off_detail(request, pk):
    """
    View write-off details
    Manager/Office only
    """
    # Permission check
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied. Only managers can view write-offs.')
        return redirect('sales:list')
    
    from .models import BadDebtWriteOff
    write_off = get_object_or_404(BadDebtWriteOff, pk=pk)
    
    context = {
        'write_off': write_off,
    }
    return render(request, 'payments/write_off_detail.html', context)


@login_required
def write_off_list(request):
    """
    List all bad debt write-offs
    Manager/Office only
    """
    # Permission check
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied. Only managers can view write-offs.')
        return redirect('sales:list')
    
    from .models import BadDebtWriteOff
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    # Base queryset
    write_offs = BadDebtWriteOff.objects.all().select_related(
        'bill', 'shop', 'requested_by', 'approved_by'
    ).order_by('-write_off_date')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        if status_filter == 'pending':
            write_offs = write_offs.filter(approval_status='pending')
        elif status_filter == 'approved':
            write_offs = write_offs.filter(approval_status='approved')
        elif status_filter == 'executed':
            write_offs = write_offs.filter(executed=True)
    
    # Filter by reason
    reason_filter = request.GET.get('reason')
    if reason_filter:
        write_offs = write_offs.filter(reason=reason_filter)
    
    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        write_offs = write_offs.filter(
            Q(write_off_number__icontains=search_query) |
            Q(shop__shop_name__icontains=search_query) |
            Q(bill__bill_number__icontains=search_query) |
            Q(detailed_notes__icontains=search_query)
        )
    
    # Calculate statistics
    stats = write_offs.aggregate(
        total_count=Count('id'),
        total_amount=Sum('write_off_amount'),
        executed_count=Count('id', filter=Q(executed=True)),
        executed_amount=Sum('write_off_amount', filter=Q(executed=True))
    )
    
    # Pagination
    per_page = 20
    paginator = Paginator(write_offs, per_page)
    page = request.GET.get('page', 1)
    
    try:
        write_offs_page = paginator.page(page)
    except PageNotAnInteger:
        write_offs_page = paginator.page(1)
    except EmptyPage:
        write_offs_page = paginator.page(paginator.num_pages)
    
    context = {
        'write_offs': write_offs_page,
        'stats': stats,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': write_offs_page,
    }
    return render(request, 'payments/write_off_list.html', context)


