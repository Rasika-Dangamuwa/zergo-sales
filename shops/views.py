from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
# from django.contrib.gis.geos import Point
from .models import Shop, ShopVisit, ShopAccess
from accounts.models import SalesRepLocation, User
from .location_utils import get_nearby_shops
import json


@login_required
def shop_list(request):
    """List all shops with access level awareness, pending items, and rich stats"""
    from django.db.models import Sum, Count, Q, F, Value, IntegerField, DecimalField, Subquery, OuterRef
    from django.db.models.functions import Coalesce
    from django.utils import timezone
    from datetime import timedelta, datetime
    from decimal import Decimal
    from sales.models import Bill, Return
    from payments.models import SalesAccountSettlement
    from shops.models import ShopPhotoHistory
    
    now = timezone.now()
    local_now = timezone.localtime(now)
    today = local_now.date()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)
    
    # ====== DATE-RANGE FILTER (registration date) ======
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    date_preset = request.GET.get('date_preset', '')  # today, 7d, 30d, 90d, all
    
    base_qs = Shop.objects.filter(is_active=True)
    
    # Status filter (admin/office can view inactive shops)
    status_filter = request.GET.get('status', 'active')
    if not request.user.is_sales_rep:
        if status_filter == 'inactive':
            base_qs = Shop.objects.filter(is_active=False)
        elif status_filter == 'all':
            base_qs = Shop.objects.all()
        # else: default 'active' keeps is_active=True filter
    
    # Apply date presets
    if date_preset == 'today':
        base_qs = base_qs.filter(created_at__date=today)
        date_from = today.strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')
    elif date_preset == '7d':
        base_qs = base_qs.filter(created_at__gte=seven_days_ago)
        date_from = seven_days_ago.date().strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')
    elif date_preset == '30d':
        base_qs = base_qs.filter(created_at__gte=thirty_days_ago)
        date_from = thirty_days_ago.date().strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')
    elif date_preset == '90d':
        ninety_days_ago = now - timedelta(days=90)
        base_qs = base_qs.filter(created_at__gte=ninety_days_ago)
        date_from = ninety_days_ago.date().strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')
    elif date_from or date_to:
        # Custom date range
        if date_from:
            try:
                df = datetime.strptime(date_from, '%Y-%m-%d').date()
                base_qs = base_qs.filter(created_at__date__gte=df)
            except ValueError:
                pass
        if date_to:
            try:
                dt = datetime.strptime(date_to, '%Y-%m-%d').date()
                base_qs = base_qs.filter(created_at__date__lte=dt)
            except ValueError:
                pass
    
    # Total count (before date filter) for "new shops" badge
    total_all_shops = Shop.objects.filter(is_active=True).count()
    new_shops_7d = Shop.objects.filter(is_active=True, created_at__gte=seven_days_ago).count()
    new_shops_today = Shop.objects.filter(is_active=True, created_at__date=today).count()
    
    shops = list(base_qs.select_related('created_by'))
    shop_ids = [s.id for s in shops]

    # ── Bulk: access levels for sales reps ──
    if request.user.is_sales_rep:
        access_map = {
            a['shop_id']: a['access_level']
            for a in ShopAccess.objects.filter(
                shop_id__in=shop_ids, sales_rep=request.user, is_active=True
            ).values('shop_id', 'access_level')
        }
        for shop in shops:
            shop.user_access_level = access_map.get(shop.id, 1)
    else:
        for shop in shops:
            shop.user_access_level = 3

    # ── Bulk: outstanding bills ──
    bills_filter = Q(shop_id__in=shop_ids, bill_status__in=['draft', 'confirmed'], balance_amount__gt=0)
    if request.user.is_sales_rep:
        bills_filter &= Q(sales_rep=request.user)
    bills_map = {
        b['shop_id']: b
        for b in Bill.objects.filter(bills_filter).values('shop_id').annotate(
            count=Count('id'), total=Sum('balance_amount')
        )
    }

    # ── Bulk: pending payments ──
    pay_filter = Q(shop_id__in=shop_ids, settlement_status='pending')
    if request.user.is_sales_rep:
        pay_filter &= Q(received_by=request.user)
    pay_map = {
        p['shop_id']: p
        for p in SalesAccountSettlement.objects.filter(pay_filter).values('shop_id').annotate(
            count=Count('id'), total=Sum('amount')
        )
    }

    # ── Bulk: pending returns ──
    ret_filter = Q(shop_id__in=shop_ids, is_verified=False)
    if request.user.is_sales_rep:
        ret_filter &= Q(created_by=request.user)
    ret_map = {
        r['shop_id']: r['count']
        for r in Return.objects.filter(ret_filter).exclude(
            settlement_status='cancelled'
        ).values('shop_id').annotate(count=Count('id'))
    }

    # ── Bulk: last visit per shop ──
    from django.db.models import Max
    visit_map = {
        v['shop_id']: v['last_visit']
        for v in ShopVisit.objects.filter(shop_id__in=shop_ids).values('shop_id').annotate(
            last_visit=Max('visit_date')
        )
    }

    # ── Bulk: latest photo upload date per shop ──
    one_year_ago = now - timedelta(days=365)
    photo_map = {
        p['shop_id']: p['latest']
        for p in ShopPhotoHistory.objects.filter(shop_id__in=shop_ids).values('shop_id').annotate(
            latest=Max('uploaded_at')
        )
    }

    # ── Assign all enrichment in one pass ──
    for shop in shops:
        sid = shop.id

        b = bills_map.get(sid, {})
        shop.pending_bills_count = b.get('count', 0)
        shop.total_outstanding   = b.get('total') or Decimal('0')

        p = pay_map.get(sid, {})
        shop.pending_payments_count = p.get('count', 0)
        shop.pending_payment_amount = p.get('total') or Decimal('0')

        shop.pending_returns_count = ret_map.get(sid, 0)
        shop.total_pending = shop.pending_bills_count + shop.pending_payments_count + shop.pending_returns_count

        last_visit_dt = visit_map.get(sid)
        shop.last_visit_date = last_visit_dt
        if last_visit_dt:
            shop.days_since_visit = (today - timezone.localtime(last_visit_dt).date()).days
        else:
            shop.days_since_visit = None

        latest_photo = photo_map.get(sid)
        shop.needs_photo   = (latest_photo is None) or (latest_photo < one_year_ago)
        shop.photo_message = '' if not shop.needs_photo else (
            'No photo uploaded yet' if latest_photo is None
            else f'Last photo {(now - latest_photo).days} days ago'
        )

        if shop.credit_limit and shop.credit_limit > 0:
            shop.credit_usage_pct = int((shop.total_outstanding / shop.credit_limit) * 100)
            shop.credit_bar_pct   = min(100, shop.credit_usage_pct)
        else:
            shop.credit_usage_pct = 0
            shop.credit_bar_pct   = 0
    
    # Summary stats
    shops_list = list(shops)
    total_shops = len(shops_list)
    
    # Access level counts
    level_1_count = sum(1 for s in shops_list if s.user_access_level == 1)
    level_2_count = sum(1 for s in shops_list if s.user_access_level == 2)
    level_3_count = sum(1 for s in shops_list if s.user_access_level == 3)
    
    # Pending totals
    total_pending_bills = sum(s.pending_bills_count for s in shops_list)
    total_pending_payments = sum(s.pending_payments_count for s in shops_list)
    total_pending_returns = sum(s.pending_returns_count for s in shops_list)
    total_all_pending = total_pending_bills + total_pending_payments + total_pending_returns
    grand_outstanding = sum(s.total_outstanding for s in shops_list)
    
    # Shops needing attention
    shops_with_pending = sum(1 for s in shops_list if s.total_pending > 0)
    shops_no_visit_30d = sum(1 for s in shops_list if s.days_since_visit is None or s.days_since_visit > 30)
    shops_need_photo = sum(1 for s in shops_list if s.needs_photo)
    shops_over_credit = sum(1 for s in shops_list if s.credit_usage_pct >= 80)
    
    # Identify new shops (registered within 7 days)
    for shop in shops_list:
        if shop.created_at and (today - timezone.localtime(shop.created_at).date()).days <= 7:
            shop.is_new = True
        else:
            shop.is_new = False
    
    context = {
        'shops': shops_list,
        'total_shops': total_shops,
        'total_all_shops': total_all_shops,
        # Access level counts
        'level_1_count': level_1_count,
        'level_2_count': level_2_count,
        'level_3_count': level_3_count,
        # Pending summary
        'total_pending_bills': total_pending_bills,
        'total_pending_payments': total_pending_payments,
        'total_pending_returns': total_pending_returns,
        'total_all_pending': total_all_pending,
        'grand_outstanding': grand_outstanding,
        # Attention needed
        'shops_with_pending': shops_with_pending,
        'shops_no_visit_30d': shops_no_visit_30d,
        'shops_need_photo': shops_need_photo,
        'shops_over_credit': shops_over_credit,
        # New shops
        'new_shops_7d': new_shops_7d,
        'new_shops_today': new_shops_today,
        # Date filter state
        'date_from': date_from,
        'date_to': date_to,
        'date_preset': date_preset,
        'is_date_filtered': bool(date_from or date_to or date_preset),
        'status_filter': status_filter,
    }
    return render(request, 'shops/shop_list.html', context)


