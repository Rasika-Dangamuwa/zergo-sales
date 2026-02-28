import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'returns'
        ORDER BY ordinal_position;
    """)
    
    columns = cursor.fetchall()
    
    print("\n=== RETURNS TABLE COLUMNS ===\n")
    print(f"{'Column Name':<30} {'Data Type':<20} {'Nullable'}")
    print("=" * 70)
    
    for col in columns:
        print(f"{col[0]:<30} {col[1]:<20} {col[2]}")
    
    print(f"\n\nTotal columns: {len(columns)}")
    
    # Check for specific problematic fields
    print("\n=== CHECKING PROBLEMATIC FIELDS ===\n")
    column_names = [col[0] for col in columns]
    
    problematic_fields = [
        'approved_by_id', 'approved_at', 'cash_paid_by_id', 'return_status', 
        'field_cash_given', 'field_cash_amount', 'field_cash_given_at',
        'field_cash_notes', 'field_receipt_number'
    ]
    
    for field in problematic_fields:
        exists = field in column_names
        status = "✓ EXISTS" if exists else "✗ MISSING"
        print(f"{field:<30} {status}")
