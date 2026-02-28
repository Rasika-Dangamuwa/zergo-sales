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
    ORDER BY tablename
""")
all_tables = cursor.fetchall()

print('All tables in database:')
print('=' * 50)
for table in all_tables:
    print(f'  {table[0]}')

print(f'\nTotal: {len(all_tables)} tables')