@login_required
def add_shop(request):
    """Add new shop"""
    if request.method == 'POST':
        try:
            from shops.models import ShopPhotoHistory
            
            # Get location coordinates
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            
            shop = Shop.objects.create(
                shop_name=request.POST.get('shop_name'),
                owner_name=request.POST.get('owner_name'),
                shop_type=request.POST.get('shop_type'),
                phone_number=request.POST.get('phone_number'),
                alternate_phone=request.POST.get('alternate_phone'),
                email=request.POST.get('email'),
                address_line1=request.POST.get('address_line1'),
                address_line2=request.POST.get('address_line2'),
                city=request.POST.get('city'),
                district=request.POST.get('district'),
                postal_code=request.POST.get('postal_code'),
                latitude=float(latitude) if latitude else None,
                longitude=float(longitude) if longitude else None,
                credit_limit=request.POST.get('credit_limit', 0),
                assigned_sales_rep=request.user if request.user.is_sales_rep else None,
                created_by=request.user
            )
            
            # Handle shop photo upload via ShopPhotoHistory
            if request.FILES.get('shop_photo'):
                ShopPhotoHistory.objects.create(
                    shop=shop,
                    photo=request.FILES['shop_photo'],
                    uploaded_by=request.user,
                    notes=f'Initial shop photo uploaded during registration',
                    is_active=True
                )
            
            messages.success(request, f'Shop {shop.shop_name} added successfully! Shop code: {shop.shop_code}')
            return redirect('shops:detail', pk=shop.pk)
        except Exception as e:
            messages.error(request, f'Error adding shop: {str(e)}')
    
    return render(request, 'shops/add_shop.html')


