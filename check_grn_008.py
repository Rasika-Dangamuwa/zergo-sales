"""
Check GRN-20260118-008 and its transactions
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Purchase, CompanyTransaction

print("=" * 120)
print("CHECKING GRN-20260118-008")
print("=" * 120)

try:
    grn = Purchase.objects.get(grn_number='GRN-20260118-008')
    print(f"\n✅ GRN Found: {grn.grn_number}")
    print(f"  Company: {grn.company.company_name}")
    print(f"  Amount: Rs. {grn.total_amount:,.2f}")
    print(f"  Status: {grn.status}")
    print(f"  Stock Updated: {grn.stock_updated}")
    
    # Check if it created a transaction
    grn_txns = CompanyTransaction.objects.filter(purchase=grn)
    print(f"\n  Company Transactions:")
    if grn_txns.exists():
        for txn in grn_txns:
            print(f"    ✅ {txn.reference_number}: {txn.transaction_type} - {txn.amount:+,.2f}")
    else:
        print(f"    ❌ No transaction found!")
        print(f"    ⚠️  Problem: GRN status='{grn.status}' but no transaction exists")
        if grn.status == 'received':
            print(f"    💡 Solution: Transaction should have been auto-created when status='received'")
    
except Purchase.DoesNotExist:
    print(f"\n❌ GRN-20260118-008 not found!")
    print(f"   Checking what GRNs exist...")
    
    grns = Purchase.objects.all().order_by('-grn_number')[:10]
    print(f"\n   Latest GRNs:")
    for grn in grns:
        print(f"     {grn.grn_number} - Rs. {grn.total_amount:,.2f} - {grn.status}")

print("\n" + "=" * 120)
