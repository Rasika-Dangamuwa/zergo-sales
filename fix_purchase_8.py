import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Purchase, PurchaseItem

try:
    purchase = Purchase.objects.get(pk=8)
    print(f"Fixing GRN: {purchase.grn_number}")
    
    items = purchase.items.all()
    print(f"Found {items.count()} items")
    
    for item in items:
        print(f"\nFixing item: {item.product.product_name}")
        print(f"  Current: marked_price={item.marked_price}, unit_price={item.unit_price}, line_total={item.line_total}")
        
        # Set the correct pricing from product master
        item.marked_price = item.product.marked_price
        item.shop_discount_percentage = item.product.discount_percentage  # Product.discount_percentage is the shop discount
        item.invoice_price = item.product.shop_price
        item.company_discount_percentage = item.product.company_discount_percentage
        
        # Save will auto-calculate unit_price, line_total, etc.
        item.save()
        
        item.refresh_from_db()
        print(f"  Fixed: marked_price={item.marked_price}, unit_price={item.unit_price}, line_total={item.line_total}")
    
    # Recalculate purchase totals
    print("\n--- Recalculating purchase totals ---")
    purchase.calculate_totals()
    purchase.refresh_from_db()
    
    print(f"\nFinal Totals:")
    print(f"Subtotal: Rs. {purchase.subtotal}")
    print(f"Discount Amount: Rs. {purchase.discount_amount}")
    print(f"Total Amount: Rs. {purchase.total_amount}")
    
    print("\n✓ GRN #8 fixed successfully!")
    
except Purchase.DoesNotExist:
    print("Purchase #8 not found!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
