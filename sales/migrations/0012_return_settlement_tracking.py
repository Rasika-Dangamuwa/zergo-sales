# Generated migration for return settlement tracking

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sales', '0008_return_applied_amount_return_is_applied'),
    ]

    operations = [
        migrations.AddField(
            model_name='return',
            name='settlement_status',
            field=models.CharField(
                choices=[
                    ('unsettled', 'Unsettled'),
                    ('settled_cash', 'Settled - Cash Paid'),
                    ('available', 'Available for Application'),
                    ('partially_applied', 'Partially Applied'),
                    ('fully_applied', 'Fully Applied')
                ],
                default='unsettled',
                help_text='Tracks how the return is being settled',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='return',
            name='cash_paid_by',
            field=models.ForeignKey(
                blank=True,
                help_text='User who paid cash to customer',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='cash_settled_returns',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name='return',
            name='cash_paid_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When cash was paid to customer',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='return',
            name='cash_receipt_number',
            field=models.CharField(
                blank=True,
                help_text='Cash receipt number',
                max_length=50,
                null=True
            ),
        ),
    ]
