"""
Drop old cash account tables from previous attempt
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Drop tables if they exist
    cursor.execute("DROP TABLE IF EXISTS sales_rep_transactions CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS advance_requests CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS sales_rep_cash_accounts CASCADE;")
    print("✅ Old tables dropped successfully")