@login_required
def shop_detail(request, pk):
    """World-class comprehensive shop detail view with access control"""
    from django.db.models import Sum, Count, Q, Avg, F
    from django.utils import timezone
    from datetime import timedelta
    from decimal import Decimal
    from sales.models import Bill, Return, ItemExchange
    from payments.models import SalesAccountSettlement as Payment
    from shops.models import ShopPhotoHistory
    
    shop = get_object_or_404(Shop, pk=pk)
    
    # Check access permissions
    if request.user.is_sales_rep:
        access_level = ShopAccess.get_rep_access_level(shop, request.user)
        if access_level == 1:
            messages.error(request, 'You have view-only access. Cannot view shop details page.')
            return redirect('shops:list')
        can_see_others_engagement = (access_level == 3)
    else:
        access_level = 3
        can_see_others_engagement = True
    
    # ====== BASE QUERYSETS (with access filtering) ======
    bills_qs = Bill.objects.filter(shop=shop, bill_status__in=['draft', 'confirmed'])
    payments_qs = Payment.objects.filter(shop=shop)
    returns_qs = Return.objects.filter(shop=shop)
    exchanges_qs = ItemExchange.objects.filter(shop=shop)
    visits_qs = ShopVisit.objects.filter(shop=shop)
    
    if not can_see_others_engagement and request.user.is_sales_rep:
        bills_qs = bills_qs.filter(sales_rep=request.user)
        payments_qs = payments_qs.filter(received_by=request.user)
        returns_qs = returns_qs.filter(created_by=request.user)
        exchanges_qs = exchanges_qs.filter(created_by=request.user)
        visits_qs = visits_qs.filter(sales_rep=request.user)
    
    # ====== PENDING ITEMS ======
    pending_bills = bills_qs.filter(balance_amount__gt=0).order_by('-bill_date')
    
    # Annotate each bill with its pending payment amount
    from django.db.models import Subquery, OuterRef
    pending_bills = pending_bills.annotate(
        pending_payment_total=Sum(
            'settlements__amount',
            filter=Q(settlements__settlement_status='pending')
        )
    )
    
    pending_payments = payments_qs.filter(settlement_status='pending').order_by('-settlement_date')
    pending_returns = returns_qs.filter(is_verified=False).exclude(settlement_status='cancelled').order_by('-return_date')
    uncollected_cheques = payments_qs.filter(
        settlement_method='cheque', settlement_status='completed', cheque_collected=False
    ).order_by('-settlement_date')
    
    # ====== WORLD-CLASS 4-TIER BALANCE SYSTEM ======
    # Tier 1: TOTAL DEBT (all unpaid bills before any settlement attempt)
    total_debt = pending_bills.aggregate(total=Sum('balance_amount'))['total'] or Decimal('0')
    
    # Tier 2: PENDING VERIFICATION (cheques/bank transfers submitted but not cleared)
    pending_cheques = pending_payments.filter(settlement_method='cheque').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    pending_bank = pending_payments.filter(settlement_method='bank_transfer').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_pending_verification = pending_cheques + pending_bank
    
    # Tier 3: ACTUAL CASH DUE (what they really owe after clearing pending payments)
    actual_cash_due = total_debt - total_pending_verification
    
    # Tier 4: CREDIT AVAILABLE (after considering actual debt)
    available_credit_safe = shop.credit_limit - actual_cash_due if shop.credit_limit else Decimal('0')
    
    # Legacy values for backward compatibility
    total_outstanding = total_debt
    pending_payment_amount = total_pending_verification
    pending_return_amount = pending_returns.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    uncollected_cheques_amount = uncollected_cheques.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    pending_cheques_amount = pending_cheques
    pending_bank_transfers_amount = pending_bank
    actual_credit = actual_cash_due
    
    # ====== COMPREHENSIVE STATS ======
    all_bills = bills_qs.order_by('-bill_date')
    all_payments = payments_qs.filter(settlement_status='completed').order_by('-settlement_date')
    all_returns = returns_qs.order_by('-return_date')
    all_exchanges = exchanges_qs.order_by('-exchange_date')
    all_visits = visits_qs.order_by('-visit_date')
    
    total_bills_count = all_bills.count()
    total_payments_count = all_payments.count()
    total_returns_count = all_returns.count()
    total_exchanges_count = all_exchanges.count()
    total_visits_count = visits_qs.count()
    
    bill_totals = all_bills.aggregate(
        total_sales=Sum('total_amount'),
        total_paid=Sum('paid_amount'),
        avg_bill=Avg('total_amount'),
    )
    total_sales = bill_totals['total_sales'] or Decimal('0')
    total_paid = bill_totals['total_paid'] or Decimal('0')
    avg_bill_value = bill_totals['avg_bill'] or Decimal('0')
    total_return_amount = all_returns.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    net_sales = total_sales - total_return_amount
    payment_rate = (total_paid / total_sales * 100) if total_sales > 0 else Decimal('0')
    
    # Recent visit count (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_visit_count = visits_qs.filter(visit_date__gte=thirty_days_ago).count()
    
    # Available credit
    available_credit = shop.credit_limit - total_outstanding if shop.credit_limit else Decimal('0')
    
    # ====== SHOP PHOTO HISTORY ======
    photo_history = ShopPhotoHistory.objects.filter(shop=shop).order_by('-uploaded_at')
    needs_photo, photo_message = ShopPhotoHistory.needs_new_photo(shop)
    
    # ====== SHOP VISIT STATUS ======
    last_visit = ShopVisit.get_last_visit(shop)
    last_visit_by_user = ShopVisit.get_last_visit(shop, request.user) if request.user.is_sales_rep else last_visit
    visited_today = ShopVisit.already_visited_today(shop, request.user)
    
    # ====== NEW SHOP FLAG (registered within 7 days) ======
    is_new_shop = shop.created_at and (timezone.now() - shop.created_at).days <= 7
    
    # ====== CONTEXT ======
    context = {
        'shop': shop,
        'is_new_shop': is_new_shop,
        
        # Photo History
        'photo_history': photo_history,
        'needs_new_photo': needs_photo,
        'photo_message': photo_message,
        
        # Pending Items
        'pending_bills': pending_bills,
        'pending_payments': pending_payments,
        'pending_returns': pending_returns,
        'uncollected_cheques': uncollected_cheques,
        
        # Pending Counts
        'pending_bills_count': pending_bills.count(),
        'pending_payments_count': pending_payments.count(),
        'pending_returns_count': pending_returns.count(),
        'uncollected_cheques_count': uncollected_cheques.count(),
        
        # Pending Amounts
        'total_outstanding': total_outstanding,
        'actual_credit': actual_credit,
        'pending_payment_amount': pending_payment_amount,
        'pending_return_amount': pending_return_amount,
        'pending_cheques_amount': pending_cheques_amount,
        'pending_bank_transfers_amount': pending_bank_transfers_amount,
        'uncollected_cheques_amount': uncollected_cheques_amount,
        
        # All Records (for history tabs)
        'all_bills': all_bills[:50],
        'all_payments': all_payments[:50],
        'all_returns': all_returns[:50],
        'all_exchanges': all_exchanges[:50],
        'all_visits': all_visits,
        
        # Summary Stats
        'total_bills_count': total_bills_count,
        'total_payments_count': total_payments_count,
        'total_returns_count': total_returns_count,
        'total_exchanges_count': total_exchanges_count,
        'total_visits_count': total_visits_count,
        'total_sales': total_sales,
        'total_paid': total_paid,
        'total_return_amount': total_return_amount,
        'net_sales': net_sales,
        'payment_rate': payment_rate,
        'avg_bill_value': avg_bill_value,
        'available_credit': available_credit,
        'recent_visit_count': recent_visit_count,
        
        # Access Control
        'user_access_level': access_level,
        'can_see_others_engagement': can_see_others_engagement,
        
        # Visit Tracking
        'last_visit': last_visit,
        'last_visit_by_user': last_visit_by_user,
        'visited_today': visited_today,
    }
    return render(request, 'shops/shop_detail.html', context)


