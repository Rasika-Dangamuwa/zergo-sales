"""
FOC Reset Views
Handle FOC data archiving and reset operations
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q, Count
from django.db import transaction as db_transaction
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
import json

from products.models import FOCValueAccount, FOCValueTransaction
from .foc_reset_models import FOCReset, FOCResetTransaction


@login_required
def foc_reset_confirm(request):
    """Confirmation page before resetting FOC data"""
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    # Get current statistics to show what will be reset
    active_transactions = FOCValueTransaction.objects.filter(is_archived=False)
    
    stats = {
        'total_transactions': active_transactions.count(),
        'total_foc_received': active_transactions.filter(
            transaction_type='foc_received'
        ).aggregate(total=Sum('foc_value'))['total'] or Decimal('0'),
        'total_foc_given': active_transactions.filter(
            transaction_type__in=['foc_given', 'implicit_foc']
        ).aggregate(total=Sum('foc_value'))['total'] or Decimal('0'),
        'total_foc_returned': active_transactions.filter(
            transaction_type='return_foc_restored'
        ).aggregate(total=Sum('foc_value'))['total'] or Decimal('0'),
        'total_products': active_transactions.values('product').distinct().count(),
        'total_sales_reps': active_transactions.filter(
            sales_rep__isnull=False
        ).values('sales_rep').distinct().count(),
        'total_companies': FOCValueAccount.objects.count(),
    }
    
    context = {
        'stats': stats,
    }
    
    return render(request, 'sales/foc_reset_confirm.html', context)


@login_required
def foc_reset_list(request):
    """List all FOC resets with summary totals"""
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    resets = FOCReset.objects.all().order_by('-reset_date')
    
    # Calculate cumulative totals
    cumulative_totals = {
        'total_foc_received': sum(r.total_foc_received for r in resets),
        'total_foc_given': sum(r.total_foc_given for r in resets),
        'total_foc_returned': sum(r.total_foc_returned for r in resets),
        'net_foc_value': sum(r.net_foc_value for r in resets),
        'total_transactions': sum(r.total_transactions for r in resets),
    }
    
    # Aggregate product-wise summary across all resets
    product_totals = {}
    for reset in resets:
        for product in reset.product_summary_snapshot:
            product_key = product.get('product', '')
            if product_key not in product_totals:
                product_totals[product_key] = {
                    'product': product_key,
                    'company': product.get('company', ''),
                    'foc_received_qty': 0,
                    'foc_received_value': 0,
                    'foc_given_qty': 0,
                    'foc_given_value': 0,
                    'implicit_foc_value': 0,
                    'foc_returned_qty': 0,
                    'foc_returned_value': 0,
                    'net_foc_value': 0,
                }
            
            # Accumulate values
            product_totals[product_key]['foc_received_qty'] += product.get('foc_received_qty', 0)
            product_totals[product_key]['foc_received_value'] += product.get('foc_received_value', 0)
            product_totals[product_key]['foc_given_qty'] += product.get('foc_given_qty', 0)
            product_totals[product_key]['foc_given_value'] += product.get('foc_given_value', 0)
            product_totals[product_key]['implicit_foc_value'] += product.get('implicit_foc_value', 0)
            product_totals[product_key]['foc_returned_qty'] += product.get('foc_returned_qty', 0)
            product_totals[product_key]['foc_returned_value'] += product.get('foc_returned_value', 0)
            
            # Calculate net FOC value
            product_totals[product_key]['net_foc_value'] = (
                product_totals[product_key]['foc_received_value'] +
                product_totals[product_key]['foc_returned_value'] -
                product_totals[product_key]['foc_given_value'] -
                product_totals[product_key]['implicit_foc_value']
            )
    
    # Get current display order from Product table for sorting
    from products.models import Product
    product_display_orders = {}
    for product in Product.objects.all():
        product_key = f"{product.product_name} - {product.size}"
        product_display_orders[product_key] = product.display_order or 999
    
    # Add display order to product totals
    for product_key in product_totals:
        product_totals[product_key]['display_order'] = product_display_orders.get(product_key, 999)
    
    # Convert to sorted list (by display_order, then product name)
    product_summary = sorted(product_totals.values(), key=lambda x: (x['display_order'], x['product']))
    
    # Calculate grand totals for products
    product_grand_totals = {
        'total_foc_received_qty': sum(p['foc_received_qty'] for p in product_summary),
        'total_foc_received_value': sum(p['foc_received_value'] for p in product_summary),
        'total_foc_given_qty': sum(p['foc_given_qty'] for p in product_summary),
        'total_foc_given_value': sum(p['foc_given_value'] for p in product_summary),
        'total_implicit_foc_value': sum(p['implicit_foc_value'] for p in product_summary),
        'total_foc_returned_qty': sum(p['foc_returned_qty'] for p in product_summary),
        'total_foc_returned_value': sum(p['foc_returned_value'] for p in product_summary),
        'net_total': sum(p['net_foc_value'] for p in product_summary),
    }
    
    # Aggregate sales rep summary across all resets
    rep_totals = {}
    for reset in resets:
        for rep in reset.sales_rep_summary_snapshot:
            rep_key = rep.get('sales_rep', '')
            if rep_key not in rep_totals:
                rep_totals[rep_key] = {
                    'sales_rep': rep_key,
                    'foc_given_qty': 0,
                    'foc_given_value': 0,
                    'implicit_foc_value': 0,
                    'foc_returned_qty': 0,
                    'foc_returned_value': 0,
                    'total_foc_used': 0,
                }
            
            # Accumulate values
            rep_totals[rep_key]['foc_given_qty'] += rep.get('foc_given_qty', 0)
            rep_totals[rep_key]['foc_given_value'] += rep.get('foc_given_value', 0)
            rep_totals[rep_key]['implicit_foc_value'] += rep.get('implicit_foc_value', 0)
            rep_totals[rep_key]['foc_returned_qty'] += rep.get('foc_returned_qty', 0)
            rep_totals[rep_key]['foc_returned_value'] += rep.get('foc_returned_value', 0)
            
            # Calculate total FOC used
            rep_totals[rep_key]['total_foc_used'] = (
                rep_totals[rep_key]['foc_given_value'] +
                rep_totals[rep_key]['implicit_foc_value'] -
                rep_totals[rep_key]['foc_returned_value']
            )
    
    # Convert to sorted list
    sales_rep_summary = sorted(rep_totals.values(), key=lambda x: x['sales_rep'])
    
    # Calculate grand totals for sales reps
    rep_grand_totals = {
        'total_foc_given_qty': sum(r['foc_given_qty'] for r in sales_rep_summary),
        'total_foc_given_value': sum(r['foc_given_value'] for r in sales_rep_summary),
        'total_implicit_foc_value': sum(r['implicit_foc_value'] for r in sales_rep_summary),
        'total_foc_returned_qty': sum(r['foc_returned_qty'] for r in sales_rep_summary),
        'total_foc_returned_value': sum(r['foc_returned_value'] for r in sales_rep_summary),
        'total_foc_used': sum(r['total_foc_used'] for r in sales_rep_summary),
    }
    
    context = {
        'resets': resets,
        'cumulative_totals': cumulative_totals,
        'product_summary': product_summary,
        'product_grand_totals': product_grand_totals,
        'sales_rep_summary': sales_rep_summary,
        'rep_grand_totals': rep_grand_totals,
    }
    
    return render(request, 'sales/foc_reset_list.html', context)


@login_required
def foc_reset_detail(request, reset_id):
    """View detailed data for a specific reset"""
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    reset = get_object_or_404(FOCReset, pk=reset_id)
    
    # Parse JSON snapshots
    company_accounts = reset.company_accounts_snapshot
    product_summary = reset.product_summary_snapshot
    sales_rep_summary = reset.sales_rep_summary_snapshot
    transaction_breakdown = reset.transaction_types_breakdown
    
    # Calculate net FOC value for each product
    for product in product_summary:
        net_foc = (
            product.get('foc_received_value', 0) + 
            product.get('foc_returned_value', 0) - 
            product.get('foc_given_value', 0) - 
            product.get('implicit_foc_value', 0)
        )
        product['net_foc_value'] = net_foc
    
    # Calculate totals for product summary
    total_received_qty = sum(p.get('foc_received_qty', 0) for p in product_summary)
    total_given_qty = sum(p.get('foc_given_qty', 0) for p in product_summary)
    total_returned_qty = sum(p.get('foc_returned_qty', 0) for p in product_summary)
    total_implicit_value = sum(p.get('implicit_foc_value', 0) for p in product_summary)
    
    # Calculate totals for sales rep summary (from sales rep snapshot, not global totals)
    from decimal import Decimal
    total_rep_given_value = sum(Decimal(str(rep.get('foc_given_value', 0))) for rep in sales_rep_summary)
    total_rep_implicit_value = sum(Decimal(str(rep.get('implicit_foc_value', 0))) for rep in sales_rep_summary)
    total_rep_returned_value = sum(Decimal(str(rep.get('foc_returned_value', 0))) for rep in sales_rep_summary)
    
    # Calculate total FOC used for sales reps (given + implicit - returned)
    total_foc_used = total_rep_given_value + total_rep_implicit_value - total_rep_returned_value
    
    # Get all archived transactions for this reset
    archived_transactions = FOCResetTransaction.objects.filter(
        reset=reset
    ).order_by('-transaction_date', '-id')
    
    context = {
        'reset': reset,
        'company_accounts': company_accounts,
        'product_summary': product_summary,
        'sales_rep_summary': sales_rep_summary,
        'transaction_breakdown': transaction_breakdown,
        'archived_transactions': archived_transactions,
        'total_received_qty': total_received_qty,
        'total_given_qty': total_given_qty,
        'total_returned_qty': total_returned_qty,
        'total_implicit_value': total_implicit_value,
        'total_foc_used': total_foc_used,
        'total_rep_given_value': total_rep_given_value,
        'total_rep_implicit_value': total_rep_implicit_value,
        'total_rep_returned_value': total_rep_returned_value,
    }
    
    return render(request, 'sales/foc_reset_detail.html', context)


@login_required
def process_foc_reset(request):
    """
    Process FOC reset - Archive all current FOC data and mark as archived
    Only admin/office can perform this operation
    """
    if request.user.user_type not in ['admin', 'office']:
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})
    
    try:
        with db_transaction.atomic():
            # Get all non-archived FOC transactions
            active_transactions = FOCValueTransaction.objects.filter(is_archived=False)
            
            if not active_transactions.exists():
                return JsonResponse({
                    'success': False,
                    'error': 'No active FOC transactions to reset'
                })
            
            # Calculate dashboard totals
            total_foc_received = active_transactions.filter(
                transaction_type='foc_received'
            ).aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
            
            total_foc_given = active_transactions.filter(
                transaction_type__in=['foc_given', 'implicit_foc']
            ).aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
            
            total_foc_returned = active_transactions.filter(
                transaction_type='return_foc_restored'
            ).aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
            
            net_foc_value = total_foc_received - total_foc_given + total_foc_returned
            
            # Get company accounts snapshot
            accounts = FOCValueAccount.objects.all()
            company_accounts_data = []
            utilizations = []
            
            for acc in accounts:
                company_accounts_data.append({
                    'company': acc.company.company_name,
                    'foc_received': float(acc.total_foc_received_value),
                    'foc_given': float(acc.total_foc_given_value),
                    'net_value': float(acc.net_foc_value),
                    'utilization': float(acc.foc_utilization_percentage),
                })
                if acc.total_foc_received_value > 0:
                    utilizations.append(acc.foc_utilization_percentage)
            
            avg_utilization = sum(utilizations) / len(utilizations) if utilizations else Decimal('0')
            
            # Get product summary snapshot
            product_summary = active_transactions.values(
                'product__product_name',
                'product__size',
                'product__company__company_name',
                'product__display_order'
            ).annotate(
                foc_received_qty=Sum('foc_quantity', filter=Q(transaction_type='foc_received')),
                foc_given_qty=Sum('foc_quantity', filter=Q(transaction_type='foc_given')),
                foc_returned_qty=Sum('foc_quantity', filter=Q(transaction_type='return_foc_restored')),
                foc_received_value=Sum('foc_value', filter=Q(transaction_type='foc_received')),
                foc_given_value=Sum('foc_value', filter=Q(transaction_type='foc_given')),
                implicit_foc_value=Sum('foc_value', filter=Q(transaction_type='implicit_foc')),
                foc_returned_value=Sum('foc_value', filter=Q(transaction_type='return_foc_restored')),
            ).order_by('product__display_order', 'product__product_name')
            
            product_summary_data = [
                {
                    'product': f"{p['product__product_name']} - {p['product__size']}",
                    'company': p['product__company__company_name'],
                    'display_order': p['product__display_order'] or 999,
                    'foc_received_qty': float(p['foc_received_qty'] or 0),
                    'foc_given_qty': float(p['foc_given_qty'] or 0),
                    'foc_returned_qty': float(p['foc_returned_qty'] or 0),
                    'foc_received_value': float(p['foc_received_value'] or 0),
                    'foc_given_value': float(p['foc_given_value'] or 0),
                    'implicit_foc_value': float(p['implicit_foc_value'] or 0),
                    'foc_returned_value': float(p['foc_returned_value'] or 0),
                }
                for p in product_summary
            ]
            
            # Get sales rep summary snapshot
            sales_rep_summary = active_transactions.filter(
                sales_rep__isnull=False
            ).values(
                'sales_rep__first_name',
                'sales_rep__last_name',
                'sales_rep__username'
            ).annotate(
                foc_given_qty=Sum('foc_quantity', filter=Q(transaction_type='foc_given')),
                foc_returned_qty=Sum('foc_quantity', filter=Q(transaction_type='return_foc_restored')),
                foc_given_value=Sum('foc_value', filter=Q(transaction_type='foc_given')),
                implicit_foc_value=Sum('foc_value', filter=Q(transaction_type='implicit_foc')),
                foc_returned_value=Sum('foc_value', filter=Q(transaction_type='return_foc_restored')),
                bills_count=Count('bill_item_id', distinct=True)
            ).order_by('sales_rep__first_name')
            
            sales_rep_summary_data = [
                {
                    'sales_rep': f"{s['sales_rep__first_name']} {s['sales_rep__last_name']}",
                    'foc_given_qty': float(s['foc_given_qty'] or 0),
                    'foc_returned_qty': float(s['foc_returned_qty'] or 0),
                    'foc_given_value': float(s['foc_given_value'] or 0),
                    'implicit_foc_value': float(s['implicit_foc_value'] or 0),
                    'foc_returned_value': float(s['foc_returned_value'] or 0),
                    'bills_count': s['bills_count'] or 0,
                }
                for s in sales_rep_summary
            ]
            
            # Transaction type breakdown
            txn_breakdown = active_transactions.values('transaction_type').annotate(
                count=Count('id'),
                total_value=Sum('foc_value')
            )
            
            transaction_breakdown_data = [
                {
                    'type': t['transaction_type'],
                    'count': t['count'],
                    'total_value': float(t['total_value'] or 0),
                }
                for t in txn_breakdown
            ]
            
            # Create reset record
            reset = FOCReset.objects.create(
                reset_by=request.user,
                total_foc_received=total_foc_received,
                total_foc_given=total_foc_given,
                total_foc_returned=total_foc_returned,
                net_foc_value=net_foc_value,
                avg_utilization=avg_utilization,
                total_transactions=active_transactions.count(),
                total_products=active_transactions.values('product').distinct().count(),
                total_sales_reps=active_transactions.filter(sales_rep__isnull=False).values('sales_rep').distinct().count(),
                company_accounts_snapshot=company_accounts_data,
                product_summary_snapshot=product_summary_data,
                sales_rep_summary_snapshot=sales_rep_summary_data,
                transaction_types_breakdown=transaction_breakdown_data,
            )
            
            # Archive all active transactions
            archived_count = 0
            for txn in active_transactions:
                # Get IDs for creating links
                purchase_id = txn.purchase_item.purchase.id if txn.purchase_item and txn.purchase_item.purchase else None
                bill_id = txn.bill_item.bill.id if txn.bill_item and txn.bill_item.bill else None
                return_id = txn.return_item.return_ref.id if txn.return_item and txn.return_item.return_ref else None
                
                # Create archived transaction record
                FOCResetTransaction.objects.create(
                    reset=reset,
                    transaction_type=txn.transaction_type,
                    transaction_date=txn.transaction_date,
                    company_name=txn.foc_account.company.company_name if txn.foc_account else '',
                    product_name=txn.product.product_name if txn.product else '',
                    product_size=txn.product.size if txn.product else '',
                    shop_name=txn.shop.shop_name if txn.shop else '',
                    sales_rep_name=f"{txn.sales_rep.first_name} {txn.sales_rep.last_name}" if txn.sales_rep else '',
                    foc_quantity=txn.foc_quantity,
                    shop_price_at_time=txn.shop_price_at_time,
                    foc_value=txn.foc_value,
                    reference_number=txn.reference_number,
                    notes=txn.notes,
                    purchase_id=purchase_id,
                    bill_id=bill_id,
                    return_id=return_id,
                )
                archived_count += 1
            
            # Mark all transactions as archived
            active_transactions.update(is_archived=True)
            
            # Update all FOC account balances to reflect the archival
            for account in FOCValueAccount.objects.all():
                account.update_balance()
            
            return JsonResponse({
                'success': True,
                'reset_number': reset.reset_number,
                'transactions_archived': archived_count,
                'message': f'FOC reset completed. {archived_count} transactions archived as {reset.reset_number}'
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
