import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()
from django.db import connection

cursor = connection.cursor()

# Check which schema we're in
cursor.execute('SHOW search_path')
print('Search path:', cursor.fetchone())

# Check if global_product_id exists in each schema
for schema in ['public', 'dist_zergo001', 'dist_002', 'dist_003']:
    cursor.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = 'products' "
        "AND column_name = 'global_product_id'",
        [schema]
    )
    col = cursor.fetchone()
    print(f'{schema}.products.global_product_id: {"EXISTS" if col else "MISSING"}')

# Also check migration records
cursor.execute(
    "SELECT app, name FROM public.django_migrations "
    "WHERE app = 'products' AND name LIKE '%global%'"
)
print('\nMigration records in public.django_migrations:')
for row in cursor.fetchall():
    print(f'  {row[0]}.{row[1]}')
