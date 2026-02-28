import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'business_system.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema='public' AND table_type='BASE TABLE' 
    ORDER BY table_name
""")

print("\nAll Database Tables:")
print("=" * 60)
for row in cursor.fetchall():
    if 'sales' in row[0].lower() or 'bill' in row[0].lower() or 'commission' in row[0].lower():
        print(f">>> {row[0]}")  # Highlight relevant tables
    else:
        print(row[0])
print("=" * 60)
