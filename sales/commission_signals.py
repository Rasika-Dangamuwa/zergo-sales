"""
Django Signals for Real-time Commission Tracking
Automatically creates commission transactions when:
- Bills are created
- Payments are received
- Returns are processed
- Write-offs are executed

ENHANCED (Jan 2026): Added transaction safety, logging, better error handling
"""

from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import logging

from sales.models import Bill, Return, CommissionTransaction
from payments.models import SalesAccountSettlement, BadDebtWriteOff

logger = logging.getLogger(__name__)


def _recalculate_running_balances(sales_rep):
    """
    Helper function to recalculate all running balances for a sales rep
    Used after deleting a commission transaction
    """
    try:
        with transaction.atomic():
            all_txns = CommissionTransaction.objects.filter(
                sales_rep=sales_rep
            ).select_for_update().order_by('transaction_date', 'created_at')
            
            running_balance = Decimal('0.00')
            
            for txn in all_txns:
                running_balance += txn.commission_earned
                if txn.running_balance != running_balance:
                    txn.running_balance = running_balance
                    txn.save(update_fields=['running_balance'])
            
            logger.info(f"Recalculated running balances for {sales_rep.get_full_name()}")
    except Exception as e:
        logger.error(f"Error recalculating running balances for {sales_rep.get_full_name()}: {e}")


@receiver(post_save, sender=Bill, dispatch_uid="create_commission_on_bill_creation_unique")
def create_commission_on_bill_creation(sender, instance, created, **kwargs):
    """
    Create commission transaction when a new bill is created
    Only for confirmed bills, not drafts
    ENHANCED: Better logging, duplicate prevention handled in model
    """
    if created and instance.bill_status == 'confirmed':
        try:
            with transaction.atomic():
                CommissionTransaction.create_for_bill(
                    bill=instance,
                    created_by=instance.sales_rep
                )
                logger.info(f"Commission transaction created for Bill {instance.bill_number}")
        except Exception as e:
            # Log error but don't fail the bill creation
            logger.error(f"Error creating commission transaction for bill {instance.bill_number}: {e}")
            # Don't raise - bill creation should succeed even if commission fails


