"""
Update invoice prices for existing purchase return items
Run this once to fix existing data
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import PurchaseReturnItem
from decimal import Decimal

def update_return_invoice_prices():
    """Update invoice_price for all purchase return items"""
    
    items = PurchaseReturnItem.objects.all()
    updated_count = 0
    
    for item in items:
        # If invoice_price is 0 or None, calculate it
        if not item.invoice_price or item.invoice_price == 0:
            # Get marked price (use product's marked price if item doesn't have one)
            marked_price = item.marked_price if item.marked_price else item.product.marked_price
            
            # Get shop discount percentage (use product's if item doesn't have one)
            shop_discount_pct = item.shop_discount_percentage if item.shop_discount_percentage else item.product.discount_percentage
            
            # Get company discount percentage (use product's if item doesn't have one)
            company_discount_pct = item.company_discount_percentage if item.company_discount_percentage else item.product.company_discount_percentage
            
            # Calculate invoice price (marked price - shop discount)
            shop_discount_amount = (marked_price * shop_discount_pct) / 100
            invoice_price = marked_price - shop_discount_amount
            
            # Calculate unit price (invoice price - company discount)
            company_discount_amount = (invoice_price * company_discount_pct) / 100
            unit_price = invoice_price - company_discount_amount
            
            # Update the item
            item.marked_price = marked_price
            item.shop_discount_percentage = shop_discount_pct
            item.invoice_price = invoice_price
            item.company_discount_percentage = company_discount_pct
            item.unit_price = unit_price
            item.line_total = item.quantity * unit_price
            
            item.save()
            updated_count += 1
            
            print(f"Updated {item.purchase_return.pr_number} - {item.product.product_name}")
            print(f"  Marked: Rs.{marked_price}, Shop Disc: {shop_discount_pct}%")
            print(f"  Invoice: Rs.{invoice_price}, Company Disc: {company_discount_pct}%")
            print(f"  Unit: Rs.{unit_price}, Line Total: Rs.{item.line_total}")
            print()
    
    print(f"\nTotal items updated: {updated_count}")

if __name__ == '__main__':
    print("Updating invoice prices for purchase return items...")
    print("-" * 60)
    update_return_invoice_prices()
    print("-" * 60)
    print("Done!")
