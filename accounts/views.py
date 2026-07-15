from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from decimal import Decimal
from .models import User


@require_http_methods(["GET", "POST"])
def custom_logout(request):
    """Logout that accepts both GET and POST to avoid CSRF errors on stale tabs"""
    auth_logout(request)
    return redirect('login')


@login_required
def profile_view(request):
    """View current user's own profile with activity stats"""
    user = request.user
    
    from sales.models import Bill, Return, ItemExchange
    from payments.models import SalesAccountSettlement
    from shops.models import Shop, ShopVisit
    
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    activity = {}
    
    if user.user_type == 'sales_rep':
        activity['total_bills'] = Bill.objects.filter(
            sales_rep=user, bill_status='confirmed'
        ).count()
        activity['month_bills'] = Bill.objects.filter(
            sales_rep=user, bill_status='confirmed',
            bill_date__gte=month_start
        ).count()
        total_revenue = Bill.objects.filter(
            sales_rep=user, bill_status='confirmed'
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        month_revenue = Bill.objects.filter(
            sales_rep=user, bill_status='confirmed',
            bill_date__gte=month_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        activity['total_revenue'] = total_revenue
        activity['month_revenue'] = month_revenue
        activity['total_returns'] = Return.objects.filter(created_by=user).count()
        activity['total_exchanges'] = ItemExchange.objects.filter(created_by=user).count()
        activity['assigned_shops'] = Shop.objects.filter(assigned_sales_rep=user).count()
        activity['total_visits'] = ShopVisit.objects.filter(sales_rep=user).count()
        activity['total_payments'] = SalesAccountSettlement.objects.filter(
            received_by=user, settlement_status='completed'
        ).count()
        
        # Recent bills
        activity['recent_bills'] = Bill.objects.filter(
            sales_rep=user, bill_status='confirmed'
        ).select_related('shop').order_by('-bill_date')[:5]
        
        # Money account
        from accounts.money_account_models import UserMoneyAccount
        try:
            money_account = UserMoneyAccount.objects.get(user=user)
            activity['money_balance'] = money_account.current_balance
        except UserMoneyAccount.DoesNotExist:
            activity['money_balance'] = None
    
    elif user.user_type in ('admin', 'office'):
        activity['total_bills'] = Bill.objects.filter(
            sales_rep=user, bill_status='confirmed'
        ).count()
        activity['total_returns'] = Return.objects.filter(created_by=user).count()
        activity['total_exchanges'] = ItemExchange.objects.filter(created_by=user).count()
        activity['total_payments'] = SalesAccountSettlement.objects.filter(
            received_by=user, settlement_status='completed'
        ).count()
    
    return render(request, 'accounts/profile.html', {
        'user_obj': user,
        'activity': activity,
    })


@login_required
def edit_profile(request):
    """Edit own profile — name, phone, address, picture"""
    user = request.user
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name).strip()
        user.last_name = request.POST.get('last_name', user.last_name).strip()
        user.phone_number = request.POST.get('phone_number', '').strip() or None
        user.address = request.POST.get('address', '').strip() or None
        user.email = request.POST.get('email', '').strip()
        
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
        
        # Handle remove picture
        if request.POST.get('remove_picture') == '1' and user.profile_picture:
            user.profile_picture.delete(save=False)
            user.profile_picture = None
        
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('accounts:profile')
    
    return render(request, 'accounts/edit_profile.html', {'user_obj': user})


@login_required
def change_password(request):
    """Change own password — requires current password"""
    if request.method == 'POST':
        current_pw = request.POST.get('current_password', '')
        new_pw1 = request.POST.get('new_password1', '')
        new_pw2 = request.POST.get('new_password2', '')
        
        if not request.user.check_password(current_pw):
            messages.error(request, 'Current password is incorrect.')
        elif not new_pw1 or len(new_pw1) < 6:
            messages.error(request, 'New password must be at least 6 characters.')
        elif new_pw1 != new_pw2:
            messages.error(request, 'New passwords do not match.')
        else:
            request.user.set_password(new_pw1)
            request.user.save()
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:profile')
    
    return render(request, 'accounts/change_password.html')