@login_required
def edit_shop(request, pk):
    """Edit shop"""
    from shops.models import ShopPhotoHistory
    
    shop = get_object_or_404(Shop, pk=pk)
    
    if request.method == 'POST':
        try:
            shop.shop_name = request.POST.get('shop_name')
            shop.owner_name = request.POST.get('owner_name')
            shop.shop_type = request.POST.get('shop_type')
            shop.phone_number = request.POST.get('phone_number')
            shop.alternate_phone = request.POST.get('alternate_phone')
            shop.email = request.POST.get('email')
            shop.address_line1 = request.POST.get('address_line1')
            shop.address_line2 = request.POST.get('address_line2')
            shop.city = request.POST.get('city')
            shop.district = request.POST.get('district')
            shop.postal_code = request.POST.get('postal_code')
            shop.credit_limit = request.POST.get('credit_limit', 0)
            
            # Update location if provided
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            if latitude and longitude:
                shop.latitude = float(latitude)
                shop.longitude = float(longitude)
            
            shop.save()
            
            # Handle photo upload via ShopPhotoHistory system
            if 'shop_photo' in request.FILES:
                photo = request.FILES['shop_photo']
                ShopPhotoHistory.objects.create(
                    shop=shop,
                    photo=photo,
                    uploaded_by=request.user,
                    notes='Updated via edit shop form',
                    is_active=True
                )
            
            messages.success(request, 'Shop updated successfully!')
            return redirect('shops:detail', pk=shop.pk)
        except Exception as e:
            messages.error(request, f'Error updating shop: {str(e)}')
    
    return render(request, 'shops/edit_shop.html', {'shop': shop})

