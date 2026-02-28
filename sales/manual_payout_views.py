"""
Manual Commission Payout Views
Professional commission disbursement to user money accounts
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db import transaction as db_transaction
from datetime import datetime, date
from decimal import Decimal
import json

from .models import CommissionTransaction
from .commission_schedule_models import CommissionPayoutHistory, UserCommissionPayout
from accounts.models import User
from accounts.money_account_models import UserMoneyAccount, MoneyTransaction
from accounts.tenant_utils import get_tenant_users


@login_required
def manual_payout_list(request):
    """
    Manual Commission Payout Page
    Shows all users with commission balances ready for payout
    Distributor and admin can process payouts manually
    """
    # Only distributor and admin can access
    if request.user.user_type == 'sales_rep':
        messages.error(request, 'Access denied. Only admin and distributor can process commission payouts.')
        return redirect('sales:commission_dashboard')
    
    # Get all active users (tenant-scoped)
    all_users = get_tenant_users().filter(
        is_active=True
    ).order_by('first_name', 'last_name')
    
    # Build list with balances
    payout_candidates = []
    total_payable = Decimal('0.00')
    
    for user in all_users:
        commission_balance = CommissionTransaction.get_rep_balance(user)
        
        if commission_balance > 0:
            # Get or create money account
            money_account, created = UserMoneyAccount.objects.get_or_create(
                user=user,
                defaults={
                    'created_by': request.user,
                    'opening_balance': Decimal('0.00')
                }
            )
            
            # Get last payout date for this user
            last_payout = UserCommissionPayout.objects.filter(
                user=user,
                status='success'
            ).select_related('history').order_by('-created_at').first()
            
            last_payout_date = last_payout.history.execution_date if last_payout else None
            
            payout_candidates.append({
                'user': user,
                'commission_balance': commission_balance,
                'money_account': money_account,
                'money_balance': money_account.current_balance,
                'last_payout_date': last_payout_date,
            })
            total_payable += commission_balance
    
    # Get recent payout history (last 20)
    recent_payouts = CommissionPayoutHistory.objects.filter(
        is_manual=True
    ).order_by('-execution_date')[:20]
    
    context = {
        'payout_candidates': payout_candidates,
        'total_payable': total_payable,
        'recent_payouts': recent_payouts,
    }
    
    return render(request, 'sales/manual_payout_list.html', context)


@login_required
def process_manual_payout(request):
    """
    Process manual payout for selected users
    Creates MoneyTransactions and logs in CommissionPayoutHistory
    """
    # Only distributor and admin can access
    if request.user.user_type == 'sales_rep':
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})
    
    try:
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        notes = data.get('notes', '')
        
        if not user_ids:
            return JsonResponse({'success': False, 'error': 'No users selected'})
        
        # Process payout in atomic transaction
        with db_transaction.atomic():
            execution_start = timezone.now()
            
            # Create payout history record
            payout_history = CommissionPayoutHistory.objects.create(
                schedule=None,  # Manual payout has no schedule
                execution_date=execution_start,
                status='success',  # Will update if failures occur
                period_start=None,
                period_end=execution_start,
                is_manual=True,
                executed_by=request.user,
                notes=notes
            )
            
            successful_count = 0
            failed_count = 0
            total_amount = Decimal('0.00')
            details = []
            
            for user_id in user_ids:
                try:
                    user = User.objects.get(id=user_id, is_active=True)
                    commission_balance = CommissionTransaction.get_rep_balance(user)
                    
                    if commission_balance <= 0:
                        failed_count += 1
                        details.append({
                            'user': user.get_full_name(),
                            'status': 'skipped',
                            'reason': 'No balance'
                        })
                        continue
                    
                    # Get or create money account
                    money_account, _ = UserMoneyAccount.objects.get_or_create(
                        user=user,
                        defaults={
                            'created_by': request.user,
                            'opening_balance': Decimal('0.00')
                        }
                    )
                    
                    # Create money transaction
                    money_txn = MoneyTransaction.objects.create(
                        account=money_account,
                        transaction_type='commission_payment',
                        amount=commission_balance,
                        payment_method='adjustment',
                        description=f'Manual Commission Disbursement - {execution_start.strftime("%B %Y")}',
                        commission_reference=execution_start.strftime('%Y-%m'),
                        reference_number=payout_history.payout_number if hasattr(payout_history, 'payout_number') else '',
                        notes=notes,
                        transaction_date=execution_start,
                        created_by=request.user
                    )
                    
                    # Update money account balance
                    money_account.update_balance()
                    
                    # CRITICAL: Create CommissionTransaction to clear the commission balance
                    # This debits the commission (negative amount) to zero out the running balance
                    CommissionTransaction.objects.create(
                        transaction_type='adjustment',
                        transaction_date=execution_start,
                        sales_rep=user,
                        applicable_rate=Decimal('0.00'),
                        commission_earned=-commission_balance,  # NEGATIVE to debit/clear balance
                        notes=f'Commission cleared - Manual payout {payout_history.payout_number}',
                        bill=None,
                        settlement=None,
                        return_ref=None,
                        payout_history=payout_history
                    )
                    
                    # Create user payout record
                    UserCommissionPayout.objects.create(
                        history=payout_history,
                        user=user,
                        commission_balance=commission_balance,
                        amount_credited=commission_balance,
                        money_transaction=money_txn,
                        status='success'
                    )
                    
                    successful_count += 1
                    total_amount += commission_balance
                    details.append({
                        'user': user.get_full_name(),
                        'amount': float(commission_balance),
                        'status': 'success'
                    })
                    
                except Exception as e:
                    failed_count += 1
                    details.append({
                        'user_id': user_id,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            # Update payout history
            execution_end = timezone.now()
            duration = (execution_end - execution_start).total_seconds()
            
            payout_history.total_users_processed = successful_count
            payout_history.total_amount_credited = total_amount
            payout_history.successful_payouts = successful_count
            payout_history.failed_payouts = failed_count
            payout_history.skipped_payouts = 0
            payout_history.duration_seconds = duration
            payout_history.details = json.dumps(details)
            
            if failed_count > 0 and successful_count > 0:
                payout_history.status = 'partial'
            elif failed_count == len(user_ids):
                payout_history.status = 'failed'
            else:
                payout_history.status = 'success'
            
            payout_history.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Payout completed: {successful_count} successful, {failed_count} failed',
            'payout_number': payout_history.payout_number,
            'successful_count': successful_count,
            'failed_count': failed_count,
            'total_amount': float(total_amount)
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def payout_history_detail(request, history_id):
    """
    View details of a specific payout execution
    """
    # Only distributor and admin can access
    if request.user.user_type == 'sales_rep':
        messages.error(request, 'Access denied.')
        return redirect('sales:commission_dashboard')
    
    payout_history = get_object_or_404(CommissionPayoutHistory, id=history_id)
    
    # Get user payout records
    user_payouts = UserCommissionPayout.objects.filter(
        history=payout_history
    ).select_related('user', 'money_transaction').order_by('user__first_name', 'user__last_name')
    
    # Calculate totals and counts
    total_commission_balance = sum(p.commission_balance for p in user_payouts)
    total_amount_credited = sum(p.amount_credited for p in user_payouts)
    successful_count = user_payouts.filter(status='success').count()
    failed_count = user_payouts.filter(status='failed').count()
    
    context = {
        'payout': payout_history,  # Template uses 'payout'
        'payout_history': payout_history,
        'user_payouts': user_payouts,
        'total_commission_balance': total_commission_balance,
        'total_amount_credited': total_amount_credited,
        'successful_count': successful_count,
        'failed_count': failed_count,
    }
    
    return render(request, 'sales/payout_history_detail.html', context)


@login_required
def payout_detail_by_number(request, payout_number):
    """
    Find payout by number and redirect to detail page
    Allows linking from money transactions via payout number
    """
    payout_history = get_object_or_404(CommissionPayoutHistory, payout_number=payout_number)
    return redirect('sales:payout_history_detail', history_id=payout_history.id)
