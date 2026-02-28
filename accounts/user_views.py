from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import User
from .forms import UserCreateForm, UserEditForm, PasswordResetByAdminForm
from .tenant_utils import get_tenant_users


@login_required
def user_list(request):
    """List all users with filtering and search — Admin/Office only"""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    users = get_tenant_users().order_by('first_name', 'last_name')
    
    # Non-admin users cannot see admin accounts
    is_admin = request.user.user_type == 'admin'
    if not is_admin:
        users = users.exclude(user_type='admin')
    
    # ── Filters ──
    role_filter = request.GET.get('role', 'all')
    status_filter = request.GET.get('status', 'active')
    search_query = request.GET.get('q', '').strip()
    
    if role_filter != 'all':
        users = users.filter(user_type=role_filter)
    
    if status_filter == 'active':
        users = users.filter(is_active=True, is_active_employee=True)
    elif status_filter == 'inactive':
        users = users.filter(Q(is_active=False) | Q(is_active_employee=False))
    
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(employee_id__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    # ── Stats (scoped to visible users) ──
    all_users = get_tenant_users()
    if not is_admin:
        all_users = all_users.exclude(user_type='admin')
    stats = {
        'total': all_users.count(),
        'active': all_users.filter(is_active=True, is_active_employee=True).count(),
        'inactive': all_users.filter(Q(is_active=False) | Q(is_active_employee=False)).count(),
        'admins': all_users.filter(user_type='admin').count() if is_admin else 0,
        'office': all_users.filter(user_type='office').count(),
        'sales_reps': all_users.filter(user_type='sales_rep').count(),
    }
    
    # ── Annotate with bill counts for sales reps ──
    from sales.models import Bill
    
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    user_data = []
    for user in users:
        data = {'user': user}
        if user.user_type == 'sales_rep':
            data['total_bills'] = Bill.objects.filter(
                sales_rep=user, bill_status='confirmed'
            ).count()
            data['month_bills'] = Bill.objects.filter(
                sales_rep=user, bill_status='confirmed',
                bill_date__gte=month_start
            ).count()
            month_revenue = Bill.objects.filter(
                sales_rep=user, bill_status='confirmed',
                bill_date__gte=month_start
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
            data['month_revenue'] = month_revenue
        user_data.append(data)
    
    context = {
        'user_data': user_data,
        'stats': stats,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'search_query': search_query,
        'result_count': users.count(),
    }
    return render(request, 'accounts/user_list.html', context)


@login_required
def user_detail(request, pk):
    """View detailed user profile — Admin/Office only"""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    user_obj = get_object_or_404(User, pk=pk)
    
    # Non-admin users cannot view admin profiles
    if user_obj.user_type == 'admin' and request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('accounts:user_list')
    
    # ── Activity stats ──
    from sales.models import Bill, Return, ItemExchange
    from payments.models import SalesAccountSettlement
    from shops.models import Shop, ShopVisit
    
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    activity = {}
    if user_obj.user_type == 'sales_rep':
        activity['total_bills'] = Bill.objects.filter(
            sales_rep=user_obj, bill_status='confirmed'
        ).count()
        activity['month_bills'] = Bill.objects.filter(
            sales_rep=user_obj, bill_status='confirmed',
            bill_date__gte=month_start
        ).count()
        total_revenue = Bill.objects.filter(
            sales_rep=user_obj, bill_status='confirmed'
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        month_revenue = Bill.objects.filter(
            sales_rep=user_obj, bill_status='confirmed',
            bill_date__gte=month_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        activity['total_revenue'] = total_revenue
        activity['month_revenue'] = month_revenue
        
        activity['total_returns'] = Return.objects.filter(
            created_by=user_obj
        ).count()
        
        activity['assigned_shops'] = Shop.objects.filter(
            assigned_sales_rep=user_obj
        ).count()
        
        # Money account
        from accounts.money_account_models import UserMoneyAccount
        try:
            money_account = UserMoneyAccount.objects.get(user=user_obj)
            activity['money_balance'] = money_account.current_balance
        except UserMoneyAccount.DoesNotExist:
            activity['money_balance'] = None
    
    # ── Unified Activity Timeline ──
    timeline = []
    
    # Bills
    bills_qs = Bill.objects.filter(sales_rep=user_obj).select_related('shop').order_by('-bill_date')[:50]
    for b in bills_qs:
        status_map = {'confirmed': ('Confirmed', 'success'), 'draft': ('Draft', 'warning'), 'cancelled': ('Cancelled', 'danger')}
        st = status_map.get(b.bill_status, (b.bill_status, 'secondary'))
        timeline.append({
            'type': 'Bill',
            'icon': 'fa-file-invoice',
            'color': '#0078D7',
            'ref': b.bill_number,
            'date': b.bill_date,
            'shop': b.shop.shop_name if b.shop else '—',
            'amount': b.total_amount,
            'status': st[0],
            'status_class': st[1],
        })
    
    # Returns
    returns_qs = Return.objects.filter(created_by=user_obj).select_related('shop').order_by('-return_date')[:30]
    for r in returns_qs:
        status_map = {
            'unsettled': ('Unsettled', 'warning'), 'settled_cash': ('Settled', 'success'),
            'cancelled': ('Cancelled', 'danger'), 'available': ('Available', 'info'),
            'partially_applied': ('Partial', 'warning'), 'fully_applied': ('Applied', 'success'),
        }
        st = status_map.get(r.settlement_status, (r.settlement_status or 'Pending', 'secondary'))
        timeline.append({
            'type': 'Return',
            'icon': 'fa-undo-alt',
            'color': '#ef4444',
            'ref': r.return_number,
            'date': r.return_date,
            'shop': r.shop.shop_name if r.shop else '—',
            'amount': r.total_amount,
            'status': st[0],
            'status_class': st[1],
        })
    
    # Exchanges
    exchanges_qs = ItemExchange.objects.filter(created_by=user_obj).select_related('shop').order_by('-exchange_date')[:30]
    for e in exchanges_qs:
        status_map = {'pending': ('Pending', 'warning'), 'completed': ('Completed', 'success'), 'cancelled': ('Cancelled', 'danger')}
        st = status_map.get(e.exchange_status, (e.exchange_status, 'secondary'))
        timeline.append({
            'type': 'Exchange',
            'icon': 'fa-exchange-alt',
            'color': '#8b5cf6',
            'ref': e.exchange_number,
            'date': e.exchange_date,
            'shop': e.shop.shop_name if e.shop else '—',
            'amount': None,
            'status': st[0],
            'status_class': st[1],
        })
    
    # Settlements / Payments
    settlements_qs = SalesAccountSettlement.objects.filter(
        received_by=user_obj
    ).select_related('shop').order_by('-settlement_date')[:30]
    for s in settlements_qs:
        status_map = {
            'pending': ('Pending', 'warning'), 'completed': ('Completed', 'success'),
            'cancelled': ('Cancelled', 'danger'), 'bounced': ('Bounced', 'danger'),
        }
        st = status_map.get(s.settlement_status, (s.settlement_status, 'secondary'))
        timeline.append({
            'type': 'Payment',
            'icon': 'fa-money-bill-wave',
            'color': '#10b981',
            'ref': s.settlement_number,
            'date': s.settlement_date,
            'shop': s.shop.shop_name if s.shop else '—',
            'amount': s.amount,
            'status': st[0],
            'status_class': st[1],
        })
    
    # Shop Visits (sales_rep only)
    if user_obj.user_type == 'sales_rep':
        visits_qs = ShopVisit.objects.filter(sales_rep=user_obj).select_related('shop').order_by('-visit_date')[:30]
        type_labels = {
            'manual': 'Manual Visit', 'auto_bill': 'Bill Visit',
            'auto_payment': 'Payment Visit', 'auto_return': 'Return Visit',
            'auto_exchange': 'Exchange Visit',
        }
        for v in visits_qs:
            timeline.append({
                'type': 'Visit',
                'icon': 'fa-map-marker-alt',
                'color': '#06b6d4',
                'ref': type_labels.get(v.visit_type, v.visit_type),
                'date': v.visit_date,
                'shop': v.shop.shop_name if v.shop else '—',
                'amount': None,
                'status': type_labels.get(v.visit_type, v.visit_type),
                'status_class': 'info',
            })
    
    # Sort all activities by date descending → keep latest 50
    timeline.sort(key=lambda x: x['date'] if x['date'] else timezone.now(), reverse=True)
    timeline = timeline[:50]
    
    # ── Activity filter ──
    activity_filter = request.GET.get('activity', 'all')
    if activity_filter != 'all':
        filter_map = {'bills': 'Bill', 'returns': 'Return', 'exchanges': 'Exchange', 'payments': 'Payment', 'visits': 'Visit'}
        if activity_filter in filter_map:
            timeline = [t for t in timeline if t['type'] == filter_map[activity_filter]]
    
    context = {
        'user_obj': user_obj,
        'activity': activity,
        'timeline': timeline,
        'activity_filter': activity_filter,
    }
    return render(request, 'accounts/user_detail.html', context)


@login_required
def user_create(request):
    """Create a new user — Admin/Office only"""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST, request.FILES, current_user=request.user)
        if form.is_valid():
            # Server-side guard: non-admin cannot create admin accounts
            if form.cleaned_data.get('user_type') == 'admin' and request.user.user_type != 'admin':
                messages.error(request, 'Only admins can create admin accounts.')
                return redirect('accounts:user_list')
            user = form.save(commit=False)
            # Auto-assign user to current tenant
            from accounts.tenant_utils import get_current_tenant
            current_tenant = get_current_tenant()
            if current_tenant:
                user.tenant = current_tenant
            elif request.user.tenant:
                user.tenant = request.user.tenant
            user.save()
            messages.success(request, f'User "{user.get_full_name()}" created successfully.')
            return redirect('accounts:user_detail', pk=user.pk)
    else:
        form = UserCreateForm(current_user=request.user)
    
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'is_edit': False,
        'page_title': 'Create New User',
    })


@login_required
def user_edit(request, pk):
    """Edit an existing user — Admin/Office only"""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    user_obj = get_object_or_404(User, pk=pk)
    
    # Non-admin users cannot edit admin accounts
    if user_obj.user_type == 'admin' and request.user.user_type != 'admin':
        messages.error(request, 'Only admins can edit admin accounts.')
        return redirect('accounts:user_detail', pk=pk)
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user_obj, current_user=request.user)
        if form.is_valid():
            # Server-side guard: non-admin cannot assign admin role
            if form.cleaned_data.get('user_type') == 'admin' and request.user.user_type != 'admin':
                messages.error(request, 'Only admins can assign admin role.')
                return redirect('accounts:user_detail', pk=pk)
            form.save()
            messages.success(request, f'User "{user_obj.get_full_name()}" updated successfully.')
            return redirect('accounts:user_detail', pk=user_obj.pk)
    else:
        form = UserEditForm(instance=user_obj, current_user=request.user)
    
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'is_edit': True,
        'user_obj': user_obj,
        'page_title': f'Edit {user_obj.get_full_name()}',
    })


