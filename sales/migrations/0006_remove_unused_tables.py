# Generated manually on 2025-12-31
# Remove unused database tables: sales, sale_items, payments, purchase_orders, purchase_order_items

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0005_return_returnitem'),
    ]

    operations = [
        migrations.RunSQL(
            # Drop unused tables
            sql="""
                DROP TABLE IF EXISTS payments CASCADE;
                DROP TABLE IF EXISTS sale_items CASCADE;
                DROP TABLE IF EXISTS sales CASCADE;
                DROP TABLE IF EXISTS purchase_order_items CASCADE;
                DROP TABLE IF EXISTS purchase_orders CASCADE;
            """,
            # Reverse migration - recreate tables would be complex, so we make it irreversible
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
