"""
Signal handlers for the payments app
"""
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import SalesAccountSettlement


@receiver(post_delete, sender=SalesAccountSettlement)
def recalculate_bill_on_settlement_delete(sender, instance, **kwargs):
    """
    When a settlement is deleted (not just cancelled), recalculate the bill's totals.
    
    This prevents data integrity issues where:
    - A settlement is created → bill.paid_amount increases
    - Settlement is deleted (bypassing the cancel view) → bill.paid_amount doesn't decrease
    
    The proper cancellation flow uses the cancel_payment view which calls calculate_totals(),
    but direct deletions (e.g., from Django admin) bypass this logic.
    
    This signal handler ensures bill totals are ALWAYS updated when settlements are removed.
    """
    if instance.bill:
        instance.bill.calculate_payment_totals()