@login_required
def shop_map(request):
    """Full-screen shop map with rich data overlay"""
    from django.db.models import Sum, Q
    from django.utils import timezone
    from datetime import timedelta
    from decimal import Decimal
    from sales.models import Bill
    from payments.models import SalesAccountSettlement
    
    now = timezone.now()
    today = timezone.localdate()
    
    shops = Shop.objects.filter(is_active=True, latitude__isnull=False, longitude__isnull=False)
    
    shops_data = []
    total_outstanding = Decimal('0')
    total_pending = 0
    level_counts = {1: 0, 2: 0, 3: 0}
    visited_today_count = 0
    never_visited_count = 0
    
    for shop in shops:
        # Access level
        if request.user.is_sales_rep:
            level = ShopAccess.get_rep_access_level(shop, request.user)
        else:
            level = 3
        level_counts[level] = level_counts.get(level, 0) + 1
        
        # Outstanding
        outstanding = Bill.objects.filter(
            shop=shop, bill_status__in=['draft', 'confirmed'], balance_amount__gt=0
        ).aggregate(total=Sum('balance_amount'))['total'] or Decimal('0')
        total_outstanding += outstanding
        
        # Pending items
        pending_bills = Bill.objects.filter(
            shop=shop, bill_status__in=['draft', 'confirmed'], balance_amount__gt=0
        ).count()
        pending_payments = SalesAccountSettlement.objects.filter(
            shop=shop, settlement_status='pending'
        ).count()
        pending = pending_bills + pending_payments
        total_pending += pending
        
        # Last visit
        last_visit = ShopVisit.objects.filter(shop=shop).order_by('-visit_date').first()
        if last_visit:
            visit_local = timezone.localtime(last_visit.visit_date)
            days_since = (today - visit_local.date()).days
            visit_str = visit_local.strftime('%b %d, %Y %I:%M %p')
            if days_since == 0:
                visited_today_count += 1
        else:
            days_since = None
            visit_str = None
            never_visited_count += 1
        
        # Is new (within 7 days)
        is_new = (today - timezone.localtime(shop.created_at).date()).days <= 7 if shop.created_at else False
        
        shops_data.append({
            'id': shop.pk,
            'code': shop.shop_code or '',
            'name': shop.shop_name,
            'owner': shop.owner_name,
            'type': shop.get_shop_type_display(),
            'type_key': shop.shop_type,
            'phone': shop.phone_number or '',
            'address': f"{shop.address_line1}, {shop.city}" if shop.address_line1 else shop.city,
            'city': shop.city or '',
            'lat': float(shop.latitude),
            'lng': float(shop.longitude),
            'level': level,
            'outstanding': float(outstanding),
            'pending': pending,
            'pending_bills': pending_bills,
            'pending_payments': pending_payments,
            'days_since_visit': days_since,
            'visit_str': visit_str,
            'is_new': is_new,
            'photo': shop.shop_photo.url if shop.shop_photo else None,
        })
    
    # Shops without coordinates
    no_location_count = Shop.objects.filter(
        is_active=True
    ).filter(Q(latitude__isnull=True) | Q(longitude__isnull=True)).count()
    
    context = {
        'shops_json': shops_data,
        'total_shops': len(shops_data),
        'no_location_count': no_location_count,
        'total_outstanding': total_outstanding,
        'total_pending': total_pending,
        'level_counts': level_counts,
        'visited_today_count': visited_today_count,
        'never_visited_count': never_visited_count,
    }
    return render(request, 'shops/shop_map.html', context)


