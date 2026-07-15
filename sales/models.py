from django.db import models
from django.db.models import Sum, Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from shops.models import Shop
from products.models import Product
from accounts.models import User
from PIL import Image
import os


class Sale(models.Model):
    """Sales Transaction - Lorry Operation (Bill + Delivery)"""
    
    SALE_STATUS_CHOICES = (
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    )
    
    DELIVERY_STATUS_CHOICES = (
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
    )
    
    SETTLEMENT_STATUS_CHOICES = (
        ('unsettled', 'Unsettled'),
        ('partial_settled', 'Partially Settled'),
        ('settled', 'Settled'),
    )
    
    # Sale Information
    sale_number = models.CharField(max_length=50, unique=True, editable=False)
    sale_date = models.DateTimeField(default=timezone.now)
    
    # Customer & Sales Rep
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name='sales')
    sales_rep = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sales')
    
    # Financial Details
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    sale_status = models.CharField(max_length=20, choices=SALE_STATUS_CHOICES, default='confirmed')
    settlement_status = models.CharField(max_length=20, choices=SETTLEMENT_STATUS_CHOICES, default='unsettled')
    delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default='delivered')
    
    # Delivery Details
    vehicle_number = models.CharField(max_length=20, blank=True, null=True)
    delivered_by = models.CharField(max_length=200, blank=True, null=True, help_text="Driver/Helper name")
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sales'
        ordering = ['-sale_date']
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'
    
    def __str__(self):
        return f"{self.sale_number} - {self.shop.shop_name}"
    
    def save(self, *args, **kwargs):
        # Auto-generate sale number if not set
        if not self.sale_number:
            self.sale_number = self.generate_sale_number()
        super().save(*args, **kwargs)
    
    def generate_sale_number(self):
        """Generate unique sale number: SAL-DISTCODE-YYYYMMDD-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('SAL', Sale, 'sale_number')
    
    def calculate_totals(self):
        """Calculate sale totals from items"""
        items = self.items.all()
        
        self.subtotal = sum(item.line_total for item in items)
        self.discount_amount = (self.subtotal * self.discount_percentage) / 100
        self.tax_amount = sum(item.tax_amount for item in items)
        self.total_amount = self.subtotal - self.discount_amount + self.tax_amount
        
        # Calculate paid amount from settlements (only completed settlements)
        self.calculate_payment_totals()
    
    def calculate_payment_totals(self):
        """
        Calculate ONLY payment-related totals (paid_amount, balance, status).
        Use this when settlements change but line items haven't.
        """
        # Calculate paid amount from settlements (only completed settlements)
        # Exclude cancelled, pending, and bounced settlements from paid amount
        self.paid_amount = sum(
            settlement.amount 
            for settlement in self.settlements.filter(settlement_status='completed')
        )
        self.balance_amount = self.total_amount - self.paid_amount
        
        # Update settlement status
        if self.paid_amount == 0:
            self.settlement_status = 'unsettled'
        elif self.paid_amount >= self.total_amount:
            self.settlement_status = 'settled'
        else:
            self.settlement_status = 'partial_settled'
        
        # Save ONLY payment-related fields to avoid overwriting line item totals
        self.save(update_fields=['paid_amount', 'balance_amount', 'settlement_status'])
    
    def get_commission_eligible_amount(self):
        """Get amount eligible for commission (only collected payments)"""
        collected_settlements = self.settlements.filter(commission_eligible=True, settlement_status='completed')
        return sum(settlement.amount for settlement in collected_settlements)


class SaleItem(models.Model):
    """Sale Line Items - Flavor-specific products"""
    
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, help_text="Flavor-specific product")
    
    # Quantity & Pricing
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    foc_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Free of Charge quantity given to shop")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'sale_items'
        verbose_name = 'Sale Item'
        verbose_name_plural = 'Sale Items'
    
    def __str__(self):
        return f"{self.sale.sale_number} - {self.product.product_name}"
    
    @property
    def total_quantity(self):
        """Total quantity including FOC"""
        return self.quantity + self.foc_quantity
    
    def calculate_line_total(self):
        """Calculate line item total (FOC not charged)"""
        subtotal = self.quantity * self.unit_price  # Only paid quantity
        self.discount_amount = (subtotal * self.discount_percentage) / Decimal('100')
        amount_after_discount = subtotal - self.discount_amount
        self.tax_amount = (amount_after_discount * self.tax_percentage) / Decimal('100')
        self.line_total = amount_after_discount + self.tax_amount
        return self.line_total
    
    def save(self, *args, **kwargs):
        self.calculate_line_total()
        super().save(*args, **kwargs)


# Keep old models for backward compatibility (will be migrated)
class Bill(models.Model):
    """Old Bill Model - Being replaced by Sale"""
    
    BILL_STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    )
    
    SETTLEMENT_STATUS_CHOICES = (
        ('unsettled', 'Unsettled'),
        ('partial_settled', 'Partially Settled'),
        ('settled', 'Settled'),
    )
    
    bill_number = models.CharField(max_length=50, unique=True)
    bill_date = models.DateTimeField(default=timezone.now)
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name='bills', null=True, blank=True)
    customer_name = models.CharField(max_length=255, blank=True, null=True, help_text='For unregistered customers')
    sales_rep = models.ForeignKey(User, on_delete=models.PROTECT, related_name='old_sales')
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    bill_status = models.CharField(max_length=20, choices=BILL_STATUS_CHOICES, default='draft')
    settlement_status = models.CharField(max_length=20, choices=SETTLEMENT_STATUS_CHOICES, default='unsettled')
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bills'
        ordering = ['-bill_date']
    
    def __str__(self):
        if self.shop:
            return f"{self.bill_number} - {self.shop.shop_name}"
        elif self.customer_name:
            return f"{self.bill_number} - {self.customer_name} (Unregistered)"
        else:
            return f"{self.bill_number} - Unknown Customer"
    
    def save(self, *args, **kwargs):
        # Auto-generate bill number if not set
        if not self.bill_number:
            self.bill_number = self.generate_bill_number()
        super().save(*args, **kwargs)
    
    def generate_bill_number(self):
        """Generate unique bill number: BILL-DISTCODE-YYYYMMDD-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('BILL', Bill, 'bill_number', date_value=self.bill_date)
    
    def calculate_totals(self):
        """Calculate bill totals from items"""
        items = self.items.all()
        
        self.subtotal = sum(item.line_total for item in items) if items.exists() else Decimal('0')
        
        # If discount_amount is set directly, use it; otherwise calculate from percentage
        if self.discount_amount > 0:
            # Discount amount was set directly, calculate percentage
            if self.subtotal > 0:
                self.discount_percentage = (self.discount_amount / self.subtotal) * Decimal('100')
            else:
                self.discount_percentage = Decimal('0')
        else:
            # Calculate discount from percentage
            self.discount_amount = (self.subtotal * self.discount_percentage) / Decimal('100')
        
        self.tax_amount = sum(item.tax_amount for item in items) if items.exists() else Decimal('0')
        self.total_amount = self.subtotal - self.discount_amount + self.tax_amount
        
        # Calculate paid amount from settlements (only completed settlements)
        # Exclude cancelled, pending, and bounced settlements from paid amount
        self.paid_amount = sum(
            settlement.amount 
            for settlement in self.settlements.filter(settlement_status='completed')
        )
        self.balance_amount = self.total_amount - self.paid_amount
        
        # Update settlement status
        if self.paid_amount == 0:
            self.settlement_status = 'unsettled'
        elif self.paid_amount >= self.total_amount:
            self.settlement_status = 'settled'
        else:
            self.settlement_status = 'partial_settled'
        
        self.save()


