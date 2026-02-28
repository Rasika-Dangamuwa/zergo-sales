from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Q, Count
from decimal import Decimal
from .models import OldPayment as Payment, CreditNote, PaymentAttachment
from shops.models import Shop
from sales.models import Bill


@login_required
def payment_list(request):
    """List all payments with filters"""
    if request.user.is_sales_rep:
        payments = Payment.objects.filter(received_by=request.user).select_related('shop', 'bill', 'received_by')
    else:
        payments = Payment.objects.all().select_related('shop', 'bill', 'received_by', 'verified_by')
    
    # Filter by payment method
    method = request.GET.get('method')
    if method:
        payments = payments.filter(payment_method=method)
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        payments = payments.filter(status=status)
    
    # Filter by date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
    
    # Order by latest first
    payments = payments.order_by('-payment_date')
    
    # Calculate statistics
    stats = payments.aggregate(
        total_amount=Sum('amount'),
        total_count=Count('id')
    )
    
    # Status breakdown
    status_breakdown = {
        'completed': payments.filter(status='completed').aggregate(total=Sum('amount'), count=Count('id')),
        'pending': payments.filter(status='pending').aggregate(total=Sum('amount'), count=Count('id')),
        'cancelled': payments.filter(status='cancelled').aggregate(total=Sum('amount'), count=Count('id')),
        'bounced': payments.filter(status='bounced').aggregate(total=Sum('amount'), count=Count('id')),
    }
    
    context = {
        'payments': payments,
        'stats': stats,
        'status_breakdown': status_breakdown,
        'current_method': method,
        'current_status': status,
    }
    return render(request, 'payments/payment_list.html', context)


@login_required
def pending_payments(request):
    """List all pending payments for office verification"""
    if request.user.is_sales_rep:
        messages.error(request, 'Access denied. Only office staff can view this page.')
        return redirect('payments:list')
    
    pending = Payment.objects.filter(status='pending').select_related('shop', 'bill', 'received_by').order_by('-payment_date')
    
    # Separate by payment method
    cheques = pending.filter(payment_method='cheque')
    bank_transfers = pending.filter(payment_method='bank_transfer')
    
    context = {
        'cheques': cheques,
        'bank_transfers': bank_transfers,
        'total_pending': pending.count(),
        'total_amount': pending.aggregate(total=Sum('amount'))['total'] or Decimal('0'),
    }
    return render(request, 'payments/pending_payments.html', context)


@login_required
@transaction.atomic
def add_payment(request):
    """Add new payment"""
    if request.method == 'POST':
        try:
            shop_id = request.POST.get('shop_id')
            shop = Shop.objects.get(pk=shop_id)
            
            bill_id = request.POST.get('bill_id')
            bill = Bill.objects.get(pk=bill_id) if bill_id else None
            
            payment = Payment.objects.create(
                shop=shop,
                bill=bill,
                payment_method=request.POST.get('payment_method'),
                amount=request.POST.get('amount'),
                reference_number=request.POST.get('reference_number'),
                bank_name=request.POST.get('bank_name'),
                cheque_date=request.POST.get('cheque_date') if request.POST.get('cheque_date') else None,
                notes=request.POST.get('notes'),
                received_by=request.user,
                status='pending' if request.POST.get('payment_method') in ['cheque', 'bank_transfer'] else 'completed'
            )
            
            if 'attachment' in request.FILES:
                payment.attachment = request.FILES['attachment']
            
            payment.generate_payment_number()
            payment.save()
            
            # Update bill payment if bill is linked
            if bill:
                bill.paid_amount += float(request.POST.get('amount'))
                bill.calculate_totals()
            
            # Update shop balance
            shop.current_balance -= float(request.POST.get('amount'))
            shop.save()
            
            messages.success(request, f'Payment {payment.payment_number} recorded successfully!')
            return redirect('payments:detail', pk=payment.pk)
            
        except Exception as e:
            messages.error(request, f'Error recording payment: {str(e)}')
    
    # GET request
    if request.user.is_sales_rep:
        shops = Shop.objects.filter(assigned_sales_rep=request.user, is_active=True)
    else:
        shops = Shop.objects.filter(is_active=True)
    
    context = {
        'shops': shops
    }
    return render(request, 'payments/add_payment.html', context)


