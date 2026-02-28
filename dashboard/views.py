from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from sales.models import Bill
from payments.models import SalesAccountSettlement as Payment
from shops.models import Shop
from products.models import Product
from django.db import models


@login_required
def home(request):
    """Main dashboard hub — redirects sales reps to their dedicated dashboard"""
    # Sales reps always go to their dedicated dashboard
    if request.user.is_sales_rep:
        return redirect('dashboard:sales_rep')
    
    # Initialize context for admin/office
    context = {
        'user': request.user,
    }
    
    # Add statistics for office and admin users
    if request.user.user_type in ['admin', 'office']:
        from decimal import Decimal
        from sales.models import Return, ItemExchange
        from payments.models import SalesAccountSettlement
        from products.models import Purchase, PurchaseOrder, PurchaseReturn, ProductStatusAdjustment
        from accounts.money_account_models import AdvanceRequest
        
        today = timezone.localdate()
        
        # ===== TODAY'S SNAPSHOT =====
        today_bills = Bill.objects.filter(bill_date__date=today, bill_status='confirmed')
        today_sales_total = today_bills.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        today_returns = Return.objects.filter(return_date__date=today).exclude(settlement_status='cancelled')
        today_returns_total = today_returns.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        today_payments = SalesAccountSettlement.objects.filter(
            settlement_date__date=today
        ).exclude(settlement_status='cancelled')
        today_collections = today_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # ===== RECEIVABLES SUMMARY =====
        unsettled_bills = Bill.objects.filter(
            bill_status='confirmed',
            settlement_status__in=['unsettled', 'partial_settled']
        )
        unsettled_bills_count = unsettled_bills.count()
        total_receivable = unsettled_bills.aggregate(t=Sum('balance_amount'))['t'] or Decimal('0')
        
        # ===== DETAILED PENDING WORK LISTS =====
        
        # 1a. Uncollected Cheques — rep hasn't handed over the physical cheque yet
        uncollected_cheques = SalesAccountSettlement.objects.filter(
            settlement_method='cheque',
            settlement_status='pending',
            cheque_collected=False,
        ).select_related('shop', 'bill', 'received_by').order_by('cheque_date', 'settlement_date')
        
        # 1b. Collected Cheques — in hand, awaiting bank clearing (sorted by cheque_date)
        collected_pending_cheques = SalesAccountSettlement.objects.filter(
            settlement_method='cheque',
            settlement_status='pending',
            cheque_collected=True,
        ).select_related('shop', 'bill', 'received_by', 'collected_by').order_by('cheque_date', 'settlement_date')
        
        # 2. Pending Bank Transfers — awaiting confirmation
        pending_bank_transfers = SalesAccountSettlement.objects.filter(
            settlement_method='bank_transfer',
            settlement_status='pending'
        ).select_related('shop', 'bill', 'received_by').order_by('-settlement_date')
        
        # 3. Returns Needing Verification
        unverified_returns = Return.objects.filter(
            is_verified=False
        ).exclude(
            settlement_status='cancelled'
        ).select_related('shop', 'created_by', 'bill').order_by('-return_date')
        
        # 4. Unsettled Returns — cash refund pending
        unsettled_returns = Return.objects.filter(
            settlement_status='unsettled'
        ).select_related('shop', 'created_by').order_by('-return_date')
        
        # 5. Pending Status Adjustments — awaiting approval
        pending_adjustments = ProductStatusAdjustment.objects.filter(
            approval_status='pending'
        ).select_related('adjusted_by').prefetch_related('items__product').order_by('-adjustment_date')
        
        # 6. Pending Advance Requests (tenant-scoped: accounts is shared app)
        from accounts.tenant_utils import get_tenant_filter
        pending_advances = AdvanceRequest.objects.filter(
            status='pending', **get_tenant_filter('user__tenant')
        ).select_related('user').order_by('-request_date')
        
        # 7. Pending Exchanges — awaiting approval
        pending_exchanges = ItemExchange.objects.filter(
            exchange_status='pending'
        ).select_related('shop', 'created_by').order_by('-exchange_date')
        
        # 9. Pending Purchase Returns
        pending_purchase_returns = PurchaseReturn.objects.filter(
            status__in=['pending', 'sent_to_supplier', 'company_approved']
        ).select_related('company', 'purchase', 'created_by').order_by('-return_date')
        
        # 10. Stock alerts
        low_stock = Product.objects.filter(
            is_active=True,
            quantity_in_stock__gt=0,
            quantity_in_stock__lte=F('minimum_stock_level')
        ).order_by('quantity_in_stock')[:10]
        low_stock_count = Product.objects.filter(
            is_active=True,
            quantity_in_stock__lte=F('minimum_stock_level')
        ).count()
        out_of_stock = Product.objects.filter(
            is_active=True, quantity_in_stock__lte=0
        ).order_by('product_name')[:10]
        out_of_stock_count = out_of_stock.count()
        
        # 12. Draft POs / Ordered POs awaiting delivery
        draft_pos = PurchaseOrder.objects.filter(status='draft').order_by('-created_at')[:5]
        ordered_pos = PurchaseOrder.objects.filter(status='ordered').order_by('-created_at')[:5]
        
        # 13. Draft GRNs / Unpaid GRNs
        draft_grns = Purchase.objects.filter(status='draft').select_related('company').order_by('-grn_date')[:5]
        unpaid_grns = Purchase.objects.filter(
            status='received', payment_status__in=['unpaid', 'partially_paid']
        ).select_related('company').order_by('-grn_date')[:10]
        
        # ===== SECTION COUNTS for tab badges =====
        section_counts = {
            'uncollected_cheques': uncollected_cheques.count(),
            'collected_cheques': collected_pending_cheques.count(),
            'bank_transfers': pending_bank_transfers.count(),
            'unverified_returns': unverified_returns.count(),
            'unsettled_returns': unsettled_returns.count(),
            'adjustments': pending_adjustments.count(),
            'advances': pending_advances.count(),
            'exchanges': pending_exchanges.count(),
            'purchase_returns': pending_purchase_returns.count(),
            'low_stock': low_stock_count,
            'out_of_stock': out_of_stock_count,
        }
        total_pending = sum(section_counts.values())
        
        # Count critical vs other
        critical_count = section_counts['out_of_stock']
        high_count = (section_counts['unverified_returns'] + section_counts['unsettled_returns']
                      + section_counts['adjustments'] + section_counts['advances'])
        
        context.update({
            # Today's snapshot
            'today_bills_count': today_bills.count(),
            'today_sales_total': today_sales_total,
            'today_returns_count': today_returns.count(),
            'today_returns_total': today_returns_total,
            'today_collections': today_collections,
            'today': today,
            # Key metrics
            'total_receivable': total_receivable,
            'unsettled_bills_count': unsettled_bills_count,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            # Actual lists
            'uncollected_cheques': uncollected_cheques,
            'collected_pending_cheques': collected_pending_cheques,
            'pending_bank_transfers': pending_bank_transfers,
            'unverified_returns': unverified_returns,
            'unsettled_returns': unsettled_returns,
            'pending_adjustments': pending_adjustments,
            'pending_advances': pending_advances,
            'pending_exchanges': pending_exchanges,
            'pending_purchase_returns': pending_purchase_returns,
            'low_stock_products': low_stock,
            'out_of_stock_products': out_of_stock,
            'draft_pos': draft_pos,
            'ordered_pos': ordered_pos,
            'draft_grns': draft_grns,
            'unpaid_grns': unpaid_grns,
            # Section counts
            'section_counts': section_counts,
            'total_pending': total_pending,
            'critical_count': critical_count,
            'high_count': high_count,
        })
    
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def sales_rep_dashboard(request):
    """World-class sales rep dashboard with comprehensive field data"""
    if not request.user.is_sales_rep:
        return redirect('dashboard:office')
    
    from decimal import Decimal
    from sales.models import Return, ItemExchange, CommissionTransaction
    from shops.models import ShopVisit, ShopAccess
    from accounts.money_account_models import UserMoneyAccount
    
    user = request.user
    today = timezone.localdate()
    now = timezone.now()
    week_ago = today - timedelta(days=7)
    month_start = today.replace(day=1)
    yesterday = today - timedelta(days=1)
    
    # ===== MY SHOPS =====
    all_shops = Shop.objects.filter(is_active=True)
    # Shops with access level 2+ (assigned or granted)
    access_grants = ShopAccess.objects.filter(
        sales_rep=user, is_active=True, access_level__gte=2
    ).values_list('shop_id', flat=True)
    assigned_shops = all_shops.filter(
        Q(assigned_sales_rep=user) | Q(pk__in=access_grants)
    ).distinct()
    total_my_shops = assigned_shops.count()
    
    # ===== TODAY'S VISITS =====
    today_visits = ShopVisit.objects.filter(
        sales_rep=user, visit_date__date=today
    )
    today_visit_count = today_visits.count()
    visited_shop_ids = list(today_visits.values_list('shop_id', flat=True))
    
    # ===== TODAY'S SALES =====
    my_bills = Bill.objects.filter(sales_rep=user, bill_status='confirmed')
    today_bills = my_bills.filter(bill_date__date=today)
    today_sales_total = today_bills.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    today_bills_count = today_bills.count()
    
    # Today's returns (for net sales)
    today_returns_total = Return.objects.filter(
        created_by=user,
        return_date__date=today
    ).exclude(
        settlement_status='cancelled'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    today_net_sales = today_sales_total - today_returns_total
    
    # Yesterday comparison
    yesterday_bills = my_bills.filter(bill_date__date=yesterday)
    yesterday_total = yesterday_bills.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    # ===== WEEK & MONTH =====
    week_bills = my_bills.filter(bill_date__date__gte=week_ago)
    week_gross = week_bills.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    week_count = week_bills.count()
    week_returns_total = Return.objects.filter(
        created_by=user,
        return_date__date__gte=week_ago
    ).exclude(
        settlement_status='cancelled'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    week_total = week_gross - week_returns_total
    
    month_bills = my_bills.filter(bill_date__date__gte=month_start)
    month_total = month_bills.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    month_count = month_bills.count()
    
    # Month returns (to calculate net sales)
    month_returns_total = Return.objects.filter(
        created_by=user,
        return_date__date__gte=month_start
    ).exclude(
        settlement_status='cancelled'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    month_net_sales = month_total - month_returns_total
    
    # ===== TODAY'S COLLECTIONS (payments received) =====
    today_settlements = Payment.objects.filter(
        received_by=user,
        settlement_status='completed',
        settlement_date__date=today
    )
    today_collections_gross = today_settlements.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    today_collections_count = today_settlements.count()
    
    # Today's cash refunds (reduce collections)
    today_cash_refunds = Return.objects.filter(
        created_by=user,
        settlement_status='settled_cash',
        cash_paid_at__date=today
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    today_collections = today_collections_gross - today_cash_refunds
    
    month_settlements = Payment.objects.filter(
        received_by=user,
        settlement_status='completed',
        settlement_date__date__gte=month_start
    )
    month_collections_gross = month_settlements.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Month cash refunds
    month_cash_refunds = Return.objects.filter(
        created_by=user,
        settlement_status='settled_cash',
        cash_paid_at__date__gte=month_start
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    month_collections = month_collections_gross - month_cash_refunds
    
    # ===== OUTSTANDING / PENDING =====
    outstanding_bills = my_bills.filter(
        settlement_status__in=['unsettled', 'partial_settled']
    )
    total_outstanding = outstanding_bills.aggregate(
        total=Sum('balance_amount')
    )['total'] or Decimal('0')
    outstanding_count = outstanding_bills.count()
    
    # Pending verifications (payments I submitted awaiting verification)
    pending_verifications = Payment.objects.filter(
        received_by=user,
        settlement_status='pending'
    ).count()
    
    # ===== RETURNS =====
    my_returns = Return.objects.filter(created_by=user)
    today_returns = my_returns.filter(created_at__date=today).count()
    pending_returns = my_returns.filter(settlement_status='unsettled').count()
    
    # ===== EXCHANGES =====
    today_exchanges = ItemExchange.objects.filter(
        created_by=user, exchange_date__date=today
    ).count()
    
    # ===== COMMISSION =====
    commission_balance = CommissionTransaction.get_rep_balance(user)
    
    # This month's commission earned (match commission page logic:
    # exclude writeoffs and negative adjustments like payouts)
    month_commission_txns = CommissionTransaction.objects.filter(
        sales_rep=user,
        transaction_date__date__gte=month_start
    ).exclude(
        transaction_type='writeoff_executed'
    ).exclude(
        transaction_type='adjustment',
        commission_earned__lt=0
    )
    month_commission = month_commission_txns.aggregate(
        total=Sum('commission_earned')
    )['total'] or Decimal('0')
    
    # Current rate
    from sales.models import CommissionRateHistory
    current_rate = CommissionRateHistory.objects.filter(
        is_active=True
    ).order_by('-effective_from').first()
    commission_rate_pct = current_rate.rate if current_rate else Decimal('0')
    
    # ===== MONEY ACCOUNT =====
    try:
        money_account = UserMoneyAccount.objects.get(user=user)
        money_balance = money_account.current_balance
    except UserMoneyAccount.DoesNotExist:
        money_balance = Decimal('0')
    
    # ===== RECENT ACTIVITY (last 15 items, mixed) =====
    recent_bills_list = list(
        my_bills.order_by('-bill_date')[:8].values(
            'pk', 'bill_number', 'shop__shop_name', 'total_amount',
            'bill_date', 'settlement_status'
        )
    )
    for b in recent_bills_list:
        b['activity_type'] = 'bill'
        b['activity_time'] = b['bill_date']
    
    recent_payments_list = list(
        Payment.objects.filter(received_by=user).order_by('-settlement_date')[:8].values(
            'pk', 'settlement_number', 'shop__shop_name', 'amount',
            'settlement_date', 'settlement_method', 'settlement_status'
        )
    )
    for p in recent_payments_list:
        p['activity_type'] = 'payment'
        p['activity_time'] = p['settlement_date']
    
    # Merge and sort by time
    recent_activity = sorted(
        recent_bills_list + recent_payments_list,
        key=lambda x: x['activity_time'] or now,
        reverse=True
    )[:12]
    
    # ===== TOP SHOPS (by sales this month) =====
    from sales.models import BillItem
    top_shops = my_bills.filter(
        bill_date__date__gte=month_start
    ).values(
        'shop__pk', 'shop__shop_name', 'shop__shop_code'
    ).annotate(
        total_sales=Sum('total_amount'),
        bill_count=Count('id')
    ).order_by('-total_sales')[:5]
    
    # ===== DAILY NET SALES CHART DATA (last 7 days) =====
    daily_sales = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_gross = my_bills.filter(bill_date__date=d).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')
        day_returns = Return.objects.filter(
            created_by=user,
            return_date__date=d
        ).exclude(
            settlement_status='cancelled'
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        daily_sales.append({
            'date': d.strftime('%a'),
            'total': float(day_gross - day_returns),
        })
    
    # ===== SHOPS NEEDING ATTENTION =====
    shops_not_visited = assigned_shops.exclude(
        pk__in=ShopVisit.objects.filter(
            sales_rep=user, visit_date__date=today
        ).values_list('shop_id', flat=True)
    ).count()
    
    context = {
        # Today's performance
        'today_sales': today_net_sales,
        'today_bills_count': today_bills_count,
        'today_returns_total': today_returns_total,
        'today_collections': today_collections,
        'today_collections_count': today_collections_count,
        'today_cash_refunds': today_cash_refunds,
        'month_cash_refunds': month_cash_refunds,
        'today_visit_count': today_visit_count,
        'today_returns': today_returns,
        'today_exchanges': today_exchanges,
        'yesterday_total': yesterday_total,
        
        # Period stats
        'week_total': week_total,
        'week_count': week_count,
        'month_total': month_total,
        'month_net_sales': month_net_sales,
        'month_returns_total': month_returns_total,
        'month_count': month_count,
        'month_collections': month_collections,
        
        # Outstanding
        'total_outstanding': total_outstanding,
        'outstanding_count': outstanding_count,
        'pending_verifications': pending_verifications,
        'pending_returns': pending_returns,
        
        # Shops
        'total_my_shops': total_my_shops,
        'shops_not_visited': shops_not_visited,
        
        # Commission & money
        'commission_balance': commission_balance,
        'month_commission': month_commission,
        'commission_rate_pct': commission_rate_pct,
        'money_balance': money_balance,
        
        # Lists
        'recent_activity': recent_activity,
        'top_shops': top_shops,
        'daily_sales': daily_sales,
        
        # Date
        'today': today,
    }
    return render(request, 'dashboard/sales_rep_dashboard.html', context)


@login_required
def office_dashboard(request):
    """Dashboard for office staff and admin"""
    if request.user.is_sales_rep:
        return redirect('dashboard:sales_rep')
    
    # Get date range
    today = timezone.localdate()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Overall statistics
    total_shops = Shop.objects.filter(is_active=True).count()
    total_products = Product.objects.filter(is_active=True).count()
    
    # Sales statistics
    all_bills = Bill.objects.filter(bill_status='confirmed')
    
    today_sales = all_bills.filter(bill_date__date=today)
    today_total = today_sales.aggregate(total=Sum('total_amount'))['total'] or 0
    
    week_sales = all_bills.filter(bill_date__date__gte=week_ago)
    week_total = week_sales.aggregate(total=Sum('total_amount'))['total'] or 0
    
    month_sales = all_bills.filter(bill_date__date__gte=month_ago)
    month_total = month_sales.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Payment statistics
    all_payments = Payment.objects.filter(settlement_status='completed')
    
    today_payments = all_payments.filter(settlement_date__date=today)
    today_payment_total = today_payments.aggregate(total=Sum('amount'))['total'] or 0
    
    week_payments = all_payments.filter(settlement_date__date__gte=week_ago)
    week_payment_total = week_payments.aggregate(total=Sum('amount'))['total'] or 0
    
    month_payments = all_payments.filter(settlement_date__date__gte=month_ago)
    month_payment_total = month_payments.aggregate(total=Sum('amount'))['total'] or 0
    
    # Outstanding amounts
    total_outstanding = Shop.objects.filter(is_active=True).aggregate(
        total=Sum('current_balance')
    )['total'] or 0
    
    # Pending cheques
    pending_cheques = Payment.objects.filter(
        settlement_method='cheque',
        settlement_status='pending'
    ).count()
    
    # Low stock products
    low_stock_products = Product.objects.filter(
        is_active=True,
        quantity_in_stock__lte=models.F('minimum_stock_level')
    ).count()
    
    # Top selling products this month
    from django.db.models import F
    from sales.models import BillItem
    
    top_products = BillItem.objects.filter(
        bill__bill_date__date__gte=month_ago,
        bill__bill_status='confirmed'
    ).values(
        'product__product_name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_sales=Sum('line_total')
    ).order_by('-total_sales')[:10]
    
    # Top performing sales reps
    from accounts.models import User
    
    top_reps = all_bills.filter(
        bill_date__date__gte=month_ago
    ).values(
        'sales_rep__username',
        'sales_rep__first_name',
        'sales_rep__last_name'
    ).annotate(
        total_sales=Sum('total_amount'),
        total_bills=Count('id')
    ).order_by('-total_sales')[:10]
    
    # Recent activities
    recent_bills = all_bills.order_by('-bill_date')[:10]
    recent_payments = Payment.objects.all().order_by('-settlement_date')[:10]
    
    context = {
        'total_shops': total_shops,
        'total_products': total_products,
        'today_sales': today_total,
        'today_bills': today_sales.count(),
        'week_sales': week_total,
        'week_bills': week_sales.count(),
        'month_sales': month_total,
        'month_bills': month_sales.count(),
        'today_payments': today_payment_total,
        'today_payment_count': today_payments.count(),
        'week_payments': week_payment_total,
        'month_payments': month_payment_total,
        'total_outstanding': total_outstanding,
        'pending_cheques': pending_cheques,
        'low_stock_products': low_stock_products,
        'top_products': top_products,
        'top_reps': top_reps,
        'recent_bills': recent_bills,
        'recent_payments': recent_payments,
    }
    return render(request, 'dashboard/office_dashboard.html', context)


@login_required
def sales_report(request):
    """Detailed sales report"""
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    sales_rep_id = request.GET.get('sales_rep')
    
    bills = Bill.objects.filter(bill_status='confirmed')
    
    if start_date:
        bills = bills.filter(bill_date__date__gte=start_date)
    
    if end_date:
        bills = bills.filter(bill_date__date__lte=end_date)
    
    if sales_rep_id and not request.user.is_sales_rep:
        bills = bills.filter(sales_rep_id=sales_rep_id)
    elif request.user.is_sales_rep:
        bills = bills.filter(sales_rep=request.user)
    
    # Calculate totals
    total_sales = bills.aggregate(total=Sum('total_amount'))['total'] or 0
    total_paid = bills.aggregate(total=Sum('paid_amount'))['total'] or 0
    total_balance = bills.aggregate(total=Sum('balance_amount'))['total'] or 0
    
    from accounts.models import User
    from accounts.tenant_utils import get_tenant_users
    sales_reps = get_tenant_users().filter(user_type='sales_rep', is_active_employee=True)
    
    context = {
        'bills': bills,
        'total_sales': total_sales,
        'total_paid': total_paid,
        'total_balance': total_balance,
        'total_bills': bills.count(),
        'sales_reps': sales_reps,
    }
    return render(request, 'dashboard/sales_report.html', context)


@login_required
def payment_report(request):
    """Detailed payment report"""
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    payment_method = request.GET.get('payment_method')
    
    payments = Payment.objects.exclude(settlement_status='cancelled')
    
    if start_date:
        payments = payments.filter(settlement_date__date__gte=start_date)
    
    if end_date:
        payments = payments.filter(settlement_date__date__lte=end_date)
    
    if payment_method:
        payments = payments.filter(settlement_method=payment_method)
    
    if request.user.is_sales_rep:
        payments = payments.filter(received_by=request.user)
    
    # Calculate totals
    total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
    total_count = payments.count()
    average_payment = (total_amount / total_count) if total_count > 0 else 0
    
    # Group by payment method
    by_method = payments.values('settlement_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    context = {
        'payments': payments,
        'total_amount': total_amount,
        'total_payments': total_count,
        'average_payment': average_payment,
        'by_method': by_method,
    }
    return render(request, 'dashboard/payment_report.html', context)


@login_required
def profit_loss_report(request):
    """Profit & Loss report with FIFO-based COGS"""
    from decimal import Decimal
    from datetime import datetime
    from sales.models import BillItem, Return
    from sales.models import CommissionTransaction
    from products.models import Company, StockMovement
    from products.models import FOCValueTransaction
    from payments.models import BadDebtWriteOff
    from expenses.models import Expense, ExpenseCategory
    
    # Access control: admin & office only
    if request.user.user_type not in ('admin', 'office'):
        from django.contrib import messages
        messages.error(request, 'Access denied. Only office staff can view the P&L report.')
        return redirect('dashboard:home')
    
    # Date filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    company_id = request.GET.get('company')
    
    # === REVENUE ===
    bills = Bill.objects.filter(bill_status='confirmed')
    if start_date:
        bills = bills.filter(bill_date__date__gte=start_date)
    if end_date:
        bills = bills.filter(bill_date__date__lte=end_date)
    
    bill_items = BillItem.objects.filter(bill__in=bills)
    if company_id:
        bill_items = bill_items.filter(product__company_id=company_id)
        bills = bills.filter(items__product__company_id=company_id).distinct()
    
    gross_sales = bills.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    bill_discounts = bills.aggregate(t=Sum('discount_amount'))['t'] or Decimal('0')
    
    # === RETURNS ===
    returns = Return.objects.exclude(settlement_status='cancelled')
    if start_date:
        returns = returns.filter(return_date__date__gte=start_date)
    if end_date:
        returns = returns.filter(return_date__date__lte=end_date)
    if company_id:
        returns = returns.filter(items__product__company_id=company_id).distinct()
    
    total_returns = returns.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    
    net_sales = gross_sales - total_returns
    
    # === COST OF RETURNED GOODS (to compute Net COGS) ===
    valid_return_numbers = list(returns.values_list('return_number', flat=True))
    returns_cost_movements = StockMovement.objects.filter(
        movement_type='return',
        reference_number__in=valid_return_numbers
    ).select_related('product', 'product__company')
    
    returns_cost = returns_cost_movements.aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
    
    # Build returns cost ledger (transaction-level breakdown)
    # Group stock movements by return_number, then join with Return for metadata
    from sales.models import ReturnItem
    returns_by_number = {r.return_number: r for r in returns.select_related('shop', 'created_by')}
    
    returns_cost_ledger = []
    running_returns_cost = Decimal('0')
    for mv in returns_cost_movements.order_by('-created_at'):
        ret_obj = returns_by_number.get(mv.reference_number)
        mv_cost = mv.total_cost or Decimal('0')
        running_returns_cost += mv_cost
        unit_cost = mv.unit_cost or Decimal('0')
        qty = mv.quantity or 0
        
        # Get the return selling price from ReturnItem
        return_revenue = Decimal('0')
        if ret_obj:
            ret_item = ReturnItem.objects.filter(
                return_ref=ret_obj, product=mv.product
            ).first()
            if ret_item:
                return_revenue = ret_item.total_price or Decimal('0')
        
        returns_cost_ledger.append({
            'date': ret_obj.return_date if ret_obj else mv.created_at,
            'return_number': mv.reference_number or '-',
            'shop': ret_obj.shop.shop_name if ret_obj and ret_obj.shop else (ret_obj.customer_name if ret_obj else '-'),
            'product_code': mv.product.product_code if mv.product else '-',
            'product_name': mv.product.product_name if mv.product else '-',
            'size': mv.product.size if mv.product else '-',
            'company': mv.product.company.company_name if mv.product and mv.product.company else '-',
            'quantity': qty,
            'unit_cost': unit_cost,
            'total_cost': mv_cost,
            'return_revenue': return_revenue,
            'settlement_status': ret_obj.get_settlement_status_display() if ret_obj else '-',
            'return_reason': ret_obj.get_return_reason_display() if ret_obj else '-',
            'running_cost': running_returns_cost,
        })
    
    # === COGS (FIFO-based from BillItem.total_cost) ===
    cogs = bill_items.aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
    net_cogs = cogs - returns_cost
    
    # COGS Transaction-level breakdown: every bill item with full cost details
    cogs_transactions = (
        bill_items
        .select_related('bill', 'bill__shop', 'product', 'product__company')
        .order_by('-bill__bill_date', '-bill__id', 'id')
    )
    
    cogs_ledger = []
    running_cogs = Decimal('0')
    for item in cogs_transactions:
        total_units = (item.quantity or 0) + (item.foc_quantity or 0)
        item_cost = item.total_cost or Decimal('0')
        running_cogs += item_cost
        revenue = item.line_total or Decimal('0')
        profit = revenue - item_cost
        margin = (profit / revenue * 100) if revenue > 0 else Decimal('0')
        
        cogs_ledger.append({
            'date': item.bill.bill_date,
            'bill_number': item.bill.bill_number,
            'shop': item.bill.shop.shop_name if item.bill.shop else (item.bill.customer_name or '-'),
            'product_code': item.product.product_code,
            'product_name': item.product.product_name,
            'size': item.product.size,
            'company': item.product.company.company_name if item.product.company else '-',
            'qty_sold': item.quantity or 0,
            'foc_qty': item.foc_quantity or 0,
            'total_units': total_units,
            'unit_price': item.unit_price or Decimal('0'),
            'revenue': revenue,
            'unit_cost': item.unit_cost or Decimal('0'),
            'total_cost': item_cost,
            'profit': profit,
            'margin': margin,
            'running_cogs': running_cogs,
            'cost_breakdown': item.cost_breakdown or [],
        })
    
    # Also build product summary from this data
    from collections import defaultdict
    product_summary = defaultdict(lambda: {
        'qty_sold': Decimal('0'), 'foc_given': Decimal('0'),
        'total_cost': Decimal('0'), 'revenue': Decimal('0'),
        'product_name': '', 'product_code': '', 'size': '',
    })
    for item in cogs_ledger:
        key = item['product_code']
        ps = product_summary[key]
        ps['product_code'] = item['product_code']
        ps['product_name'] = item['product_name']
        ps['size'] = item['size']
        ps['qty_sold'] += item['qty_sold']
        ps['foc_given'] += item['foc_qty']
        ps['total_cost'] += item['total_cost']
        ps['revenue'] += item['revenue']
    
    cogs_by_product = []
    for key, ps in sorted(product_summary.items(), key=lambda x: x[1]['total_cost'], reverse=True):
        total_units = ps['qty_sold'] + ps['foc_given']
        avg_cost = (ps['total_cost'] / total_units) if total_units > 0 else Decimal('0')
        margin = ((ps['revenue'] - ps['total_cost']) / ps['revenue'] * 100) if ps['revenue'] > 0 else Decimal('0')
        cogs_by_product.append({
            'product_code': ps['product_code'],
            'product_name': ps['product_name'],
            'size': ps['size'],
            'qty_sold': ps['qty_sold'],
            'foc_given': ps['foc_given'],
            'total_units': total_units,
            'avg_unit_cost': avg_cost,
            'total_cost': ps['total_cost'],
            'revenue': ps['revenue'],
            'margin': margin,
        })
    
    gross_profit = net_sales - net_cogs
    gross_margin = (gross_profit / net_sales * 100) if net_sales > 0 else Decimal('0')
    
    # === EXPENSES ===
    # 1. Commission
    commission_qs = CommissionTransaction.objects.all()
    if start_date:
        commission_qs = commission_qs.filter(created_at__date__gte=start_date)
    if end_date:
        commission_qs = commission_qs.filter(created_at__date__lte=end_date)
    total_commission = commission_qs.aggregate(t=Sum('commission_earned'))['t'] or Decimal('0')
    
    # 2. FOC Net Cost
    foc_filter = {'is_archived': False}
    if start_date:
        foc_filter['transaction_date__date__gte'] = start_date
    if end_date:
        foc_filter['transaction_date__date__lte'] = end_date
    if company_id:
        foc_filter['foc_account__company_id'] = company_id
    
    foc_given = FOCValueTransaction.objects.filter(
        transaction_type__in=['foc_given', 'implicit_foc'], **foc_filter
    ).aggregate(t=Sum('foc_value'))['t'] or Decimal('0')
    
    foc_restored = FOCValueTransaction.objects.filter(
        transaction_type='return_foc_restored', **foc_filter
    ).aggregate(t=Sum('foc_value'))['t'] or Decimal('0')
    
    net_foc_cost = foc_given - foc_restored
    
    # 3. Bad Debt Write-offs
    bad_debt_qs = BadDebtWriteOff.objects.filter(approval_status='approved', executed=True)
    if start_date:
        bad_debt_qs = bad_debt_qs.filter(write_off_date__date__gte=start_date)
    if end_date:
        bad_debt_qs = bad_debt_qs.filter(write_off_date__date__lte=end_date)
    total_bad_debt = bad_debt_qs.aggregate(t=Sum('write_off_amount'))['t'] or Decimal('0')
    
    # 4. Damage/Wastage
    damage_qs = StockMovement.objects.filter(movement_type='damage')
    if start_date:
        damage_qs = damage_qs.filter(created_at__date__gte=start_date)
    if end_date:
        damage_qs = damage_qs.filter(created_at__date__lte=end_date)
    if company_id:
        damage_qs = damage_qs.filter(product__company_id=company_id)
    total_damage = damage_qs.aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
    
    # 5. Stock Write-offs (status_adjustment + non_resaleable_out)
    writeoff_types = ['status_adjustment', 'non_resaleable_out']
    writeoff_qs = StockMovement.objects.filter(movement_type__in=writeoff_types)
    if start_date:
        writeoff_qs = writeoff_qs.filter(created_at__date__gte=start_date)
    if end_date:
        writeoff_qs = writeoff_qs.filter(created_at__date__lte=end_date)
    if company_id:
        writeoff_qs = writeoff_qs.filter(product__company_id=company_id)
    total_writeoffs = writeoff_qs.aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
    
    # 6. Supplier Returns (purchase_return + return_to_company)
    # These reduce inventory value and represent cost of goods returned to suppliers
    supplier_return_types = ['purchase_return', 'return_to_company']
    supplier_return_qs = StockMovement.objects.filter(movement_type__in=supplier_return_types)
    if start_date:
        supplier_return_qs = supplier_return_qs.filter(created_at__date__gte=start_date)
    if end_date:
        supplier_return_qs = supplier_return_qs.filter(created_at__date__lte=end_date)
    if company_id:
        supplier_return_qs = supplier_return_qs.filter(product__company_id=company_id)
    total_supplier_returns = supplier_return_qs.aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
    # Note: These are stock outflows (negative qty) with positive cost — they represent
    # the value of goods returned to the supplier (not an expense but an inventory adjustment)
    
    # 7. Stock Adjustments (manual corrections)
    adjustment_qs = StockMovement.objects.filter(movement_type='adjustment')
    if start_date:
        adjustment_qs = adjustment_qs.filter(created_at__date__gte=start_date)
    if end_date:
        adjustment_qs = adjustment_qs.filter(created_at__date__lte=end_date)
    if company_id:
        adjustment_qs = adjustment_qs.filter(product__company_id=company_id)
    # Split: negative adjustments = shrinkage/loss, positive = found/correction
    adjustment_losses = adjustment_qs.filter(quantity__lt=0).aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
    adjustment_gains = adjustment_qs.filter(quantity__gt=0).aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
    net_adjustment_loss = adjustment_losses - adjustment_gains  # net loss
    
    # 8. Operating Expenses (from Expense model)
    op_expense_qs = Expense.objects.filter(approval_status='approved')
    if start_date:
        op_expense_qs = op_expense_qs.filter(expense_date__gte=start_date)
    if end_date:
        op_expense_qs = op_expense_qs.filter(expense_date__lte=end_date)
    total_operating_expenses = op_expense_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    
    # Category breakdown of operating expenses
    op_expense_by_category = (
        op_expense_qs
        .values('category__name', 'category__icon', 'category__color')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    
    # === SUB-TOTALS for proper P&L structure ===
    # Operating Expenses = Sales & Distribution + General & Administrative
    total_opex = total_commission + net_foc_cost + total_operating_expenses
    
    # Losses & Write-offs
    total_losses = total_bad_debt + total_damage + total_writeoffs
    if net_adjustment_loss > 0:
        total_losses += net_adjustment_loss
    
    # Operating Profit = Gross Profit - Operating Expenses
    operating_profit = gross_profit - total_opex
    operating_margin = (operating_profit / net_sales * 100) if net_sales > 0 else Decimal('0')
    
    # Total All Expenses
    total_expenses = total_opex + total_losses
    net_profit = gross_profit - total_expenses
    net_margin = (net_profit / net_sales * 100) if net_sales > 0 else Decimal('0')
    
    # === COMPANY BREAKDOWN ===
    companies = Company.objects.filter(is_active=True).order_by('company_name')
    company_breakdown = []
    for comp in companies:
        comp_items = bill_items.filter(product__company=comp)
        comp_bills = bills.filter(items__product__company=comp).distinct()
        
        comp_revenue = comp_bills.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
        comp_gross_cogs = comp_items.aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
        # Net COGS: subtract cost of returned goods for this company
        comp_return_cost = StockMovement.objects.filter(
            movement_type='return',
            reference_number__in=valid_return_numbers,
            product__company=comp
        ).aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
        comp_returns_revenue = returns.filter(items__product__company=comp).distinct().aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
        comp_net_revenue = comp_revenue - comp_returns_revenue
        comp_cogs = comp_gross_cogs - comp_return_cost
        comp_gp = comp_net_revenue - comp_cogs
        comp_margin = (comp_gp / comp_net_revenue * 100) if comp_net_revenue > 0 else Decimal('0')
        
        if comp_revenue > 0 or comp_cogs > 0:
            company_breakdown.append({
                'company': comp,
                'revenue': comp_revenue,
                'cogs': comp_cogs,
                'gross_profit': comp_gp,
                'margin': comp_margin,
            })
    
    # === MONTHLY TREND (last 6 months) ===
    from django.db.models.functions import TruncMonth
    from django.db.models import Subquery, OuterRef
    
    # Revenue from Bills (no duplication)
    monthly_revenue = (
        Bill.objects.filter(bill_status='confirmed')
        .annotate(month=TruncMonth('bill_date'))
        .values('month')
        .annotate(revenue=Sum('total_amount'))
        .order_by('-month')[:6]
    )
    
    # COGS from BillItems
    monthly_cogs = (
        BillItem.objects.filter(bill__bill_status='confirmed')
        .annotate(month=TruncMonth('bill__bill_date'))
        .values('month')
        .annotate(cogs=Sum('total_cost'))
        .order_by('-month')[:6]
    )
    
    # Monthly returns (revenue deduction)
    monthly_returns_rev = (
        Return.objects.exclude(settlement_status='cancelled')
        .annotate(month=TruncMonth('return_date'))
        .values('month')
        .annotate(returns_rev=Sum('total_amount'))
        .order_by('-month')[:6]
    )
    
    # Monthly returns cost (COGS deduction)
    monthly_returns_cost = (
        StockMovement.objects.filter(
            movement_type='return',
            reference_number__in=valid_return_numbers
        )
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(returns_cost=Sum('total_cost'))
        .order_by('-month')[:6]
    )
    
    # Merge into single list with Net values
    cogs_by_month = {m['month']: m['cogs'] or 0 for m in monthly_cogs}
    returns_rev_by_month = {m['month']: m['returns_rev'] or 0 for m in monthly_returns_rev}
    returns_cost_by_month = {m['month']: m['returns_cost'] or 0 for m in monthly_returns_cost}
    
    # Monthly operating expenses (from Expense model)
    monthly_expenses = (
        Expense.objects.filter(approval_status='approved')
        .annotate(month=TruncMonth('expense_date'))
        .values('month')
        .annotate(expenses=Sum('amount'))
        .order_by('-month')[:6]
    )
    expenses_by_month = {m['month']: float(m['expenses'] or 0) for m in monthly_expenses}
    
    monthly_merged = []
    for m in monthly_revenue:
        month = m['month']
        gross_rev = m['revenue'] or 0
        gross_cog = cogs_by_month.get(month, 0)
        ret_rev = returns_rev_by_month.get(month, 0)
        ret_cost = returns_cost_by_month.get(month, 0)
        net_rev = gross_rev - ret_rev
        net_cog = gross_cog - ret_cost
        month_exp = expenses_by_month.get(month, 0)
        monthly_merged.append({
            'month': month,
            'revenue': net_rev,
            'cogs': net_cog,
            'expenses': month_exp,
        })
    
    monthly_trend = sorted(monthly_merged, key=lambda x: x['month'])
    
    # For chart
    chart_labels = [m['month'].strftime('%b %Y') for m in monthly_trend]
    chart_revenue = [float(m['revenue'] or 0) for m in monthly_trend]
    chart_cogs = [float(m['cogs'] or 0) for m in monthly_trend]
    chart_profit = [float((m['revenue'] or 0) - (m['cogs'] or 0)) for m in monthly_trend]
    chart_expenses = [float(m['expenses'] or 0) for m in monthly_trend]
    chart_net_profit = [float((m['revenue'] or 0) - (m['cogs'] or 0) - (m['expenses'] or 0)) for m in monthly_trend]
    
    # === FIFO COST LAYERS ===
    from products.models import FIFOCostLayer
    # Exclude layers from cancelled returns
    cancelled_return_numbers = list(
        Return.objects.filter(settlement_status='cancelled').values_list('return_number', flat=True)
    )
    layers_qs = FIFOCostLayer.objects.select_related('product', 'product__company').exclude(
        layer_source='return',
        reference_number__in=cancelled_return_numbers,
    ).order_by('product__product_name', 'created_at')
    
    fifo_layers = []
    for layer in layers_qs:
        total_value = layer.unit_cost * layer.remaining_quantity
        consumed = layer.original_quantity - layer.remaining_quantity
        fifo_layers.append({
            'id': layer.id,
            'product_code': layer.product.product_code,
            'product_name': layer.product.product_name,
            'size': layer.product.size,
            'company': layer.product.company.company_name if layer.product.company else '-',
            'source': layer.get_layer_source_display(),
            'source_key': layer.layer_source,
            'reference': layer.reference_number or '-',
            'unit_cost': layer.unit_cost,
            'original_qty': layer.original_quantity,
            'remaining_qty': layer.remaining_quantity,
            'consumed_qty': consumed,
            'total_value': total_value,
            'is_exhausted': layer.is_exhausted,
            'created_at': layer.created_at,
        })
    
    # Layer summary stats
    total_layers = len(fifo_layers)
    active_layers = sum(1 for l in fifo_layers if not l['is_exhausted'])
    exhausted_layers = total_layers - active_layers
    total_inventory_value = sum(l['total_value'] for l in fifo_layers if not l['is_exhausted'])
    
    # === COST LAYER BREAKDOWN BY SOURCE ===
    source_labels = {
        'purchase': {'label': 'Purchase / GRN', 'icon': 'fa-truck', 'color': '#2563eb'},
        'opening_balance': {'label': 'Opening Balance', 'icon': 'fa-box-open', 'color': '#0891b2'},
        'return': {'label': 'Sales Returns', 'icon': 'fa-undo-alt', 'color': '#f59e0b'},
        'exchange_in': {'label': 'Exchange IN', 'icon': 'fa-exchange-alt', 'color': '#10b981'},
        'adjustment': {'label': 'Adjustments', 'icon': 'fa-sliders-h', 'color': '#6b7280'},
    }
    layer_source_breakdown = {}
    for layer in fifo_layers:
        src = layer['source_key']
        if src not in layer_source_breakdown:
            meta = source_labels.get(src, {'label': src.replace('_', ' ').title(), 'icon': 'fa-layer-group', 'color': '#6b7280'})
            layer_source_breakdown[src] = {
                'source_key': src,
                'label': meta['label'],
                'icon': meta['icon'],
                'color': meta['color'],
                'total_layers': 0,
                'active_layers': 0,
                'exhausted_layers': 0,
                'total_original_qty': 0,
                'total_consumed_qty': 0,
                'total_remaining_qty': 0,
                'total_value': Decimal('0'),           # active remaining value
                'total_original_value': Decimal('0'),  # full original value
            }
        bucket = layer_source_breakdown[src]
        bucket['total_layers'] += 1
        bucket['total_original_qty'] += layer['original_qty']
        bucket['total_consumed_qty'] += layer['consumed_qty']
        bucket['total_remaining_qty'] += layer['remaining_qty']
        bucket['total_original_value'] += layer['unit_cost'] * layer['original_qty']
        if not layer['is_exhausted']:
            bucket['active_layers'] += 1
            bucket['total_value'] += layer['total_value']
        else:
            bucket['exhausted_layers'] += 1
    
    # Sort: purchase first, then by value descending
    source_order = ['purchase', 'opening_balance', 'return', 'exchange_in', 'adjustment']
    layer_breakdown_list = sorted(
        layer_source_breakdown.values(),
        key=lambda x: (source_order.index(x['source_key']) if x['source_key'] in source_order else 99)
    )
    
    context = {
        # Revenue
        'gross_sales': gross_sales,
        'bill_discounts': bill_discounts,
        'total_returns': total_returns,
        'net_sales': net_sales,
        # COGS
        'cogs': cogs,
        'returns_cost': returns_cost,
        'returns_cost_ledger': returns_cost_ledger,
        'net_cogs': net_cogs,
        'gross_profit': gross_profit,
        'gross_margin': gross_margin,
        # Expenses
        'total_commission': total_commission,
        'net_foc_cost': net_foc_cost,
        'total_bad_debt': total_bad_debt,
        'total_damage': total_damage,
        'total_writeoffs': total_writeoffs,
        'total_supplier_returns': total_supplier_returns,
        'net_adjustment_loss': net_adjustment_loss,
        'total_operating_expenses': total_operating_expenses,
        'op_expense_by_category': op_expense_by_category,
        'total_opex': total_opex,
        'total_losses': total_losses,
        'operating_profit': operating_profit,
        'operating_margin': operating_margin,
        'total_expenses': total_expenses,
        # Bottom line
        'net_profit': net_profit,
        'net_margin': net_margin,
        # Breakdowns
        'company_breakdown': company_breakdown,
        'cogs_breakdown': cogs_by_product,
        'cogs_ledger': cogs_ledger,
        # FIFO Layers
        'fifo_layers': fifo_layers,
        'total_layers': total_layers,
        'active_layers': active_layers,
        'exhausted_layers': exhausted_layers,
        'total_inventory_value': total_inventory_value,
        'layer_breakdown': layer_breakdown_list,
        # Chart
        'chart_labels': chart_labels,
        'chart_revenue': chart_revenue,
        'chart_cogs': chart_cogs,
        'chart_profit': chart_profit,
        'chart_expenses': chart_expenses,
        'chart_net_profit': chart_net_profit,
        # Filters
        'companies': companies,
        'total_bills': bills.count(),
    }
    return render(request, 'dashboard/profit_loss_report.html', context)


@login_required
def distributor_eod_report(request):
    """
    Distributor End of Day Report — office/admin view aggregating all reps' daily activity.
    Shows combined summary + per-rep breakdown with collection actions.
    """
    from decimal import Decimal
    from datetime import datetime as dt
    from django.contrib.auth import get_user_model
    from sales.eod_views import get_rep_eod_data, get_product_breakdown
    from tenants.models import GlobalCaseValueSetting
    from payments.models import SalesAccountSettlement
    from sales.models import Bill, BillItem, Return
    from products.models import FOCValueTransaction
    from shops.models import ShopVisit
    from business.models import DistributorProfile
    from collections import OrderedDict

    User = get_user_model()

    # Access control: admin & office only
    if request.user.user_type not in ('admin', 'office'):
        from django.contrib import messages as msg
        msg.error(request, 'Access denied. Only office staff can view the distributor EOD report.')
        return redirect('dashboard:home')

    # Date param (default: today)
    date_str = request.GET.get('date', '')
    try:
        report_date = dt.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.localdate()
    except (ValueError, TypeError):
        report_date = timezone.localdate()

    # Navigation dates
    prev_date = report_date - timedelta(days=1)
    next_date = report_date + timedelta(days=1)
    is_today = report_date == timezone.localdate()
    is_future = next_date > timezone.localdate()

    # Business profile
    business = DistributorProfile.objects.filter(is_active=True).first()
    area = business.city if business else 'N/A'
    business_name = business.business_name if business else 'N/A'

    # Case value (global setting from public schema)
    case_value = GlobalCaseValueSetting.get_active_case_value(report_date)

    # Discover all users who had bill activity on this date
    active_rep_ids = Bill.objects.filter(
        bill_date__date=report_date,
        bill_status='confirmed'
    ).values_list('sales_rep', flat=True).distinct()

    # Also include users who received payments or created returns on this date
    payment_rep_ids = SalesAccountSettlement.objects.filter(
        settlement_date__date=report_date
    ).exclude(settlement_status='cancelled').values_list('received_by', flat=True).distinct()

    return_rep_ids = Return.objects.filter(
        return_date__date=report_date
    ).values_list('created_by', flat=True).distinct()

    # Union of all active user IDs
    all_rep_ids = set(active_rep_ids) | set(payment_rep_ids) | set(return_rep_ids)
    all_rep_ids.discard(None)

    # Get user objects
    from accounts.tenant_utils import get_tenant_users
    reps = get_tenant_users().filter(id__in=all_rep_ids).order_by('first_name', 'last_name')

    # Gather per-rep data
    rep_data_list = []
    grand = {
        'total_sale': Decimal('0'),
        'total_pack': Decimal('0'),
        'bill_count': 0,
        'new_outlets': 0,
        'total_foc_given': Decimal('0'),
        'total_credit': Decimal('0'),
        'total_cheque': Decimal('0'),
        'total_cash': Decimal('0'),
        'total_bank': Decimal('0'),
        'cash_refunds': Decimal('0'),
        'net_cash': Decimal('0'),
        'total_return_value': Decimal('0'),
        'return_count': 0,
        'shops_visited': 0,
    }

    for rep in reps:
        data = get_rep_eod_data(rep, report_date, case_value)
        rep_data_list.append(data)
        # Accumulate grand totals
        for key in grand:
            grand[key] += data[key] if isinstance(data[key], (int, Decimal)) else 0

    # Total collections (cash + cheque + bank)
    grand['total_collected'] = grand['total_cash'] + grand['total_cheque'] + grand['total_bank']

    # Add total_collected to each rep data too
    for rd in rep_data_list:
        rd['total_collected'] = rd['total_cash'] + rd['total_cheque'] + rd['total_bank']

    # Uncollected cheques for this date (for collection actions)
    uncollected_cheques = SalesAccountSettlement.objects.filter(
        settlement_method='cheque',
        settlement_status='pending',
        cheque_collected=False,
        settlement_date__date=report_date
    ).select_related('bill__shop', 'received_by').order_by('settlement_date')

    # All-time uncollected cheques (regardless of date) for a summary count
    all_uncollected_count = SalesAccountSettlement.objects.filter(
        settlement_method='cheque',
        settlement_status='pending',
        cheque_collected=False
    ).count()

    # Combined product breakdown (all reps)
    product_breakdown = get_product_breakdown(report_date)

    context = {
        'report_date': report_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'is_today': is_today,
        'is_future': is_future,
        'area': area,
        'business_name': business_name,
        'case_value': case_value,
        'rep_data': rep_data_list,
        'rep_count': len(rep_data_list),
        'grand': grand,
        'uncollected_cheques': uncollected_cheques,
        'all_uncollected_count': all_uncollected_count,
        'product_breakdown': product_breakdown,
        'page_title': f'Distributor EOD Report - {report_date}',
    }
    return render(request, 'dashboard/distributor_eod_report.html', context)