class BillItem(models.Model):
    """Old Bill Item Model - Being replaced by SaleItem"""
    
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    foc_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Free of Charge quantity given to shop")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # FIFO cost tracking
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        help_text="FIFO weighted-average cost per unit at time of sale"
    )
    total_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Total COGS for this line = (quantity + foc_quantity) × unit_cost"
    )
    cost_breakdown = models.JSONField(
        null=True, blank=True,
        help_text="FIFO layer breakdown: [{source, reference, unit_cost, qty_consumed}, ...]"
    )
    
    class Meta:
        db_table = 'bill_items'
    
    def __str__(self):
        return f"{self.bill.bill_number} - {self.product.product_name}"
    
    @property
    def total_quantity(self):
        """Total quantity including FOC"""
        return self.quantity + self.foc_quantity
    
    def calculate_line_total(self):
        """Calculate line item total (FOC not charged)"""
        subtotal = self.quantity * self.unit_price  # Only paid quantity
        self.discount_amount = (subtotal * self.discount_percentage) / Decimal('100')
        amount_after_discount = subtotal - self.discount_amount
        self.tax_amount = (amount_after_discount * self.tax_percentage) / Decimal('100')
        self.line_total = amount_after_discount + self.tax_amount
        return self.line_total
    
    def save(self, *args, **kwargs):
        self.calculate_line_total()
        super().save(*args, **kwargs)



