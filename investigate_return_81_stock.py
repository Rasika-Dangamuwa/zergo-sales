"""
Deep investigation of Return 81 stock effects
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, ReturnItem
from products.models import StockMovement, Product
from django.db.models import Sum

print("=" * 80)
print("RETURN 81 - DEEP STOCK INVESTIGATION")
print("=" * 80)

try:
    return_obj = Return.objects.get(pk=81)
    
    print(f"\n📋 RETURN DETAILS:")
    print(f"   Return Number: {return_obj.return_number}")
    print(f"   Shop: {return_obj.shop.shop_name}")
    print(f"   Created By: {return_obj.created_by.get_full_name()}")
    print(f"   Return Date: {return_obj.return_date}")
    print(f"   Total Amount: Rs. {return_obj.total_amount}")
    print(f"   Settlement Status: {return_obj.settlement_status}")
    print(f"   Settlement Method: {return_obj.settlement_method}")
    print(f"   Is Verified: {return_obj.is_verified}")
    print(f"   Created At: {return_obj.created_at}")
    
    # Get return items
    items = ReturnItem.objects.filter(return_ref=return_obj).select_related('product')
    
    print(f"\n📦 RETURN ITEMS ({items.count()} items):")
    print("-" * 80)
    
    for item in items:
        print(f"\n   Product: {item.product.product_name}")
        print(f"   Quantity Returned: {item.quantity}")
        print(f"   FOC Returned: {item.foc_quantity}")
        print(f"   Total Bottles: {item.quantity + item.foc_quantity}")
        print(f"   Unit Price: Rs. {item.unit_price}")
        
        # Check current stock
        print(f"\n   📊 CURRENT STOCK STATUS:")
        print(f"      Current Stock in DB: {item.product.quantity_in_stock}")
        
        # Get all stock movements for this product related to this return
        movements = StockMovement.objects.filter(
            product=item.product,
            reference_number=return_obj.return_number
        ).order_by('created_at')
        
        print(f"\n   📝 STOCK MOVEMENTS (Return {return_obj.return_number}):")
        if movements.exists():
            for mov in movements:
                print(f"      - Date: {mov.created_at}")
                print(f"        Type: {mov.movement_type}")
                print(f"        Quantity Change: {mov.quantity:+d}")
                print(f"        Previous Stock: {mov.previous_quantity}")
                print(f"        New Stock: {mov.new_quantity}")
                print(f"        Notes: {mov.notes}")
                print()
        else:
            print(f"      ⚠️ NO STOCK MOVEMENTS FOUND!")
        
        # Get ALL stock movements for this product (last 10)
        all_movements = StockMovement.objects.filter(
            product=item.product
        ).order_by('-created_at')[:10]
        
        print(f"\n   📜 RECENT STOCK MOVEMENTS (Last 10 for {item.product.product_name}):")
        for mov in all_movements:
            print(f"      - {mov.created_at.strftime('%Y-%m-%d %H:%M')} | {mov.movement_type:20} | Qty: {mov.quantity:+4d} | Prev: {mov.previous_quantity:4d} | New: {mov.new_quantity:4d} | Ref: {mov.reference_number}")
        
        # Calculate expected stock if return was processed
        print(f"\n   🔍 STOCK ANALYSIS:")
        
        # Sum all stock movements for this product
        total_movements = StockMovement.objects.filter(
            product=item.product
        ).aggregate(
            total_qty=Sum('quantity')
        )
        
        # Get initial stock from first movement
        first_movement = StockMovement.objects.filter(
            product=item.product
        ).order_by('created_at').first()
        
        if first_movement:
            initial_stock = first_movement.previous_quantity
            calculated_stock = initial_stock + (total_movements['total_qty'] or 0)
            print(f"      Initial stock (from first movement): {initial_stock}")
            print(f"      Total movements sum: {total_movements['total_qty'] or 0}")
            print(f"      Calculated from movements: {calculated_stock}")
            print(f"      Current DB stock: {item.product.quantity_in_stock}")
            print(f"      Difference: {item.product.quantity_in_stock - calculated_stock}")
            
            if item.product.quantity_in_stock != calculated_stock:
                print(f"      ⚠️ WARNING: Stock mismatch detected!")
            else:
                print(f"      ✅ Stock matches movement history")
        else:
            print(f"      ⚠️ No stock movements found for this product")
    
    # Check if return was cancelled and stock reversed
    print(f"\n" + "=" * 80)
    print("RETURN STATUS & STOCK REVERSAL CHECK:")
    print("=" * 80)
    
    if return_obj.settlement_status == 'cancelled':
        print(f"   ⚠️ This return is CANCELLED")
        print(f"   Expected: Stock should be REVERSED (subtracted back)")
        
        # Check for reversal movements
        reversal_movements = StockMovement.objects.filter(
            reference_number=return_obj.return_number,
            notes__icontains='cancelled'
        )
        
        if reversal_movements.exists():
            print(f"\n   ✅ FOUND {reversal_movements.count()} REVERSAL MOVEMENTS:")
            for mov in reversal_movements:
                print(f"      - Product: {mov.product.product_name}")
                print(f"        Quantity Change: {mov.quantity:+d}")
                print(f"        Previous: {mov.previous_quantity} → New: {mov.new_quantity}")
                print(f"        Notes: {mov.notes}")
        else:
            print(f"\n   ❌ NO REVERSAL MOVEMENTS FOUND!")
            print(f"      This means stock was added but NOT reversed when cancelled")
            print(f"      ISSUE: Stock may be inflated!")
    else:
        print(f"   ✅ This return is ACTIVE (status: {return_obj.settlement_status})")
        print(f"   Expected: Stock should be ADDED (returned items back to inventory)")
    
    print("\n" + "=" * 80)

except Return.DoesNotExist:
    print(f"\n❌ Return 81 not found!")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
