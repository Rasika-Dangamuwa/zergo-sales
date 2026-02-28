"""
End of Day (EOD) Report Models
Created: January 31, 2026

Models for tracking daily sales routes and case value settings.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class CaseValueSetting(models.Model):
    """
    Tracks active case value (price per case) over time with history.
    Used to calculate Total Pack (Total Sale / Active Case Value)
    """
    
    case_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price per case (e.g., 2160.00)"
    )
    
    effective_date = models.DateField(
        help_text="Date when this case value becomes effective"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Only one setting should be active at a time"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='case_value_settings'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'eod_case_value_settings'
        ordering = ['-effective_date']
        verbose_name = 'Case Value Setting'
        verbose_name_plural = 'Case Value Settings'
    
    def __str__(self):
        return f"Rs. {self.case_value} (Effective: {self.effective_date})"
    
    def save(self, *args, **kwargs):
        """Ensure only one active setting exists"""
        if self.is_active:
            # Deactivate all other settings
            CaseValueSetting.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_case_value(cls, for_date=None):
        """Get active case value for a specific date or today"""
        if for_date is None:
            for_date = timezone.localdate()
        
        # Get the most recent case value setting effective on or before the date
        setting = cls.objects.filter(
            effective_date__lte=for_date
        ).order_by('-effective_date').first()
        
        if setting:
            return setting.case_value
        return Decimal('2160.00')  # Default fallback


class DailyRoute(models.Model):
    """
    Stores the route(s) worked by a sales rep on a specific date.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='daily_routes'
    )
    
    date = models.DateField(
        help_text="Date the route was worked"
    )
    
    route = models.CharField(
        max_length=500,
        help_text="Route name(s) worked, e.g., 'Wattala & Sedawatta'"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Any additional notes about the day"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'eod_daily_routes'
        unique_together = [['user', 'date']]
        ordering = ['-date']
        verbose_name = 'Daily Route'
        verbose_name_plural = 'Daily Routes'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.date} - {self.route}"
