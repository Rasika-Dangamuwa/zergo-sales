"""
User Money Account Views - Commission Payment Management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Q
from decimal import Decimal

from accounts.models import User
from accounts.money_account_models import (
    UserMoneyAccount, MoneyTransaction, AdvanceRequest
)
from accounts.tenant_utils import get_tenant_users, get_tenant_filter


@login_required
def money_account_dashboard(request):
    """
    User money account dashboard
    - Users see only their own account
    - Admin/Office can view any user's account via ?user_id parameter
    """
    # Determine which account to display
    if request.user.is_office_staff:
        user_id = request.GET.get('user_id')
        if user_id:
            viewing_user = get_object_or_404(User, pk=user_id)
        else:
            viewing_user = request.user
    else:
        # Regular users can only see their own account
        viewing_user = request.user
    
    # Get or create money account
    account, created = UserMoneyAccount.objects.get_or_create(
        user=viewing_user,
        defaults={
            'created_by': request.user,
            'opening_date': timezone.localdate()
        }
    )
    
    # Get recent transactions
    recent_transactions = account.transactions.all()[:20]
    
    # Get pending advance requests
    pending_advances = AdvanceRequest.objects.filter(
        user=viewing_user,
        status='pending'
    ).order_by('-request_date')
    
    # Get approved but not paid advances
    approved_advances = AdvanceRequest.objects.filter(
        user=viewing_user,
        status='approved'
    ).order_by('-approved_at')
    
    # Calculate monthly stats (current month)
    from datetime import date
    today = date.today()
    month_start = today.replace(day=1)
    
    month_transactions = account.transactions.filter(
        transaction_date__gte=month_start
    )
    
    month_credits = month_transactions.filter(
        transaction_type__in=['credit', 'commission_payment', 'bonus', 'adjustment_credit']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    month_debits = month_transactions.filter(
        transaction_type__in=['debit', 'payment', 'adjustment_debit']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    month_advances = month_transactions.filter(
        transaction_type='advance_given'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Calculate net for this month (earned - paid - advances drawn)
    month_net = month_credits - month_debits - month_advances
    
    # Get all users for admin/office dropdown (tenant-scoped)
    if request.user.is_office_staff:
        all_users = get_tenant_users().filter(
            is_active=True
        ).order_by('first_name', 'last_name')
    else:
        all_users = []
    
    context = {
        'account': account,
        'viewing_user': viewing_user,
        'recent_transactions': recent_transactions,
        'pending_advances': pending_advances,
        'approved_advances': approved_advances,
        'month_credits': month_credits,
        'month_debits': month_debits,
        'month_advances': month_advances,
        'month_net': month_net,
        'all_users': all_users,
        'is_viewing_others': viewing_user != request.user,
    }
    
    return render(request, 'accounts/money_account_dashboard.html', context)


@login_required
def all_money_accounts(request):
    """List all user money accounts - Admin/Office only"""
    if not request.user.is_office_staff:
        messages.error(request, 'Access denied.')
        return redirect('accounts:money_account_dashboard')
    
    # Get all active users with their accounts (tenant-scoped)
    users = get_tenant_users().filter(is_active=True).order_by('first_name', 'last_name')
    
    accounts_data = []
    total_payable = Decimal('0.00')  # What we owe to users
    total_advance = Decimal('0.00')  # What users owe us
    
    for user in users:
        account, _ = UserMoneyAccount.objects.get_or_create(
            user=user,
            defaults={'created_by': request.user}
        )
        
        accounts_data.append({
            'user': user,
            'account': account
        })
        
        if account.current_balance > 0:
            total_payable += account.current_balance
        else:
            total_advance += abs(account.current_balance)
    
    context = {
        'accounts_data': accounts_data,
        'total_accounts': len(accounts_data),
        'total_owed': total_payable,
        'total_credited': sum(item['account'].total_credited for item in accounts_data),
        'total_paid': sum(item['account'].total_debited for item in accounts_data),
    }
    
    return render(request, 'accounts/all_money_accounts.html', context)


@login_required
@transaction.atomic
def add_credit(request):
    """Add credit to user account (commission payment, bonus, etc) - Admin/Office only"""
    if not request.user.is_office_staff:
        messages.error(request, 'Access denied.')
        return redirect('accounts:money_account_dashboard')
    
    if request.method == 'POST':
        try:
            user_id = request.POST.get('user_id')
            amount = Decimal(request.POST.get('amount'))
            transaction_type = request.POST.get('transaction_type')
            description = request.POST.get('description')
            commission_ref = request.POST.get('commission_reference', '')
            notes = request.POST.get('notes', '')
            
            ALLOWED_CREDIT_TYPES = {'credit', 'commission_payment', 'bonus', 'adjustment_credit'}
            if transaction_type not in ALLOWED_CREDIT_TYPES:
                raise ValueError(f"Invalid transaction type. Must be one of: {', '.join(ALLOWED_CREDIT_TYPES)}")
            
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            user = get_object_or_404(User, pk=user_id)
            account, _ = UserMoneyAccount.objects.get_or_create(
                user=user,
                defaults={'created_by': request.user}
            )
            
            # Create transaction
            MoneyTransaction.objects.create(
                account=account,
                transaction_type=transaction_type,
                amount=amount,
                description=description,
                commission_reference=commission_ref if commission_ref else None,
                notes=notes,
                created_by=request.user
            )
            
            messages.success(request, f'Rs. {amount:,.2f} credited to {user.get_full_name()}')
            return redirect(f'/accounts/money-account/?user_id={user_id}')
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    # GET request - show form
    users = get_tenant_users().filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'users': users
    }
    
    return render(request, 'accounts/add_credit.html', context)


@login_required
@transaction.atomic
def make_payment(request):
    """Make payment to user - Admin/Office only"""
    if not request.user.is_office_staff:
        messages.error(request, 'Access denied.')
        return redirect('accounts:money_account_dashboard')
    
    if request.method == 'POST':
        try:
            user_id = request.POST.get('user_id')
            amount = Decimal(request.POST.get('amount'))
            payment_method = request.POST.get('payment_method')
            reference_number = request.POST.get('reference_number', '')
            description = request.POST.get('description')
            notes = request.POST.get('notes', '')
            
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            user = get_object_or_404(User, pk=user_id)
            account, _ = UserMoneyAccount.objects.get_or_create(
                user=user,
                defaults={'created_by': request.user}
            )
            
            # Check if user has sufficient balance
            if account.current_balance < amount:
                raise ValueError(f"Insufficient balance. Available: Rs. {account.current_balance:,.2f}")
            
            # Create transaction
            MoneyTransaction.objects.create(
                account=account,
                transaction_type='payment',
                amount=amount,
                payment_method=payment_method,
                reference_number=reference_number if reference_number else None,
                description=description,
                notes=notes,
                created_by=request.user
            )
            
            messages.success(request, f'Payment of Rs. {amount:,.2f} disbursed to {user.get_full_name()}')
            return redirect(f'/accounts/money-account/?user_id={user_id}')
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    # GET request
    user_id = request.GET.get('user_id')
    users = get_tenant_users().filter(is_active=True).order_by('first_name', 'last_name')
    
    selected_user = None
    selected_account = None
    if user_id:
        selected_user = get_object_or_404(User, pk=user_id)
        selected_account, _ = UserMoneyAccount.objects.get_or_create(
            user=selected_user,
            defaults={'created_by': request.user}
        )
    
    context = {
        'users': users,
        'selected_user': selected_user,
        'selected_account': selected_account,
    }
    
    return render(request, 'accounts/make_payment.html', context)


@login_required
@transaction.atomic
def add_debit(request):
    """Add debit to user account (penalty, deduction, correction) - Admin/Office only"""
    if not request.user.is_office_staff:
        messages.error(request, 'Access denied.')
        return redirect('accounts:money_account_dashboard')
    
    if request.method == 'POST':
        try:
            user_id = request.POST.get('user_id')
            amount = Decimal(request.POST.get('amount'))
            transaction_type = request.POST.get('transaction_type', 'adjustment_debit')
            description = request.POST.get('description')
            notes = request.POST.get('notes', '')
            
            ALLOWED_DEBIT_TYPES = {'debit', 'payment', 'advance_given', 'advance_recovery', 'adjustment_debit'}
            if transaction_type not in ALLOWED_DEBIT_TYPES:
                raise ValueError(f"Invalid transaction type. Must be one of: {', '.join(ALLOWED_DEBIT_TYPES)}")
            
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            user = get_object_or_404(User, pk=user_id)
            account, _ = UserMoneyAccount.objects.get_or_create(
                user=user,
                defaults={'created_by': request.user}
            )
            
            # Create transaction
            MoneyTransaction.objects.create(
                account=account,
                transaction_type=transaction_type,
                amount=amount,
                description=description,
                notes=notes,
                created_by=request.user
            )
            
            messages.success(request, f'Rs. {amount:,.2f} debited from {user.get_full_name()}\'s account')
            return redirect(f'/accounts/money-account/?user_id={user_id}')
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    # GET request - show form
    user_id = request.GET.get('user_id')
    users = get_tenant_users().filter(is_active=True).order_by('first_name', 'last_name')
    
    selected_user = None
    selected_account = None
    if user_id:
        selected_user = get_object_or_404(User, pk=user_id)
        selected_account, _ = UserMoneyAccount.objects.get_or_create(
            user=selected_user,
            defaults={'created_by': request.user}
        )
    
    context = {
        'users': users,
        'selected_user': selected_user,
        'selected_account': selected_account,
    }
    
    return render(request, 'accounts/add_debit.html', context)


@login_required
@transaction.atomic
def request_advance(request):
    """User requests an advance"""
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount'))
            reason = request.POST.get('reason', '')
            
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            if not reason:
                raise ValueError("Reason is required")
            
            # Create advance request
            AdvanceRequest.objects.create(
                user=request.user,
                requested_amount=amount,
                reason=reason
            )
            
            messages.success(request, f'Advance request for Rs. {amount:,.2f} submitted successfully!')
            return redirect('accounts:money_account_dashboard')
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('accounts:money_account_dashboard')
    
    return render(request, 'accounts/request_advance.html')


@login_required
def advance_requests_list(request):
    """List all advance requests - Admin/Office only"""
    if not request.user.is_office_staff:
        messages.error(request, 'Access denied.')
        return redirect('accounts:money_account_dashboard')
    
    # Get pending requests (tenant-scoped)
    tenant_filter = get_tenant_filter('user__tenant')
    pending = AdvanceRequest.objects.filter(
        status='pending', **tenant_filter
    ).select_related('user').order_by('-request_date')
    
    # Get approved but not paid
    approved = AdvanceRequest.objects.filter(
        status='approved', **tenant_filter
    ).select_related('user').order_by('-approved_at')
    
    # Get recent completed (paid/rejected)
    completed = AdvanceRequest.objects.filter(
        status__in=['paid', 'rejected', 'cancelled'], **tenant_filter
    ).select_related('user', 'approved_by').order_by('-updated_at')[:30]
    
    context = {
        'pending': pending,
        'approved': approved,
        'completed': completed,
    }
    
    return render(request, 'accounts/advance_requests_list.html', context)


@login_required
@transaction.atomic
def approve_advance(request, pk):
    """Approve advance request - Admin/Office only"""
    if not request.user.is_office_staff:
        messages.error(request, 'Access denied.')
        return redirect('accounts:money_account_dashboard')
    
    advance_req = get_object_or_404(AdvanceRequest, pk=pk)
    
    if advance_req.status != 'pending':
        messages.warning(request, 'This request has already been processed.')
        return redirect('accounts:advance_requests_list')
    
    if request.method == 'POST':
        try:
            approved_amount = Decimal(request.POST.get('approved_amount'))
            approval_notes = request.POST.get('approval_notes', '')
            
            if approved_amount <= 0:
                raise ValueError("Amount must be positive")
            
            advance_req.status = 'approved'
            advance_req.approved_amount = approved_amount
            advance_req.approved_by = request.user
            advance_req.approved_at = timezone.now()
            advance_req.approval_notes = approval_notes
            advance_req.save()
            
            messages.success(request, f'Advance request approved for Rs. {approved_amount:,.2f}')
            return redirect('accounts:advance_requests_list')
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return redirect('accounts:advance_requests_list')


@login_required
@transaction.atomic
def reject_advance(request, pk):
    """Reject advance request - Admin/Office only"""
    if not request.user.is_office_staff:
        messages.error(request, 'Access denied.')
        return redirect('accounts:money_account_dashboard')
    
    advance_req = get_object_or_404(AdvanceRequest, pk=pk)
    
    if advance_req.status != 'pending':
        messages.warning(request, 'This request has already been processed.')
        return redirect('accounts:advance_requests_list')
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        
        advance_req.status = 'rejected'
        advance_req.rejection_reason = rejection_reason
        advance_req.save()
        
        messages.success(request, 'Advance request rejected.')
        return redirect('accounts:advance_requests_list')
    
    return redirect('accounts:advance_requests_list')


@login_required
@transaction.atomic
def pay_advance(request, pk):
    """Pay approved advance - Admin/Office only"""
    if not request.user.is_office_staff:
        messages.error(request, 'Access denied.')
        return redirect('accounts:money_account_dashboard')
    
    advance_req = get_object_or_404(AdvanceRequest, pk=pk)
    
    if advance_req.status != 'approved':
        messages.error(request, 'Advance must be approved first.')
        return redirect('accounts:advance_requests_list')
    
    if request.method == 'POST':
        try:
            payment_method = request.POST.get('payment_method')
            payment_reference = request.POST.get('payment_reference', '')
            override_limit = request.POST.get('override_limit') == 'on'  # Checkbox to bypass validation
            
            # Get or create account
            account, _ = UserMoneyAccount.objects.get_or_create(
                user=advance_req.user,
                defaults={'created_by': request.user}
            )
            
            # Update balance to get current state
            account.update_balance()
            account.refresh_from_db()
            
            # CRITICAL VALIDATION: Cannot advance more than current balance
            # (Cannot pay them more than we owe them) - UNLESS override is enabled
            if not override_limit and advance_req.approved_amount > account.current_balance:
                raise ValueError(
                    f"Cannot disburse advance of Rs. {advance_req.approved_amount:,.2f}. "
                    f"User's balance due is only Rs. {account.current_balance:,.2f}. "
                    f"They must earn more commission before drawing this advance. "
                    f"Check 'Override Balance Limit' to proceed anyway."
                )
            
            # Create advance transaction (will decrease balance, can go negative if overridden)
            txn = MoneyTransaction.objects.create(
                account=account,
                transaction_type='advance_given',
                amount=advance_req.approved_amount,
                payment_method=payment_method,
                reference_number=payment_reference if payment_reference else None,
                description=f'Advance payment - {advance_req.request_number}',
                notes=f'Reason: {advance_req.reason}' + (' [OVERRIDE: Exceeded balance limit]' if override_limit else ''),
                advance_request=advance_req,
                created_by=request.user
            )
            
            # Update advance request
            advance_req.status = 'paid'
            advance_req.paid_at = timezone.now()
            advance_req.payment_method = payment_method
            advance_req.payment_reference = payment_reference
            advance_req.save()
            
            messages.success(request, f'Advance of Rs. {advance_req.approved_amount:,.2f} disbursed to {advance_req.user.get_full_name()}')
            return redirect('accounts:advance_requests_list')
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return redirect('accounts:advance_requests_list')


@login_required
@transaction.atomic
def recover_advance(request):
    """Recover advance from user earnings - Admin/Office only"""
    if not request.user.is_office_staff:
        messages.error(request, 'Access denied.')
        return redirect('accounts:money_account_dashboard')
    
    if request.method == 'POST':
        try:
            user_id = request.POST.get('user_id')
            amount = Decimal(request.POST.get('amount'))
            description = request.POST.get('description')
            notes = request.POST.get('notes', '')
            advance_request_id = request.POST.get('advance_request_id', '')
            transaction_date = request.POST.get('transaction_date')
            
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            user = get_object_or_404(User, pk=user_id)
            
            # Get account and ensure balance is up to date
            try:
                account = UserMoneyAccount.objects.get(user=user)
                account.update_balance()  # Recalculate from transactions
                account.refresh_from_db()  # Get fresh values
            except UserMoneyAccount.DoesNotExist:
                raise ValueError("User has no money account")
            
            # Calculate current outstanding advance
            outstanding = max(account.total_advance_given - account.total_advance_recovered, Decimal('0.00'))
            
            if outstanding <= 0:
                raise ValueError("User has no outstanding advance to recover")
            
            if amount > outstanding:
                raise ValueError(f"Cannot recover Rs. {amount:,.2f}. Outstanding advance is only Rs. {outstanding:,.2f}")
            
            # Get advance request if specified
            advance_req = None
            if advance_request_id:
                advance_req = AdvanceRequest.objects.filter(pk=advance_request_id).first()
            
            # Create recovery transaction
            MoneyTransaction.objects.create(
                account=account,
                transaction_type='advance_recovery',
                amount=amount,
                transaction_date=transaction_date,
                description=description,
                notes=notes,
                advance_request=advance_req,
                created_by=request.user
            )
            
            messages.success(request, f'Advance recovery of Rs. {amount:,.2f} recorded for {user.get_full_name()}')
            return redirect(f'/accounts/money-account/?user_id={user_id}')
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    # GET request
    user_id = request.GET.get('user_id')
    users = get_tenant_users().filter(is_active=True).order_by('first_name', 'last_name')
    
    selected_user = None
    selected_account = None
    if user_id:
        selected_user = get_object_or_404(User, pk=user_id)
        selected_account, _ = UserMoneyAccount.objects.get_or_create(
            user=selected_user,
            defaults={'created_by': request.user}
        )
    
    context = {
        'users': users,
        'selected_user': selected_user,
        'selected_account': selected_account,
    }
    
    return render(request, 'accounts/recover_advance.html', context)


@login_required
def transaction_history(request):
    """View full transaction history for a user"""
    # Determine which user's history to show
    if request.user.is_office_staff:
        user_id = request.GET.get('user_id')
        if user_id:
            viewing_user = get_object_or_404(User, pk=user_id)
        else:
            viewing_user = request.user
    else:
        viewing_user = request.user
    
    # Get account
    account = get_object_or_404(UserMoneyAccount, user=viewing_user)
    
    # Get all transactions
    transactions = account.transactions.all()
    
    # Filter by type if specified
    txn_type = request.GET.get('type')
    if txn_type:
        transactions = transactions.filter(transaction_type=txn_type)
    
    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        transactions = transactions.filter(transaction_date__date__gte=start_date)
    if end_date:
        transactions = transactions.filter(transaction_date__date__lte=end_date)
    
    context = {
        'account': account,
        'viewing_user': viewing_user,
        'transactions': transactions,
        'selected_type': txn_type,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'accounts/transaction_history.html', context)
