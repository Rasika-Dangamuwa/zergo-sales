from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal, InvalidOperation

from .models import (
    Return, Bill, CommissionSettings, 
    CommissionRateHistory, CommissionTransaction
)
from payments.models import OldPayment
from accounts.models import User


@login_required
def commission_dashboard(request):
    """
    Redirect to commission settings (new real-time system)
    Old monthly batch system removed - replaced by real-time CommissionTransaction tracking
    """
    messages.info(request, 'Commission system upgraded to real-time tracking. View settings below.')
    return redirect('sales:commission_settings')


# OLD commission_detail view removed - relied on CommissionRecord (deprecated)
# Use CommissionTransaction admin interface for detailed transaction history


# OLD generate_commission_records view removed - no longer needed with real-time tracking
# Commission transactions are created automatically via Django signals



    """
    World-Class Commission Dashboard
    - Sales reps: See only their own commission
    - Office/Admin: Can select any user to view/manage commission for payment
    - Auto-detects user role and shows appropriate interface
    """
    
    # Determine viewing permissions
    is_manager = request.user.is_office_staff
    
    # Get selected user (for managers) or current user (for sales reps)
    selected_user_id = request.GET.get('user_id')
    
    if is_manager and selected_user_id:
        # Manager viewing specific user's commission
        try:
            viewing_user = User.objects.get(id=selected_user_id)
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            viewing_user = request.user
    else:
        # Sales rep viewing own commission, or manager with no selection
        viewing_user = request.user
    
    # Get all users who have made sales (for manager dropdown)
    users_with_sales = []
    if is_manager:
        # Get distinct users who have bills
        users_with_sales = User.objects.filter(
            old_sales__isnull=False
        ).distinct().order_by('first_name', 'last_name', 'username')
    
    # Get date range filter
    year = request.GET.get('year', timezone.now().year)
    month = request.GET.get('month', None)
    
    # Base query for viewing user's commissions
    commissions = CommissionRecord.objects.filter(sales_rep=viewing_user)
    
    # Filter by year/month if provided
    if month:
        month_str = f"{year}-{str(month).zfill(2)}"
        commissions = commissions.filter(month=month_str)
    else:
        commissions = commissions.filter(month__startswith=str(year))
    
    # Order by month descending
    commissions = commissions.order_by('-month')
    
    # Calculate summary statistics
    total_collected = commissions.aggregate(total=Sum('collected_amount'))['total'] or Decimal('0')
    total_returns = commissions.aggregate(total=Sum('returns_amount'))['total'] or Decimal('0')
    total_write_offs = commissions.aggregate(total=Sum('write_offs_amount'))['total'] or Decimal('0')
    total_commission = commissions.aggregate(total=Sum('commission_amount'))['total'] or Decimal('0')
    pending_commission = commissions.filter(settlement_status='unsettled').aggregate(total=Sum('commission_amount'))['total'] or Decimal('0')
    paid_commission = commissions.filter(settlement_status='settled').aggregate(total=Sum('commission_amount'))['total'] or Decimal('0')
    
    # Get current month data for quick stats
    current_month_str = timezone.now().strftime('%Y-%m')
    current_month_record = commissions.filter(month=current_month_str).first()
    
    # Get recent payments eligible for commission
    recent_payments = OldPayment.objects.filter(
        bill__sales_rep=viewing_user,
        status='completed'
    ).select_related('bill', 'bill__shop').order_by('-payment_date')[:10]
    
    # Years for filter dropdown
    years = list(range(timezone.now().year, timezone.now().year - 5, -1))
    months = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    
    context = {
        'commissions': commissions,
        'total_collected': total_collected,
        'total_returns': total_returns,
        'total_write_offs': total_write_offs,
        'total_commission': total_commission,
        'pending_commission': pending_commission,
        'paid_commission': paid_commission,
        'current_month_record': current_month_record,
        'recent_payments': recent_payments,
        'selected_year': int(year),
        'selected_month': int(month) if month else None,
        'years': years,
        'months': months,
        # New world-class features
        'is_manager': is_manager,
        'viewing_user': viewing_user,
        'users_with_sales': users_with_sales,
        'selected_user_id': int(selected_user_id) if selected_user_id else None,
    }
    
    return render(request, 'sales/commission_dashboard.html', context)


