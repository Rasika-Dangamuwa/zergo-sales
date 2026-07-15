from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from collections import defaultdict
import csv

from .models import (
    CommissionRateHistory, 
    CommissionTransaction,
    Bill,
    Return,
    CommissionPayoutSchedule,
    CommissionPayoutHistory,
    UserCommissionPayout
)
from accounts.models import User
from accounts.tenant_utils import get_tenant_users
from payments.models import SalesAccountSettlement


@login_required
def commission_dashboard(request):
    """
    Sales Rep Commission Dashboard - Enhanced World-Class View
    Shows commission earnings, transactions, and analytics
    """
    # Get selected user (sales rep sees only themselves, office can select)
    if request.user.is_sales_rep:
        selected_user = request.user
    else:
        # Office/Admin can select any user (anyone can make sales)
        user_id = request.GET.get('user')
        if user_id:
            selected_user = get_object_or_404(User, id=user_id, is_active=True)
        else:
            # Default to first active user with commission transactions
            selected_user = get_tenant_users().filter(
                is_active=True,
                commission_transactions__isnull=False
            ).distinct().first()
            
            if not selected_user:
                # If no users with commissions, default to any active user
                selected_user = get_tenant_users().filter(is_active=True).first()
            
            if not selected_user:
                messages.warning(request, 'No active users found')
                return redirect('sales:commission_settings')
    
    # Get date filters
    today = timezone.localdate()
    month_filter = request.GET.get('month', f"{today.year}-{today.month:02d}")
    
    try:
        year, month = map(int, month_filter.split('-'))
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month + 1, 1)
    except (ValueError, AttributeError):
        # Default to current month
        month_start = date(today.year, today.month, 1)
        if today.month == 12:
            month_end = date(today.year + 1, 1, 1)
        else:
            month_end = date(today.year, today.month + 1, 1)
        month_filter = f"{today.year}-{today.month:02d}"
    
    # Convert to timezone-aware datetimes for DateTimeField queries
    month_start_dt = timezone.make_aware(datetime.combine(month_start, datetime.min.time()))
    month_end_dt = timezone.make_aware(datetime.combine(month_end, datetime.min.time()))
    
    # Get commission transactions for selected month - EXCLUDE WRITE-OFFS (tracking only, no commission impact)
    month_transactions = CommissionTransaction.objects.filter(
        sales_rep=selected_user,
        transaction_date__gte=month_start_dt,
        transaction_date__lt=month_end_dt
    ).exclude(
        transaction_type='writeoff_executed'
    ).select_related('bill', 'settlement', 'bill__shop').order_by('-transaction_date', '-id')
    
    # Calculate statistics (exclude payout adjustments from historical earnings)
    total_commission = month_transactions.exclude(
        transaction_type='adjustment',
        commission_earned__lt=0
    ).aggregate(
        total=Sum('commission_earned')
    )['total'] or Decimal('0.00')
    
    # Total Sales - from ACTUAL bills (bill_created commission txns may not exist)
    month_bills = Bill.objects.filter(
        sales_rep=selected_user,
        bill_date__gte=month_start_dt,
        bill_date__lt=month_end_dt,
        bill_status='confirmed'
    )
    bills_count = month_bills.count()
    total_sales = month_bills.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # Total Returns - exclude cancelled returns (their stock/commission was already reversed)
    month_returns = Return.objects.filter(
        created_by=selected_user,
        return_date__gte=month_start_dt,
        return_date__lt=month_end_dt
    ).exclude(settlement_status='cancelled')
    returns_count = month_returns.count()
    total_returns = month_returns.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    payments_received = month_transactions.filter(transaction_type='payment_received')
    total_collected = payments_received.aggregate(total=Sum('collected_amount'))['total'] or Decimal('0.00')
    # Commission earned from collections only
    collection_commission = payments_received.aggregate(total=Sum('commission_earned'))['total'] or Decimal('0.00')
    payments_count = payments_received.count()
    
    # Payment cancellations in this month
    payments_cancelled = month_transactions.filter(transaction_type='payment_cancelled')
    total_cancelled = payments_cancelled.aggregate(total=Sum('collected_amount'))['total'] or Decimal('0.00')
    cancelled_commission = payments_cancelled.aggregate(total=Sum('commission_earned'))['total'] or Decimal('0.00')
    cancelled_count = payments_cancelled.count()
    
    # Net collections = received - cancelled
    net_collected = total_collected - abs(total_cancelled)
    net_collection_commission = collection_commission + cancelled_commission  # cancelled_commission is negative
    
    # Return commission deductions (from commission transactions)
    returns_processed = month_transactions.filter(transaction_type='return_processed')
    return_commission = returns_processed.aggregate(total=Sum('commission_earned'))['total'] or Decimal('0.00')
    
    # Return cancellations: when a return is cancelled, previously-deducted commission is credited back
    returns_cancelled_txns = month_transactions.filter(transaction_type='return_cancelled')
    return_cancelled_commission = returns_cancelled_txns.aggregate(total=Sum('commission_earned'))['total'] or Decimal('0.00')
    
    # Net return commission impact = deductions + credits back (deduction is negative, credit is positive)
    net_return_commission = return_commission + return_cancelled_commission
    
    writeoffs = month_transactions.filter(transaction_type='writeoff_executed')
    writeoffs_count = writeoffs.count()
    
    # Payouts (negative adjustments = commission disbursed to money account)
    payout_txns = month_transactions.filter(transaction_type='adjustment', commission_earned__lt=0)
    total_payouts = abs(payout_txns.aggregate(total=Sum('commission_earned'))['total'] or Decimal('0.00'))
    payouts_count = payout_txns.count()
    
    # Get current balance (all-time)
    current_balance = CommissionTransaction.get_rep_balance(selected_user)
    
    # Get opening balance for selected month (balance at end of previous month)
    opening_balance = CommissionTransaction.get_rep_balance(
        selected_user, 
        as_of_date=month_start_dt - timedelta(seconds=1)
    )
    
    # Closing balance = actual balance at end of selected month (includes payouts/adjustments)
    closing_balance = CommissionTransaction.get_rep_balance(
        selected_user,
        as_of_date=month_end_dt - timedelta(seconds=1)
    )
    
    # Get previous month for comparison
    if month_start.month == 1:
        prev_month_start = date(month_start.year - 1, 12, 1)
        prev_month_end = month_start
    else:
        prev_month_start = date(month_start.year, month_start.month - 1, 1)
        prev_month_end = month_start
    
    prev_start_dt = timezone.make_aware(datetime.combine(prev_month_start, datetime.min.time()))
    prev_end_dt = timezone.make_aware(datetime.combine(prev_month_end, datetime.min.time()))
    
    prev_month_commission = CommissionTransaction.objects.filter(
        sales_rep=selected_user,
        transaction_date__gte=prev_start_dt,
        transaction_date__lt=prev_end_dt
    ).exclude(
        transaction_type='adjustment',
        commission_earned__lt=0
    ).aggregate(total=Sum('commission_earned'))['total'] or Decimal('0.00')
    
    # Calculate percentage change
    if prev_month_commission > 0:
        commission_change_pct = ((total_commission - prev_month_commission) / prev_month_commission) * 100
    else:
        commission_change_pct = 100 if total_commission > 0 else 0
    
    # Prepare chart data - daily commission for the month (exclude payout adjustments)
    # Use local date (not UTC) so transactions near midnight land on the correct day
    transactions_by_date = defaultdict(lambda: Decimal('0.00'))
    for txn in month_transactions.exclude(transaction_type='adjustment', commission_earned__lt=0):
        txn_date = timezone.localtime(txn.transaction_date).date()
        transactions_by_date[txn_date] += txn.commission_earned
    
    chart_dates = []
    chart_commission = []
    
    current_date = month_start
    while current_date < month_end and current_date <= today:
        chart_dates.append(current_date.strftime('%d %b'))
        chart_commission.append(float(transactions_by_date.get(current_date, Decimal('0.00'))))
        current_date += timedelta(days=1)
    
    # Get transaction type breakdown
    type_breakdown = {}
    for txn_type, txn_label in CommissionTransaction.TRANSACTION_TYPE_CHOICES:
        count = month_transactions.filter(transaction_type=txn_type).count()
        if count > 0:
            type_breakdown[txn_label] = count
    
    # Get current commission rate
    current_rate = CommissionRateHistory.get_current_rate()
    
    # Get all users for dropdown (office/admin only) - anyone can make sales
    if request.user.is_office_staff:
        all_sales_reps = get_tenant_users().filter(
            is_active=True
        ).order_by('first_name', 'last_name')
    else:
        all_sales_reps = []
    
    # Generate month options for dropdown (last 12 months)
    month_options = []
    for i in range(12):
        opt_date = today.replace(day=1) - timedelta(days=i*30)
        month_options.append({
            'value': f"{opt_date.year}-{opt_date.month:02d}",
            'label': opt_date.strftime('%B %Y')
        })
    
    context = {
        'selected_user': selected_user,
        'selected_month': month_filter,
        'month_options': month_options,
        'all_sales_reps': all_sales_reps,
        
        # Summary Statistics
        'current_balance': current_balance,
        'opening_balance': opening_balance,
        'closing_balance': closing_balance,
        'total_commission': total_commission,
        'total_sales': total_sales,
        'total_collected': total_collected,
        'net_collected': net_collected,
        'collection_commission': collection_commission,
        'net_collection_commission': net_collection_commission,
        'total_returns': total_returns,
        'return_commission': return_commission,
        'net_return_commission': net_return_commission,
        'cancelled_count': cancelled_count,
        'total_payouts': total_payouts,
        'payouts_count': payouts_count,
        'bills_count': bills_count,
        'payments_count': payments_count,
        'returns_count': returns_count,
        'writeoffs_count': writeoffs_count,
        
        # Comparison
        'prev_month_commission': prev_month_commission,
        'commission_change_pct': commission_change_pct,
        
        # Transactions
        'transactions': month_transactions[:100],  # Limit to 100 for performance
        'total_transactions': month_transactions.count(),
        
        # Charts
        'chart_dates': chart_dates,
        'chart_commission': chart_commission,
        
        # Breakdown
        'type_breakdown': type_breakdown,
        
        # Settings
        'current_rate': current_rate,
    }
    
    return render(request, 'sales/commission_dashboard.html', context)


