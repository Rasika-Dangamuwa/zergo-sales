"""
End of Day (EOD) Report Views
Created: January 31, 2026

Views for managing and displaying daily sales EOD reports.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from decimal import Decimal
from datetime import datetime, timedelta
import json

from .eod_models import DailyRoute
from tenants.models import GlobalCaseValueSetting
from .models import Bill, BillItem, Return
from shops.models import Shop, ShopVisit
from products.models import Product, Category, FOCValueTransaction
from payments.models import SalesAccountSettlement
from business.models import DistributorProfile
from collections import OrderedDict


def get_rep_eod_data(user, report_date, case_value=None):
    """
    Shared helper: gather all EOD metrics for a single rep on a single date.
    Returns a dict with all key metrics. Used by both rep EOD and distributor EOD.
    """
    if case_value is None:
        case_value = GlobalCaseValueSetting.get_active_case_value(report_date)

    # Confirmed bills
    bills = Bill.objects.filter(
        sales_rep=user,
        bill_date__date=report_date,
        bill_status='confirmed'
    )
    total_sale = bills.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    bill_count = bills.count()
    total_pack = total_sale / case_value if case_value > 0 else Decimal('0')

    # New outlets
    new_outlets = Shop.objects.filter(created_by=user, created_at__date=report_date).count()

    # FOC given (all types)
    total_foc_given = FOCValueTransaction.objects.filter(
        bill_item__bill__sales_rep=user,
        bill_item__bill__bill_date__date=report_date,
        bill_item__bill__bill_status='confirmed'
    ).aggregate(total=Sum('foc_value'))['total'] or Decimal('0')

    # Credit (remaining unpaid from today's bills)
    total_settled = SalesAccountSettlement.objects.filter(
        bill__sales_rep=user,
        bill__bill_date__date=report_date,
        bill__bill_status='confirmed'
    ).exclude(settlement_status__in=['cancelled', 'bounced']).aggregate(
        total=Sum('amount'))['total'] or Decimal('0')
    total_credit = total_sale - total_settled

    # Cheques received
    total_cheque = SalesAccountSettlement.objects.filter(
        received_by=user,
        settlement_date__date=report_date,
        settlement_method='cheque'
    ).exclude(settlement_status__in=['cancelled', 'bounced']).aggregate(
        total=Sum('amount'))['total'] or Decimal('0')

    # Cash collected
    total_cash = SalesAccountSettlement.objects.filter(
        received_by=user,
        settlement_date__date=report_date,
        settlement_method='cash',
        settlement_status='completed'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # Bank transfers
    total_bank = SalesAccountSettlement.objects.filter(
        received_by=user,
        settlement_date__date=report_date,
        settlement_method='bank_transfer'
    ).exclude(settlement_status__in=['cancelled', 'bounced']).aggregate(
        total=Sum('amount'))['total'] or Decimal('0')

    # Cash refunds paid out
    cash_refunds = Return.objects.filter(
        created_by=user,
        settlement_status='settled_cash',
        cash_paid_at__date=report_date
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    net_cash = total_cash - cash_refunds

    # Returns
    returns_qs = Return.objects.filter(
        created_by=user,
        return_date__date=report_date
    )
    total_return_value = returns_qs.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    return_count = returns_qs.count()

    # Shops visited
    shops_visited = ShopVisit.objects.filter(
        sales_rep=user,
        visit_date__date=report_date
    ).values('shop').distinct().count()

    # Route
    try:
        daily_route = DailyRoute.objects.get(user=user, date=report_date)
        route = daily_route.route
    except DailyRoute.DoesNotExist:
        route = ''

    return {
        'user': user,
        'user_name': user.get_full_name() or user.username,
        'route': route,
        'total_sale': total_sale,
        'total_pack': total_pack,
        'bill_count': bill_count,
        'new_outlets': new_outlets,
        'total_foc_given': total_foc_given,
        'total_credit': total_credit,
        'total_cheque': total_cheque,
        'total_cash': total_cash,
        'total_bank': total_bank,
        'cash_refunds': cash_refunds,
        'net_cash': net_cash,
        'total_return_value': total_return_value,
        'return_count': return_count,
        'shops_visited': shops_visited,
    }


def get_product_breakdown(report_date, user=None):
    """
    Build product breakdown grouped by size.
    If user is None, aggregates across all reps.
    """
    all_products = Product.objects.filter(
        is_active=True
    ).select_related('company').order_by('display_order', 'product_name')

    sold_filter = {
        'bill__bill_date__date': report_date,
        'bill__bill_status': 'confirmed',
    }
    if user:
        sold_filter['bill__sales_rep'] = user

    sold_items = BillItem.objects.filter(**sold_filter).values(
        'product_id').annotate(total_qty=Sum('quantity'))
    sold_qty_dict = {item['product_id']: item['total_qty'] for item in sold_items}

    product_breakdown = OrderedDict()
    for product in all_products:
        size = product.size
        if size not in product_breakdown:
            product_breakdown[size] = []
        product_breakdown[size].append({
            'name': product.product_name,
            'quantity': sold_qty_dict.get(product.id, 0)
        })
    return product_breakdown


@login_required
def eod_settings(request):
    """
    EOD Settings page - shows global case value (read-only).
    Case value is now managed globally via Platform Settings.
    """
    from django_tenants.utils import schema_context
    
    with schema_context('public'):
        settings_list = list(GlobalCaseValueSetting.objects.all())
        active_setting = GlobalCaseValueSetting.objects.filter(is_active=True).first()
    
    context = {
        'settings': settings_list,
        'active_setting': active_setting,
        'page_title': 'EOD Settings'
    }
    
    return render(request, 'sales/eod_settings.html', context)


@login_required
def eod_date_list(request):
    """
    List all dates the user has worked (has bills)
    """
    user = request.user
    
    # Get distinct dates where user has bills
    dates = Bill.objects.filter(
        sales_rep=user,
        bill_status='confirmed'
    ).annotate(date_only=TruncDate('bill_date')).values_list('date_only', flat=True).distinct().order_by('-date_only')
    
    # Get routes for these dates
    routes = DailyRoute.objects.filter(user=user).values('date', 'route')
    route_dict = {r['date']: r['route'] for r in routes}
    
    # Build date list with summary
    date_list = []
    for date in dates:
        bills = Bill.objects.filter(sales_rep=user, bill_date__date=date, bill_status='confirmed')
        total_sale = bills.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        bill_count = bills.count()
        
        date_list.append({
            'date': date,
            'route': route_dict.get(date, 'Not set'),
            'total_sale': total_sale,
            'bill_count': bill_count
        })
    
    context = {
        'date_list': date_list,
        'page_title': 'EOD Reports'
    }
    
    return render(request, 'sales/eod_date_list.html', context)


@login_required
def eod_detail(request, date):
    """
    EOD Report detail for a specific date
    """
    user = request.user
    report_date = datetime.strptime(date, '%Y-%m-%d').date()
    
    # Check if route is set for this date
    try:
        daily_route = DailyRoute.objects.get(user=user, date=report_date)
        route = daily_route.route
    except DailyRoute.DoesNotExist:
        # First time accessing this date - redirect to set route
        return redirect('sales:eod_set_route', date=date)
    
    # Get business profile for area
    business = DistributorProfile.objects.filter(is_active=True).first()
    area = business.city if business else 'N/A'
    
    # Get active case value for this date (global setting)
    case_value = GlobalCaseValueSetting.get_active_case_value(report_date)
    
    # Get all confirmed bills for this date
    bills = Bill.objects.filter(
        sales_rep=user,
        bill_date__date=report_date,
        bill_status='confirmed'
    ).prefetch_related('items__product')
    
    # Calculate totals
    total_sale = bills.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    bill_count = bills.count()
    
    # Calculate total pack
    total_pack = total_sale / case_value if case_value > 0 else Decimal('0')
    
    # Get new outlets registered today
    new_outlets = Shop.objects.filter(created_by=user, created_at__date=report_date).count()
    
    # Get FOC value (from FOCValueTransaction)
    from products.models import FOCValueTransaction
    foc_transactions = FOCValueTransaction.objects.filter(
        bill_item__bill__sales_rep=user,
        bill_item__bill__bill_date__date=report_date,
        bill_item__bill__bill_status='confirmed',
        transaction_type='explicit'
    )
    total_foc_value = foc_transactions.aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
    
    # Get total FOC value given (all FOC transactions including ratio-based)
    all_foc_transactions = FOCValueTransaction.objects.filter(
        bill_item__bill__sales_rep=user,
        bill_item__bill__bill_date__date=report_date,
        bill_item__bill__bill_status='confirmed'
    )
    total_foc_given = all_foc_transactions.aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
    
    # Get payment method breakdowns
    from payments.models import SalesAccountSettlement
    
    # Calculate CREDIT (remaining unpaid balance of today's bills)
    # Get all settlements for today's bills (exclude cancelled and bounced)
    settlements_for_todays_bills = SalesAccountSettlement.objects.filter(
        bill__sales_rep=user,
        bill__bill_date__date=report_date,
        bill__bill_status='confirmed'
    ).exclude(settlement_status__in=['cancelled', 'bounced'])
    total_settled = settlements_for_todays_bills.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_credit = total_sale - total_settled  # Remaining balance
    
    # Include cheques received today (exclude cancelled and bounced)
    all_cheques = SalesAccountSettlement.objects.filter(
        received_by=user,
        settlement_date__date=report_date,
        settlement_method='cheque'
    ).exclude(settlement_status__in=['cancelled', 'bounced'])
    total_cheque = all_cheques.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Group products by size and get product breakdown
    # Get all active products sorted by display_order
    all_products = Product.objects.filter(
        is_active=True
    ).select_related('company').order_by('display_order', 'product_name')
    
    # Get sold quantities for this date
    sold_items = BillItem.objects.filter(
        bill__sales_rep=user,
        bill__bill_date__date=report_date,
        bill__bill_status='confirmed'
    ).values('product_id').annotate(total_qty=Sum('quantity'))
    
    # Create a dict for quick lookup of sold quantities
    sold_qty_dict = {item['product_id']: item['total_qty'] for item in sold_items}
    
    # Build product breakdown - maintain display_order within each size
    from collections import OrderedDict
    product_breakdown = OrderedDict()
    
    for product in all_products:
        size = product.size
        
        if size not in product_breakdown:
            product_breakdown[size] = []
        
        # Get quantity sold (0 if not sold)
        quantity = sold_qty_dict.get(product.id, 0)
        
        product_breakdown[size].append({
            'name': product.product_name,
            'quantity': quantity
        })
    
    # Use the OrderedDict as-is to preserve insertion order
    sorted_breakdown = product_breakdown
    
    # Get returns for this date
    returns = Return.objects.filter(
        created_by=user,
        return_date__date=report_date
    )
    total_return_value = returns.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    return_count = returns.count()
    
    # Get print profile for thermal receipt preview
    from sales.print_engine import UnifiedPrintEngine
    
    # Use unified print engine for consistent branding (same as all receipts)
    engine = UnifiedPrintEngine(user, receipt_type='field_receipt')
    print_context = engine.get_print_context({})
    
    # Build context with EOD data, then merge engine context on top
    context = {
        'date': report_date,
        'area': area,
        'route': route,
        'user_name': user.get_full_name() or user.username,
        'product_breakdown': sorted_breakdown,
        'total_sale': total_sale,
        'total_pack': total_pack,
        'bill_count': bill_count,
        'new_outlets': new_outlets,
        'total_foc_given': total_foc_given,
        'total_credit': total_credit,
        'total_cheque': total_cheque,
        'total_return_value': total_return_value,
        'return_count': return_count,
        'case_value': case_value,
        'page_title': f'EOD Report - {report_date}',
    }
    # Merge all engine keys (branding, print_profile, footer_text, fonts, logo, paper_specs, etc.)
    context.update(print_context)
    
    return render(request, 'sales/eod_detail.html', context)


@login_required
def eod_set_route(request, date):
    """
    Set route for a date (first time access)
    """
    if request.method == 'POST':
        user = request.user
        report_date = datetime.strptime(date, '%Y-%m-%d').date()
        route_input = request.POST.get('route')
        
        DailyRoute.objects.create(
            user=user,
            date=report_date,
            route=route_input
        )
        
        messages.success(request, 'Route set successfully!')
        return redirect('sales:eod_detail', date=date)
    
    # GET request - show route entry form
    report_date = datetime.strptime(date, '%Y-%m-%d').date()
    context = {
        'date': report_date,
        'page_title': 'Set Route'
    }
    return render(request, 'sales/eod_set_route.html', context)


@login_required
def eod_update_route(request, date):
    """
    Update route for a specific date
    """
    if request.method == 'POST':
        user = request.user
        report_date = datetime.strptime(date, '%Y-%m-%d').date()
        route_input = request.POST.get('route')
        
        daily_route, created = DailyRoute.objects.update_or_create(
            user=user,
            date=report_date,
            defaults={'route': route_input}
        )
        
        messages.success(request, 'Route updated successfully!')
        return redirect('sales:eod_detail', date=date)
    
    return redirect('sales:eod_detail', date=date)


@login_required
def eod_export_text(request, date):
    """
    Export EOD report as plain text
    """
    user = request.user
    report_date = datetime.strptime(date, '%Y-%m-%d').date()
    
    # Get daily route
    try:
        daily_route = DailyRoute.objects.get(user=user, date=report_date)
        route = daily_route.route
    except DailyRoute.DoesNotExist:
        route = 'Not set'
    
    # Get business profile
    business = DistributorProfile.objects.filter(is_active=True).first()
    area = business.city if business else 'N/A'
    
    # Get data (same as eod_detail)
    case_value = GlobalCaseValueSetting.get_active_case_value(report_date)
    bills = Bill.objects.filter(
        sales_rep=user,
        bill_date__date=report_date,
        bill_status='confirmed'
    )
    
    total_sale = bills.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    bill_count = bills.count()
    total_pack = total_sale / case_value if case_value > 0 else Decimal('0')
    new_outlets = Shop.objects.filter(created_by=user, created_at__date=report_date).count()
    
    from products.models import FOCValueTransaction
    all_foc_transactions = FOCValueTransaction.objects.filter(
        bill_item__bill__sales_rep=user,
        bill_item__bill__bill_date__date=report_date,
        bill_item__bill__bill_status='confirmed'
    )
    total_foc_given = all_foc_transactions.aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
    
    # Get payment method breakdowns
    from payments.models import SalesAccountSettlement
    
    # Calculate CREDIT (remaining unpaid balance of today's bills)
    # Get all settlements for today's bills (exclude cancelled and bounced)
    settlements_for_todays_bills = SalesAccountSettlement.objects.filter(
        bill__sales_rep=user,
        bill__bill_date__date=report_date,
        bill__bill_status='confirmed'
    ).exclude(settlement_status__in=['cancelled', 'bounced'])
    total_settled = settlements_for_todays_bills.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_credit = total_sale - total_settled  # Remaining balance
    
    # Include cheques received today (exclude cancelled and bounced)
    all_cheques = SalesAccountSettlement.objects.filter(
        received_by=user,
        settlement_date__date=report_date,
        settlement_method='cheque'
    ).exclude(settlement_status__in=['cancelled', 'bounced'])
    total_cheque = all_cheques.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Product breakdown - Show all active products
    # Get all active products sorted by display_order
    all_products = Product.objects.filter(
        is_active=True
    ).select_related('company').order_by('display_order', 'product_name')
    
    # Get sold quantities for this date
    sold_items = BillItem.objects.filter(
        bill__sales_rep=user,
        bill__bill_date__date=report_date,
        bill__bill_status='confirmed'
    ).values('product_id').annotate(total_qty=Sum('quantity'))
    
    # Create a dict for quick lookup of sold quantities
    sold_qty_dict = {item['product_id']: item['total_qty'] for item in sold_items}
    
    # Build product breakdown - maintain display_order within each size
    from collections import OrderedDict
    product_breakdown = OrderedDict()
    
    for product in all_products:
        size = product.size
        
        if size not in product_breakdown:
            product_breakdown[size] = []
        
        # Get quantity sold (0 if not sold)
        quantity = sold_qty_dict.get(product.id, 0)
        
        product_breakdown[size].append({
            'name': product.product_name,
            'quantity': quantity
        })
    
    # Build text output
    text_lines = []
    text_lines.append(f"DATE: {report_date}")
    text_lines.append(f"AREA: {area}")
    text_lines.append(f"ROUTE: {route}")
    text_lines.append(f"Sales Rep: {user.get_full_name() or user.username}")
    text_lines.append("")
    
    # Product breakdown - iterate in insertion order
    for size, products in product_breakdown.items():
        text_lines.append(f"{size}")
        for product in products:
            text_lines.append(f"{product['name']}: {int(product['quantity'])}")
        text_lines.append("")
    
    text_lines.append("")
    text_lines.append(f"TOTAL SALE: Rs. {total_sale:,.2f}")
    text_lines.append(f"TOTAL PACK: {total_pack:,.2f}")
    text_lines.append(f"P/C: {bill_count}")
    text_lines.append(f"N/O: {new_outlets:02d}")
    text_lines.append(f"FOC GIVEN: Rs. {total_foc_given:,.2f}")
    text_lines.append(f"CREDIT: Rs. {total_credit:,.2f}")
    text_lines.append(f"CHEQUE: Rs. {total_cheque:,.2f}")
    
    # Get returns for this date
    returns = Return.objects.filter(
        created_by=user,
        return_date__date=report_date
    )
    total_return_value = returns.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    return_count = returns.count()
    text_lines.append(f"RETURNS: Rs. {total_return_value:,.2f}")
    text_lines.append(f"({return_count} return{'s' if return_count != 1 else ''})")
    
    text_content = "\n".join(text_lines)
    
    response = HttpResponse(text_content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="EOD_{report_date}_{user.username}.txt"'
    
    return response


@login_required
def eod_export_pdf(request, date):
    """
    Export EOD report as PDF
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from io import BytesIO
    
    user = request.user
    report_date = datetime.strptime(date, '%Y-%m-%d').date()
    
    # Get data (same as text export)
    try:
        daily_route = DailyRoute.objects.get(user=user, date=report_date)
        route = daily_route.route
    except DailyRoute.DoesNotExist:
        route = 'Not set'
    
    business = DistributorProfile.objects.filter(is_active=True).first()
    area = business.city if business else 'N/A'
    
    case_value = GlobalCaseValueSetting.get_active_case_value(report_date)
    bills = Bill.objects.filter(
        sales_rep=user,
        bill_date__date=report_date,
        bill_status='confirmed'
    )
    
    total_sale = bills.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    bill_count = bills.count()
    total_pack = total_sale / case_value if case_value > 0 else Decimal('0')
    new_outlets = Shop.objects.filter(created_by=user, created_at__date=report_date).count()
    
    from products.models import FOCValueTransaction
    all_foc_transactions = FOCValueTransaction.objects.filter(
        bill_item__bill__sales_rep=user,
        bill_item__bill__bill_date__date=report_date,
        bill_item__bill__bill_status='confirmed'
    )
    total_foc_given = all_foc_transactions.aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
    
    # Get payment method breakdowns
    from payments.models import SalesAccountSettlement
    
    # Calculate CREDIT (remaining unpaid balance of today's bills)
    # Get all settlements for today's bills (exclude cancelled and bounced)
    settlements_for_todays_bills = SalesAccountSettlement.objects.filter(
        bill__sales_rep=user,
        bill__bill_date__date=report_date,
        bill__bill_status='confirmed'
    ).exclude(settlement_status__in=['cancelled', 'bounced'])
    total_settled = settlements_for_todays_bills.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_credit = total_sale - total_settled  # Remaining balance
    
    # Include cheques received today (exclude cancelled and bounced)
    all_cheques = SalesAccountSettlement.objects.filter(
        received_by=user,
        settlement_date__date=report_date,
        settlement_method='cheque'
    ).exclude(settlement_status__in=['cancelled', 'bounced'])
    total_cheque = all_cheques.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Product breakdown - Show all active products
    # Get all active products sorted by display_order
    all_products = Product.objects.filter(
        is_active=True
    ).select_related('company').order_by('display_order', 'product_name')
    
    # Get sold quantities for this date
    sold_items = BillItem.objects.filter(
        bill__sales_rep=user,
        bill__bill_date__date=report_date,
        bill__bill_status='confirmed'
    ).values('product_id').annotate(total_qty=Sum('quantity'))
    
    # Create a dict for quick lookup of sold quantities
    sold_qty_dict = {item['product_id']: item['total_qty'] for item in sold_items}
    
    # Build product breakdown - maintain display_order within each size
    from collections import OrderedDict
    product_breakdown = OrderedDict()
    
    for product in all_products:
        size = product.size
        
        if size not in product_breakdown:
            product_breakdown[size] = []
        
        # Get quantity sold (0 if not sold)
        quantity = sold_qty_dict.get(product.id, 0)
        
        product_breakdown[size].append({
            'name': product.product_name,
            'quantity': quantity
        })
    
    # Create PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Header
    y_position = height - 40*mm
    p.setFont("Helvetica-Bold", 16)
    p.drawString(20*mm, y_position, "END OF DAY REPORT")
    
    y_position -= 10*mm
    p.setFont("Helvetica", 10)
    p.drawString(20*mm, y_position, f"DATE: {report_date}")
    
    y_position -= 5*mm
    p.drawString(20*mm, y_position, f"AREA: {area}")
    
    y_position -= 5*mm
    p.drawString(20*mm, y_position, f"ROUTE: {route}")
    
    y_position -= 5*mm
    p.drawString(20*mm, y_position, f"Sales Rep: {user.get_full_name() or user.username}")
    
    y_position -= 10*mm
    
    # Product breakdown - iterate in insertion order
    p.setFont("Helvetica-Bold", 11)
    for size, products in product_breakdown.items():
        if y_position < 40*mm:  # New page if needed
            p.showPage()
            y_position = height - 40*mm
        
        p.setFont("Helvetica-Bold", 11)
        p.drawString(20*mm, y_position, f"{size}")
        y_position -= 5*mm
        
        p.setFont("Helvetica", 10)
        for product in products:
            p.drawString(30*mm, y_position, f"{product['name']}: {int(product['quantity'])}")
            y_position -= 4*mm
        
        y_position -= 3*mm
    
    # Totals
    y_position -= 5*mm
    if y_position < 60*mm:
        p.showPage()
        y_position = height - 40*mm
    
    p.setFont("Helvetica-Bold", 11)
    p.drawString(20*mm, y_position, "SUMMARY")
    y_position -= 6*mm
    
    p.setFont("Helvetica", 10)
    p.drawString(20*mm, y_position, f"TOTAL SALE: Rs. {total_sale:,.2f}")
    y_position -= 5*mm
    
    p.drawString(20*mm, y_position, f"TOTAL PACK: {total_pack:.2f}")
    y_position -= 5*mm
    
    p.drawString(20*mm, y_position, f"P/C (Bill Count): {bill_count}")
    y_position -= 5*mm
    
    p.drawString(20*mm, y_position, f"N/O (New Outlets): {new_outlets:02d}")
    y_position -= 5*mm
    
    p.drawString(20*mm, y_position, f"FOC GIVEN: Rs. {total_foc_given:,.2f}")
    y_position -= 5*mm
    
    p.drawString(20*mm, y_position, f"CREDIT: Rs. {total_credit:,.2f}")
    y_position -= 5*mm
    
    p.drawString(20*mm, y_position, f"CHEQUE: Rs. {total_cheque:,.2f}")
    y_position -= 5*mm
    
    # Get returns for this date
    returns = Return.objects.filter(
        created_by=user,
        return_date__date=report_date
    )
    total_return_value = returns.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    return_count = returns.count()
    p.drawString(20*mm, y_position, f"RETURNS: Rs. {total_return_value:,.2f} ({return_count} return{'s' if return_count != 1 else ''})")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="EOD_{report_date}_{user.username}.pdf"'
    
    return response
