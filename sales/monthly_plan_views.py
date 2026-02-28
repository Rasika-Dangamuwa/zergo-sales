"""
Monthly Plan Views
Created: February 20, 2026

Views for creating, editing, viewing, and exporting monthly sales plans.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.db.models.functions import ExtractDay
from django.utils import timezone
from django.http import HttpResponse
from decimal import Decimal
from datetime import date
import calendar

from .monthly_plan_models import MonthlyPlan, MonthlyPlanDay
from tenants.models import GlobalCaseValueSetting
from .models import Bill, BillItem
from shops.models import Shop
from business.models import DistributorProfile


def _get_achievements(user, year, month):
    """
    Compute daily achievements for a user in a given month.
    Returns dict: {day_number: {rd, pc, no, purchase}}
    - R/D: total cases (total_sale / case_value)
    - P/C: confirmed bill count
    - N/O: new shops created
    - Purchase: total cases (packs) from all business purchases
    """
    from products.models import PurchaseItem

    achievements = {}
    days_in_month = calendar.monthrange(year, month)[1]

    # Pre-compute case values per day (case value can change mid-month)
    case_values = {}
    for d in range(1, days_in_month + 1):
        case_values[d] = GlobalCaseValueSetting.get_active_case_value(date(year, month, d))

    # Bills per day
    bills_agg = (
        Bill.objects.filter(
            sales_rep=user,
            bill_date__year=year,
            bill_date__month=month,
            bill_status='confirmed'
        )
        .annotate(bill_day=ExtractDay('bill_date'))
        .values('bill_day')
        .annotate(
            bill_count=Count('id'),
            total_sale=Sum('total_amount'),
        )
    )

    bill_data = {}
    for row in bills_agg:
        bill_data[row['bill_day']] = {
            'count': row['bill_count'],
            'total_sale': row['total_sale'] or Decimal('0'),
        }

    # New outlets per day
    new_outlets_agg = (
        Shop.objects.filter(
            created_by=user,
            created_at__year=year,
            created_at__month=month,
        )
        .annotate(shop_day=ExtractDay('created_at'))
        .values('shop_day')
        .annotate(count=Count('id'))
    )
    outlets_data = {row['shop_day']: row['count'] for row in new_outlets_agg}

    # Purchase cases per day (all business purchases, not per-user)
    purchase_agg = (
        PurchaseItem.objects.filter(
            purchase__grn_date__year=year,
            purchase__grn_date__month=month,
        )
        .exclude(purchase__status='cancelled')
        .annotate(grn_day=ExtractDay('purchase__grn_date'))
        .values('grn_day')
        .annotate(total_cases=Sum('packs'))
    )
    purchase_data = {row['grn_day']: row['total_cases'] or 0 for row in purchase_agg}

    for d in range(1, days_in_month + 1):
        bd = bill_data.get(d, {'count': 0, 'total_sale': Decimal('0')})
        cv = case_values[d]
        rd_cases = bd['total_sale'] / cv if cv > 0 else Decimal('0')
        achievements[d] = {
            'rd': round(rd_cases, 2),
            'pc': bd['count'],
            'no': outlets_data.get(d, 0),
            'purchase': purchase_data.get(d, 0),
        }

    return achievements


@login_required
def monthly_plan_list(request):
    """List user's monthly plans. Office/admin can view all users' plans."""
    user = request.user
    view_user_id = request.GET.get('user')

    # Office/admin can view other users' plans
    if view_user_id and user.user_type in ('admin', 'office'):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            view_user = User.objects.get(pk=view_user_id)
        except User.DoesNotExist:
            view_user = user
    else:
        view_user = user

    plans = MonthlyPlan.objects.filter(user=view_user).select_related('user')

    # For office: get all users for dropdown
    all_users = None
    if user.user_type in ('admin', 'office'):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        all_users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')

    context = {
        'plans': plans,
        'view_user': view_user,
        'all_users': all_users,
        'page_title': 'Monthly Plans',
    }
    return render(request, 'sales/monthly_plan_list.html', context)


@login_required
def monthly_plan_create(request):
    """Create or edit a monthly plan."""
    user = request.user

    if request.method == 'POST':
        year = int(request.POST.get('year', timezone.localdate().year))
        month = int(request.POST.get('month', timezone.localdate().month))
        area = request.POST.get('area', '')

        # Check if plan already exists
        plan, created = MonthlyPlan.objects.get_or_create(
            user=user,
            year=year,
            month=month,
            defaults={'area': area}
        )
        if not created:
            plan.area = area
            plan.save()

        # Save daily entries
        days_in_month = calendar.monthrange(year, month)[1]
        for d in range(1, days_in_month + 1):
            route = request.POST.get(f'route_{d}', '').strip()
            is_off = route.lower() == 'off' or request.POST.get(f'off_{d}') == '1'
            target_rd = int(request.POST.get(f'rd_{d}', 0) or 0)
            target_pc = int(request.POST.get(f'pc_{d}', 0) or 0)
            target_no = int(request.POST.get(f'no_{d}', 0) or 0)
            target_purchase = int(request.POST.get(f'purchase_{d}', 0) or 0)

            if is_off:
                route = 'Off'
                target_rd = 0
                target_pc = 0
                target_no = 0
                target_purchase = 0

            MonthlyPlanDay.objects.update_or_create(
                plan=plan,
                day=d,
                defaults={
                    'route': route,
                    'is_off': is_off,
                    'target_rd': target_rd,
                    'target_pc': target_pc,
                    'target_no': target_no,
                    'target_purchase': target_purchase,
                }
            )

        messages.success(request, f'Monthly plan for {calendar.month_name[month]} {year} saved successfully.')
        return redirect('sales:monthly_plan_detail', pk=plan.pk)

    # GET - show form
    year = int(request.GET.get('year', timezone.localdate().year))
    month = int(request.GET.get('month', timezone.localdate().month))

    # Check if editing existing plan
    existing = MonthlyPlan.objects.filter(user=user, year=year, month=month).first()
    existing_days = {}
    if existing:
        for pd in existing.days.all():
            existing_days[pd.day] = pd

    # Build day data
    days_in_month = calendar.monthrange(year, month)[1]
    days = []
    for d in range(1, days_in_month + 1):
        day_date = date(year, month, d)
        day_name = calendar.day_abbr[day_date.weekday()]
        ex = existing_days.get(d)
        days.append({
            'day': d,
            'day_name': day_name,
            'is_sunday': day_date.weekday() == 6,
            'route': ex.route if ex else '',
            'is_off': ex.is_off if ex else False,
            'target_rd': ex.target_rd if ex else 0,
            'target_pc': ex.target_pc if ex else 0,
            'target_no': ex.target_no if ex else 0,
            'target_purchase': ex.target_purchase if ex else 0,
        })

    # Business profile for area default
    business = DistributorProfile.objects.filter(is_active=True).first()
    default_area = business.city if business else ''

    # Year/month options
    current_year = timezone.localdate().year
    years = list(range(current_year - 1, current_year + 2))
    months_list = [(i, calendar.month_name[i]) for i in range(1, 13)]

    context = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'days': days,
        'existing': existing,
        'default_area': existing.area if existing else default_area,
        'years': years,
        'months': months_list,
        'page_title': f'{"Edit" if existing else "Create"} Monthly Plan - {calendar.month_name[month]} {year}',
    }
    return render(request, 'sales/monthly_plan_create.html', context)


@login_required
def monthly_plan_detail(request, pk):
    """View a monthly plan with auto-filled achievements and cumulative targets."""
    plan = get_object_or_404(MonthlyPlan, pk=pk)

    # Access control: owner or office/admin
    if plan.user != request.user and request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('sales:monthly_plan_list')

    # Get daily plan entries
    plan_days = {pd.day: pd for pd in plan.days.all()}

    # Get achievements
    achievements = _get_achievements(plan.user, plan.year, plan.month)

    # Build rows with cumulative targets and cumulative achievements
    rows = []
    cum_target = {'rd': 0, 'pc': 0, 'no': 0, 'purchase': 0}
    cum_achievement = {'rd': Decimal('0'), 'pc': 0, 'no': 0, 'purchase': 0}
    total_target = {'rd': 0, 'pc': 0, 'no': 0, 'purchase': 0}
    total_achievement = {'rd': Decimal('0'), 'pc': 0, 'no': 0, 'purchase': 0}

    for d in range(1, plan.days_in_month + 1):
        day_date = date(plan.year, plan.month, d)
        day_name = calendar.day_abbr[day_date.weekday()]
        pd_obj = plan_days.get(d)
        ach = achievements.get(d, {'rd': 0, 'pc': 0, 'no': 0, 'purchase': 0})

        target = {
            'rd': pd_obj.target_rd if pd_obj else 0,
            'pc': pd_obj.target_pc if pd_obj else 0,
            'no': pd_obj.target_no if pd_obj else 0,
            'purchase': pd_obj.target_purchase if pd_obj else 0,
        }

        # Accumulate targets
        for key in cum_target:
            cum_target[key] += target[key]
            total_target[key] += target[key]

        # Accumulate achievements (running total)
        for key in cum_achievement:
            cum_achievement[key] += ach[key]
            total_achievement[key] = cum_achievement[key]  # total = final cumulative

        rows.append({
            'day': d,
            'day_name': day_name,
            'is_off': pd_obj.is_off if pd_obj else False,
            'route': pd_obj.route if pd_obj else '',
            'target': target,
            'daily_achievement': {  # daily (non-cumulative) achievement
                'rd': round(ach['rd'], 2),
                'pc': ach['pc'],
                'no': ach['no'],
                'purchase': ach['purchase'],
            },
            'achievement': {  # cumulative achievement
                'rd': round(cum_achievement['rd'], 2),
                'pc': cum_achievement['pc'],
                'no': cum_achievement['no'],
                'purchase': cum_achievement['purchase'],
            },
            'cum_target': dict(cum_target),  # copy
            'is_past': day_date < timezone.localdate(),
            'is_today': day_date == timezone.localdate(),
        })

    # Smart back button
    referer = request.META.get('HTTP_REFERER', '')
    if '/dashboard/' in referer:
        back_url = referer
        back_label = 'Back to Dashboard'
    else:
        back_url = request.path.rsplit('/', 2)[0] + '/'
        back_label = 'Back to Plans'

    context = {
        'plan': plan,
        'rows': rows,
        'total_target': total_target,
        'total_achievement': {
            'rd': round(total_achievement['rd'], 2),
            'pc': total_achievement['pc'],
            'no': total_achievement['no'],
            'purchase': total_achievement['purchase'],
        },
        'back_url': back_url,
        'back_label': back_label,
        'page_title': f'Monthly Plan - {plan.get_month_display()} {plan.year}',
    }
    return render(request, 'sales/monthly_plan_detail.html', context)


@login_required
def monthly_plan_export_pdf(request, pk):
    """Export monthly plan as PDF matching the attached spreadsheet layout."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from io import BytesIO

    plan = get_object_or_404(MonthlyPlan, pk=pk)

    # Access control
    if plan.user != request.user and request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('sales:monthly_plan_list')

    plan_days = {pd.day: pd for pd in plan.days.all()}
    achievements = _get_achievements(plan.user, plan.year, plan.month)

    # Setup PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('PlanTitle', parent=styles['Title'], fontSize=14, alignment=TA_CENTER, spaceAfter=2)
    header_style = ParagraphStyle('PlanHeader', parent=styles['Normal'], fontSize=8, alignment=TA_LEFT)
    header_right = ParagraphStyle('PlanHeaderRight', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT, fontName='Helvetica-Bold')
    cell_style = ParagraphStyle('PlanCell', parent=styles['Normal'], fontSize=6, alignment=TA_CENTER)
    cell_left = ParagraphStyle('PlanCellLeft', parent=styles['Normal'], fontSize=6, alignment=TA_LEFT)
    cell_bold = ParagraphStyle('PlanCellBold', parent=styles['Normal'], fontSize=6, alignment=TA_CENTER, fontName='Helvetica-Bold')
    cell_bold_left = ParagraphStyle('PlanCellBoldLeft', parent=cell_bold, alignment=TA_LEFT)

    elements = []

    # Title
    elements.append(Paragraph('Monthly Plan', title_style))
    elements.append(Spacer(1, 2 * mm))

    # Header info table
    total_targets = plan.get_total_targets()
    user_name = plan.user.get_full_name() or plan.user.username

    header_data = [
        [
            Paragraph(f'<b>Name:</b> {user_name}', header_style),
            '', '',
            Paragraph(f'<b>Total R/D Target: {total_targets["rd"]:,}</b>', header_right),
        ],
        [
            Paragraph(f'<b>Area:</b> {plan.area}', header_style),
            '', '',
            Paragraph(f'<b>Total P/C Target: {total_targets["pc"]:,}</b>', header_right),
        ],
        [
            Paragraph(f'<b>Month/Year:</b> {plan.get_month_display()} {plan.year}', header_style),
            '', '',
            Paragraph(f'<b>Total New Outlet Target: {total_targets["no"]:,}</b>', header_right),
        ],
    ]
    header_table = Table(header_data, colWidths=[80 * mm, 40 * mm, 40 * mm, 80 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3 * mm))

    # Main data table - Header rows
    col_headers_row1 = [
        Paragraph('', cell_bold),   # Date
        Paragraph('', cell_bold),   # Route
        Paragraph('<b>Target</b>', cell_bold),
        Paragraph('', cell_bold), Paragraph('', cell_bold), Paragraph('', cell_bold),
        Paragraph('<b>Achievement</b>', cell_bold),
        Paragraph('', cell_bold), Paragraph('', cell_bold), Paragraph('', cell_bold),
        Paragraph('<b>Cum Target</b>', cell_bold),
        Paragraph('', cell_bold), Paragraph('', cell_bold), Paragraph('', cell_bold),
    ]

    col_headers_row2 = [
        Paragraph('<b>Date</b>', cell_bold),
        Paragraph('<b>Route</b>', cell_bold_left),
        Paragraph('<b>R/D</b>', cell_bold), Paragraph('<b>P/C</b>', cell_bold),
        Paragraph('<b>N/O</b>', cell_bold), Paragraph('<b>Purchase</b>', cell_bold),
        Paragraph('<b>R/D</b>', cell_bold), Paragraph('<b>P/C</b>', cell_bold),
        Paragraph('<b>N/O</b>', cell_bold), Paragraph('<b>Purchase</b>', cell_bold),
        Paragraph('<b>R/D</b>', cell_bold), Paragraph('<b>P/C</b>', cell_bold),
        Paragraph('<b>N/O</b>', cell_bold), Paragraph('<b>Purchase</b>', cell_bold),
    ]

    data_rows = [col_headers_row1, col_headers_row2]

    cum_target = {'rd': 0, 'pc': 0, 'no': 0, 'purchase': 0}
    cum_ach = {'rd': Decimal('0'), 'pc': 0, 'no': 0, 'purchase': 0}
    total_target = {'rd': 0, 'pc': 0, 'no': 0, 'purchase': 0}

    def fmt(v):
        """Format value with commas, blank for zero."""
        if not v:
            return ''
        if isinstance(v, Decimal):
            return f'{v:,.2f}'
        return f'{v:,}'

    def fmta(v):
        """Format value with commas, always show (even zero)."""
        if isinstance(v, Decimal):
            return f'{v:,.2f}'
        return f'{v:,}'

    for d in range(1, plan.days_in_month + 1):
        pd_obj = plan_days.get(d)
        ach = achievements.get(d, {'rd': 0, 'pc': 0, 'no': 0, 'purchase': 0})

        is_off = pd_obj.is_off if pd_obj else False
        route = pd_obj.route if pd_obj else ''
        t_rd = pd_obj.target_rd if pd_obj and not is_off else 0
        t_pc = pd_obj.target_pc if pd_obj and not is_off else 0
        t_no = pd_obj.target_no if pd_obj and not is_off else 0
        t_pur = pd_obj.target_purchase if pd_obj and not is_off else 0

        cum_target['rd'] += t_rd
        cum_target['pc'] += t_pc
        cum_target['no'] += t_no
        cum_target['purchase'] += t_pur
        total_target['rd'] += t_rd
        total_target['pc'] += t_pc
        total_target['no'] += t_no
        total_target['purchase'] += t_pur

        # Cumulative achievements
        for key in cum_ach:
            cum_ach[key] += ach[key]

        if is_off:
            row = [
                Paragraph(str(d), cell_style),
                Paragraph('Off', cell_left),
                Paragraph('', cell_style), Paragraph('', cell_style),
                Paragraph('', cell_style), Paragraph('', cell_style),
                Paragraph(fmt(cum_ach['rd']), cell_style),
                Paragraph(fmt(cum_ach['pc']), cell_style),
                Paragraph(fmt(cum_ach['no']), cell_style),
                Paragraph(fmt(cum_ach['purchase']), cell_style),
                Paragraph(fmta(cum_target['rd']), cell_style),
                Paragraph(fmta(cum_target['pc']), cell_style),
                Paragraph(fmta(cum_target['no']), cell_style),
                Paragraph(fmta(cum_target['purchase']), cell_style),
            ]
        else:
            row = [
                Paragraph(str(d), cell_style),
                Paragraph(route, cell_left),
                Paragraph(fmt(t_rd), cell_style),
                Paragraph(fmt(t_pc), cell_style),
                Paragraph(fmt(t_no), cell_style),
                Paragraph(fmt(t_pur), cell_style),
                Paragraph(fmt(cum_ach['rd']), cell_style),
                Paragraph(fmt(cum_ach['pc']), cell_style),
                Paragraph(fmt(cum_ach['no']), cell_style),
                Paragraph(fmt(cum_ach['purchase']), cell_style),
                Paragraph(fmta(cum_target['rd']), cell_style),
                Paragraph(fmta(cum_target['pc']), cell_style),
                Paragraph(fmta(cum_target['no']), cell_style),
                Paragraph(fmta(cum_target['purchase']), cell_style),
            ]
        data_rows.append(row)

    # Total row
    total_row = [
        Paragraph('', cell_bold),
        Paragraph('<b>Total</b>', cell_bold_left),
        Paragraph(f'<b>{total_target["rd"]:,}</b>', cell_bold),
        Paragraph(f'<b>{total_target["pc"]:,}</b>', cell_bold),
        Paragraph(f'<b>{total_target["no"]:,}</b>', cell_bold),
        Paragraph(f'<b>{total_target["purchase"]:,}</b>', cell_bold),
        Paragraph(f'<b>{cum_ach["rd"]:,.2f}</b>', cell_bold),
        Paragraph(f'<b>{cum_ach["pc"]:,}</b>', cell_bold),
        Paragraph(f'<b>{cum_ach["no"]:,}</b>', cell_bold),
        Paragraph(f'<b>{cum_ach["purchase"]:,}</b>', cell_bold),
        Paragraph('', cell_bold), Paragraph('', cell_bold),
        Paragraph('', cell_bold), Paragraph('', cell_bold),
    ]
    data_rows.append(total_row)

    # Column widths (landscape A4 usable ~257mm)
    col_widths = [
        10 * mm,   # Date
        42 * mm,   # Route
        15 * mm, 15 * mm, 12 * mm, 18 * mm,  # Target
        15 * mm, 15 * mm, 12 * mm, 18 * mm,  # Achievement
        15 * mm, 15 * mm, 12 * mm, 18 * mm,  # Cum Target
    ]

    main_table = Table(data_rows, colWidths=col_widths, repeatRows=2)

    # Table styling
    style_commands = [
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        # Header row 1 spans
        ('SPAN', (2, 0), (5, 0)),    # Target
        ('SPAN', (6, 0), (9, 0)),    # Achievement
        ('SPAN', (10, 0), (13, 0)),  # Cum Target
        ('SPAN', (0, 0), (0, 1)),    # Date
        ('SPAN', (1, 0), (1, 1)),    # Route
        # Header background
        ('BACKGROUND', (0, 0), (-1, 1), colors.Color(0.9, 0.9, 0.9)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.9, 0.9)),
        # Alignment
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 1.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]

    # Highlight "Off" day rows
    for i, d in enumerate(range(1, plan.days_in_month + 1)):
        pd_obj = plan_days.get(d)
        if pd_obj and pd_obj.is_off:
            row_idx = i + 2  # offset for 2 header rows
            style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.Color(0.95, 0.95, 0.95)))

    main_table.setStyle(TableStyle(style_commands))
    elements.append(main_table)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    filename = f"Monthly_Plan_{user_name.replace(' ', '_')}_{plan.get_month_display()}_{plan.year}.pdf"
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
