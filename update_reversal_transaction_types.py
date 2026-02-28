"""
Update existing reversal transactions to use payment_cancelled type
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction

# Find all reversal transactions (negative commission with payment_received type)
reversals = CommissionTransaction.objects.filter(
    transaction_type='payment_received',
    commission_earned__lt=0
)

print(f"\nFound {reversals.count()} reversal transactions to update\n")

updated = 0
for rev in reversals:
    rev.transaction_type = 'payment_cancelled'
    rev.save(update_fields=['transaction_type'])
    updated += 1
    print(f"✅ Updated transaction ID {rev.id} - Settlement: {rev.settlement.settlement_number if rev.settlement else 'N/A'}")

print(f"\n📊 Summary: Updated {updated} reversal transactions to 'payment_cancelled' type")
