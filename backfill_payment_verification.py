"""
Script to update existing completed payments with missing verification info
Run this once to backfill old data
"""
from django.utils import timezone
from payments.models import OldPayment as Payment

# Find all completed payments without verified_by
payments_to_update = Payment.objects.filter(
    status='completed',
    verified_by__isnull=True
)

print(f"Found {payments_to_update.count()} completed payments without verification info")

for payment in payments_to_update:
    # Set verified_by to the person who received the payment
    # Set verified_at to the payment creation date (best approximation)
    payment.verified_by = payment.received_by
    payment.verified_at = payment.created_at
    payment.save()
    print(f"Updated {payment.payment_number}")

print(f"\n✅ Updated {payments_to_update.count()} payments successfully!")