@login_required
def payment_detail(request, pk):
    """Payment detail view"""
    payment = get_object_or_404(Payment, pk=pk)
    
    # Get attachments
    attachments = payment.attachments.all().order_by('attachment_type')
    
    context = {
        'payment': payment,
        'attachments': attachments,
        'bill': payment.bill,
        'shop': payment.shop,
    }
    return render(request, 'payments/payment_detail.html', context)


@login_required
@transaction.atomic
def cancel_payment(request, pk):
    """Cancel a payment"""
    payment = get_object_or_404(Payment, pk=pk)
    
    # Check permissions
    if request.user.is_sales_rep and payment.received_by != request.user:
        messages.error(request, 'You can only cancel your own payments.')
        return redirect('payments:detail', pk=pk)
    
    # Check if already cancelled
    if payment.status == 'cancelled':
        messages.warning(request, 'Payment is already cancelled.')
        return redirect('payments:detail', pk=pk)
    
    # Don't allow cancelling completed/verified payments for sales reps
    if request.user.is_sales_rep and payment.status == 'completed':
        messages.error(request, 'Cannot cancel a completed payment. Please contact office.')
        return redirect('payments:detail', pk=pk)
    
    if request.method == 'POST':
        try:
            # Reverse bill payment if linked and if payment was completed
            if payment.bill and payment.status == 'completed':
                payment.bill.paid_amount -= payment.amount
                payment.bill.balance_amount = payment.bill.total_amount - payment.bill.paid_amount
                
                # Update payment status
                if payment.bill.paid_amount >= payment.bill.total_amount:
                    payment.bill.payment_status = 'paid'
                elif payment.bill.paid_amount > 0:
                    payment.bill.payment_status = 'partial'
                else:
                    payment.bill.payment_status = 'unpaid'
                
                payment.bill.save()
            
            # Reverse shop balance if payment was completed
            if payment.status == 'completed':
                payment.shop.current_balance += payment.amount
                payment.shop.save()
            
            # Cancel payment
            payment.status = 'cancelled'
            payment.notes = (payment.notes or '') + f"\nCancelled by {request.user.get_full_name()} on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            payment.save()
            
            messages.success(request, f'Payment {payment.payment_number} has been cancelled.')
            return redirect('payments:detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f'Error cancelling payment: {str(e)}')
            return redirect('payments:detail', pk=pk)
    
    context = {
        'payment': payment,
    }
    return render(request, 'payments/cancel_payment.html', context)


@login_required
@transaction.atomic
def confirm_bank_transfer(request, pk):
    """Confirm a bank transfer (office only)"""
    if request.user.is_sales_rep:
        messages.error(request, 'Only office staff can confirm bank transfers.')
        return redirect('payments:detail', pk=pk)
    
    payment = get_object_or_404(Payment, pk=pk)
    
    if payment.payment_method != 'bank_transfer':
        messages.error(request, 'This is not a bank transfer payment.')
        return redirect('payments:detail', pk=pk)
    
    if payment.status != 'pending':
        messages.warning(request, 'Payment is already processed.')
        return redirect('payments:detail', pk=pk)
    
    if request.method == 'POST':
        try:
            # Update payment to completed
            payment.status = 'completed'
            payment.verified_by = request.user
            payment.verified_at = timezone.now()
            payment.notes = (payment.notes or '') + f"\nBank transfer confirmed by {request.user.get_full_name()} on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            payment.save()
            
            # Update bill if linked
            if payment.bill:
                payment.bill.paid_amount += payment.amount
                payment.bill.balance_amount = payment.bill.total_amount - payment.bill.paid_amount
                
                # Update payment status
                if payment.bill.paid_amount >= payment.bill.total_amount:
                    payment.bill.payment_status = 'paid'
                elif payment.bill.paid_amount > 0:
                    payment.bill.payment_status = 'partial'
                
                payment.bill.save()
            
            messages.success(request, f'Bank transfer {payment.payment_number} confirmed successfully!')
            return redirect('payments:detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f'Error confirming bank transfer: {str(e)}')
    
    context = {
        'payment': payment,
        'attachments': payment.attachments.all(),
    }
    return render(request, 'payments/confirm_bank_transfer.html', context)


@login_required
@transaction.atomic
def clear_cheque(request, pk):
    """Mark cheque as cleared (office only)"""
    if request.user.is_sales_rep:
        messages.error(request, 'Only office staff can clear cheques.')
        return redirect('payments:detail', pk=pk)
    
    payment = get_object_or_404(Payment, pk=pk)
    
    if payment.payment_method != 'cheque':
        messages.error(request, 'This is not a cheque payment.')
        return redirect('payments:detail', pk=pk)
    
    if payment.status != 'pending':
        messages.warning(request, 'Cheque is already processed.')
        return redirect('payments:detail', pk=pk)
    
    if request.method == 'POST':
        try:
            cleared_date = request.POST.get('cleared_date')
            
            # Update payment to completed
            payment.status = 'completed'
            payment.verified_by = request.user
            payment.verified_at = timezone.now()
            payment.notes = (payment.notes or '') + f"\nCheque cleared on {cleared_date} by {request.user.get_full_name()}"
            payment.save()
            
            # Update bill if linked
            if payment.bill:
                payment.bill.paid_amount += payment.amount
                payment.bill.balance_amount = payment.bill.total_amount - payment.bill.paid_amount
                
                # Update payment status
                if payment.bill.paid_amount >= payment.bill.total_amount:
                    payment.bill.payment_status = 'paid'
                elif payment.bill.paid_amount > 0:
                    payment.bill.payment_status = 'partial'
                
                payment.bill.save()
            
            messages.success(request, f'Cheque {payment.payment_number} marked as cleared!')
            return redirect('payments:detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f'Error clearing cheque: {str(e)}')
    
    context = {
        'payment': payment,
        'attachments': payment.attachments.all(),
        'today': timezone.now().date(),
    }
    return render(request, 'payments/clear_cheque.html', context)


@login_required
@transaction.atomic
def bounce_cheque(request, pk):
    """Mark cheque as bounced (office only)"""
    if request.user.is_sales_rep:
        messages.error(request, 'Only office staff can mark cheques as bounced.')
        return redirect('payments:detail', pk=pk)
    
    payment = get_object_or_404(Payment, pk=pk)
    
    if payment.payment_method != 'cheque':
        messages.error(request, 'This is not a cheque payment.')
        return redirect('payments:detail', pk=pk)
    
    if payment.status != 'pending':
        messages.warning(request, 'Cheque is already processed.')
        return redirect('payments:detail', pk=pk)
    
    if request.method == 'POST':
        try:
            bounce_reason = request.POST.get('bounce_reason', 'Cheque bounced')
            
            # Update payment to bounced
            payment.status = 'bounced'
            payment.verified_by = request.user
            payment.verified_at = timezone.now()
            payment.notes = (payment.notes or '') + f"\nCheque bounced: {bounce_reason}. Marked by {request.user.get_full_name()} on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            payment.save()
            
            messages.warning(request, f'Cheque {payment.payment_number} marked as bounced.')
            return redirect('payments:detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f'Error marking cheque as bounced: {str(e)}')
    
    context = {
        'payment': payment,
        'attachments': payment.attachments.all(),
    }
    return render(request, 'payments/bounce_cheque.html', context)


@login_required
def verify_payment(request, pk):
    """Verify a pending payment"""
    if request.user.is_sales_rep:
        messages.error(request, 'Only office staff can verify payments.')
        return redirect('payments:detail', pk=pk)
    
    payment = get_object_or_404(Payment, pk=pk)
    
    if payment.status != 'pending':
        messages.warning(request, 'Payment is already processed.')
        return redirect('payments:detail', pk=pk)
    
    payment.verify_payment(request.user)
    messages.success(request, 'Payment verified successfully!')
    
    return redirect('payments:detail', pk=pk)


@login_required
def cheque_list(request):
    """List all cheque payments"""
    cheques = Payment.objects.filter(payment_method='cheque').select_related('shop', 'received_by')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        cheques = cheques.filter(status=status)
    
    context = {
        'cheques': cheques,
        'pending_cheques': cheques.filter(status='pending').count()
    }
    return render(request, 'payments/cheque_list.html', context)


@login_required
def credit_note_list(request):
    """List all credit notes"""
    if request.user.is_sales_rep:
        credit_notes = CreditNote.objects.filter(created_by=request.user).select_related('shop')
    else:
        credit_notes = CreditNote.objects.all().select_related('shop', 'created_by')
    
    context = {
        'credit_notes': credit_notes
    }
    return render(request, 'payments/credit_note_list.html', context)