@login_required
def commission_detail(request, month):
    """
    Redirect to commission settings
    Old monthly batch system removed - use CommissionTransaction admin interface
    """
    messages.info(request, 'Commission detail view removed. Use Admin interface to view CommissionTransaction history.')
    return redirect('sales:commission_settings')


@login_required
def generate_commission_records(request):
    """
    No longer needed - commission transactions created automatically via signals
    """
    messages.info(request, 'Commission generation is now automatic. No manual generation needed!')
    return redirect('sales:commission_settings')


@login_required
def commission_settings(request):
    """
    World-Class Commission Settings Management
    - Default commission rate
    - Historical rate tracking with effective dates
    - Real-time commission calculations
    - Automated payout scheduling
    """
    
    # Only managers can access
    if not request.user.is_office_staff:
        messages.error(request, 'Access denied. Only managers can access commission settings.')
        return redirect('dashboard:sales_rep')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_rate_history':
            # Add new rate with effective date
            new_rate = request.POST.get('new_rate')
            effective_from_str = request.POST.get('effective_from')
            notes = request.POST.get('notes', '')
            
            if new_rate and effective_from_str:
                try:
                    from django.utils import timezone
                    import pytz
                    from zergo_sales import settings
                    
                    rate = Decimal(new_rate)
                    # Parse as date and convert to datetime at current time with milliseconds
                    effective_date = datetime.strptime(effective_from_str, '%Y-%m-%d').date()
                    
                    # Get current time with milliseconds in local timezone
                    local_tz = pytz.timezone(settings.TIME_ZONE)
                    now_local = timezone.now().astimezone(local_tz)
                    
                    # Combine date with current time (preserving milliseconds)
                    effective_from = local_tz.localize(
                        datetime.combine(effective_date, now_local.time())
                    )
                    
                    if rate < 0 or rate > 100:
                        messages.error(request, 'Commission rate must be between 0 and 100')
                    elif effective_date < date.today():
                        messages.error(request, 'Effective date cannot be in the past')
                    else:
                        # Create new rate history
                        CommissionRateHistory.set_new_rate(
                            rate=rate,
                            effective_from=effective_from,
                            created_by=request.user,
                            notes=notes
                        )
                        
                        messages.success(
                            request, 
                            f'New commission rate {rate}% will be effective from {effective_from.strftime("%d %b %Y %H:%M:%S")}'
                        )
                except (ValueError, InvalidOperation) as e:
                    messages.error(request, f'Invalid input: {e}')
        
        elif action == 'configure_payout_schedule':
            # Configure automated payout schedule
            frequency = request.POST.get('frequency')
            payout_day = request.POST.get('payout_day_of_month')
            payout_time_str = request.POST.get('payout_time')
            minimum_amount = request.POST.get('minimum_payout_amount')
            # Checkbox sends 'on' when checked, None when unchecked
            is_active = request.POST.get('is_active') == 'on'
            
            try:
                # Parse payout_time first to ensure it's valid
                from datetime import datetime, time
                if payout_time_str:
                    payout_time = datetime.strptime(payout_time_str, '%H:%M').time()
                else:
                    payout_time = time(9, 0)  # Default to 9 AM
                
                # Get or create schedule (only one active schedule allowed)
                schedule, created = CommissionPayoutSchedule.objects.get_or_create(
                    defaults={
                        'frequency': frequency or 'monthly',
                        'payout_time': payout_time,
                        'created_by': request.user
                    }
                )
                
                # Update settings
                schedule.frequency = frequency or 'monthly'
                schedule.payout_day_of_month = int(payout_day) if payout_day else 1
                schedule.payout_time = payout_time
                schedule.minimum_payout_amount = Decimal(minimum_amount) if minimum_amount else Decimal('0.00')
                schedule.is_active = is_active
                
                # Calculate next run date AFTER all fields are set
                schedule.next_run_date = schedule.calculate_next_run_date()
                schedule.save()
                
                messages.success(
                    request,
                    f'Payout schedule {"activated" if is_active else "deactivated"}. Next run: {schedule.next_run_date.strftime("%d %b %Y at %I:%M %p")}'
                )
            except Exception as e:
                messages.error(request, f'Error configuring schedule: {str(e)}')
        
        return redirect('sales:commission_settings')
    
    # Get rate history
    rate_history = CommissionRateHistory.objects.all()[:20]  # Last 20 rates
    current_rate_obj = CommissionRateHistory.objects.filter(is_active=True).first()
    
    # Get payout schedule
    payout_schedule = CommissionPayoutSchedule.objects.first()
    
    # Get payout history
    payout_history = CommissionPayoutHistory.objects.all()[:10]
    
    # Get real-time commission statistics
    today = date.today()
    this_month_start = date(today.year, today.month, 1)
    
    month_transactions = CommissionTransaction.objects.filter(
        transaction_date__gte=this_month_start
    )
    
    # Calculate month totals (exclude payout adjustments from earnings - historical data)
    month_total_commission = month_transactions.exclude(
        transaction_type='adjustment',
        commission_earned__lt=0  # Exclude negative adjustments (payouts)
    ).aggregate(
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
        'default_commission_rate': current_rate_obj.rate if current_rate_obj else Decimal('5.00'),
        'last_updated': current_rate_obj.created_at if current_rate_obj else None,
        'updated_by': current_rate_obj.created_by if current_rate_obj else None,
        
        # Rate History
        'rate_history': rate_history,
        'current_rate_obj': current_rate_obj,
        'current_active_rate': current_rate_obj.rate if current_rate_obj else Decimal('5.00'),
        
        # Payout Schedule
        'payout_schedule': payout_schedule,
        'payout_history': payout_history,
        
        # Real-time Statistics
        'month_total_commission': month_total_commission,
        'month_payments': month_payments,
        'month_returns': month_returns,
        'month_transaction_count': month_transactions.count(),
        'today': today,
    }
    
    return render(request, 'sales/commission_settings.html', context)