@login_required
def user_toggle_active(request, pk):
    """Toggle user active/inactive status — Admin/Office only, POST only"""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    if request.method != 'POST':
        return redirect('accounts:user_detail', pk=pk)
    
    user_obj = get_object_or_404(User, pk=pk)
    
    # Cannot deactivate yourself
    if user_obj.pk == request.user.pk:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('accounts:user_detail', pk=pk)
    
    # Non-admin cannot deactivate admin
    if user_obj.user_type == 'admin' and request.user.user_type != 'admin':
        messages.error(request, 'Only admins can deactivate admin accounts.')
        return redirect('accounts:user_detail', pk=pk)
    
    user_obj.is_active = not user_obj.is_active
    user_obj.is_active_employee = user_obj.is_active
    user_obj.save(update_fields=['is_active', 'is_active_employee'])
    
    status = 'activated' if user_obj.is_active else 'deactivated'
    messages.success(request, f'User "{user_obj.get_full_name()}" has been {status}.')
    return redirect('accounts:user_detail', pk=pk)


@login_required
def user_reset_password(request, pk):
    """Reset a user's password — Admin/Office only"""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    user_obj = get_object_or_404(User, pk=pk)
    
    # Non-admin cannot reset admin passwords
    if user_obj.user_type == 'admin' and request.user.user_type != 'admin':
        messages.error(request, 'Only admins can reset admin passwords.')
        return redirect('accounts:user_detail', pk=pk)
    
    if request.method == 'POST':
        form = PasswordResetByAdminForm(request.POST)
        if form.is_valid():
            user_obj.set_password(form.cleaned_data['new_password1'])
            user_obj.save()
            messages.success(request, f'Password for "{user_obj.get_full_name()}" has been reset.')
            return redirect('accounts:user_detail', pk=pk)
    else:
        form = PasswordResetByAdminForm()
    
    return render(request, 'accounts/user_reset_password.html', {
        'form': form,
        'user_obj': user_obj,
    })


