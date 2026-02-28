"""
Check for products with negative stock
"""
import os
import sys
import django

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Product

print("\n" + "="*80)
print("PRODUCTS WITH NEGATIVE STOCK")
print("="*80)

negative_stock = Product.objects.filter(quantity_in_stock__lt=0, is_active=True).order_by('quantity_in_stock')

if negative_stock.exists():
    print(f"\n⚠️  Found {negative_stock.count()} products with NEGATIVE stock:")
    print("-" * 80)
    for p in negative_stock:
        print(f"\nID: {p.id}")
        print(f"Name: {p.product_name}")
        print(f"Size: {p.size}")
        print(f"Price: Rs. {p.marked_price}")
        print(f"Stock: {p.quantity_in_stock} ⚠️")
else:
    print("\n✅ No products with negative stock found")

print("\n" + "="*80)
print("250ML PRODUCTS (Rs. 100.00)")
print("="*80)

products_250ml = Product.objects.filter(
    size='250ML',
    marked_price=100,
    is_active=True
).order_by('product_name')

print(f"\nFound {products_250ml.count()} products:")
print("-" * 80)

for p in products_250ml:
    status = "⚠️ NEGATIVE" if p.quantity_in_stock < 0 else "✅" if p.quantity_in_stock > 0 else "⚡ ZERO"
    print(f"\n{status} ID: {p.id} - {p.product_name}")
    print(f"    Stock: {p.quantity_in_stock}")
    print(f"    Final Price: Rs. {p.final_price}")

print("\n" + "="*80)
