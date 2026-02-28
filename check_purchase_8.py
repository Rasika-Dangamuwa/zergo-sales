import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Purchase, PurchaseItem

try:
    purchase = Purchase.objects.get(pk=8)
    print(f"GRN Number: {purchase.grn_number}")
    print(f"Company: {purchase.company.company_name}")
    print(f"Status: {purchase.status}")
    print(f"\nFinancial Totals:")
    print(f"Subtotal: Rs. {purchase.subtotal}")
    print(f"Discount Amount: Rs. {purchase.discount_amount}")
    print(f"Total Amount: Rs. {purchase.total_amount}")
    
    items = purchase.items.all()
    print(f"\nNumber of Items: {items.count()}")
    
    if items.exists():
        print("\nItems:")
        for item in items:
            print(f"  - {item.product.product_name}: {item.quantity} bottles @ Rs. {item.unit_price} = Rs. {item.line_total}")
    
    # Recalculate totals
    print("\n--- Recalculating totals ---")
    purchase.calculate_totals()
    purchase.refresh_from_db()
    
    print(f"\nAfter Recalculation:")
    print(f"Subtotal: Rs. {purchase.subtotal}")
    print(f"Discount Amount: Rs. {purchase.discount_amount}")
    print(f"Total Amount: Rs. {purchase.total_amount}")
    
except Purchase.DoesNotExist:
    print("Purchase #8 not found!")
