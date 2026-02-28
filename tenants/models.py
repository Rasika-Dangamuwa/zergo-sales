"""
Tenant Models for Multi-Distributor Architecture

Each distributor gets their own PostgreSQL schema, providing complete data 
isolation. This module defines the Tenant (Distributor) and Domain models
required by django-tenants.

Schema layout:
  - public schema: Tenant, Domain, User (shared tables)
  - tenant schemas: shops, products, sales, payments, business (per-distributor)
"""

from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal


class Distributor(TenantMixin):
    """
    Represents a single distributor business (tenant).
    
    Each Distributor gets their own PostgreSQL schema containing all 
    business data (shops, products, sales, payments, etc.).
    
    The schema_name field (from TenantMixin) is the PostgreSQL schema name.
    Example: schema_name='dist_001' → all tables in 'dist_001' schema.
    """
    
    # Business identification
    name = models.CharField(
        max_length=200,
        help_text="Distributor business name"
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique distributor code (e.g., 'DIST001')"
    )
    
    # Contact info
    owner_name = models.CharField(max_length=200, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')
    
    # Business details
    business_registration = models.CharField(max_length=50, blank=True, default='')
    tax_id = models.CharField(max_length=50, blank=True, default='')
    
    # Subscription / status
    is_active = models.BooleanField(default=True)
    
    PLAN_CHOICES = (
        ('trial', 'Trial'),
        ('basic', 'Basic'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    )
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='trial')
    plan_expires = models.DateField(null=True, blank=True)
    max_users = models.PositiveIntegerField(default=10, help_text="Max users allowed")
    max_shops = models.PositiveIntegerField(default=500, help_text="Max shops allowed")
    
    # Metadata
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, default='')
    
    # Logo for central dashboard
    logo = models.ImageField(upload_to='tenant_logos/', blank=True, null=True)
    
    # Schema creation is handled by tenants.utils.create_tenant_schema()
    # which clones the public schema structure instead of running migrations
    # from scratch (avoids historical migration conflicts).
    auto_create_schema = False
    
    class Meta:
        db_table = 'distributors'
        ordering = ['name']
        verbose_name = 'Distributor'
        verbose_name_plural = 'Distributors'
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def is_trial_expired(self):
        if self.plan == 'trial' and self.plan_expires:
            return timezone.now().date() > self.plan_expires
        return False


class Domain(DomainMixin):
    """
    Domain/subdomain mapping for each distributor.
    
    Examples:
      - dist001.zergo.com → Distributor 1's schema
      - dist002.zergo.com → Distributor 2's schema
      - zergo.com (is_primary=True, tenant=public) → Central admin
    
    For local development:
      - dist001.localhost → Distributor 1
      - localhost → Central admin (public tenant)
    """
    
    class Meta:
        db_table = 'domains'
        verbose_name = 'Domain'
        verbose_name_plural = 'Domains'
    
    def __str__(self):
        return self.domain


class GlobalCaseValueSetting(models.Model):
    """
    Global case value setting shared across all tenants.
    
    Stored in the public schema so that a single configuration applies
    to all distributors. Used to calculate Total Pack (Total Sale / Active Case Value)
    in EOD reports, summaries, and monthly plans.
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
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        related_name='global_case_value_settings'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'global_case_value_settings'
        ordering = ['-effective_date']
        verbose_name = 'Global Case Value Setting'
        verbose_name_plural = 'Global Case Value Settings'
    
    def __str__(self):
        return f"Rs. {self.case_value} (Effective: {self.effective_date})"
    
    def save(self, *args, **kwargs):
        """Ensure only one active setting exists."""
        if self.is_active:
            GlobalCaseValueSetting.objects.filter(
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_case_value(cls, for_date=None):
        """
        Get active case value for a specific date or today.
        
        Always queries the public schema regardless of current tenant context.
        """
        from django_tenants.utils import schema_context
        
        if for_date is None:
            for_date = timezone.localdate()
        
        with schema_context('public'):
            setting = cls.objects.filter(
                effective_date__lte=for_date
            ).order_by('-effective_date').first()
        
        if setting:
            return setting.case_value
        return Decimal('2160.00')  # Default fallback
