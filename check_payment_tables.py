import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT tablename 
    FROM pg_tables 
    WHERE schemaname = 'public' 
    AND tablename LIKE '%payment%' 
    ORDER BY tablename
""")
tables = cursor.fetchall()

print('Payment-related tables in database:')
for table in tables:
    print(f'  - {table[0]}')
    
cursor.execute("""
    SELECT tablename 
    FROM pg_tables 
    WHERE schemaname = 'public'
    AND (tablename LIKE '%sale%' OR tablename LIKE '%bill%')
    ORDER BY tablename
""")
sales_tables = cursor.fetchall()
print('\nSales/Bill-related tables:')
for table in sales_tables:
    print(f'  - {table[0]}')

# Check old_payments columns
cursor.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'old_payments'
    AND (column_name LIKE '%bill%' OR column_name LIKE '%sale%')
    ORDER BY ordinal_position
""")
old_payment_cols = cursor.fetchall()
print('\nold_payments foreign key columns:')
for col in old_payment_cols:
    print(f'  - {col[0]}: {col[1]}')

print(f'\nTotal tables in database: {len(all_tables)}')
