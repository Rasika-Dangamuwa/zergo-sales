# Generated manually on 2026-01-24
# Custom migration to rename OldPayment to SalesAccountSettlement with data preservation

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0004_remove_payment_reconciliation'),
        ('sales', '0029_remove_commission_settings'),
        ('shops', '0002_shop_shop_photo_alter_shop_shop_code'),
        ('accounts', '0002_salesreplocation'),
    ]

    operations = [
        # Step 1: Rename model
        migrations.RenameModel(
            old_name='OldPayment',
            new_name='SalesAccountSettlement',
        ),
        
        # Step 2: Rename database table
        migrations.AlterModelTable(
            name='salesaccountsettlement',
            table='sales_account_settlements',
        ),
        
        # Step 3: Rename fields
        migrations.RenameField(
            model_name='salesaccountsettlement',
            old_name='payment_number',
            new_name='settlement_number',
        ),
        migrations.RenameField(
            model_name='salesaccountsettlement',
            old_name='payment_date',
            new_name='settlement_date',
        ),
        migrations.RenameField(
            model_name='salesaccountsettlement',
            old_name='payment_method',
            new_name='settlement_method',
        ),
        migrations.RenameField(
            model_name='salesaccountsettlement',
            old_name='status',
            new_name='settlement_status',
        ),
        
        # Step 4: Update related names in foreign keys
        migrations.AlterField(
            model_name='salesaccountsettlement',
            name='shop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='settlements', to='shops.shop'),
        ),
        migrations.AlterField(
            model_name='salesaccountsettlement',
            name='bill',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='settlements', to='sales.bill'),
        ),
        migrations.AlterField(
            model_name='salesaccountsettlement',
            name='return_ref',
            field=models.ForeignKey(blank=True, help_text='Sales return used for settlement offset', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='settlement_applications', to='sales.return'),
        ),
        migrations.AlterField(
            model_name='salesaccountsettlement',
            name='received_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='received_settlements', to='accounts.user'),
        ),
        migrations.AlterField(
            model_name='salesaccountsettlement',
            name='verified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_settlements', to='accounts.user'),
        ),
        
        # Step 5: Update help texts and other field properties
        migrations.AlterField(
            model_name='salesaccountsettlement',
            name='is_provisional',
            field=models.BooleanField(default=False, help_text='Settlement using pending return - awaiting approval'),
        ),
        migrations.AlterField(
            model_name='salesaccountsettlement',
            name='attachment',
            field=models.FileField(blank=True, null=True, upload_to='settlement_proofs/'),
        ),
        
        # Step 6: Update model meta options
        migrations.AlterModelOptions(
            name='salesaccountsettlement',
            options={
                'ordering': ['-settlement_date'],
                'verbose_name': 'Sales Account Settlement',
                'verbose_name_plural': 'Sales Account Settlements',
            },
        ),
        
        # Step 7: Update PaymentAttachment model
        migrations.RenameModel(
            old_name='PaymentAttachment',
            new_name='SettlementAttachment',
        ),
        migrations.AlterModelTable(
            name='settlementattachment',
            table='settlement_attachments',
        ),
        migrations.RenameField(
            model_name='settlementattachment',
            old_name='payment',
            new_name='settlement',
        ),
        migrations.AlterField(
            model_name='settlementattachment',
            name='settlement',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='payments.salesaccountsettlement'),
        ),
        migrations.AlterField(
            model_name='settlementattachment',
            name='file',
            field=models.FileField(upload_to='settlement_attachments/'),
        ),
        migrations.AlterModelOptions(
            name='settlementattachment',
            options={
                'ordering': ['-uploaded_at'],
                'verbose_name': 'Settlement Attachment',
                'verbose_name_plural': 'Settlement Attachments',
            },
        ),
    ]