@receiver(post_save, sender=SalesAccountSettlement, dispatch_uid="create_commission_on_payment_unique")
def create_commission_on_payment(sender, instance, created, **kwargs):
    """
    Create commission transaction when settlement is received
    Only for completed settlements
    Handle cancellations by removing orphaned commission transactions
    ENHANCED: Better duplicate check, improved logging, cancellation handling,
    using dispatch_uid to prevent duplicate signal registration
    """
    logger.info(f"Signal triggered for settlement {instance.settlement_number}, status={instance.settlement_status}, created={created}")
    
    if instance.settlement_status == 'completed' and instance.bill:
        # Enhanced duplicate check - handled in create_for_payment now
        try:
            with transaction.atomic():
                CommissionTransaction.create_for_payment(
                    payment=instance,
                    bill=instance.bill
                )
                
                # Update bill's settlement status (only payment fields, not line items)
                logger.info(f"Calling bill.calculate_payment_totals() for Bill {instance.bill.bill_number}")
                
                # Fallback for servers that don't have calculate_payment_totals yet
                if hasattr(instance.bill, 'calculate_payment_totals'):
                    instance.bill.calculate_payment_totals()
                else:
                    # Manual fallback calculation
                    from decimal import Decimal
                    total_paid = sum(
                        s.amount for s in instance.bill.settlements.filter(settlement_status='completed')
                    )
                    instance.bill.paid_amount = total_paid
                    instance.bill.balance_amount = instance.bill.total_amount - total_paid
                    
                    if instance.bill.balance_amount <= 0:
                        instance.bill.settlement_status = 'settled'
                    elif instance.bill.paid_amount > 0:
                        instance.bill.settlement_status = 'partially_settled'
                    else:
                        instance.bill.settlement_status = 'unsettled'
                    
                    instance.bill.save(update_fields=['paid_amount', 'balance_amount', 'settlement_status'])
                    logger.warning(f"Used fallback calculation for Bill {instance.bill.bill_number} - server needs restart")
                
                logger.info(f"After calculate_payment_totals(): paid_amount={instance.bill.paid_amount}")
                
                logger.info(f"Commission transaction created for payment on Bill {instance.bill.bill_number}")
                
        except Exception as e:
            logger.error(f"Error creating commission transaction for payment on Bill {instance.bill.bill_number}: {e}")
            # Don't raise - payment should succeed even if commission fails
    
    elif instance.settlement_status in ['cancelled', 'bounced'] and instance.bill and not created:
        # Settlement was cancelled/bounced - reverse the commission by creating offsetting transaction
        try:
            with transaction.atomic():
                # Find the original commission transaction for this settlement (positive commission)
                original_txn = CommissionTransaction.objects.filter(
                    transaction_type='payment_received',
                    settlement=instance,
                    commission_earned__gt=0  # Only positive commission (original transaction)
                ).first()
                
                # Check if reversal already exists
                reversal_exists = CommissionTransaction.objects.filter(
                    transaction_type='payment_received',
                    settlement=instance,
                    commission_earned__lt=0  # Negative commission (reversal)
                ).exists()
                
                if original_txn and not reversal_exists:
                    # Create a reversal transaction with negative collected_amount
                    # This way the save() method will calculate negative commission naturally
                    reversal = CommissionTransaction.objects.create(
                        transaction_type='payment_cancelled',
                        transaction_date=timezone.now(),
                        sales_rep=original_txn.sales_rep,
                        bill=original_txn.bill,
                        settlement=instance,
                        collected_amount=-original_txn.collected_amount,  # Negative of original collection
                        notes=f"REVERSAL: Settlement {instance.settlement_number} {instance.settlement_status} - Commission cancelled"
                    )
                    logger.info(f"Created reversal transaction (ID: {reversal.id}) with commission {reversal.commission_earned} for {instance.settlement_status} settlement {instance.settlement_number}")
                elif reversal_exists:
                    logger.info(f"Reversal transaction already exists for settlement {instance.settlement_number}")
                
                # Update bill's settlement status (only payment fields, not line items)
                # Fallback for servers that don't have calculate_payment_totals yet
                if hasattr(instance.bill, 'calculate_payment_totals'):
                    instance.bill.calculate_payment_totals()
                else:
                    # Manual fallback calculation
                    from decimal import Decimal
                    total_paid = sum(
                        s.amount for s in instance.bill.settlements.filter(settlement_status='completed')
                    )
                    instance.bill.paid_amount = total_paid
                    instance.bill.balance_amount = instance.bill.total_amount - total_paid
                    
                    if instance.bill.balance_amount <= 0:
                        instance.bill.settlement_status = 'settled'
                    elif instance.bill.paid_amount > 0:
                        instance.bill.settlement_status = 'partially_settled'
                    else:
                        instance.bill.settlement_status = 'unsettled'
                    
                    instance.bill.save(update_fields=['paid_amount', 'balance_amount', 'settlement_status'])
                    logger.warning(f"Used fallback calculation for Bill {instance.bill.bill_number} - server needs restart")
                
        except Exception as e:
            logger.error(f"Error creating reversal transaction for {instance.settlement_status} settlement {instance.settlement_number}: {e}")
            # Don't raise - settlement cancellation should succeed even if commission cleanup fails


@receiver(post_save, sender=Return, dispatch_uid="create_commission_on_return_unique")
def create_commission_on_return(sender, instance, created, **kwargs):
    """
    Create commission transaction when return is processed
    Reduces commission
    ENHANCED: Better logging, duplicate prevention in model
    """
    if created:
        try:
            with transaction.atomic():
                CommissionTransaction.create_for_return(
                    return_obj=instance
                )
                logger.info(f"Commission transaction created for Return {instance.return_number}")
        except Exception as e:
            logger.error(f"Error creating commission transaction for return {instance.return_number}: {e}")
            # Don't raise - return should succeed even if commission fails


