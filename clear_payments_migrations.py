import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import connection

# Delete the problematic migration record from django_migrations table
cursor = connection.cursor()

print("Clearing migration history for payments app...")
cursor.execute("DELETE FROM django_migrations WHERE app = 'payments'")
print(f"Deleted {cursor.rowcount} payment migration records")

connection.commit()
print("✅ Migration history cleared. Now run: python manage.py migrate payments --fake-initial")
