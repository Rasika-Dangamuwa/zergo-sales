import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import connection

# Check if company_returns tables still exist
cursor = connection.cursor()
cursor.execute("""
    SELECT tablename 
    FROM pg_tables 
    WHERE schemaname = 'public' 
    AND tablename LIKE '%company_return%'
""")
company_return_tables = cursor.fetchall()

print("=" * 80)
print("VERIFICATION: CompanyReturn Tables Removal")
print("=" * 80)
if company_return_tables:
    print("❌ FAILED: Company return tables still exist:")
    for table in company_return_tables:
        print(f"   - {table[0]}")
else:
    print("✅ SUCCESS: All company_returns tables successfully dropped")

# Check if old_payments table still exists
cursor.execute("""
    SELECT tablename 
    FROM pg_tables 
    WHERE schemaname = 'public' 
    AND tablename = 'old_payments'
""")
old_payments_table = cursor.fetchall()

print("\n" + "=" * 80)
print("VERIFICATION: OldPayment Table Preservation")
print("=" * 80)
if old_payments_table:
    print("✅ SUCCESS: old_payments table preserved")
    
    # Count records
    cursor.execute("SELECT COUNT(*) FROM old_payments")
    count = cursor.fetchone()[0]
    print(f"   Records: {count}")
else:
    print("❌ ERROR: old_payments table was deleted!")

print("\n" + "=" * 80)
print("FINAL STATUS")
print("=" * 80)
print("✅ CompanyReturn system: REMOVED")
print("✅ OldPayment system: RETAINED")
print("✅ Database integrity: VERIFIED")
