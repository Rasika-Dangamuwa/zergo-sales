import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import PurchaseReturn, PurchaseReturnItem

try:
    pr = PurchaseReturn.objects.get(pk=6)
    print(f"Fixing Purchase Return: {pr.pr_number}")
    
    items = pr.items.all()
    print(f"Found {items.count()} items")
    
    for item in items:
        print(f"\nFixing item: {item.product.product_name}")
        print(f"  Current: marked_price={item.marked_price}, unit_price={item.unit_price}, line_total={item.line_total}")
        
        # Set the correct pricing from product master
        item.marked_price = item.product.marked_price
        item.shop_discount_percentage = item.product.discount_percentage  # Product.discount_percentage is the shop discount
        item.invoice_price = item.product.shop_price
        item.company_discount_percentage = item.product.company_discount_percentage
        
        # Save will auto-calculate unit_price, line_total
        item.save()
        
        item.refresh_from_db()
        print(f"  Fixed: marked_price={item.marked_price}, unit_price={item.unit_price}, line_total={item.line_total}")
    
    # Recalculate purchase return totals
    print("\n--- Recalculating purchase return totals ---")
    pr.calculate_totals()
    pr.refresh_from_db()
    
    print(f"\nFinal Totals:")
    print(f"Subtotal: Rs. {pr.subtotal}")
    print(f"Discount Amount: Rs. {pr.discount_amount}")
    print(f"Total Amount: Rs. {pr.total_amount}")
    
    print("\n✓ Purchase Return #6 fixed successfully!")
    
except PurchaseReturn.DoesNotExist:
    print("Purchase Return #6 not found!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