@login_required
def export_commission_csv(request):
    """
    Export commission transactions to CSV
    Access: Sales reps can export their own, office/admin can export any user
    """
    # Get filters
    user_id = request.GET.get('user')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    transaction_type = request.GET.get('type')
    
    # Determine which user's data to export
    if request.user.is_sales_rep:
        if user_id and int(user_id) != request.user.id:
            messages.error(request, 'You can only export your own commission data')
            return redirect('sales:commission_dashboard')
        selected_user = request.user
    else:
        if user_id:
            selected_user = get_object_or_404(User, id=user_id, user_type='sales_rep')
        else:
            # Export all sales reps
            selected_user = None
    
    # Build query
    transactions = CommissionTransaction.objects.all().select_related('sales_rep', 'bill')
    
    if selected_user:
        transactions = transactions.filter(sales_rep=selected_user)
    
    if from_date:
        try:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            transactions = transactions.filter(transaction_date__date__gte=from_date_obj)
        except ValueError:
            pass
    
    if to_date:
        try:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            transactions = transactions.filter(transaction_date__date__lte=to_date_obj)
        except ValueError:
            pass
    
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    # Order by date
    transactions = transactions.order_by('-transaction_date')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f"commission_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    # Write headers
    writer.writerow([
        'Date',
        'Sales Rep',
        'Transaction Type',
        'Bill Number',
        'Sales Amount',
        'Collected Amount',
        'Return Amount',
        'Rate %',
        'Commission Earned',
        'Running Balance',
        'Notes'
    ])
    
    # Write data
    for txn in transactions:
        writer.writerow([
            txn.transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
            txn.sales_rep.get_full_name(),
            txn.get_transaction_type_display(),
            txn.bill.bill_number if txn.bill else '-',
            f"{txn.sales_amount:.2f}",
            f"{txn.collected_amount:.2f}",
            f"{txn.return_amount:.2f}",
            f"{txn.applicable_rate:.2f}",
            f"{txn.commission_earned:.2f}",
            f"{txn.running_balance:.2f}",
            txn.notes or ''
        ])
    
    return response


