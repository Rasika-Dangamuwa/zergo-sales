"""
Clear All Purchase Data - Start Fresh
Removes all purchase-related records from database
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import (
    Purchase, PurchaseItem, PurchaseReturn, PurchaseReturnItem,
    PurchaseReturnSettlement, StockMovement, CompanyTransaction,
    CompanyPayment, PaymentAllocation, PurchaseOrder, PurchaseOrderItem,
    Product, CompanyAccount
)

print("=" * 80)
print("CLEAR ALL PURCHASE DATA")
print("=" * 80)

# Count records before deletion
print("\n📊 Current Data Counts:")
print("-" * 80)
grn_count = Purchase.objects.count()
grn_item_count = PurchaseItem.objects.count()
pr_count = PurchaseReturn.objects.count()
pr_item_count = PurchaseReturnItem.objects.count()
settlement_count = PurchaseReturnSettlement.objects.count()
po_count = PurchaseOrder.objects.count()
po_item_count = PurchaseOrderItem.objects.count()
payment_count = CompanyPayment.objects.count()
allocation_count = PaymentAllocation.objects.count()
transaction_count = CompanyTransaction.objects.count()
stock_movement_count = StockMovement.objects.filter(
    movement_type__in=['purchase', 'purchase_return']
).count()

print(f"GRNs (Purchases): {grn_count}")
print(f"GRN Items: {grn_item_count}")
print(f"Purchase Returns: {pr_count}")
print(f"Purchase Return Items: {pr_item_count}")
print(f"Return Settlements: {settlement_count}")
print(f"Purchase Orders: {po_count}")
print(f"Purchase Order Items: {po_item_count}")
print(f"Company Payments: {payment_count}")
print(f"Payment Allocations: {allocation_count}")
print(f"Company Transactions: {transaction_count}")
print(f"Stock Movements (purchase/return): {stock_movement_count}")

total_records = (grn_count + grn_item_count + pr_count + pr_item_count + 
                settlement_count + po_count + po_item_count + payment_count + 
                allocation_count + transaction_count + stock_movement_count)

print(f"\n🗑️  Total records to delete: {total_records}")

if total_records == 0:
    print("\n✅ No purchase data found. Database is already clean.")
    exit()

print("\n⚠️  WARNING: This will DELETE ALL purchase-related data!")
print("This includes:")
print("  • All GRNs and their items")
print("  • All purchase returns and settlements")
print("  • All purchase orders")
print("  • All company payments and allocations")
print("  • All company account transactions")
print("  • All purchase-related stock movements")
print("\n⚠️  STOCK QUANTITIES WILL NOT BE REVERSED!")
print("You may need to manually adjust stock levels after this operation.")

# Ask for confirmation
response = input("\n❓ Are you sure you want to delete all this data? (yes/no): ").strip().lower()

if response != 'yes':
    print("\n❌ Operation cancelled. No data was deleted.")
    exit()

print("\n🚀 Starting deletion...")
print("-" * 80)

# Delete in correct order (respecting foreign key constraints)
deleted = {}

# 1. Delete payment allocations first (references payments and purchases)
count = PaymentAllocation.objects.all().delete()[0]
deleted['Payment Allocations'] = count
print(f"✓ Deleted {count} payment allocations")

# 2. Delete company payments
count = CompanyPayment.objects.all().delete()[0]
deleted['Company Payments'] = count
print(f"✓ Deleted {count} company payments")

# 3. Delete purchase return settlements (references returns and GRNs)
count = PurchaseReturnSettlement.objects.all().delete()[0]
deleted['Purchase Return Settlements'] = count
print(f"✓ Deleted {count} purchase return settlements")

# 4. Delete purchase return items
count = PurchaseReturnItem.objects.all().delete()[0]
deleted['Purchase Return Items'] = count
print(f"✓ Deleted {count} purchase return items")

# 5. Delete purchase returns
count = PurchaseReturn.objects.all().delete()[0]
deleted['Purchase Returns'] = count
print(f"✓ Deleted {count} purchase returns")

# 6. Delete purchase items
count = PurchaseItem.objects.all().delete()[0]
deleted['Purchase Items'] = count
print(f"✓ Deleted {count} purchase items")

# 7. Delete purchases (GRNs)
count = Purchase.objects.all().delete()[0]
deleted['Purchases (GRNs)'] = count
print(f"✓ Deleted {count} purchases (GRNs)")

# 8. Delete purchase order items
count = PurchaseOrderItem.objects.all().delete()[0]
deleted['Purchase Order Items'] = count
print(f"✓ Deleted {count} purchase order items")

# 9. Delete purchase orders
count = PurchaseOrder.objects.all().delete()[0]
deleted['Purchase Orders'] = count
print(f"✓ Deleted {count} purchase orders")

# 10. Delete company transactions
count = CompanyTransaction.objects.all().delete()[0]
deleted['Company Transactions'] = count
print(f"✓ Deleted {count} company transactions")

# 11. Delete stock movements (purchase/return only)
count = StockMovement.objects.filter(
    movement_type__in=['purchase', 'purchase_return']
).delete()[0]
deleted['Stock Movements'] = count
print(f"✓ Deleted {count} stock movements (purchase/return)")

print("\n" + "=" * 80)
print("✅ DELETION COMPLETE")
print("=" * 80)

print("\n📋 Summary:")
total_deleted = sum(deleted.values())
for category, count in deleted.items():
    if count > 0:
        print(f"  • {category}: {count}")

print(f"\n🗑️  Total records deleted: {total_deleted}")

# Reset company account balances
print("\n💰 Resetting Company Account Balances...")
print("-" * 80)
accounts = CompanyAccount.objects.all()
for account in accounts:
    old_balance = account.current_balance
    account.update_balance()
    account.refresh_from_db()
    new_balance = account.current_balance
    
    if old_balance != new_balance:
        print(f"  {account.company.company_name}:")
        print(f"    Before: Rs. {old_balance:,.2f} → After: Rs. {new_balance:,.2f}")
    else:
        print(f"  {account.company.company_name}: Rs. {new_balance:,.2f} (unchanged)")

print(f"\n✅ All {accounts.count()} company account balances synced!")

# Show current product stock (for reference)
print("\n📦 Current Product Stock Levels:")
print("-" * 80)
products = Product.objects.all().order_by('product_name')[:10]
for product in products:
    print(f"  {product.product_name}: {product.quantity_in_stock} bottles")

if Product.objects.count() > 10:
    print(f"  ... and {Product.objects.count() - 10} more products")

print("\n⚠️  IMPORTANT NOTES:")
print("  1. Stock quantities were NOT automatically adjusted")
print("  2. If you need to reset stock to zero, run: python reset_all_stock.py")
print("  3. Company account balances have been recalculated and synced")
print("  4. You can now start creating fresh GRNs and purchase returns")

print("\n" + "=" * 80)
print("Ready to start fresh! 🎉")
print("=" * 80)
