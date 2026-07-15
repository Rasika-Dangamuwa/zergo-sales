"""
User Money Account System - Commission Payment Management
Tracks actual money added to users, payments made to them, advances requested/given
"""
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from accounts.models import User


class UserMoneyAccount(models.Model):
    """
    Money account for each user - tracks their financial balance with the company
    This is separate from commission tracking - it tracks actual money transactions
    """
    user = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name='money_account'
    )
    
    # Opening Balance
    opening_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Starting balance when account created"
    )
    
    opening_date = models.DateField(
        default=timezone.now,
        help_text="Date account was created"
    )
    
    opening_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes about opening balance"
    )
    
    # Auto-calculated Totals
    total_credited = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total amount added to account (commissions, bonuses, etc)"
    )
    
    total_debited = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total amount paid out to user"
    )
    
    total_advance_given = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total advances given (money given before earning)"
    )
    
    total_advance_recovered = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total advance recovered from earnings"
    )
    
    # Current Balance
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current balance - Positive = We owe user, Negative = User owes us (advance)"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_money_accounts'
    )
    
    class Meta:
        db_table = 'user_money_accounts'
        ordering = ['user__first_name', 'user__last_name']
        verbose_name = 'User Money Account'
        verbose_name_plural = 'User Money Accounts'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Rs. {self.current_balance:,.2f}"
    
    def update_balance(self):
        """
        Recalculate balance from all transactions
        Balance = opening_balance + credits - debits + advances_given - advances_recovered
        """
        from django.db.models import Sum

        txns = self.transactions.all()
        
        # Sum by transaction type
        credits = txns.filter(
            transaction_type__in=['credit', 'commission_payment', 'bonus', 'adjustment_credit']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        debits = txns.filter(
            transaction_type__in=['debit', 'payment', 'adjustment_debit']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        advances_given = txns.filter(
            transaction_type='advance_given'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        advances_recovered = txns.filter(
            transaction_type='advance_recovery'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Update totals
        self.total_credited = credits
        self.total_debited = debits
        self.total_advance_given = advances_given
        self.total_advance_recovered = advances_recovered
        
        # Calculate current balance
        # Positive = We owe user (from earned commissions not yet paid)
        # Negative = User took more advances than earned (should not happen with validation)
        self.current_balance = (
            self.opening_balance +
            credits -
            debits -
            advances_given
        )
        # Note: advances_recovered is legacy - not used in new model
        
        self.save(update_fields=[
            'total_credited',
            'total_debited',
            'total_advance_given',
            'total_advance_recovered',
            'current_balance',
            'updated_at'
        ])
    
    @property
    def balance_owed_to_user(self):
        """Amount we owe to the user (positive balance)"""
        return max(self.current_balance, Decimal('0.00'))
    
    @property
    def outstanding_advance(self):
        """Total advances taken (for reporting only - already deducted from balance)"""
        return self.total_advance_given


class MoneyTransaction(models.Model):
    """
    Individual money transaction for a user account
    """
    TRANSACTION_TYPE_CHOICES = (
        ('credit', 'Credit - Add Money'),
        ('debit', 'Debit - Remove Money'),
        ('commission_payment', 'Commission Payment'),
        ('bonus', 'Bonus Payment'),
        ('payment', 'Payment to User'),
        ('advance_given', 'Advance Given'),
        ('advance_recovery', 'Advance Recovery'),
        ('adjustment_credit', 'Adjustment (Credit)'),
        ('adjustment_debit', 'Adjustment (Debit)'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('adjustment', 'Adjustment'),
    )
    
    # Transaction Details
    transaction_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False
    )
    
    account = models.ForeignKey(
        UserMoneyAccount,
        on_delete=models.PROTECT,
        related_name='transactions'
    )
    
    transaction_type = models.CharField(
        max_length=30,
        choices=TRANSACTION_TYPE_CHOICES
    )
    
    transaction_date = models.DateTimeField(default=timezone.now)
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Payment Details (for payments and advances)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        null=True
    )
    
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Cheque number, bank ref, receipt number, etc."
    )
    
    # Description and Notes
    description = models.CharField(
        max_length=200,
        help_text="Brief description of transaction"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes"
    )
    
    # Related Objects
    advance_request = models.ForeignKey(
        'AdvanceRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    
    commission_reference = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Commission month/period reference (e.g., 2026-01)"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_money_transactions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'money_transactions'
        ordering = ['-transaction_date', '-id']
        verbose_name = 'Money Transaction'
        verbose_name_plural = 'Money Transactions'
        indexes = [
            models.Index(fields=['account', '-transaction_date']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['transaction_date']),
        ]
    
    def __str__(self):
        return f"{self.transaction_number} - {self.account.user.get_full_name()} - Rs. {self.amount:,.2f}"
    
    def save(self, *args, **kwargs):
        # Auto-generate transaction number
        if not self.transaction_number:
            self.transaction_number = self.generate_transaction_number()
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Update account balance after saving
        if is_new:
            self.account.update_balance()
    
    def generate_transaction_number(self):
        """Generate unique transaction number: MONEY-DISTCODE-YYYY-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('MONEY', MoneyTransaction, 'transaction_number', mode='yearly')


class AdvanceRequest(models.Model):
    """
    Employee advance request and approval workflow
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    )
    
    # Request Details
    request_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='advance_requests'
    )
    
    requested_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    request_date = models.DateTimeField(default=timezone.now)
    
    reason = models.TextField(
        help_text="Reason for requesting advance"
    )
    
    # Approval
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    approved_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount approved (may differ from requested)"
    )
    
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_advances'
    )
    
    approved_at = models.DateTimeField(null=True, blank=True)
    
    approval_notes = models.TextField(blank=True, null=True)
    
    # Rejection
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Payment
    paid_at = models.DateTimeField(null=True, blank=True)
    
    payment_method = models.CharField(
        max_length=20,
        choices=MoneyTransaction.PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True
    )
    
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'advance_requests'
        ordering = ['-request_date']
        verbose_name = 'Advance Request'
        verbose_name_plural = 'Advance Requests'
        indexes = [
            models.Index(fields=['user', '-request_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.request_number} - {self.user.get_full_name()} - Rs. {self.requested_amount:,.2f}"
    
    def save(self, *args, **kwargs):
        # Auto-generate request number
        if not self.request_number:
            self.request_number = self.generate_request_number()
        super().save(*args, **kwargs)
    
    def generate_request_number(self):
        """Generate unique request number: ADV-DISTCODE-YYYY-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('ADV', AdvanceRequest, 'request_number', mode='yearly')
