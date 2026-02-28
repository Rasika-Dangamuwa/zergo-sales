# Generated migration to rename unit_price to marked_price in StockKeepingUnit

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_auto_20251220_0345'),
    ]

    operations = [
        # Rename unit_price to marked_price in StockKeepingUnit
        migrations.RenameField(
            model_name='stockkeepingunit',
            old_name='unit_price',
            new_name='marked_price',
        ),
        
        # Update the unique_together constraint
        migrations.AlterUniqueTogether(
            name='stockkeepingunit',
            unique_together={('company', 'size', 'marked_price')},
        ),
        
        # Update the ordering
        migrations.AlterModelOptions(
            name='stockkeepingunit',
            options={
                'verbose_name': 'Stock Keeping Unit (SKU)',
                'verbose_name_plural': 'Stock Keeping Units (SKUs)',
                'db_table': 'stock_keeping_units',
                'ordering': ['company', 'size', 'marked_price'],
            },
        ),
        
        # Remove the selling_price field from Product
        migrations.RemoveField(
            model_name='product',
            name='selling_price',
        ),
        
        # Update Product discount_percentage default to 10.00
        migrations.AlterField(
            model_name='product',
            name='discount_percentage',
            field=models.DecimalField(decimal_places=2, default=10.00, help_text='Discount % given to shops', max_digits=5),
        ),
    ]
