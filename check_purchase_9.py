import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Purchase, PurchaseItem

try:
    purchase = Purchase.objects.get(pk=9)
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
            print(f"  - {item.product.product_name}:")
            print(f"      Packs: {item.packs}, Loose: {item.loose_bottles}, Qty: {item.quantity}")
            print(f"      Marked Price: Rs. {item.marked_price}")
            print(f"      Unit Price: Rs. {item.unit_price}")
            print(f"      Line Total: Rs. {item.line_total}")
    
except Purchase.DoesNotExist:
    print("Purchase #9 not found!")
