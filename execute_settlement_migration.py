"""Execute SQL migration for settlement_status"""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import connection

# Read SQL file
with open('migrate_settlement_status.sql', 'r') as f:
    sql = f.read()

# Execute
with connection.cursor() as cursor:
    cursor.execute(sql)
    print("✓ Settlement status migration executed successfully!")
    print("✓ Database updated: payment_status → settlement_status")
    print("✓ Values updated: unpaid→unsettled, partial→partial_settled, paid→settled")
