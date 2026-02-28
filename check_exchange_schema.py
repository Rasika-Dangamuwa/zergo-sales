import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='exchange_items' ORDER BY ordinal_position")
columns = [row[0] for row in cursor.fetchall()]

print("Current exchange_items table columns:")
for col in columns:
    print(f"  - {col}")

# Check for sample row
cursor.execute("SELECT * FROM exchange_items LIMIT 1")
cols = [desc[0] for desc in cursor.description]
row = cursor.fetchone()

if row:
    print("\nSample row data:")
    for col, val in zip(cols, row):
        print(f"  {col}: {val}")
else:
    print("\nNo rows in table")
