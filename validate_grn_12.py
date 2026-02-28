import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Purchase, PurchaseReturn

print("=" * 80)
print("COMPREHENSIVE VALIDATION: GRN #12")
print("=" * 80)

try:
    grn = Purchase.objects.get(pk=12)
    
    # Basic Information
    print("\n1. BASIC INFORMATION")
    print("-" * 80)
    print(f"GRN Number: {grn.grn_number}")
    print(f"GRN Date: {grn.grn_date}")
    print(f"Invoice Date: {grn.invoice_date}")
    print(f"Supplier Invoice #: {grn.supplier_invoice_number}")
    print(f"Company: {grn.company.company_name}")
    print(f"Status: {grn.status}")
    print(f"Stock Updated: {grn.stock_updated}")
    print(f"Created By: {grn.created_by.username}")
    
    # Items Detail
    print("\n2. ITEMS DETAIL")
    print("-" * 80)
    items = grn.items.all()
    print(f"Total Items: {items.count()}")
    
    calculated_subtotal = Decimal('0')
    calculated_total = Decimal('0')
    
    for i, item in enumerate(items, 1):
        print(f"\nItem {i}: {item.product.product_name}")
        print(f"  Packs: {item.packs} × {item.bottles_per_pack} bottles")
        print(f"  Loose: {item.loose_bottles} bottles")
        print(f"  Total Quantity: {item.quantity} bottles")
        print(f"  FOC: {item.foc_quantity} bottles")
        print(f"  ---")
        print(f"  Marked Price: Rs. {item.marked_price:.2f}")
        print(f"  Shop Discount: {item.shop_discount_percentage}%")
        print(f"  Invoice Price (Shop Price): Rs. {item.invoice_price:.2f}")
        print(f"  Value Before Disc: Rs. {item.quantity * item.invoice_price:.2f}")
        print(f"  Company Discount: {item.company_discount_percentage}%")
        print(f"  Discount Amount: Rs. {(item.invoice_price * item.company_discount_percentage / 100) * item.quantity:.2f}")
        print(f"  Unit Price (Final): Rs. {item.unit_price:.2f}")
        print(f"  Line Total: Rs. {item.line_total:.2f}")
        
        # Calculate expected values
        expected_invoice_price = item.marked_price - (item.marked_price * item.shop_discount_percentage / 100)
        expected_unit_price = item.invoice_price - (item.invoice_price * item.company_discount_percentage / 100)
        expected_line_total = item.quantity * expected_unit_price
        
        # Validate
        if abs(item.invoice_price - expected_invoice_price) > 0.01:
            print(f"  ⚠️  WARNING: Invoice price mismatch! Expected: {expected_invoice_price:.2f}")
        if abs(item.unit_price - expected_unit_price) > 0.01:
            print(f"  ⚠️  WARNING: Unit price mismatch! Expected: {expected_unit_price:.2f}")
        if abs(item.line_total - expected_line_total) > 0.01:
            print(f"  ⚠️  WARNING: Line total mismatch! Expected: {expected_line_total:.2f}")
        
        calculated_total += item.line_total
    
    # Financial Summary
    print("\n3. FINANCIAL SUMMARY")
    print("-" * 80)
    print(f"Subtotal (from DB): Rs. {grn.subtotal:.2f}")
    print(f"Discount Amount (from DB): Rs. {grn.discount_amount:.2f}")
    print(f"Total Amount (from DB): Rs. {grn.total_amount:.2f}")
    print(f"Calculated Total (sum of line totals): Rs. {calculated_total:.2f}")
    
    if abs(grn.total_amount - calculated_total) > 0.01:
        print(f"⚠️  WARNING: Total mismatch! DB: {grn.total_amount:.2f}, Calculated: {calculated_total:.2f}")
    else:
        print("✓ Total amount matches sum of line totals")
    
    # Payment Status
    print("\n4. PAYMENT STATUS")
    print("-" * 80)
    print(f"Payment Status (DB): {grn.payment_status}")
    print(f"Amount Paid (DB): Rs. {grn.amount_paid:.2f}")
    
    # Check calculated properties
    print(f"Total Paid (calculated): Rs. {grn.total_paid:.2f}")
    print(f"Amount Outstanding (calculated): Rs. {grn.amount_outstanding:.2f}")
    print(f"Calculated Payment Status: {grn.calculated_payment_status}")
    if hasattr(grn, 'payment_percentage'):
        print(f"Payment Percentage: {grn.payment_percentage:.1f}%")
    
    # Payment Allocations
    allocations = grn.payment_allocations.all()
    print(f"\nPayment Allocations: {allocations.count()}")
    total_allocated = Decimal('0')
    for alloc in allocations:
        print(f"  - Payment {alloc.payment.payment_number}: Rs. {alloc.allocated_amount:.2f}")
        print(f"    Date: {alloc.payment.payment_date}")
        print(f"    Method: {alloc.payment.get_payment_method_display()}")
        total_allocated += alloc.allocated_amount
    
    if allocations.exists():
        print(f"\nTotal Allocated: Rs. {total_allocated:.2f}")
        if abs(total_allocated - grn.total_paid) > 0.01:
            print(f"⚠️  WARNING: Allocated amount doesn't match total_paid!")
        else:
            print("✓ Allocation total matches total_paid")
    
    # Returns Settled
    print("\n5. RETURNS SETTLED WITH THIS GRN")
    print("-" * 80)
    settled_returns = PurchaseReturn.objects.filter(replacement_grn=grn)
    print(f"Returns Count: {settled_returns.count()}")
    
    total_settled_amount = Decimal('0')
    for ret in settled_returns:
        print(f"\n  Return: {ret.pr_number}")
        print(f"  Return Date: {ret.return_date}")
        print(f"  Status: {ret.status}")
        print(f"  Total Amount: Rs. {ret.total_amount:.2f}")
        print(f"  Settled Amount: Rs. {ret.replacement_received_value or 0:.2f}")
        total_settled_amount += (ret.replacement_received_value or Decimal('0'))
    
    if settled_returns.exists():
        print(f"\nTotal Settled: Rs. {total_settled_amount:.2f}")
        remaining = grn.total_amount - total_settled_amount
        print(f"Remaining Available: Rs. {remaining:.2f}")
        
        if total_settled_amount < grn.total_amount:
            print("Status: ⚠️  Partially Settled")
        elif total_settled_amount >= grn.total_amount:
            print("Status: ✓ Fully Settled")
    
    # Stock Summary
    print("\n6. STOCK SUMMARY")
    print("-" * 80)
    summary = {
        'total_items': items.count(),
        'total_packs': sum(item.packs for item in items),
        'total_loose': sum(item.loose_bottles for item in items),
        'total_bottles': sum(item.quantity for item in items),
        'total_foc': sum(item.foc_quantity for item in items),
    }
    print(f"Total Items: {summary['total_items']}")
    print(f"Total Packs: {summary['total_packs']}")
    print(f"Total Loose Bottles: {summary['total_loose']}")
    print(f"Total Bottles: {summary['total_bottles']}")
    print(f"Total FOC: {summary['total_foc']}")
    
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    
except Purchase.DoesNotExist:
    print("❌ GRN #12 not found!")
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
