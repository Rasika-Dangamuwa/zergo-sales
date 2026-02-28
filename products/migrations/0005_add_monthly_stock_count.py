# Generated manually for monthly stock count feature

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('products', '0004_add_flavor_tracking_and_sales'),
    ]

    operations = [
        migrations.CreateModel(
            name='MonthlyStockCount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count_date', models.DateField(help_text='Date of stock count (usually month-end)')),
                ('physical_count', models.IntegerField(help_text='Actual physical count of this flavor')),
                ('calculated_balance', models.IntegerField(blank=True, help_text='Calculated balance from transactions (auto-filled)', null=True)),
                ('variance', models.IntegerField(blank=True, help_text='Difference: Physical - Calculated (auto-calculated)', null=True)),
                ('adjustment_made', models.BooleanField(default=False, help_text='Whether adjustment was posted')),
                ('adjustment_reason', models.TextField(blank=True, help_text='Reason for variance (e.g., damage, theft, counting error)', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('counted_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stock_counts', to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stock_counts', to='products.product')),
            ],
            options={
                'db_table': 'monthly_stock_counts',
                'ordering': ['-count_date', 'product__company', 'product__sku__size', 'product__flavor'],
            },
        ),
        migrations.AddConstraint(
            model_name='monthlystockcount',
            constraint=models.UniqueConstraint(fields=('count_date', 'product'), name='unique_count_date_product'),
        ),
    ]