@login_required  
def export_commission_pdf(request):
    """
    Export commission statement as PDF
    Requires ReportLab library
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        messages.error(request, 'PDF export requires ReportLab library. Please contact administrator.')
        return redirect('sales:commission_dashboard')
    
    # Get filters
    user_id = request.GET.get('user')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Determine user
    if request.user.is_sales_rep:
        selected_user = request.user
    else:
        if user_id:
            selected_user = get_object_or_404(User, id=user_id, user_type='sales_rep')
        else:
            messages.error(request, 'Please select a sales representative')
            return redirect('sales:commission_dashboard')
    
    # Build query
    transactions = CommissionTransaction.objects.filter(
        sales_rep=selected_user
    ).select_related('bill').order_by('-transaction_date')
    
    if from_date:
        try:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            transactions = transactions.filter(transaction_date__date__gte=from_date_obj)
        except ValueError:
            from_date_obj = None
    else:
        from_date_obj = None
    
    if to_date:
        try:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            transactions = transactions.filter(transaction_date__date__lte=to_date_obj)
        except ValueError:
            to_date_obj = None
    else:
        to_date_obj = None
    
    # Create PDF response
    response = HttpResponse(content_type='application/pdf')
    filename = f"commission_statement_{selected_user.username}_{timezone.now().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Create PDF document
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    elements.append(Paragraph('Commission Statement', title_style))
    elements.append(Spacer(1, 12))
    
    # Sales rep info
    info_data = [
        ['Sales Representative:', selected_user.get_full_name()],
        ['Employee ID:', selected_user.employee_id or 'N/A'],
        ['Period:', f"{from_date_obj or 'Start'} to {to_date_obj or 'Now'}"],
        ['Generated:', timezone.now().strftime('%d %B %Y at %H:%M')],
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Summary statistics
    total_commission = transactions.aggregate(total=Sum('commission_earned'))['total'] or Decimal('0.00')
    total_collected = transactions.filter(transaction_type='payment_received').aggregate(
        total=Sum('collected_amount')
    )['total'] or Decimal('0.00')
    total_returns = transactions.filter(transaction_type='return_processed').aggregate(
        total=Sum('return_amount')
    )['total'] or Decimal('0.00')
    
    current_balance = CommissionTransaction.get_rep_balance(selected_user)
    
    summary_data = [
        ['Summary', ''],
        ['Total Commission Earned:', f"Rs. {total_commission:,.2f}"],
        ['Total Payments Collected:', f"Rs. {total_collected:,.2f}"],
        ['Total Returns:', f"Rs. {total_returns:,.2f}"],
        ['Current Balance:', f"Rs. {current_balance:,.2f}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Transaction details
    elements.append(Paragraph('Transaction Details', styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    # Transactions table
    txn_data = [['Date', 'Type', 'Bill #', 'Amount', 'Rate', 'Commission', 'Balance']]
    
    for txn in transactions[:100]:  # Limit to 100 transactions for PDF size
        txn_data.append([
            txn.transaction_date.strftime('%d/%m/%Y'),
            txn.get_transaction_type_display()[:15],
            txn.bill.bill_number[:12] if txn.bill else '-',
            f"{txn.collected_amount or txn.sales_amount or txn.return_amount:.2f}",
            f"{txn.applicable_rate:.1f}%",
            f"{txn.commission_earned:.2f}",
            f"{txn.running_balance:.2f}",
        ])
    
    txn_table = Table(txn_data, colWidths=[
        0.9*inch, 1.2*inch, 1*inch, 0.9*inch, 0.6*inch, 0.9*inch, 1*inch
    ])
    
    txn_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
    ]))
    
    elements.append(txn_table)
    
    # Build PDF
    doc.build(elements)
    
    return response
