"""
Debug script to check 250ML Max Orange stock issue
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Product
from sales.models import BillItem
from decimal import Decimal

print("\n" + "="*80)
print("250ML MAX ORANGE STOCK INVESTIGATION")
print("="*80)

# Find the product
products = Product.objects.filter(
    product_name__icontains='250ML Max Orange',
    is_active=True
).order_by('product_name')

print(f"\nFound {products.count()} products matching '250ML Max Orange':")
print("-" * 80)

for product in products:
    print(f"\nProduct ID: {product.id}")
    print(f"Name: {product.product_name}")
    print(f"Size: {product.size}")
    print(f"Marked Price: Rs. {product.marked_price}")
    print(f"Final Price: Rs. {product.final_price}")
    print(f"Stock (quantity_in_stock): {product.quantity_in_stock}")
    print(f"Non-resaleable Stock: {product.non_resaleable_stock}")
    print(f"Total Stock: {product.total_stock}")
    print(f"Active: {product.is_active}")
    
    # Check recent bill items for this product
    recent_bills = BillItem.objects.filter(product=product).order_by('-id')[:5]
    
    if recent_bills:
        print(f"\nRecent 5 Bill Items:")
        for item in recent_bills:
            print(f"  Bill #{item.bill.bill_number} - Qty: {item.quantity}, FOC: {item.foc_quantity}, Status: {item.bill.bill_status}")
    
    # Check if there are any draft bills with this product
    draft_bills = BillItem.objects.filter(
        product=product,
        bill__bill_status='draft'
    )
    
    if draft_bills.exists():
        print(f"\n⚠️  DRAFT BILLS FOUND: {draft_bills.count()}")
        total_draft_qty = sum(item.quantity + item.foc_quantity for item in draft_bills)
        print(f"  Total Quantity in Draft Bills: {total_draft_qty}")
        for item in draft_bills:
            print(f"    Bill #{item.bill.bill_number} - Qty: {item.quantity}, FOC: {item.foc_quantity}")

print("\n" + "="*80)
