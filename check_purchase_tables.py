import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT tablename 
    FROM pg_tables 
    WHERE schemaname='public' AND tablename LIKE '%purchase%'
    ORDER BY tablename
""")

tables = cursor.fetchall()
print("Purchase-related tables:")
for table in tables:
    print(f"  - {table[0]}")

if not tables:
    print("  No purchase tables found")
