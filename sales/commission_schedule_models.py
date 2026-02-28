"""
Commission Payout Schedule Models
Automated commission crediting to user money accounts
"""
from django.db import models
from django.utils import timezone
from decimal import Decimal
from accounts.models import User


class CommissionPayoutSchedule(models.Model):
    """
    Automated Commission Payout Schedule Configuration
    Defines when and how commissions are credited to user money accounts
    """
    
    FREQUENCY_CHOICES = (
        ('monthly', 'Monthly - Last day of month'),
        ('weekly', 'Weekly - Every Monday'),
        ('biweekly', 'Bi-weekly - Every 1st and 15th'),
        ('custom', 'Custom Date'),
    )
    
    # Schedule Configuration
    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='monthly',
        help_text="How often to process payouts"
    )
    
    # For monthly/weekly/biweekly: What day/time
    payout_day_of_month = models.IntegerField(
        default=28,
        help_text="Day of month for payout (1-28 recommended, or 0 for last day)"
    )
    
    payout_time = models.TimeField(
        default='23:59:00',
        help_text="Time of day to execute payout (HH:MM:SS)"
    )
    
    # Custom date for one-time or specific payouts
    next_custom_payout = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Next scheduled custom payout date/time"
    )
    
    # Enable/Disable
    is_active = models.BooleanField(
        default=True,
        help_text="Whether automatic payouts are enabled"
    )
    
    # Execution Tracking
    last_run_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the last payout was executed"
    )
    
    next_run_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the next payout is scheduled"
    )
    
    # Settings
    minimum_payout_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Minimum commission balance required to trigger payout (0 = no minimum)"
    )
    
    auto_create_money_transactions = models.BooleanField(
        default=True,
        help_text="Automatically create money account transactions for payouts"
    )
    
    # Period to include
    include_unpaid_only = models.BooleanField(
        default=True,
        help_text="Only credit commissions that haven't been paid to money account yet"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='commission_schedules_created'
    )
    
    class Meta:
        db_table = 'commission_payout_schedules'
        ordering = ['-created_at']
        verbose_name = 'Commission Payout Schedule'
        verbose_name_plural = 'Commission Payout Schedules'
    
    def __str__(self):
        return f"{self.get_frequency_display()} - {'Active' if self.is_active else 'Inactive'}"
    
    def calculate_next_run_date(self):
        """Calculate the next scheduled run date based on frequency"""
        from datetime import datetime, timedelta, time
        from calendar import monthrange
        
        now = timezone.now()
        
        # Ensure payout_time is set (defensive programming)
        if not self.payout_time:
            self.payout_time = time(9, 0)  # Default to 9 AM
        
        if self.frequency == 'custom':
            return self.next_custom_payout
        
        elif self.frequency == 'monthly':
            # Monthly payout - use payout_time exactly as configured
            payout_day = self.payout_day_of_month or 1
            
            # Handle "last day of month" (0 means last day)
            if payout_day == 0:
                payout_day = monthrange(now.year, now.month)[1]
            else:
                payout_day = min(payout_day, monthrange(now.year, now.month)[1])
            
            current_month_date = now.replace(
                day=payout_day,
                hour=self.payout_time.hour,
                minute=self.payout_time.minute,
                second=0,
                microsecond=0
            )
            
            if current_month_date <= now:
                # Move to next month
                if now.month == 12:
                    next_month = now.replace(year=now.year + 1, month=1, day=1)
                else:
                    next_month = now.replace(month=now.month + 1, day=1)
                
                # Handle last day of month for next month
                payout_day_next = self.payout_day_of_month or 1
                if payout_day_next == 0:
                    payout_day_next = monthrange(next_month.year, next_month.month)[1]
                else:
                    payout_day_next = min(payout_day_next, monthrange(next_month.year, next_month.month)[1])
                
                next_run = next_month.replace(
                    day=payout_day_next,
                    hour=self.payout_time.hour,
                    minute=self.payout_time.minute,
                    second=0,
                    microsecond=0
                )
            else:
                next_run = current_month_date
            
            return next_run
        
        elif self.frequency == 'weekly':
            # Weekly payout (every Monday)
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7  # Next Monday
            
            next_run = now + timedelta(days=days_until_monday)
            next_run = next_run.replace(
                hour=self.payout_time.hour,
                minute=self.payout_time.minute,
                second=0,
                microsecond=0
            )
            return next_run
        
        elif self.frequency == 'biweekly':
            # Bi-weekly: 1st and 15th of month
            day_1 = now.replace(day=1, hour=self.payout_time.hour, minute=self.payout_time.minute, second=0, microsecond=0)
            day_15 = now.replace(day=15, hour=self.payout_time.hour, minute=self.payout_time.minute, second=0, microsecond=0)
            
            if now < day_1:
                return day_1
            elif now < day_15:
                return day_15
            else:
                # Move to next month 1st
                if now.month == 12:
                    return now.replace(year=now.year + 1, month=1, day=1, hour=self.payout_time.hour, minute=self.payout_time.minute, second=self.payout_time.second, microsecond=0)
                else:
                    return now.replace(month=now.month + 1, day=1, hour=self.payout_time.hour, minute=self.payout_time.minute, second=self.payout_time.second, microsecond=0)
        
        return None
    
    def save(self, *args, **kwargs):
        """Auto-calculate next run date on save"""
        if self.is_active and not self.next_run_date:
            self.next_run_date = self.calculate_next_run_date()
        super().save(*args, **kwargs)