@receiver(post_save, sender=Return)
def reverse_commission_on_return_cancellation(sender, instance, created, **kwargs):
    """
    Create reversal commission transaction when return is cancelled
    Reverses the commission deduction from the original return
    ENHANCED (Jan 26, 2026): Changed from pre_delete to post_save to handle cancellation
    """
    # Only trigger on status change to 'cancelled', not on creation or other updates
    if created or instance.settlement_status != 'cancelled':
        return
    
    # Check if this was just changed to cancelled (avoid triggering on every save)
    if hasattr(instance, '_original_status') and instance._original_status == 'cancelled':
        return  # Already cancelled, skip
    
    logger.info(f"🔥 CANCELLATION DETECTED for Return {instance.return_number}")
    
    try:
        with transaction.atomic():
            logger.info(f"   Looking for original return_processed transaction...")
            
            # Check if reversal already exists
            reversal_exists = CommissionTransaction.objects.filter(
                transaction_type='return_cancelled',
                sales_rep=instance.created_by,
                notes__contains=instance.return_number
            ).exists()
            
            if reversal_exists:
                logger.info(f"   ⚠️ Reversal already exists for {instance.return_number}, skipping")
                return
            
            # Find the original return_processed transaction
            original_txn = CommissionTransaction.objects.filter(
                transaction_type='return_processed',
                return_amount=instance.total_amount,
                sales_rep=instance.created_by,
                notes__contains=instance.return_number
            ).first()
            
            if original_txn:
                logger.info(f"   ✅ Found original transaction ID {original_txn.id}")
                logger.info(f"      Return Amount: Rs. {original_txn.return_amount}")
                logger.info(f"      Commission: Rs. {original_txn.commission_earned}")
                
                logger.info(f"   Creating reversal transaction...")
                
                # Get customer label for notes
                customer_label = instance.shop.shop_name if instance.shop else (instance.customer_name or "Unregistered Customer")
                
                # Create reversal transaction
                reversal = CommissionTransaction.objects.create(
                    transaction_type='return_cancelled',
                    transaction_date=timezone.now(),
                    sales_rep=original_txn.sales_rep,
                    bill=original_txn.bill,
                    return_ref=instance,  # Link to the return object
                    return_amount=-original_txn.return_amount,  # Opposite of original
                    notes=f"REVERSAL: Return {instance.return_number} cancelled for {customer_label} - Commission restored"
                )
                logger.info(f"   ✅ Created reversal transaction ID {reversal.id}")
                logger.info(f"      Reversal Commission: Rs. {reversal.commission_earned}")
                logger.info(f"      New Balance: Rs. {reversal.running_balance}")
            else:
                logger.warning(f"   ⚠️ Original commission transaction not found for return {instance.return_number}")
                logger.warning(f"      Return total_amount: Rs. {instance.total_amount}")
                logger.warning(f"      Sales rep: {instance.created_by.get_full_name()}")
                
    except Exception as e:
        logger.error(f"   ❌ Error creating reversal transaction for cancelled return {instance.return_number}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Don't raise - cancellation should succeed even if commission cleanup fails


@receiver(post_save, sender=BadDebtWriteOff)
def create_commission_on_writeoff(sender, instance, created, **kwargs):
    """
    Create commission transaction when write-off is executed
    Write-offs don't affect commission (payment was never collected)
    But we track them for transparency
    ENHANCED: Better logging and error handling
    """
    if instance.executed and instance.bill:
        # Check if commission transaction already exists
        existing = CommissionTransaction.objects.filter(
            transaction_type='writeoff_executed',
            bill=instance.bill
        ).exists()
        
        if not existing:
            try:
                with transaction.atomic():
                    CommissionTransaction.objects.create(
                        transaction_type='writeoff_executed',
                        transaction_date=instance.executed_at,
                        sales_rep=instance.bill.sales_rep,
                        bill=instance.bill,
                        sales_amount=instance.write_off_amount,
                        commission_earned=0,  # No commission lost
                        notes=f"Write-off executed for Bill {instance.bill.bill_number}"
                    )
                    logger.info(f"Commission transaction created for write-off on Bill {instance.bill.bill_number}")
            except Exception as e:
                logger.error(f"Error creating commission transaction for write-off on Bill {instance.bill.bill_number}: {e}")
                # Don't raise - write-off should succeed even if commission fails


# Signal to update running balances when transactions are created
@receiver(post_save, sender=CommissionTransaction)
def update_subsequent_running_balances(sender, instance, created, **kwargs):
    """
    When a new transaction is created, update running balances for all subsequent transactions
    This ensures accuracy even if transactions are entered out of order
    ENHANCED: Transaction locking, better error handling
    """
    if created:
        try:
            with transaction.atomic():
                # Get all subsequent transactions for the same sales rep with locking
                subsequent_transactions = CommissionTransaction.objects.filter(
                    sales_rep=instance.sales_rep,
                    transaction_date__gt=instance.transaction_date
                ).select_for_update().order_by('transaction_date', 'created_at')
                
                current_balance = instance.running_balance
                
                for txn in subsequent_transactions:
                    current_balance += txn.commission_earned
                    if txn.running_balance != current_balance:
                        txn.running_balance = current_balance
                        txn.save(update_fields=['running_balance'])
                
                if subsequent_transactions.exists():
                    logger.info(f"Updated {subsequent_transactions.count()} subsequent commission balances for {instance.sales_rep.get_full_name()}")
        except Exception as e:
            logger.error(f"Error updating subsequent running balances: {e}")
            # Don't raise - main transaction should succeed
