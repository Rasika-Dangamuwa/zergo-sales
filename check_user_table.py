import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE '%user%' ORDER BY tablename")
tables = cursor.fetchall()
print("User tables:")
for t in tables:
    print(f"  - {t[0]}")
