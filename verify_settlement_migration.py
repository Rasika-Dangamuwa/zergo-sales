"""Verify settlement_status migration"""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Check Bills table
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'bills' 
        AND column_name IN ('payment_status', 'settlement_status')
        ORDER BY column_name
    """)
    print("=== BILLS TABLE COLUMNS ===")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    cursor.execute("""
        SELECT settlement_status, COUNT(*) 
        FROM bills 
        GROUP BY settlement_status 
        ORDER BY settlement_status
    """)
    print("\n=== BILLS SETTLEMENT STATUS VALUES ===")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} bills")
    
    # Check CommissionRecords table
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'commission_records' 
        AND column_name IN ('payment_status', 'settlement_status')
        ORDER BY column_name
    """)
    print("\n=== COMMISSION_RECORDS TABLE COLUMNS ===")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    cursor.execute("""
        SELECT settlement_status, COUNT(*) 
        FROM commission_records 
        GROUP BY settlement_status 
        ORDER BY settlement_status
    """)
    print("\n=== COMMISSION_RECORDS SETTLEMENT STATUS VALUES ===")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} records")
    
    # Check Sales table (may not exist)
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'sales'
        )
    """)
    sales_exists = cursor.fetchone()[0]
    print(f"\n=== SALES TABLE EXISTS: {sales_exists} ===")
    
    if sales_exists:
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'sales' 
            AND column_name IN ('payment_status', 'settlement_status')
            ORDER BY column_name
        """)
        print("SALES TABLE COLUMNS:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")

print("\n✓ Verification complete!")