@login_required
def commission_detail(request, month):
    """
    Detailed commission breakdown for a specific month
    - Sales reps: Can only view their own
    - Office/Admin: Can view any user's commission
    """
    
    # Ensure month is in YYYY-MM format (max 7 characters)
    try:
        # Try to parse the month to validate format
        month_date = datetime.strptime(month, '%Y-%m')
        # Convert back to ensure correct format
        month = month_date.strftime('%Y-%m')
    except ValueError:
        # If format is invalid, try to fix it or redirect
        messages.error(request, f'Invalid month format: {month}. Expected YYYY-MM format.')
        return redirect('sales:commission_dashboard')
    
    # Determine viewing permissions
    is_manager = request.user.is_office_staff
    
    # Get selected user (for managers) or current user (for sales reps)
    selected_user_id = request.GET.get('user_id')
    
    if is_manager and selected_user_id:
        try:
            viewing_user = User.objects.get(id=selected_user_id)
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('sales:commission_dashboard')
    else:
        viewing_user = request.user
    
    # Get or create commission record for this month
    commission_record, created = CommissionRecord.objects.get_or_create(
        month=month,
        sales_rep=viewing_user,
        defaults={'commission_rate': Decimal('5.00')}
    )
    
    # Recalculate if requested
    if request.GET.get('recalculate') == 'true':
        commission_record.calculate_commission()
        messages.success(request, f'Commission recalculated for {month}')
        redirect_url = f'sales:commission_detail'
        if is_manager and selected_user_id:
            return redirect(f'{redirect_url}?user_id={selected_user_id}', month=month)
        return redirect(redirect_url, month=month)
    
    # Get all payments for this month
    # Filter by payment_date month since OldPayment doesn't have commission_month
    month_start = datetime.strptime(month, '%Y-%m')
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1, day=1)
    
    payments = OldPayment.objects.filter(
        bill__sales_rep=viewing_user,
        payment_date__gte=month_start,
        payment_date__lt=month_end,
        status='completed'
    ).select_related('bill', 'bill__shop', 'bill__sales_rep').order_by('-payment_date')
    
    # Get all returns for this month
    returns = Return.objects.filter(
        created_by=viewing_user,
        commission_month=month
    ).select_related('sale', 'sale__shop', 'bill', 'bill__shop', 'shop').order_by('-created_at')
    
    # Get all bad debt write-offs for this month
    from payments.models import BadDebtWriteOff
    write_offs = BadDebtWriteOff.objects.filter(
        bill__sales_rep=viewing_user,
        executed=True,
        executed_at__gte=month_start,
        executed_at__lt=month_end
    ).select_related('bill', 'shop', 'requested_by').order_by('-executed_at')
    
    # Get bills in this month  
    bills = Bill.objects.filter(
        sales_rep=viewing_user,
        bill_date__gte=month_start,
        bill_date__lt=month_end,
        bill_status='confirmed'
    ).select_related('shop').order_by('-bill_date')
    
    # Calculate totals
    total_bills_amount = bills.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_payments_amount = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_returns_amount = returns.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_write_offs_amount = write_offs.aggregate(total=Sum('write_off_amount'))['total'] or Decimal('0')
    
    # Payment breakdown by method
    payment_breakdown = payments.values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    context = {
        'commission_record': commission_record,
        'month': month,
        'month_display': datetime.strptime(month, '%Y-%m').strftime('%B %Y'),
        'payments': payments,
        'returns': returns,
        'write_offs': write_offs,
        'bills': bills,
        'total_bills_amount': total_bills_amount,
        'total_payments_amount': total_payments_amount,
        'total_returns_amount': total_returns_amount,
        'total_write_offs_amount': total_write_offs_amount,
        'payment_breakdown': payment_breakdown,
        'is_manager': is_manager,
        'viewing_user': viewing_user,
        'selected_user_id': viewing_user.id,
    }
    
    return render(request, 'sales/commission_detail.html', context)


@login_required
def generate_commission_records(request):
    """Generate commission records for all users who made sales for a specific month"""
    
    # Only office/admin can generate
    if not request.user.is_office_staff:
        messages.error(request, 'Only office staff and administrators can generate commission records.')
        return redirect('sales:commission_dashboard')
    
    if request.method == 'POST':
        month = request.POST.get('month')
        
        if not month:
            messages.error(request, 'Please select a month')
            return redirect('sales:commission_dashboard')
        
        # Get all users who have made sales (have bills assigned to them)
        users_with_sales = User.objects.filter(
            old_sales__isnull=False
        ).distinct()
        
        created_count = 0
        updated_count = 0
        
        for user in users_with_sales:
            record, created = CommissionRecord.objects.get_or_create(
                month=month,
                sales_rep=user,
                defaults={'commission_rate': Decimal('5.00')}
            )
            
            # Recalculate commission
            record.calculate_commission()
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        messages.success(request, f'Generated {created_count} new records and updated {updated_count} existing records for {month}')
        return redirect('dashboard:office')
    
    return redirect('dashboard:office')


