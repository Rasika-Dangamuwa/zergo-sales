"""
Data Migration Script: Migrate Existing Single-Tenant Data to Multi-Tenant Architecture

This script:
1. Creates a 'public' tenant (required by django-tenants for the main domain)
2. Creates the first distributor tenant from the existing data
3. Copies all existing business data (shops, products, sales, payments, business)
   from the public schema into the first tenant's schema
4. Links existing users to the new tenant

Run: python manage.py runscript migrate_to_multi_tenant
  OR: python migrate_to_multi_tenant.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from tenants.models import Distributor, Domain
from accounts.models import User


def run():
    print("=" * 60)
    print("MULTI-TENANT DATA MIGRATION")
    print("=" * 60)
    
    # Step 1: Create the public tenant (required by django-tenants)
    print("\n[Step 1] Creating public tenant...")
    public_tenant, created = Distributor.objects.get_or_create(
        schema_name='public',
        defaults={
            'name': 'Platform Admin',
            'code': 'PLATFORM',
            'owner_name': 'System',
            'plan': 'enterprise',
            'is_active': True,
        }
    )
    if created:
        Domain.objects.create(
            domain='localhost',
            tenant=public_tenant,
            is_primary=True,
        )
        print(f"  ✓ Created public tenant with domain 'localhost'")
    else:
        print(f"  - Public tenant already exists")

    # Step 2: Create the first distributor tenant
    print("\n[Step 2] Creating first distributor tenant...")
    
    # Try to get existing business name from DistributorProfile
    dist_name = 'Zergo Distributors'
    dist_code = 'ZERGO001'
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT business_name FROM business_distributorprofile 
                WHERE is_active = true LIMIT 1
            """)
            row = cursor.fetchone()
            if row and row[0]:
                dist_name = row[0]
    except Exception as e:
        print(f"  (Could not read existing business name: {e})")
    
    first_tenant, created = Distributor.objects.get_or_create(
        code=dist_code,
        defaults={
            'schema_name': 'dist_zergo001',
            'name': dist_name,
            'plan': 'enterprise',
            'is_active': True,
            'max_users': 50,
            'max_shops': 5000,
        }
    )
    
    if created:
        # auto_create_schema=True on the model will create the schema
        # But we need to also add a domain
        Domain.objects.create(
            domain='zergo001.localhost',
            tenant=first_tenant,
            is_primary=True,
        )
        print(f"  ✓ Created tenant '{first_tenant.name}' (schema: {first_tenant.schema_name})")
        print(f"  ✓ Domain: zergo001.localhost")
    else:
        print(f"  - Tenant '{first_tenant.name}' already exists")
    
    # Step 3: Link existing users to this tenant
    print("\n[Step 3] Linking users to tenant...")
    unlinked_users = User.objects.filter(tenant__isnull=True, is_superuser=False)
    count = unlinked_users.update(tenant=first_tenant)
    print(f"  ✓ Linked {count} users to '{first_tenant.name}'")
    
    # Make superusers platform admins
    super_count = User.objects.filter(is_superuser=True).update(is_platform_admin=True)
    print(f"  ✓ Marked {super_count} superusers as platform admins")
    
    # Step 4: Copy data from public schema to tenant schema
    print(f"\n[Step 4] Copying business data to tenant schema '{first_tenant.schema_name}'...")
    
    # Tables that belong to tenant apps (need to be copied)
    tenant_tables = _get_tenant_tables()
    
    with connection.cursor() as cursor:
        for table in tenant_tables:
            try:
                # Check if table exists in public schema
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = %s
                    )
                """, [table])
                exists = cursor.fetchone()[0]
                
                if not exists:
                    print(f"  - {table}: not in public schema, skipping")
                    continue
                
                # Check row count in public
                cursor.execute(f'SELECT COUNT(*) FROM public."{table}"')
                public_count = cursor.fetchone()[0]
                
                if public_count == 0:
                    print(f"  - {table}: empty, skipping")
                    continue
                
                # Check if table exists in tenant schema
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = %s AND table_name = %s
                    )
                """, [first_tenant.schema_name, table])
                tenant_exists = cursor.fetchone()[0]
                
                if not tenant_exists:
                    print(f"  ⚠ {table}: doesn't exist in tenant schema yet, skipping")
                    continue
                
                # Check if already has data in tenant
                cursor.execute(f'SELECT COUNT(*) FROM "{first_tenant.schema_name}"."{table}"')
                tenant_count = cursor.fetchone()[0]
                
                if tenant_count > 0:
                    print(f"  - {table}: already has {tenant_count} rows in tenant, skipping")
                    continue
                
                # Copy data
                cursor.execute(f"""
                    INSERT INTO "{first_tenant.schema_name}"."{table}"
                    SELECT * FROM public."{table}"
                """)
                
                # Reset sequence if table has an id column
                try:
                    cursor.execute(f"""
                        SELECT setval(
                            pg_get_serial_sequence('"{first_tenant.schema_name}"."{table}"', 'id'),
                            COALESCE((SELECT MAX(id) FROM "{first_tenant.schema_name}"."{table}"), 0) + 1,
                            false
                        )
                    """)
                except Exception:
                    pass  # No serial sequence
                
                print(f"  ✓ {table}: copied {public_count} rows")
                
            except Exception as e:
                print(f"  ✗ {table}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE!")
    print("=" * 60)
    print(f"\nPublic tenant domain: localhost")
    print(f"First distributor domain: zergo001.localhost")
    print(f"\nTo access the system:")
    print(f"  Platform admin:  https://localhost:8000/")
    print(f"  Distributor app: https://zergo001.localhost:8000/")
    print(f"\nNote: For local testing, add to Windows hosts file:")
    print(f"  127.0.0.1  zergo001.localhost")


def _get_tenant_tables():
    """
    Get all table names that belong to tenant apps.
    These are the tables that need to be copied from public → tenant schema.
    """
    tables = []
    
    # shops app
    tables += [
        'shops', 'shop_visits', 'shop_access', 'shop_photo_history',
    ]
    
    # products app
    tables += [
        'companies', 'categories', 'products', 'stock_counts',
        'product_status_adjustments', 'product_status_adjustment_items',
        'stock_movements', 'fifo_cost_layers',
        'purchase_orders', 'purchase_order_items',
        'purchases', 'purchase_items',
        'purchase_returns', 'purchase_return_items', 'purchase_return_settlements',
        'company_accounts', 'company_transactions', 'company_payments',
        'payment_allocations',
        'foc_value_accounts', 'foc_value_transactions',
    ]
    
    # sales app
    tables += [
        'sales', 'sale_items',
        'bills', 'bill_items',
        'commission_rate_history', 'commission_transactions',
        'print_managers',
        'returns', 'return_items',
        'item_exchanges', 'exchange_items',
        'commission_payout_schedules', 'commission_payout_history',
        'user_commission_payouts',
        'foc_resets', 'foc_reset_transactions',
    ]
    
    # payments app
    tables += [
        'sales_account_settlements', 'settlement_attachments',
        'bad_debt_writeoffs',
    ]
    
    # business app
    tables += [
        'business_distributorprofile', 'business_bankaccount',
        'business_businessaddress',
    ]
    
    return tables


if __name__ == '__main__':
    run()
