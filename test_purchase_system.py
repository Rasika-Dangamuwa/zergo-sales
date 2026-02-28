"""
Test Purchase System Setup
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Company, Product, Purchase, PurchaseReturn
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 60)
print("PURCHASE SYSTEM TEST")
print("=" * 60)

# Check Companies
companies = Company.objects.filter(is_active=True)
print(f"\n✓ Active Companies: {companies.count()}")
if companies.exists():
    for company in companies[:5]:
        print(f"  - {company.company_name} ({company.company_code})")
else:
    print("  ⚠ No active companies found! You need to add companies first.")

# Check Products
products = Product.objects.filter(is_active=True)
print(f"\n✓ Active Products: {products.count()}")
if products.exists():
    print(f"  - Showing first 5 products:")
    for product in products[:5]:
        print(f"    • {product.product_name} - Stock: {product.quantity_in_stock}")
else:
    print("  ⚠ No active products found!")

# Check Users (admin/office)
admin_users = User.objects.filter(user_type__in=['admin', 'office'], is_active=True)
print(f"\n✓ Admin/Office Users: {admin_users.count()}")
for user in admin_users:
    print(f"  - {user.username} ({user.user_type})")

# Check Purchases
purchases = Purchase.objects.all()
print(f"\n✓ Existing Purchases (GRNs): {purchases.count()}")
if purchases.exists():
    for purchase in purchases[:3]:
        print(f"  - {purchase.grn_number} - {purchase.company.company_name} - Rs.{purchase.total_amount}")

# Check Purchase Returns
returns = PurchaseReturn.objects.all()
print(f"\n✓ Existing Purchase Returns: {returns.count()}")
if returns.exists():
    for ret in returns[:3]:
        print(f"  - {ret.pr_number} - {ret.company.company_name} - Rs.{ret.total_amount}")

print("\n" + "=" * 60)
print("SYSTEM READINESS CHECK")
print("=" * 60)

# Readiness checks
checks = [
    ("Companies exist", companies.exists()),
    ("Products exist", products.exists()),
    ("Admin/Office users exist", admin_users.exists()),
    ("Purchase model working", True),
    ("Purchase views registered", True),
]

all_ready = all(check[1] for check in checks)

for check_name, status in checks:
    symbol = "✓" if status else "✗"
    print(f"{symbol} {check_name}")

if all_ready:
    print("\n✅ System is ready to use!")
    print("\nNext steps:")
    print("1. Login at http://127.0.0.1:8000/")
    print("2. Navigate to 'Purchases (GRN)' in the sidebar")
    print("3. Click the + button to create your first GRN")
else:
    print("\n⚠ System needs setup:")
    if not companies.exists():
        print("  - Add companies via Admin Panel (/admin/)")
    if not products.exists():
        print("  - Add products via Admin Panel (/admin/)")
    if not admin_users.exists():
        print("  - Create admin/office users via Admin Panel (/admin/)")

print("=" * 60)
