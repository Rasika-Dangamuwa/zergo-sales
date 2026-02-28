# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0031_add_settlement_to_commission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commissiontransaction',
            name='transaction_type',
            field=models.CharField(
                choices=[
                    ('bill_created', 'Bill Created'),
                    ('payment_received', 'Payment Received'),
                    ('payment_cancelled', 'Payment Cancelled'),
                    ('return_processed', 'Return Processed'),
                    ('writeoff_executed', 'Write-off Executed'),
                    ('adjustment', 'Manual Adjustment')
                ],
                max_length=20
            ),
        ),
    ]