# LEGACY Return model - DEPRECATED
# This model is no longer used. See the active Return model defined below (around line 844)
# Kept here commented out for reference only
"""
class Return(models.Model):
    \"\"\"Sales Return with Commission Adjustment\"\"\"
    
    REFUND_METHOD_CHOICES = (
        ('cash', 'Cash Refund'),
        ('credit_note', 'Credit Note'),
        ('adjustment', 'Account Adjustment'),
    )
    
    # Return Information
    return_number = models.CharField(max_length=50, unique=True, editable=False)
    return_date = models.DateTimeField(default=timezone.now)
    original_sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='returns', null=True, blank=True)
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name='returns', null=True, blank=True)
    customer_name = models.CharField(max_length=255, blank=True, null=True, help_text='For unregistered customers')
    sales_rep = models.ForeignKey(User, on_delete=models.PROTECT, related_name='returns')
    
    # Financial Details
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_method = models.CharField(max_length=20, choices=REFUND_METHOD_CHOICES, null=True, blank=True)
    
    # Reason
    reason = models.TextField(blank=True, null=True)
    
    # Commission Adjustment
    commission_adjusted = models.BooleanField(default=False, help_text="Deducted from rep commission")
    commission_month = models.CharField(max_length=7, blank=True, null=True, help_text="YYYY-MM to deduct from")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'returns'
        ordering = ['-return_date']
        verbose_name = 'Return'
        verbose_name_plural = 'Returns'
    
    def __str__(self):
        if self.shop:
            return f"{self.return_number} - {self.shop.shop_name}"
        elif self.customer_name:
            return f"{self.return_number} - {self.customer_name} (Unregistered)"
        else:
            return f"{self.return_number} - Unknown Customer"
    
    def save(self, *args, **kwargs):
        # Auto-generate return number
        if not self.return_number:
            self.return_number = self.generate_return_number()
        
        # Set commission month to current month
        if not self.commission_month:
            self.commission_month = timezone.now().strftime('%Y-%m')
        
        super().save(*args, **kwargs)
    
    def generate_return_number(self):
        # Generate unique return number: RET-DISTCODE-YYYYMMDD-NNNN
        from utils.number_generator import generate_number
        return generate_number('RET', Return, 'return_number')
    
    def calculate_total(self):
        # Calculate total return amount
        items = self.items.all()
        self.total_amount = sum(item.line_total for item in items)
        self.save()


class ReturnItem(models.Model):
    \"\"\"Return Line Items - Links to active Return model below\"\"\"
    
    return_record = models.ForeignKey('Return', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'return_items'
        verbose_name = 'Return Item'
        verbose_name_plural = 'Return Items'
    
    def __str__(self):
        return f"{self.return_record.return_number} - {self.product.product_name}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate line total
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
"""


# CommissionRecord model removed - replaced by real-time CommissionTransaction system
# See CommissionTransaction and CommissionRateHistory models below


# CommissionSettings removed - use CommissionRateHistory.get_current_rate() instead
# All commission rates are now managed through CommissionRateHistory with effective dates


