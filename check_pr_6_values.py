import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import PurchaseReturn, PurchaseReturnItem

try:
    pr = PurchaseReturn.objects.get(pk=6)
    print(f"PR Number: {pr.pr_number}")
    print(f"Company: {pr.company.company_name}")
    print(f"Status: {pr.status}")
    print(f"\nFinancial Totals:")
    print(f"Subtotal: Rs. {pr.subtotal}")
    print(f"Discount Amount: Rs. {pr.discount_amount}")
    print(f"Total Amount: Rs. {pr.total_amount}")
    
    items = pr.items.all()
    print(f"\nNumber of Items: {items.count()}")
    
    if items.exists():
        print("\nItems:")
        for item in items:
            print(f"\n  Product: {item.product.product_name}")
            print(f"  Quantity: {item.quantity}")
            print(f"  Unit Price: Rs. {item.unit_price}")
            print(f"  Line Total: Rs. {item.line_total}")
    
    # Try to recalculate totals
    print("\n--- Recalculating totals ---")
    pr.calculate_totals()
    pr.refresh_from_db()
    
    print(f"\nAfter Recalculation:")
    print(f"Subtotal: Rs. {pr.subtotal}")
    print(f"Total Amount: Rs. {pr.total_amount}")
    
except PurchaseReturn.DoesNotExist:
    print("Purchase Return #6 not found!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
