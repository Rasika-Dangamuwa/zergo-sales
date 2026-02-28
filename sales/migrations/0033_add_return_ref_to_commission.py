# Generated manually
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0032_add_payment_cancelled_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='commissiontransaction',
            name='return_ref',
            field=models.ForeignKey(blank=True, help_text='Return that triggered this commission (for return_processed type)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='commission_transactions', to='sales.return'),
        ),
    ]