class CommissionRateHistory(models.Model):
    """Historical Commission Rates with Effective Dates"""
    
    rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        help_text="Commission percentage (0-100)"
    )
    
    effective_from = models.DateTimeField(
        help_text="Date and time from which this rate applies"
    )
    
    effective_to = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="Date and time until which this rate applies (null = current/active)"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Is this the currently active rate?"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='commission_rates_created'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True, help_text="Reason for rate change")
    
    class Meta:
        db_table = 'commission_rate_history'
        ordering = ['-created_at']  # Show newest first (by creation time, not effective date)
        verbose_name = 'Commission Rate History'
        verbose_name_plural = 'Commission Rate History'
    
    def __str__(self):
        status = "Active" if self.is_active else "Historical"
        return f"{self.rate}% ({status}) - From {self.effective_from}"
    
    def save(self, *args, **kwargs):
        """Auto-deactivate old rates when saving a new active rate"""
        if self.is_active and not self.pk:  # New rate being created as active
            # Deactivate all other active rates
            CommissionRateHistory.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_rate_for_date(cls, target_datetime):
        """Get the commission rate applicable for a specific datetime (with millisecond precision)"""
        from datetime import date, datetime
        from django.utils import timezone
        
        # Convert to datetime if just a date is provided (for backward compatibility)
        if isinstance(target_datetime, date) and not isinstance(target_datetime, datetime):
            # If just a date, treat as start of day in local timezone
            from django.conf import settings
            import pytz
            local_tz = pytz.timezone(settings.TIME_ZONE)
            target_datetime = local_tz.localize(datetime.combine(target_datetime, datetime.min.time()))
        elif isinstance(target_datetime, str):
            target_datetime = datetime.strptime(target_datetime, '%Y-%m-%d').date()
            from django.conf import settings
            import pytz
            local_tz = pytz.timezone(settings.TIME_ZONE)
            target_datetime = local_tz.localize(datetime.combine(target_datetime, datetime.min.time()))
        
        # Ensure timezone-aware datetime
        if timezone.is_naive(target_datetime):
            target_datetime = timezone.make_aware(target_datetime)
        
        # Find rate where created_at <= target_datetime, ordered by created_at DESC
        # This ensures we get the LATEST rate that was active at the target time
        # If multiple rates exist on same day, the one created closest to (but before) target time wins
        rate_record = cls.objects.filter(
            created_at__lte=target_datetime,
            is_active=True
        ).order_by('-created_at').first()
        
        # If no active rate found, try historical rates
        if not rate_record:
            rate_record = cls.objects.filter(
                created_at__lte=target_datetime
            ).order_by('-created_at').first()
        
        if rate_record:
            return rate_record.rate
        
        # Fallback to system default if no rates defined
        return Decimal('5.00')  # Default 5% commission
    
    @classmethod
    def get_current_rate(cls):
        """Get the currently active commission rate"""
        from datetime import date
        return cls.get_rate_for_date(date.today())
    
    @classmethod
    def set_new_rate(cls, rate, effective_from, created_by=None, notes=None):
        """Set a new commission rate and deactivate previous rates"""
        from datetime import timedelta
        from django.utils import timezone
        
        # Ensure effective_from is timezone-aware datetime
        if not timezone.is_aware(effective_from):
            effective_from = timezone.make_aware(effective_from)
        
        # Deactivate all existing active rates
        cls.objects.filter(is_active=True).update(is_active=False)
        
        # Set effective_to for the previous rate (1 microsecond before new rate starts)
        previous_rate = cls.objects.filter(
            effective_to__isnull=True
        ).order_by('-effective_from').first()
        
        if previous_rate and previous_rate.effective_from < effective_from:
            # Set to 1 microsecond before the new rate starts
            previous_rate.effective_to = effective_from - timedelta(microseconds=1)
            previous_rate.is_active = False
            previous_rate.save()
        
        # Create new rate
        new_rate = cls.objects.create(
            rate=rate,
            effective_from=effective_from,
            effective_to=None,
            is_active=True,
            created_by=created_by,
            notes=notes
        )
        
        return new_rate
    
    def clean(self):
        """Validate rate history"""
        from django.core.exceptions import ValidationError
        
        if self.rate < 0 or self.rate > 100:
            raise ValidationError("Commission rate must be between 0 and 100")
        
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError("Effective to date cannot be before effective from date")
        
        # Check for overlapping periods (excluding self)
        overlapping = CommissionRateHistory.objects.filter(
            effective_from__lte=self.effective_from
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=self.effective_from)
        ).exclude(pk=self.pk)
        
        if overlapping.exists():
            raise ValidationError("This rate period overlaps with an existing rate")


