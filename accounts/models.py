from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal


class User(AbstractUser):
    """Custom User Model"""
    
    USER_TYPE_CHOICES = (
        ('admin', 'Admin'),
        ('office', 'Distributor'),
        ('sales_rep', 'Sales Representative'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='sales_rep')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    is_active_employee = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    # Multi-tenancy: which distributor this user belongs to
    # null=True for super-admin users who manage the central platform
    tenant = models.ForeignKey(
        'tenants.Distributor',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
        help_text="The distributor this user belongs to. Null for platform super-admins."
    )
    
    # Platform-level super admin (can manage all distributors)
    is_platform_admin = models.BooleanField(
        default=False,
        help_text="Platform super-admin who can manage all distributors"
    )
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.user_type})"
    
    @property
    def is_sales_rep(self):
        return self.user_type == 'sales_rep'
    
    @property
    def is_office_staff(self):
        return self.user_type in ['admin', 'office']


class SalesRepLocation(models.Model):
    """Track sales rep location history"""
    sales_rep = models.ForeignKey(User, on_delete=models.CASCADE, related_name='location_history')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy = models.FloatField(null=True, blank=True)  # GPS accuracy in meters
    timestamp = models.DateTimeField(auto_now_add=True)
    battery_level = models.IntegerField(null=True, blank=True)  # Battery percentage
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'sales_rep_locations'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['sales_rep', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.sales_rep.username} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


# Import money account models
from .money_account_models import UserMoneyAccount, MoneyTransaction, AdvanceRequest

