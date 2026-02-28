"""
FOC Reset/Archive System
Allows periodic reset of FOC data while preserving historical records
"""
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
import json

User = get_user_model()


class FOCReset(models.Model):
    """
    FOC Reset Record - Snapshot of all FOC data at reset time
    Each reset archives current FOC state and clears active transactions
    """
    
    # Reset Information
    reset_number = models.CharField(max_length=50, unique=True, editable=False)
    reset_date = models.DateTimeField(default=timezone.now)
    reset_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='foc_resets')
    
    # Summary Totals (from FOC Dashboard)
    total_foc_received = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_foc_given = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_foc_returned = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_foc_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_utilization = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Transaction Counts
    total_transactions = models.IntegerField(default=0)
    total_products = models.IntegerField(default=0)
    total_sales_reps = models.IntegerField(default=0)
    
    # Archived Data (JSON snapshots)
    company_accounts_snapshot = models.JSONField(
        help_text="Snapshot of all company FOC accounts at reset time"
    )
    product_summary_snapshot = models.JSONField(
        help_text="Product-wise FOC breakdown snapshot"
    )
    sales_rep_summary_snapshot = models.JSONField(
        help_text="Sales rep FOC usage snapshot"
    )
    transaction_types_breakdown = models.JSONField(
        help_text="Breakdown by transaction type"
    )
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'foc_resets'
        ordering = ['-reset_date']
        verbose_name = 'FOC Reset'
        verbose_name_plural = 'FOC Resets'
    
    def __str__(self):
        return f"{self.reset_number} - {self.reset_date.strftime('%Y-%m-%d')}"
    
    def generate_reset_number(self):
        """Generate reset number: FOCRST-YYYY-####"""
        today = timezone.localdate()
        year = today.year
        prefix = f'FOCRST-{year}-'
        
        # Find highest number for this year
        last_reset = FOCReset.objects.filter(
            reset_number__startswith=prefix
        ).order_by('-reset_number').first()
        
        if last_reset:
            last_number = int(last_reset.reset_number.split('-')[-1])
            counter = last_number + 1
        else:
            counter = 1
        
        return f'{prefix}{counter:04d}'
    
    def save(self, *args, **kwargs):
        if not self.reset_number:
            self.reset_number = self.generate_reset_number()
        super().save(*args, **kwargs)


class FOCResetTransaction(models.Model):
    """
    Individual transaction archived during reset
    Links to parent reset for complete transaction history
    """
    
    reset = models.ForeignKey(
        FOCReset,
        on_delete=models.CASCADE,
        related_name='archived_transactions'
    )
    
    # Original transaction data (copied from FOCValueTransaction)
    transaction_type = models.CharField(max_length=50)
    transaction_date = models.DateTimeField()
    
    # Product and Company
    company_name = models.CharField(max_length=200)
    product_name = models.CharField(max_length=200)
    product_size = models.CharField(max_length=100)
    
    # Shop and Sales Rep
    shop_name = models.CharField(max_length=200, null=True, blank=True)
    sales_rep_name = models.CharField(max_length=200, null=True, blank=True)
    
    # Quantities and Values
    foc_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shop_price_at_time = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    foc_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # References
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Store IDs for creating links
    purchase_id = models.IntegerField(null=True, blank=True, help_text="Purchase ID if from purchase")
    bill_id = models.IntegerField(null=True, blank=True, help_text="Bill ID if from bill")
    return_id = models.IntegerField(null=True, blank=True, help_text="Return ID if from return")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'foc_reset_transactions'
        ordering = ['-transaction_date']
        verbose_name = 'FOC Reset Transaction'
        verbose_name_plural = 'FOC Reset Transactions'
        indexes = [
            models.Index(fields=['reset', 'transaction_type']),
            models.Index(fields=['reset', 'company_name']),
            models.Index(fields=['reset', 'sales_rep_name']),
        ]
    
    def __str__(self):
        return f"{self.reset.reset_number} - {self.transaction_type} - {self.product_name}"