class CommissionTransaction(models.Model):
    """Real-time Commission Transaction Tracking"""
    
    TRANSACTION_TYPE_CHOICES = (
        ('bill_created', 'Bill Created'),
        ('payment_received', 'Payment Received'),
        ('payment_cancelled', 'Payment Cancelled'),
        ('return_processed', 'Return Processed'),
        ('return_cancelled', 'Return Cancelled'),
        ('writeoff_executed', 'Write-off Executed'),
        ('adjustment', 'Manual Adjustment'),
    )
    
    # Transaction Details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    transaction_date = models.DateTimeField(default=timezone.now)
    sales_rep = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='commission_transactions'
    )
    
    # Related Objects (nullable - not all transactions have all references)
    bill = models.ForeignKey(
        'Bill', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='commission_transactions'
    )
    
    settlement = models.ForeignKey(
        'payments.SalesAccountSettlement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commission_transactions',
        help_text="Settlement that triggered this commission (for payment_received type)"
    )
    
    return_ref = models.ForeignKey(
        'sales.Return',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commission_transactions',
        help_text="Return that triggered this commission (for return_processed type)"
    )
    
    payout_history = models.ForeignKey(
        'sales.CommissionPayoutHistory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commission_adjustments',
        help_text="Payout that triggered this adjustment (for payout clearing transactions)"
    )
    
    # Amount Impact
    sales_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Total bill amount (for bill_created)"
    )
    
    collected_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Payment collected (for payment_received)"
    )
    
    return_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Return amount (for return_processed)"
    )
    
    # Commission Calculation
    applicable_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        help_text="Commission rate at time of transaction"
    )
    
    commission_earned = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Commission earned from this transaction"
    )
    
    running_balance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Cumulative commission balance after this transaction"
    )
    
    # Metadata
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'commission_transactions'
        ordering = ['-transaction_date', '-created_at']
        verbose_name = 'Commission Transaction'
        verbose_name_plural = 'Commission Transactions'
        indexes = [
            models.Index(fields=['sales_rep', '-transaction_date']),
            models.Index(fields=['bill']),
            models.Index(fields=['-transaction_date']),
        ]
    
    def __str__(self):
        return f"{self.sales_rep.get_full_name()} - {self.get_transaction_type_display()} - Rs. {self.commission_earned}"
    
    def save(self, *args, **kwargs):
        """Calculate commission and running balance on save - ENHANCED with race condition protection"""
        from django.db import transaction as db_transaction
        
        # Get applicable rate based on BILL CREATION TIMESTAMP (not transaction date)
        # Commission rate should be the rate active when the bill was created,
        # not when payment was received or return was processed
        # Uses FULL TIMESTAMP (including hours, minutes, seconds, milliseconds) for precision
        if not self.applicable_rate:
            # Determine which datetime to use for rate lookup
            if self.bill:
                # Use bill's creation datetime (full timestamp) for payment/return transactions
                rate_datetime = self.bill.bill_date
            else:
                # Fallback to transaction datetime for transactions without bill reference
                rate_datetime = self.transaction_date
            
            self.applicable_rate = CommissionRateHistory.get_rate_for_date(rate_datetime)
        
        # Calculate commission based on transaction type
        if self.transaction_type == 'payment_received':
            # Commission on collected payments
            self.commission_earned = (self.collected_amount * self.applicable_rate) / 100
        
        elif self.transaction_type == 'payment_cancelled':
            # Negative commission for cancelled payments (collected_amount will be negative)
            self.commission_earned = (self.collected_amount * self.applicable_rate) / 100
        
        elif self.transaction_type == 'return_processed':
            # Negative commission for returns
            self.commission_earned = -(self.return_amount * self.applicable_rate) / 100
        
        elif self.transaction_type == 'return_cancelled':
            # Positive commission when return is deleted (reverses the deduction)
            # return_amount will be negative, so we use the same formula as return_processed
            # This will result in positive commission (double negative)
            self.commission_earned = -(self.return_amount * self.applicable_rate) / 100
        
        elif self.transaction_type == 'bill_created':
            # No immediate commission on bill creation (only when payment received)
            self.commission_earned = Decimal('0.00')
        
        elif self.transaction_type == 'writeoff_executed':
            # No commission lost on write-off (since payment was never collected)
            self.commission_earned = Decimal('0.00')
        
        # Calculate running balance with SELECT FOR UPDATE to prevent race conditions
        with db_transaction.atomic():
            # Lock previous transaction to prevent concurrent updates
            previous_transaction = CommissionTransaction.objects.filter(
                sales_rep=self.sales_rep,
                transaction_date__lt=self.transaction_date
            ).select_for_update().order_by('-transaction_date', '-created_at').first()
            
            if previous_transaction:
                self.running_balance = previous_transaction.running_balance + self.commission_earned
            else:
                self.running_balance = self.commission_earned
            
            # Call parent save within transaction
            super().save(*args, **kwargs)
    
    @classmethod
    def create_for_bill(cls, bill, created_by=None):
        """Create commission transaction when bill is created - ENHANCED with duplicate check"""
        # Check if transaction already exists for this bill
        existing = cls.objects.filter(
            transaction_type='bill_created',
            bill=bill
        ).first()
        
        if existing:
            # Update existing transaction if bill amount changed
            if existing.sales_amount != bill.total_amount:
                existing.sales_amount = bill.total_amount
                existing.save(update_fields=['sales_amount'])
            return existing
        
        return cls.objects.create(
            transaction_type='bill_created',
            transaction_date=bill.bill_date,
            sales_rep=bill.sales_rep,
            bill=bill,
            sales_amount=bill.total_amount,
            notes=f"Bill {bill.bill_number} created for {bill.shop.shop_name}"
        )
    
    @classmethod
    def create_for_payment(cls, payment, bill):
        """Create commission transaction when payment is received - ENHANCED with duplicate check"""
        # Check for duplicate POSITIVE commission (original transaction) using settlement reference
        # Allows reversals (negative commission) to be created for the same settlement
        existing = cls.objects.filter(
            transaction_type='payment_received',
            settlement=payment,
            commission_earned__gt=0  # Only check for positive commission duplicates
        ).first()
        
        if existing:
            # Transaction already exists, return it instead of creating duplicate
            return existing
        
        # For cheque/bank_transfer: use verified_at (clearance time) so it appears
        # at the top of the commission list when cleared, not buried at recording date
        if payment.settlement_method in ('cheque', 'bank_transfer') and payment.verified_at:
            txn_date = payment.verified_at
        else:
            txn_date = payment.settlement_date
        
        return cls.objects.create(
            transaction_type='payment_received',
            transaction_date=txn_date,
            sales_rep=bill.sales_rep,
            bill=bill,
            settlement=payment,
            collected_amount=payment.amount,
            notes=f"Settlement {payment.settlement_number} for Bill {bill.bill_number}"
        )
    
    @classmethod
    def create_for_return(cls, return_obj):
        """Create commission transaction when return is processed - ENHANCED with duplicate check"""
        # Check if transaction already exists for this return using return_ref
        existing = cls.objects.filter(
            transaction_type='return_processed',
            return_ref=return_obj
        ).first()
        
        if existing:
            return existing
        
        # Get customer label for notes
        customer_label = return_obj.shop.shop_name if return_obj.shop else (return_obj.customer_name or "Unregistered Customer")
        
        return cls.objects.create(
            transaction_type='return_processed',
            transaction_date=return_obj.created_at,
            sales_rep=return_obj.created_by,
            return_ref=return_obj,
            return_amount=return_obj.total_amount,
            notes=f"Return {return_obj.return_number} processed for {customer_label}"
        )
    
    @classmethod
    def get_rep_balance(cls, sales_rep, as_of_date=None):
        """Get current commission balance for a sales rep"""
        from datetime import datetime
        
        if as_of_date is None:
            as_of_date = timezone.now()
        
        latest_transaction = cls.objects.filter(
            sales_rep=sales_rep,
            transaction_date__lte=as_of_date
        ).order_by('-transaction_date', '-created_at').first()
        
        if latest_transaction:
            return latest_transaction.running_balance
        
        return Decimal('0.00')
    
    @classmethod
    def get_month_summary(cls, sales_rep, year, month):
        """Get commission summary for a specific month"""
        from datetime import datetime
        
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1)
        else:
            month_end = datetime(year, month + 1, 1)
        
        transactions = cls.objects.filter(
            sales_rep=sales_rep,
            transaction_date__gte=month_start,
            transaction_date__lt=month_end
        )
        
        summary = {
            'total_sales': transactions.filter(transaction_type='bill_created').aggregate(
                total=Sum('sales_amount'))['total'] or Decimal('0.00'),
            
            'total_collected': transactions.filter(transaction_type='payment_received').aggregate(
                total=Sum('collected_amount'))['total'] or Decimal('0.00'),
            
            'total_returns': transactions.filter(transaction_type='return_processed').aggregate(
                total=Sum('return_amount'))['total'] or Decimal('0.00'),
            
            # Exclude payout adjustments from monthly earnings (historical data should not change)
            'total_commission': transactions.exclude(
                transaction_type='adjustment',
                commission_earned__lt=0  # Exclude negative adjustments (payouts)
            ).aggregate(
                total=Sum('commission_earned'))['total'] or Decimal('0.00'),
        }
        
        return summary