class CommissionPayoutHistory(models.Model):
    """
    History of commission payout executions (both automated and manual)
    Tracks when payouts ran, how much was credited, and any errors
    """
    
    STATUS_CHOICES = (
        ('success', 'Completed Successfully'),
        ('partial', 'Partially Completed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped - No eligible payouts'),
    )
    
    # Payout Number (Professional Format: CP-YYYYMMDD-###)
    payout_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        help_text="Commission Payout voucher number",
        default='CP-TEMP-001'  # Temporary default for migration
    )
    
    schedule = models.ForeignKey(
        CommissionPayoutSchedule,
        on_delete=models.CASCADE,
        related_name='execution_history',
        null=True,
        blank=True,
        help_text="Schedule that triggered this payout (null for manual)"
    )
    
    # Manual vs Automated
    is_manual = models.BooleanField(
        default=False,
        help_text="Whether this was a manual payout or automated"
    )
    
    executed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executed_payouts',
        help_text="User who executed manual payout"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Notes about this payout (for manual payouts)"
    )
    
    execution_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Statistics
    total_users_processed = models.IntegerField(default=0)
    total_amount_credited = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    successful_payouts = models.IntegerField(default=0)
    failed_payouts = models.IntegerField(default=0)
    skipped_payouts = models.IntegerField(default=0, help_text="Users below minimum threshold")
    
    # Period Covered
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    
    # Details
    details = models.TextField(
        blank=True,
        help_text="JSON or text log of execution details"
    )
    
    error_message = models.TextField(blank=True, null=True)
    
    # Execution Time
    duration_seconds = models.IntegerField(
        default=0,
        help_text="How long the execution took"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'commission_payout_history'
        ordering = ['-execution_date']
        verbose_name = 'Commission Payout Record'
        verbose_name_plural = 'Commission Payout Records'
        indexes = [
            models.Index(fields=['-execution_date']),
            models.Index(fields=['schedule']),
            models.Index(fields=['payout_number']),
        ]
    
    def __str__(self):
        manual_label = " (Manual)" if self.is_manual else ""
        return f"{self.payout_number} - {self.execution_date.strftime('%d %b %Y')}{manual_label} - {self.get_status_display()}"
    
    def generate_payout_number(self):
        """Generate unique payout number: CP-YYYY-####"""
        from django.db.models import Max
        import re
        
        today = self.execution_date.date() if self.execution_date else timezone.localdate()
        year = today.year
        prefix = f'CP-{year}-'
        
        # Find the highest number for this year (exclude temporary numbers)
        last_payout = CommissionPayoutHistory.objects.filter(
            payout_number__startswith=prefix
        ).exclude(
            payout_number='CP-TEMP-001'
        ).aggregate(Max('payout_number'))['payout_number__max']
        
        if last_payout:
            # Extract the counter from the last number
            match = re.search(r'-(\d{4})$', last_payout)
            if match:
                counter = int(match.group(1)) + 1
            else:
                counter = 1
        else:
            counter = 1
        
        return f'{prefix}{counter:04d}'
    
    def save(self, *args, **kwargs):
        """Auto-generate payout number on create"""
        # Generate new number if empty or still has temporary default
        if not self.payout_number or self.payout_number == 'CP-TEMP-001':
            self.payout_number = self.generate_payout_number()
        super().save(*args, **kwargs)


class UserCommissionPayout(models.Model):
    """
    Individual user commission payout record
    Links commission balance to money account transaction
    """
    
    history = models.ForeignKey(
        CommissionPayoutHistory,
        on_delete=models.CASCADE,
        related_name='user_payouts'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='commission_payouts'
    )
    
    commission_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Commission balance at time of payout"
    )
    
    amount_credited = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount credited to money account"
    )
    
    money_transaction = models.ForeignKey(
        'accounts.MoneyTransaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commission_payouts'
    )
    
    status = models.CharField(
        max_length=20,
        choices=(('success', 'Success'), ('failed', 'Failed'), ('skipped', 'Skipped')),
        default='success'
    )
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_commission_payouts'
        ordering = ['-created_at']
        verbose_name = 'User Commission Payout'
        verbose_name_plural = 'User Commission Payouts'
        unique_together = [['history', 'user']]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Rs. {self.amount_credited:,.2f}"
