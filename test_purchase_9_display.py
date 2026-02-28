import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Purchase, PurchaseItem
from decimal import Decimal

try:
    purchase = Purchase.objects.select_related('company', 'created_by').get(pk=9)
    items = purchase.items.select_related('product').order_by('product__display_order', 'product__size', 'product__marked_price', 'product__product_name')
    
    print("=" * 80)
    print(f"GRN: {purchase.grn_number}")
    print(f"Company: {purchase.company.company_name}")
    print(f"Status: {purchase.get_status_display()}")
    print(f"Payment Status: {purchase.get_payment_status_display()}")
    print("=" * 80)
    
    print("\nITEMS:")
    print("-" * 80)
    for item in items:
        print(f"\nProduct: {item.product.size} {item.product.product_name}")
        print(f"  Pack Size: {item.bottles_per_pack} btl/case")
        print(f"  Packs: {item.packs}")
        print(f"  Loose: {item.loose_bottles}")
        print(f"  Quantity: {item.quantity} bottles")
        print(f"  FOC: {item.foc_quantity}")
        print(f"  Marked Price: Rs. {item.marked_price}")
        print(f"  Shop Discount %: {item.shop_discount_percentage}%")
        print(f"  Invoice Price (Shop Price): Rs. {item.invoice_price}")
        print(f"  Company Discount %: {item.company_discount_percentage}%")
        print(f"  Unit Price (Final): Rs. {item.unit_price}")
        
        # Calculate value before discount
        val_before_disc = item.line_total + item.discount_amount
        print(f"  Value Before Discount: Rs. {val_before_disc}")
        print(f"  Discount Amount: Rs. {item.discount_amount}")
        print(f"  Discount %: {item.discount_percentage}%")
        print(f"  Line Total: Rs. {item.line_total}")
    
    print("\n" + "=" * 80)
    print("TOTALS:")
    print(f"  Subtotal: Rs. {purchase.subtotal}")
    print(f"  Discount: Rs. {purchase.discount_amount}")
    print(f"  Total Amount: Rs. {purchase.total_amount}")
    print("=" * 80)
    
    print("\nPAYMENT INFO:")
    print(f"  Total Paid: Rs. {purchase.total_paid}")
    print(f"  Outstanding: Rs. {purchase.amount_outstanding}")
    print(f"  Calculated Payment Status: {purchase.calculated_payment_status}")
    print(f"  Payment Percentage: {purchase.payment_percentage}%")
    
    # Check for payment allocations
    allocations = purchase.payment_allocations.all()
    print(f"\nPayment Allocations: {allocations.count()}")
    
    # Check for transactions
    transactions = purchase.account_transactions.all()
    print(f"Account Transactions: {transactions.count()}")
    for txn in transactions:
        print(f"  - {txn.transaction_type}: Rs. {txn.amount} on {txn.transaction_date}")
    
except Purchase.DoesNotExist:
    print("Purchase #9 not found!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
