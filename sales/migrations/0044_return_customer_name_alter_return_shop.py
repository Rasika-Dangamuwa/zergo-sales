# Generated manually on 2026-01-31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0043_bill_customer_name_alter_bill_shop'),
        ('shops', '0002_shop_shop_photo_alter_shop_shop_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='return',
            name='customer_name',
            field=models.CharField(blank=True, help_text='For unregistered customers', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='return',
            name='shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='returns', to='shops.shop'),
        ),
    ]
