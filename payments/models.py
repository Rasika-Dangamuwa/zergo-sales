from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from shops.models import Shop
from sales.models import Bill
from accounts.models import User


class SalesAccountSettlement(models.Model):
    """
    Tracks all methods of settling sales bills (receivables from sales transactions).
    
    Business Logic:
    - Every settlement MUST link to a Bill (sales transaction)
    - "Credit" means unpaid bill balance, not a separate credit note
    - Settlement methods: Cash, Cheque, Bank Transfer, Return Adjustment
    - Write-offs handled separately via BadDebtWriteOff model
    
    Settlement Flow:
    1. Bill created → shop.current_balance increases
    2. Settlement recorded → bill.paid_amount increases
    3. Remaining balance "stays as credit" (unpaid receivable)
    """
    
    SETTLEMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit', 'Credit'),
        ('return_adjustment', 'Return Adjustment'),
    )
    
    SETTLEMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('bounced', 'Bounced'),  # For cheques
    )
    
    # Settlement Information
    settlement_number = models.CharField(max_length=50, unique=True)
    settlement_date = models.DateTimeField(default=timezone.now)
    
    # Related Records (Bill links every settlement to a sales transaction)
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name='settlements', null=True, blank=True)
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, related_name='settlements', null=True, blank=True)
    return_ref = models.ForeignKey('sales.Return', on_delete=models.SET_NULL, null=True, blank=True, related_name='settlement_applications', help_text="Sales return used for settlement offset")
    
    # Settlement Details
    settlement_method = models.CharField(max_length=20, choices=SETTLEMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Settlement Method Specific Fields (for cheque/bank transfers)
    reference_number = models.CharField(max_length=100, blank=True, null=True)  # For bank transfers, cheque numbers
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    cheque_date = models.DateField(blank=True, null=True)
    
    # Settlement Status
    settlement_status = models.CharField(max_length=20, choices=SETTLEMENT_STATUS_CHOICES, default='pending')
    is_provisional = models.BooleanField(default=False, help_text="Settlement using pending return - awaiting approval")
    
    # Cheque Collection Tracking (for cheque settlements only)
    cheque_collected = models.BooleanField(default=False, help_text="Physical cheque collected from rep")
    collected_at = models.DateTimeField(blank=True, null=True, help_text="When cheque was collected")
    collected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='collected_cheques', help_text="Office staff who collected the cheque")
    
    # Notes & Documentation
    notes = models.TextField(blank=True, null=True)
    attachment = models.FileField(upload_to='settlement_proofs/', blank=True, null=True)
    
    # Tracking (who received and verified the settlement)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='received_settlements')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_settlements')
    verified_at = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sales_account_settlements'
        ordering = ['-settlement_date']
        verbose_name = 'Sales Account Settlement'
        verbose_name_plural = 'Sales Account Settlements'
    
    def __str__(self):
        bill_ref = f"{self.bill.bill_number}" if self.bill else "No Bill"
        return f"{self.settlement_number} - {bill_ref} - Rs. {self.amount}"
    
    def generate_payment_number(self):
        """Generate unique settlement number: SET-DISTCODE-YYYYMMDD-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('SET', SalesAccountSettlement, 'settlement_number')
    
    def verify_settlement(self, user):
        """Mark settlement as verified and completed"""
        self.verified_by = user
        self.verified_at = timezone.now()
        self.settlement_status = 'completed'
        self.save()


# Backward compatibility alias (temporary - remove after full migration)
OldPayment = SalesAccountSettlement


class SettlementAttachment(models.Model):
    """Additional attachments for settlements (e.g., bank slips, cheque photos)"""
    
    ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'webp']
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    
    settlement = models.ForeignKey(SalesAccountSettlement, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(
        upload_to='settlement_attachments/',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'pdf', 'webp'])
        ]
    )
    description = models.CharField(max_length=200, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'settlement_attachments'
        ordering = ['-uploaded_at']
        verbose_name = 'Settlement Attachment'
        verbose_name_plural = 'Settlement Attachments'
    
    def clean(self):
        super().clean()
        if self.file and hasattr(self.file, 'size') and self.file.size > self.MAX_FILE_SIZE:
            raise ValidationError(
                f'File size must be under {self.MAX_FILE_SIZE // (1024 * 1024)} MB. '
                f'Current size: {self.file.size / (1024 * 1024):.1f} MB.'
            )

    def __str__(self):
        return f"Attachment for {self.settlement.settlement_number}"


# Backward compatibility alias
PaymentAttachment = SettlementAttachment


class BadDebtWriteOff(models.Model):
    """
    Track bad debt write-offs for uncollectable bills
    World-class debt management with full approval workflow and audit trail
    """
    
    REASON_CHOICES = (
        ('shop_closed', 'Shop Permanently Closed'),
        ('owner_deceased', 'Shop Owner Deceased'),
        ('bankruptcy', 'Bankruptcy/Insolvency'),
        ('legal_failed', 'Legal Collection Failed'),
        ('aged_debt', 'Aged Debt (180+ days)'),
        ('fraud', 'Fraud/Dispute'),
        ('other', 'Other Reason'),
    )
    
    APPROVAL_STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    # Unique number
    write_off_number = models.CharField(max_length=50, unique=True, editable=False)
    write_off_date = models.DateTimeField(auto_now_add=True)
    
    # Related records
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, related_name='write_offs')
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name='write_offs', null=True, blank=True)
    customer_name = models.CharField(max_length=255, blank=True, null=True, help_text='For unregistered customer write-offs')
    
    # Financial details
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Original bill total")
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount already paid")
    write_off_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount being written off")
    
    # Reason and justification
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    detailed_notes = models.TextField(help_text="Detailed explanation for write-off")
    
    # Approval workflow
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='requested_write_offs')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_write_offs')
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending')
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True, help_text="Reason for rejection if rejected")
    
    # Execution tracking
    executed = models.BooleanField(default=False, help_text="Whether write-off has been executed")
    executed_at = models.DateTimeField(null=True, blank=True)
    
    # Impact tracking
    bill_updated = models.BooleanField(default=False, help_text="Whether bill was updated")
    shop_balance_updated = models.BooleanField(default=False, help_text="Whether shop balance was updated")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bad_debt_write_offs'
        ordering = ['-write_off_date']
        verbose_name = 'Bad Debt Write-Off'
        verbose_name_plural = 'Bad Debt Write-Offs'
    
    def __str__(self):
        customer = self.shop.shop_name if self.shop else (self.customer_name or 'Unregistered Customer')
        return f"{self.write_off_number} - {customer} - Rs. {self.write_off_amount:,.2f}"
    
    def save(self, *args, **kwargs):
        if not self.write_off_number:
            self.write_off_number = self.generate_write_off_number()
        super().save(*args, **kwargs)
    
    def generate_write_off_number(self):
        """Generate unique write-off number: DISP-DISTCODE-YYYY-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('DISP', BadDebtWriteOff, 'write_off_number', mode='yearly')
    
    @property
    def is_pending(self):
        """Check if write-off is pending approval"""
        return self.approval_status == 'pending'
    
    @property
    def is_approved(self):
        """Check if write-off is approved"""
        return self.approval_status == 'approved'
    
    @property
    def is_rejected(self):
        """Check if write-off is rejected"""
        return self.approval_status == 'rejected'
    
    @property
    def days_since_bill(self):
        """Calculate days since bill was created"""
        from django.utils import timezone
        delta = timezone.now() - self.bill.bill_date
        return delta.days