@login_required
def commission_settings(request):
    """
    World-Class Commission Settings Management
    - Default commission rate
    - Historical rate tracking with effective dates
    - Real-time commission calculations
    """
    
    # Only managers can access
    if not request.user.is_office_staff:
        messages.error(request, 'Access denied. Only managers can access commission settings.')
        return redirect('sales:commission_dashboard')
    
    # Get or create settings
    settings = CommissionSettings.get_settings()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_default_rate':
            # Update default commission rate
            default_rate = request.POST.get('default_commission_rate')
            
            if default_rate:
                try:
                    rate = Decimal(default_rate)
                    if rate < 0 or rate > 100:
                        messages.error(request, 'Commission rate must be between 0 and 100')
                    else:
                        # Save to database
                        settings.default_commission_rate = rate
                        settings.updated_by = request.user
                        settings.save()
                        messages.success(request, f'Default commission rate updated to {rate}%')
                except (ValueError, InvalidOperation):
                    messages.error(request, 'Invalid commission rate')
        
        elif action == 'add_rate_history':
            # Add new rate with effective date
            new_rate = request.POST.get('new_rate')
            effective_from_str = request.POST.get('effective_from')
            notes = request.POST.get('notes', '')
            
            if new_rate and effective_from_str:
                try:
                    rate = Decimal(new_rate)
                    effective_from = datetime.strptime(effective_from_str, '%Y-%m-%d').date()
                    
                    if rate < 0 or rate > 100:
                        messages.error(request, 'Commission rate must be between 0 and 100')
                    elif effective_from < date.today():
                        messages.error(request, 'Effective date cannot be in the past')
                    else:
                        # Create new rate history
                        CommissionRateHistory.set_new_rate(
                            rate=rate,
                            effective_from=effective_from,
                            created_by=request.user,
                            notes=notes
                        )
                        
                        # Update default rate to match
                        settings.default_commission_rate = rate
                        settings.updated_by = request.user
                        settings.save()
                        
                        messages.success(
                            request, 
                            f'New commission rate {rate}% will be effective from {effective_from.strftime("%d %b %Y")}'
                        )
                except (ValueError, InvalidOperation) as e:
                    messages.error(request, f'Invalid input: {e}')
        
        return redirect('sales:commission_settings')
    
    # Get rate history
    rate_history = CommissionRateHistory.objects.all()[:20]  # Last 20 rates
    current_rate_obj = CommissionRateHistory.objects.filter(is_active=True).first()
    
    # Get real-time commission statistics
    today = date.today()
    this_month_start = date(today.year, today.month, 1)
    
    month_transactions = CommissionTransaction.objects.filter(
        transaction_date__gte=this_month_start
    )
    
    # Calculate month totals
    month_total_commission = month_transactions.aggregate(
        total=Sum('commission_earned')
    )['total'] or Decimal('0.00')
    
    month_payments = month_transactions.filter(
        transaction_type='payment_received'
    ).aggregate(total=Sum('collected_amount'))['total'] or Decimal('0.00')
    
    month_returns = month_transactions.filter(
        transaction_type='return_processed'
    ).aggregate(total=Sum('return_amount'))['total'] or Decimal('0.00')
    
    # Get current settings and statistics
    context = {
        'default_commission_rate': settings.default_commission_rate,
        'total_users_with_commission': User.objects.filter(old_sales__isnull=False).distinct().count(),
        'total_commission_records': CommissionRecord.objects.count(),
        'pending_commission_count': CommissionRecord.objects.filter(settlement_status='unsettled').count(),
        'paid_commission_count': CommissionRecord.objects.filter(settlement_status='settled').count(),
        'last_updated': settings.updated_at,
        'updated_by': settings.updated_by,
        
        # Rate History
        'rate_history': rate_history,
        'current_rate_obj': current_rate_obj,
        'current_active_rate': current_rate_obj.rate if current_rate_obj else settings.default_commission_rate,
        
        # Real-time Statistics
        'month_total_commission': month_total_commission,
        'month_payments': month_payments,
        'month_returns': month_returns,
        'month_transaction_count': month_transactions.count(),
        'today': today,
    }
    
    return render(request, 'sales/commission_settings.html', context)
