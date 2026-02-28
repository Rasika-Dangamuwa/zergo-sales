from django.db import models
from django.utils import timezone
from shops.models import Shop
from sales.models import Bill
from accounts.models import User


class OldPayment(models.Model):
    """OLD Payment Model - Being replaced by Payment model in sales app"""
    
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit', 'Credit'),
        ('return_adjustment', 'Return Adjustment'),
    )
    
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('bounced', 'Bounced'),  # For cheques
    )
    
    # Payment Information
    payment_number = models.CharField(max_length=50, unique=True)
    payment_date = models.DateTimeField(default=timezone.now)
    
    # Related Records
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name='old_payments')
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, related_name='old_payments', null=True, blank=True)
    return_ref = models.ForeignKey('sales.Return', on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_applications', help_text="Return used for this payment")
    
    # Payment Details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment Method Specific Fields
    reference_number = models.CharField(max_length=100, blank=True, null=True)  # For bank transfers, cheque numbers
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    cheque_date = models.DateField(blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    is_provisional = models.BooleanField(default=False, help_text="Payment using pending return - awaiting approval")
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    attachment = models.FileField(upload_to='payment_proofs/', blank=True, null=True)
    
    # Tracking
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='old_received_payments')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='old_verified_payments')
    verified_at = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'old_payments'
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.payment_number} - {self.shop.shop_name} - Rs. {self.amount}"
    
    def generate_payment_number(self):
        """Generate unique payment number: PAY-20260110-0001"""
        today = timezone.now()
        prefix = f"PAY-{today.strftime('%Y%m%d')}-"
        
        last_payment = OldPayment.objects.filter(payment_number__startswith=prefix).order_by('-payment_number').first()
        
        if last_payment:
            last_number = int(last_payment.payment_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        self.payment_number = f"{prefix}{new_number:04d}"
        return self.payment_number
    
    def verify_payment(self, user):
        """Mark payment as verified"""
        self.verified_by = user
        self.verified_at = timezone.now()
        self.status = 'completed'
        self.save()


class PaymentAttachment(models.Model):
    """Payment attachments - cheque images and bank transfer receipts"""
    
    ATTACHMENT_TYPE_CHOICES = (
        ('cheque_front', 'Cheque Front'),
        ('cheque_back', 'Cheque Back'),
        ('bank_receipt', 'Bank Transfer Receipt'),
        ('other', 'Other'),
    )
    
    payment = models.ForeignKey(OldPayment, on_delete=models.CASCADE, related_name='attachments')
    attachment_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPE_CHOICES)
    image = models.ImageField(upload_to='payment_receipts/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=200, blank=True, null=True)
    
    class Meta:
        db_table = 'payment_attachments'
        ordering = ['attachment_type', 'uploaded_at']
    
    def __str__(self):
        return f"{self.payment.payment_number} - {self.get_attachment_type_display()}"


class CreditNote(models.Model):
    """Credit Note for returns or adjustments"""
    
    credit_note_number = models.CharField(max_length=50, unique=True)
    credit_note_date = models.DateTimeField(default=timezone.now)
    
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name='credit_notes')
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, related_name='credit_notes', null=True, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    
    is_applied = models.BooleanField(default=False)
    applied_date = models.DateTimeField(blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'credit_notes'
        ordering = ['-credit_note_date']
    
    def __str__(self):
        return f"{self.credit_note_number} - {self.shop.shop_name}"


class PaymentReconciliation(models.Model):
    """Track payment reconciliation"""
    
    reconciliation_date = models.DateField()
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT)
    
    opening_balance = models.DecimalField(max_digits=10, decimal_places=2)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2)
    total_payments = models.DecimalField(max_digits=10, decimal_places=2)
    total_returns = models.DecimalField(max_digits=10, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=10, decimal_places=2)
    
    notes = models.TextField(blank=True, null=True)
    
    reconciled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payment_reconciliations'
        ordering = ['-reconciliation_date']
    
    def __str__(self):
        return f"{self.shop.shop_name} - {self.reconciliation_date}"