# ============================================================================
# PRINT MANAGEMENT SYSTEM
# ============================================================================
# Import the unified PrintManager model
from .print_manager import PrintManager


class Return(models.Model):
    """Product Return from Shop"""
    
    RETURN_REASON_CHOICES = (
        ('damaged', 'Damaged Product'),
        ('expired', 'Expired Product'),
        ('wrong_item', 'Wrong Item'),
        ('excess', 'Excess Stock'),
        ('quality', 'Quality Issue'),
        ('other', 'Other'),
    )
    
    SETTLEMENT_METHOD_CHOICES = (
        ('cash', 'Cash Refund'),
        ('bill_adjustment', 'Bill Adjustment'),
    )
    
    SETTLEMENT_STATUS_CHOICES = (
        ('unsettled', 'Awaiting Payment'),  # Approved but not settled yet
        ('settled_cash', 'Cash Paid'),  # Cash given to customer
        ('cancelled', 'Voucher Cancelled'),  # Return rejected after cash was paid
        ('available', 'Credit Available'),  # Can be applied to bills
        ('partially_applied', 'Partially Applied'),  # Some amount used
        ('fully_applied', 'Fully Applied'),  # All amount used
    )
    
    # Return Information
    return_number = models.CharField(max_length=50, unique=True, editable=False)
    return_date = models.DateTimeField(default=timezone.now)
    
    # Reference to original sale/bill
    sale = models.ForeignKey(Sale, on_delete=models.SET_NULL, null=True, blank=True, related_name='returns')
    bill = models.ForeignKey(Bill, on_delete=models.SET_NULL, null=True, blank=True, related_name='returns')
    
    # Shop and User
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name='returns', null=True, blank=True)
    customer_name = models.CharField(max_length=255, blank=True, null=True, help_text='For unregistered customers')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_returns', default=1)
    
    # Manager Verification (end-of-day review, not approval)
    is_verified = models.BooleanField(default=False, help_text="Manager verified at end of day (locks return from changes)")
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_returns')
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Return Details
    return_reason = models.CharField(max_length=20, choices=RETURN_REASON_CHOICES, default='other')
    settlement_method = models.CharField(max_length=20, choices=SETTLEMENT_METHOD_CHOICES, default='cash')
    settlement_status = models.CharField(max_length=20, choices=SETTLEMENT_STATUS_CHOICES, default='unsettled', help_text="Tracks how the return is being settled")
    notes = models.TextField(blank=True, null=True)
    
    # Cash Settlement Tracking (for settlement_method='cash')
    # Flow: Sales rep creates return + pays cash immediately (CPV issued) -> Manager verifies end of day (locks return)
    cash_paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cash_settled_returns', help_text="User who paid cash to customer (sales rep or manager)")
    cash_paid_at = models.DateTimeField(null=True, blank=True, help_text="When cash was paid to customer")
    cash_receipt_number = models.CharField(max_length=50, null=True, blank=True, help_text="Cash payment voucher number (CPV-YYYYMMDD-XXX) - issued immediately when cash paid")
    
    # Deprecated Field Cash Settlement Fields (kept for database compatibility)
    # These fields are no longer used - all cash payments now happen after manager approval
    field_cash_given = models.BooleanField(default=False, help_text="[DEPRECATED] No longer used")
    field_cash_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="[DEPRECATED] No longer used")
    field_cash_given_at = models.DateTimeField(null=True, blank=True, help_text="[DEPRECATED] No longer used")
    field_cash_notes = models.TextField(blank=True, null=True, help_text="[DEPRECATED] No longer used")
    field_receipt_number = models.CharField(max_length=50, null=True, blank=True, help_text="[DEPRECATED] No longer used")
    
    # Financial
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Amount refunded/credited")
    is_applied = models.BooleanField(default=False, help_text="Whether this return has been applied to a bill payment")
    applied_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Amount already applied to payments")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'returns'
        ordering = ['-return_date']
        verbose_name = 'Return'
        verbose_name_plural = 'Returns'
    
    def __str__(self):
        if self.shop:
            return f"{self.return_number} - {self.shop.shop_name}"
        elif self.customer_name:
            return f"{self.return_number} - {self.customer_name} (Unregistered)"
        else:
            return f"{self.return_number} - Unknown Customer"
    
    def save(self, *args, **kwargs):
        if not self.return_number:
            self.return_number = self.generate_return_number()
        super().save(*args, **kwargs)
    
    def generate_return_number(self):
        """Generate unique return number: RN-DISTCODE-YYYYMMDD-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('RN', Return, 'return_number')
    
    def calculate_totals(self):
        """Calculate total amount from return items"""
        items = self.items.all()
        self.total_amount = sum(item.total_price for item in items)
        self.save()


class ReturnItem(models.Model):
    """Individual items in a return"""
    
    return_ref = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    foc_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Condition
    is_damaged = models.BooleanField(default=False)
    is_resellable = models.BooleanField(default=True)
    
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'return_items'
    
    def __str__(self):
        return f"{self.product.product_name} - Qty: {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class ItemExchange(models.Model):
    """Item Exchange for Damaged/Expired Products - Direct Exchange without Return"""
    
    EXCHANGE_REASON_CHOICES = (
        ('damaged', 'Damaged Product'),
        ('expired', 'Expired Product'),
        ('defective', 'Defective Product'),
        ('quality', 'Quality Issue'),
    )
    
    EXCHANGE_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    # Exchange Information
    exchange_number = models.CharField(max_length=50, unique=True, editable=False)
    exchange_date = models.DateTimeField(default=timezone.now)
    
    # Shop and User
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name='exchanges')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_exchanges')
    
    # Exchange Details
    exchange_reason = models.CharField(max_length=20, choices=EXCHANGE_REASON_CHOICES)
    exchange_status = models.CharField(max_length=20, choices=EXCHANGE_STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'item_exchanges'
        ordering = ['-exchange_date']
        verbose_name = 'Item Exchange'
        verbose_name_plural = 'Item Exchanges'
    
    def __str__(self):
        return f"{self.exchange_number} - {self.shop.shop_name}"
    
    def save(self, *args, **kwargs):
        if not self.exchange_number:
            self.exchange_number = self.generate_exchange_number()
        super().save(*args, **kwargs)
    
    def generate_exchange_number(self):
        """Generate unique exchange number: EXC-DISTCODE-YYYYMMDD-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('EXC', ItemExchange, 'exchange_number')
    
    def mark_as_completed(self):
        """Mark exchange as completed"""
        self.exchange_status = 'completed'
        self.completed_at = timezone.now()
        self.save()


