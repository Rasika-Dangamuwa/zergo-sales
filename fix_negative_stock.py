"""
Fix products with negative stock by resetting them to zero
"""
import os
import sys
import django

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Product
from django.db import transaction

print("\n" + "="*80)
print("FIXING PRODUCTS WITH NEGATIVE STOCK")
print("="*80)

negative_stock = Product.objects.filter(quantity_in_stock__lt=0).order_by('quantity_in_stock')

if negative_stock.exists():
    print(f"\n⚠️  Found {negative_stock.count()} products with NEGATIVE stock:")
    print("-" * 80)
    
    for p in negative_stock:
        print(f"\nID: {p.id}")
        print(f"Name: {p.product_name}")
        print(f"Size: {p.size}")
        print(f"Price: Rs. {p.marked_price}")
        print(f"Current Stock: {p.quantity_in_stock} ⚠️")
        print(f"Non-Resaleable: {p.non_resaleable_stock}")
    
    response = input("\n\nDo you want to reset these to ZERO stock? (yes/no): ")
    
    if response.lower() == 'yes':
        with transaction.atomic():
            count = 0
            for p in negative_stock:
                old_stock = p.quantity_in_stock
                p.quantity_in_stock = 0
                p.save()
                count += 1
                print(f"✅ {p.product_name}: {old_stock} → 0")
            
            print(f"\n✅ Successfully reset {count} products to zero stock")
    else:
        print("\n❌ No changes made")
else:
    print("\n✅ No products with negative stock found")

print("\n" + "="*80)
