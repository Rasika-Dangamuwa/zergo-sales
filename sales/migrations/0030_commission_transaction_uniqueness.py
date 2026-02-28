# Generated manually for enhanced commission tracking reliability
# January 2026

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0029_remove_commission_settings'),
    ]

    operations = [
        # Add unique constraint for bill-based transactions (one transaction per bill)
        migrations.AddConstraint(
            model_name='commissiontransaction',
            constraint=models.UniqueConstraint(
                fields=['transaction_type', 'bill'],
                condition=models.Q(transaction_type='bill_created'),
                name='unique_bill_commission',
                violation_error_message='Commission transaction already exists for this bill'
            ),
        ),
        
        # Add unique constraint for payment transactions (prevent duplicate payments)
        migrations.AddConstraint(
            model_name='commissiontransaction',
            constraint=models.UniqueConstraint(
                fields=['transaction_type', 'bill', 'collected_amount', 'transaction_date'],
                condition=models.Q(transaction_type='payment_received'),
                name='unique_payment_commission',
                violation_error_message='Commission transaction already exists for this payment'
            ),
        ),
        
        # Add index for faster running balance queries
        migrations.AddIndex(
            model_name='commissiontransaction',
            index=models.Index(
                fields=['sales_rep', 'transaction_date', 'created_at'],
                name='idx_commission_balance_calc'
            ),
        ),
        
        # Add index for transaction type filtering
        migrations.AddIndex(
            model_name='commissiontransaction',
            index=models.Index(
                fields=['sales_rep', 'transaction_type', 'transaction_date'],
                name='idx_commission_type_filter'
            ),
        ),
    ]