@login_required
def shops_geojson(request):
    """Return shops as GeoJSON for map display
    
    All sales reps can see all shops on the map (Level 1 default access).
    """
    try:
        if request.user.is_sales_rep:
            # Show all active shops with coordinates (Level 1 default access)
            shops = Shop.objects.filter(is_active=True, latitude__isnull=False, longitude__isnull=False)
        else:
            shops = Shop.objects.filter(is_active=True, latitude__isnull=False, longitude__isnull=False)
        
        features = []
        for shop in shops:
            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [float(shop.longitude), float(shop.latitude)]
                },
                'properties': {
                    'shop_code': shop.shop_code or '',
                    'shop_name': shop.shop_name,
                    'owner_name': shop.owner_name,
                    'phone_number': shop.phone_number,
                    'address': shop.address_line1,
                    'city': shop.city,
                    'url': f'/shops/{shop.pk}/'
                }
            })
        
        return JsonResponse({
            'type': 'FeatureCollection',
            'features': features
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'type': 'FeatureCollection',
            'features': []
        }, status=500)


@login_required
@require_POST
def track_location(request):
    """Track sales rep location"""
    try:
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy')
        battery = data.get('battery')
        
        if not latitude or not longitude:
            return JsonResponse({'error': 'Latitude and longitude required'}, status=400)
        
        location = SalesRepLocation.objects.create(
            sales_rep=request.user,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            battery_level=battery
        )
        
        return JsonResponse({
            'success': True,
            'location_id': location.id,
            'timestamp': location.timestamp.isoformat()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def nearby_shops(request):
    """Get shops near current location (respects access levels)"""
    try:
        lat = request.GET.get('lat')
        lon = request.GET.get('lon')
        radius = float(request.GET.get('radius', 5))  # Default 5km radius
        
        if not lat or not lon:
            return JsonResponse({'error': 'Latitude and longitude required'}, status=400)
        
        # All sales reps can see all active shops (access level controls what they can do)
        shops = Shop.objects.filter(is_active=True)
        
        # Filter nearby shops
        nearby = get_nearby_shops(float(lat), float(lon), shops, radius)
        
        # Format response with access level info
        shops_data = []
        for shop, distance in nearby:
            if request.user.is_sales_rep:
                access_level = ShopAccess.get_rep_access_level(shop, request.user)
            else:
                access_level = 3
            
            shops_data.append({
                'id': shop.id,
                'shop_code': shop.shop_code or '',
                'shop_name': shop.shop_name,
                'owner_name': shop.owner_name,
                'phone_number': shop.phone_number,
                'address': shop.address_line1,
                'city': shop.city,
                'distance_km': distance,
                'latitude': float(shop.latitude),
                'longitude': float(shop.longitude),
                'access_level': access_level,
                'url': f'/shops/{shop.id}/'
            })
        
        return JsonResponse({
            'success': True,
            'count': len(shops_data),
            'radius_km': radius,
            'shops': shops_data
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def nearby_shops_page(request):
    """Display nearby shops page"""
    return render(request, 'shops/nearby_shops.html')


@login_required
def manage_shop_access(request, pk):
    """Manage access levels for a shop - Admin/Office only"""
    if not request.user.is_office_staff:
        messages.error(request, 'Access denied.')
        return redirect('shops:detail', pk=pk)
    
    shop = get_object_or_404(Shop, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'grant':
            try:
                sales_rep_id = request.POST.get('sales_rep')
                access_level = int(request.POST.get('access_level'))
                notes = request.POST.get('notes', '')
                
                sales_rep = get_object_or_404(User, pk=sales_rep_id, user_type='sales_rep')
                
                access, created = ShopAccess.objects.update_or_create(
                    shop=shop,
                    sales_rep=sales_rep,
                    defaults={
                        'access_level': access_level,
                        'granted_by': request.user,
                        'notes': notes,
                        'is_active': True
                    }
                )
                
                if created:
                    messages.success(request, f'Access Level {access_level} granted to {sales_rep.get_full_name()}')
                else:
                    messages.success(request, f'Access level updated to Level {access_level} for {sales_rep.get_full_name()}')
                    
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        
        elif action == 'revoke':
            try:
                access_id = request.POST.get('access_id')
                access = get_object_or_404(ShopAccess, id=access_id, shop=shop)
                rep_name = access.sales_rep.get_full_name()
                access.delete()
                messages.success(request, f'Access revoked for {rep_name}')
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        
        return redirect('shops:manage_access', pk=pk)
    
    # GET - Display current access grants
    access_grants = ShopAccess.objects.filter(shop=shop, is_active=True).select_related('sales_rep', 'granted_by')
    from accounts.tenant_utils import get_tenant_users
    sales_reps = get_tenant_users().filter(user_type='sales_rep', is_active=True).order_by('first_name', 'last_name')
    
    # Build comprehensive list: all sales reps with their access levels (including default Level 1)
    all_reps_with_access = []
    for rep in sales_reps:
        try:
            grant = access_grants.get(sales_rep=rep)
            all_reps_with_access.append({
                'rep': rep,
                'access_level': grant.access_level,
                'granted_by': grant.granted_by,
                'granted_at': grant.granted_at,
                'notes': grant.notes,
                'grant_id': grant.id,
                'is_default': False,
            })
        except ShopAccess.DoesNotExist:
            # Default Level 1 access for all sales reps
            all_reps_with_access.append({
                'rep': rep,
                'access_level': 1,
                'granted_by': None,
                'granted_at': None,
                'notes': 'Default access - All sales reps can view all shops',
                'grant_id': None,
                'is_default': True,
            })
    
    context = {
        'shop': shop,
        'all_reps_with_access': all_reps_with_access,
        'all_sales_reps': sales_reps,
    }
    
    return render(request, 'shops/manage_access.html', context)


@login_required
def upload_shop_photo(request, pk):
    """Upload a new shop photo"""
    from shops.models import ShopPhotoHistory
    
    shop = get_object_or_404(Shop, pk=pk)
    
    # Check permissions
    if request.user.is_sales_rep:
        access_level = ShopAccess.get_rep_access_level(shop, request.user)
        if not access_level or access_level < 2:
            messages.error(request, 'You need at least Level 2 access to upload photos.')
            return redirect('shops:detail', pk=pk)
    
    if request.method == 'POST':
        photo = request.FILES.get('photo')
        notes = request.POST.get('notes', '')
        
        if not photo:
            messages.error(request, 'Please select a photo to upload.')
            return redirect('shops:detail', pk=pk)
        
        # Create new photo history entry (will auto-set as active)
        ShopPhotoHistory.objects.create(
            shop=shop,
            photo=photo,
            uploaded_by=request.user,
            notes=notes,
            is_active=True
        )
        
        messages.success(request, 'Shop photo uploaded successfully!')
        return redirect('shops:detail', pk=pk)
    
    return redirect('shops:detail', pk=pk)


@login_required
def mark_visit(request, pk):
    """
    AJAX endpoint — manually mark a shop visit.
    Requires GPS coordinates. Checks proximity (≤500m) and once-per-day limit.
    """
    from django.http import JsonResponse
    from shops.visit_utils import try_mark_visit

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    shop = get_object_or_404(Shop, pk=pk)

    # Permission check
    if request.user.is_sales_rep:
        access_level = ShopAccess.get_rep_access_level(shop, request.user)
        if not access_level or access_level < 2:
            return JsonResponse({'status': 'error', 'message': 'Insufficient access'}, status=403)

    latitude = request.POST.get('latitude')
    longitude = request.POST.get('longitude')

    if not latitude or not longitude:
        return JsonResponse({'status': 'error', 'message': 'GPS coordinates required'}, status=400)

    success, message, visit = try_mark_visit(
        shop=shop,
        user=request.user,
        latitude=latitude,
        longitude=longitude,
        visit_type='manual',
        notes='Manual check-in from shop detail page',
    )

    if success:
        from django.utils import timezone as tz
        return JsonResponse({
            'status': 'ok',
            'message': 'Visit marked successfully!',
            'visit_time': tz.localtime(visit.visit_date).strftime('%I:%M %p'),
        })
    elif message == 'already_visited':
        return JsonResponse({
            'status': 'already',
            'message': 'You have already visited this shop today.',
        })
    elif message.startswith('too_far'):
        dist = message.split(':')[1] if ':' in message else ''
        return JsonResponse({
            'status': 'too_far',
            'message': f'You are too far from this shop ({dist}). Please move closer.',
        })
    else:
        return JsonResponse({'status': 'error', 'message': message}, status=400)


@login_required
@require_POST
def toggle_shop_active(request, pk):
    """Toggle shop active/inactive status. Admin and office only."""
    if request.user.user_type == 'sales_rep':
        messages.error(request, 'Access denied')
        return redirect('shops:detail', pk=pk)

    shop = get_object_or_404(Shop, pk=pk)
    shop.is_active = not shop.is_active
    shop.save(update_fields=['is_active'])

    status = 'active' if shop.is_active else 'inactive'
    messages.success(request, f'{shop.shop_name} marked as {status}.')
    return redirect('shops:detail', pk=pk)
