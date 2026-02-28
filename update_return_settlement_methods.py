"""
Update existing return transactions to use 'pending_settlement' instead of 'credit'
This prevents confusion when returns are later settled via cash refund.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import CompanyTransaction

print("=" * 80)
print("Updating Return Transaction Settlement Methods")
print("=" * 80)

# Find all return transactions with settlement_method='credit'
return_txns = CompanyTransaction.objects.filter(
    transaction_type='return',
    settlement_method='credit'
)

total_count = return_txns.count()
print(f"\nFound {total_count} return transactions with settlement_method='credit'")

if total_count == 0:
    print("✅ No transactions need updating.")
else:
    print("\nUpdating to 'pending_settlement'...")
    
    updated = return_txns.update(settlement_method='pending_settlement')
    
    print(f"\n✅ Updated {updated} transactions")
    print("\nVerification:")
    
    # Verify
    remaining = CompanyTransaction.objects.filter(
        transaction_type='return',
        settlement_method='credit'
    ).count()
    
    pending = CompanyTransaction.objects.filter(
        transaction_type='return',
        settlement_method='pending_settlement'
    ).count()
    
    print(f"  Returns with 'credit': {remaining}")
    print(f"  Returns with 'pending_settlement': {pending}")
    
    if remaining == 0:
        print("\n✅ All return transactions updated successfully!")
    else:
        print(f"\n⚠️ Warning: {remaining} transactions still have 'credit' method")

print("\n" + "=" * 80)
print("Update Complete")
print("=" * 80)
