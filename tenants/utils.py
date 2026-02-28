"""
Tenant Schema Utilities

Provides functions to create new tenant schemas by cloning
the existing schema structure (avoids migration replay issues).
"""

from django.db import connection
from django.apps import apps
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_shared_only_tables():
    """
    Dynamically compute tables that should ONLY exist in the public schema.
    These are tables from apps in SHARED_APPS but NOT in TENANT_APPS.
    """
    shared_only = {'distributors', 'domains'}
    for app_label in settings.SHARED_APPS:
        if app_label not in settings.TENANT_APPS:
            try:
                app_config = apps.get_app_config(app_label.split('.')[-1])
                for model in app_config.get_models():
                    shared_only.add(model._meta.db_table)
                    for m2m in model._meta.many_to_many:
                        if m2m.remote_field.through and hasattr(m2m.remote_field.through, '_meta'):
                            shared_only.add(m2m.remote_field.through._meta.db_table)
            except Exception:
                pass
    return shared_only


def create_tenant_schema(schema_name, copy_data=False):
    """
    Create a new tenant schema by cloning the public schema structure.
    
    Instead of running migrations from scratch (which can fail due to
    historical migration conflicts), this clones the existing table
    structure from the public schema.
    
    Args:
        schema_name: PostgreSQL schema name (e.g., 'dist_zergo001')
        copy_data: If True, also copies existing data from public schema.
                   Set False for new empty tenants, True for migrating existing data.
    
    Returns:
        dict with 'success', 'tables_created', 'errors' keys
    """
    result = {'success': False, 'tables_created': 0, 'errors': []}
    shared_only = get_shared_only_tables()
    
    try:
        with connection.cursor() as cursor:
            # Drop if exists from a failed previous attempt
            cursor.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            
            # Create the schema
            cursor.execute(f'CREATE SCHEMA "{schema_name}"')
            
            # Get all tables in public schema
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            all_tables = [row[0] for row in cursor.fetchall()]
            
            # Filter to tenant-only tables (exclude shared-only)
            tenant_tables = [t for t in all_tables if t not in shared_only]
            
            # Clone each table structure
            for table in tenant_tables:
                try:
                    cursor.execute(f'''
                        CREATE TABLE "{schema_name}"."{table}" 
                        (LIKE public."{table}" INCLUDING ALL)
                    ''')
                    
                    if copy_data:
                        cursor.execute(f'SELECT COUNT(*) FROM public."{table}"')
                        count = cursor.fetchone()[0]
                        if count > 0:
                            cursor.execute(f'''
                                INSERT INTO "{schema_name}"."{table}"
                                SELECT * FROM public."{table}"
                            ''')
                        
                        # Reset sequences
                        try:
                            cursor.execute(f"""
                                SELECT setval(
                                    pg_get_serial_sequence('"{schema_name}"."{table}"', 'id'),
                                    COALESCE((SELECT MAX(id) FROM "{schema_name}"."{table}"), 0) + 1,
                                    false
                                )
                            """)
                        except Exception:
                            pass
                    
                    result['tables_created'] += 1
                    
                except Exception as e:
                    result['errors'].append(f"{table}: {e}")
                    logger.warning(f"Failed to clone table {table}: {e}")
            
            # Clone foreign key constraints
            cursor.execute("""
                SELECT 
                    tc.table_name,
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
                AND tc.table_name NOT IN ({shared_list})
            """.format(
                shared_list=','.join(f"'{t}'" for t in shared_only)
            ))
            fk_rows = cursor.fetchall()
            
            for table_name, constraint_name, column_name, foreign_table, foreign_column in fk_rows:
                try:
                    # Check if FK already exists (from LIKE INCLUDING ALL)
                    cursor.execute(f"""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.table_constraints 
                            WHERE constraint_name = '{constraint_name}' 
                            AND table_schema = '{schema_name}'
                        )
                    """)
                    if cursor.fetchone()[0]:
                        continue
                    
                    # Shared-only tables → reference public schema
                    # Tenant tables → reference the new tenant schema
                    if foreign_table in shared_only:
                        ref_schema = 'public'
                        fk_name = f"{constraint_name}_xschema"
                    else:
                        ref_schema = schema_name
                        fk_name = constraint_name
                    
                    cursor.execute(f'''
                        ALTER TABLE "{schema_name}"."{table_name}"
                        ADD CONSTRAINT "{fk_name}"
                        FOREIGN KEY ("{column_name}")
                        REFERENCES "{ref_schema}"."{foreign_table}" ("{foreign_column}")
                        DEFERRABLE INITIALLY DEFERRED
                    ''')
                except Exception:
                    pass
            
            # Mark all migrations as applied
            cursor.execute("SELECT app, name FROM django_migrations ORDER BY app, name")
            migrations = cursor.fetchall()
            for app, name in migrations:
                try:
                    cursor.execute(f'''
                        INSERT INTO "{schema_name}"."django_migrations" (app, name, applied)
                        SELECT %s, %s, NOW()
                        WHERE NOT EXISTS (
                            SELECT 1 FROM "{schema_name}"."django_migrations" 
                            WHERE app = %s AND name = %s
                        )
                    ''', [app, name, app, name])
                except Exception:
                    pass
            
            result['success'] = True
            logger.info(f"Created tenant schema '{schema_name}' with {result['tables_created']} tables")
            
    except Exception as e:
        result['errors'].append(str(e))
        logger.error(f"Failed to create tenant schema '{schema_name}': {e}")
    
    return result


def delete_tenant_schema(schema_name):
    """Drop a tenant schema and all its data."""
    if schema_name == 'public':
        raise ValueError("Cannot delete the public schema!")
    
    with connection.cursor() as cursor:
        cursor.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
    
    logger.info(f"Deleted tenant schema '{schema_name}'")