class ExchangeItem(models.Model):
    """Items in an exchange - tracking both returned and replacement items"""
    
    exchange = models.ForeignKey(ItemExchange, on_delete=models.CASCADE, related_name='items')
    
    # Returned (damaged/expired) product
    returned_product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='returned_in_exchanges')
    returned_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Replacement (new) product - can be different flavor
    replacement_product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='replaced_in_exchanges')
    replacement_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Stock tracking
    is_resellable = models.BooleanField(default=False, help_text="Can returned item be resold?")
    non_resellable_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Quantity that cannot be resold")
    
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'exchange_items'
        verbose_name = 'Exchange Item'
        verbose_name_plural = 'Exchange Items'
    
    def __str__(self):
        return f"{self.returned_product.product_name} → {self.replacement_product.product_name}"
    
    def save(self, *args, **kwargs):
        # Set non-resellable quantity based on is_resellable flag
        if not self.is_resellable:
            self.non_resellable_quantity = self.returned_quantity
        else:
            self.non_resellable_quantity = Decimal('0')
        super().save(*args, **kwargs)


class BillingPreference(models.Model):
    """Per-user billing experience preferences for the Create Bill page"""

    PRICE_CHOICES = (
        ('shop_price', 'Shop Price (System Default)'),
        ('my_prices', 'My Custom Prices'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='billing_preference')
    default_price = models.CharField(max_length=20, choices=PRICE_CHOICES, default='shop_price')
    show_foc_summary = models.BooleanField(default=True)

    class Meta:
        db_table = 'billing_preferences'
        verbose_name = 'Billing Preference'
        verbose_name_plural = 'Billing Preferences'

    def __str__(self):
        return f"{self.user.get_full_name()} billing preference"


class UserProductPrice(models.Model):
    """Per-user custom price for each product, used on the Create Bill page"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_product_prices')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='user_custom_prices')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_product_prices'
        unique_together = ('user', 'product')
        verbose_name = 'User Product Price'
        verbose_name_plural = 'User Product Prices'

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.product.product_name}: Rs. {self.price}"


class AISettings(models.Model):
    """Singleton AI configuration per tenant (always pk=1)"""

    is_enabled = models.BooleanField(default=False)
    credit_risk_enabled = models.BooleanField(default=True)
    collection_intelligence_enabled = models.BooleanField(default=True)
    api_key = models.CharField(max_length=500, blank=True, default='')
    api_base_url = models.CharField(
        max_length=200, default='https://openrouter.ai/api/v1'
    )
    model_name = models.CharField(
        max_length=100, default='google/gemini-2.0-flash-exp:free'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_settings'
        verbose_name = 'AI Settings'
        verbose_name_plural = 'AI Settings'

    def __str__(self):
        return f"AI Settings (enabled={self.is_enabled})"

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# Import commission schedule models
from .commission_schedule_models import (
    CommissionPayoutSchedule,
    CommissionPayoutHistory,
    UserCommissionPayout
)

# Import FOC reset models
from .foc_reset_models import FOCReset, FOCResetTransaction
