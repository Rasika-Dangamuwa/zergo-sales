# Generated migration for flavor tracking and sales models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0002_shop_shop_photo_alter_shop_shop_code'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('products', '0003_rename_unit_price_to_marked_price'),
    ]

    operations = [
        # Add flavor field to PurchaseOrderItem
        migrations.AddField(
            model_name='purchaseorderitem',
            name='flavor',
            field=models.CharField(blank=True, help_text='Flavor received in this line (e.g., Orange, Nexta)', max_length=100, null=True),
        ),
        
        # Create Sale model
        migrations.CreateModel(
            name='Sale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice_number', models.CharField(max_length=50, unique=True)),
                ('invoice_date', models.DateField()),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('delivered', 'Delivered'), ('paid', 'Paid'), ('cancelled', 'Cancelled')], default='draft', max_length=20)),
                ('payment_status', models.CharField(choices=[('unpaid', 'Unpaid'), ('partial', 'Partially Paid'), ('paid', 'Fully Paid')], default='unpaid', max_length=20)),
                ('subtotal', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('amount_paid', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('amount_due', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('delivery_date', models.DateField(blank=True, null=True)),
                ('delivery_notes', models.TextField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_sales', to=settings.AUTH_USER_MODEL)),
                ('sales_rep', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='product_sales', to=settings.AUTH_USER_MODEL)),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sales', to='shops.shop')),
            ],
            options={
                'verbose_name': 'Sale',
                'verbose_name_plural': 'Sales',
                'db_table': 'sales',
                'ordering': ['-invoice_date', '-invoice_number'],
            },
        ),
        
        # Create SaleItem model
        migrations.CreateModel(
            name='SaleItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=1)),
                ('marked_price', models.DecimalField(decimal_places=2, help_text='MRP at time of sale', max_digits=10)),
                ('discount_percentage', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('unit_price', models.DecimalField(decimal_places=2, help_text='Price after discount', max_digits=10)),
                ('line_total', models.DecimalField(decimal_places=2, max_digits=12)),
                ('notes', models.TextField(blank=True, null=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sale_items', to='products.product')),
                ('sale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='products.sale')),
            ],
            options={
                'db_table': 'sale_items',
                'ordering': ['id'],
            },
        ),
    ]