@login_required
def user_manage_shop_access(request, pk):
    """Bulk manage shop access for a sales rep — Admin/Office only"""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    user_obj = get_object_or_404(User, pk=pk)

    if user_obj.user_type != 'sales_rep':
        messages.error(request, 'Shop access can only be managed for sales representatives.')
        return redirect('accounts:user_detail', pk=pk)

    from shops.models import Shop, ShopAccess

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'bulk_update':
            # Process bulk form submission
            shop_ids = request.POST.getlist('shop_ids')
            access_level = int(request.POST.get('access_level', 2))
            access_level = max(1, min(3, access_level))  # Clamp 1-3

            granted = 0
            for shop_id in shop_ids:
                try:
                    shop = Shop.objects.get(pk=int(shop_id))
                    access, created = ShopAccess.objects.update_or_create(
                        shop=shop,
                        sales_rep=user_obj,
                        defaults={
                            'access_level': access_level,
                            'granted_by': request.user,
                            'is_active': True,
                            'notes': f'Bulk assigned via User Management',
                        }
                    )
                    granted += 1
                except (Shop.DoesNotExist, ValueError):
                    continue

            level_labels = {1: 'View Only', 2: 'Standard', 3: 'Full Access'}
            messages.success(
                request,
                f'Granted Level {access_level} ({level_labels.get(access_level, "")}) access to {granted} shop{"s" if granted != 1 else ""} for {user_obj.get_full_name()}.'
            )
            return redirect('accounts:user_manage_shop_access', pk=pk)

        elif action == 'bulk_revoke':
            shop_ids = request.POST.getlist('shop_ids')
            revoked = ShopAccess.objects.filter(
                shop_id__in=[int(sid) for sid in shop_ids if sid.isdigit()],
                sales_rep=user_obj,
            ).delete()[0]
            messages.success(
                request,
                f'Revoked access to {revoked} shop{"s" if revoked != 1 else ""} for {user_obj.get_full_name()}.'
            )
            return redirect('accounts:user_manage_shop_access', pk=pk)

    # ── Build shop list with current access info ──
    search_query = request.GET.get('q', '').strip()
    city_filter = request.GET.get('city', '')
    access_filter = request.GET.get('access', 'all')  # all, granted, none

    shops = Shop.objects.filter(is_active=True).order_by('shop_name')

    if search_query:
        shops = shops.filter(
            Q(shop_name__icontains=search_query) |
            Q(shop_code__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(owner_name__icontains=search_query)
        )

    if city_filter:
        shops = shops.filter(city__iexact=city_filter)

    # Get all current access grants for this user
    existing_access = {
        sa.shop_id: sa
        for sa in ShopAccess.objects.filter(sales_rep=user_obj, is_active=True)
    }

    shop_data = []
    for shop in shops:
        access = existing_access.get(shop.pk)
        entry = {
            'shop': shop,
            'has_access': access is not None,
            'access_level': access.access_level if access else 0,
            'access_obj': access,
        }
        shop_data.append(entry)

    # Apply access filter
    if access_filter == 'granted':
        shop_data = [s for s in shop_data if s['has_access']]
    elif access_filter == 'none':
        shop_data = [s for s in shop_data if not s['has_access']]

    # Get unique cities for filter dropdown
    cities = Shop.objects.filter(is_active=True).values_list(
        'city', flat=True
    ).distinct().order_by('city')

    # Stats
    total_shops = Shop.objects.filter(is_active=True).count()
    granted_count = len(existing_access)
    level_counts = {1: 0, 2: 0, 3: 0}
    for sa in existing_access.values():
        if sa.access_level in level_counts:
            level_counts[sa.access_level] += 1

    context = {
        'user_obj': user_obj,
        'shop_data': shop_data,
        'result_count': len(shop_data),
        'search_query': search_query,
        'city_filter': city_filter,
        'access_filter': access_filter,
        'cities': cities,
        'total_shops': total_shops,
        'granted_count': granted_count,
        'not_granted_count': total_shops - granted_count,
        'level_counts': level_counts,
    }
    return render(request, 'accounts/user_shop_access.html', context)
