"""
View all products in 250ML category with their stock levels
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
print("ALL 250ML PRODUCTS - STOCK REPORT")
print("="*80)

products_250ml = Product.objects.filter(
    size='250ML',
    is_active=True
).order_by('marked_price', 'product_name')

print(f"\nTotal Products Found: {products_250ml.count()}")
print("-" * 80)

for p in products_250ml:
    # Stock status indicator
    if p.quantity_in_stock < 0:
        status = f"⚠️  NEGATIVE ({p.quantity_in_stock})"
        mark = "<<<< THIS IS THE PROBLEM!"
    elif p.quantity_in_stock == 0:
        status = "⚡ OUT OF STOCK"
        mark = ""
    elif p.quantity_in_stock < 100:
        status = f"⚠️  LOW ({p.quantity_in_stock})"
        mark = ""
    else:
        status = f"✅ IN STOCK ({p.quantity_in_stock})"
        mark = ""
    
    print(f"\n{status} {mark}")
    print(f"  ID: {p.id}")
    print(f"  Name: {p.product_name}")
    print(f"  Price: Rs. {p.marked_price}")
    print(f"  Final Price: Rs. {p.final_price}")
    print(f"  Stock: {p.quantity_in_stock}")
    print(f"  Non-Resaleable: {p.non_resaleable_stock}")
    print(f"  Company: {p.company.name if p.company else 'N/A'}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

negative = products_250ml.filter(quantity_in_stock__lt=0)
zero = products_250ml.filter(quantity_in_stock=0)
low = products_250ml.filter(quantity_in_stock__gt=0, quantity_in_stock__lt=100)
normal = products_250ml.filter(quantity_in_stock__gte=100)

print(f"\n⚠️  Negative Stock: {negative.count()}")
print(f"⚡ Zero Stock: {zero.count()}")
print(f"⚠️  Low Stock (< 100): {low.count()}")
print(f"✅ Normal Stock (>= 100): {normal.count()}")

if negative.exists():
    print(f"\n⚠️  ACTION REQUIRED: Fix negative stock products!")
    print(f"   Run: python fix_negative_stock.py")

print("\n" + "="*80)
