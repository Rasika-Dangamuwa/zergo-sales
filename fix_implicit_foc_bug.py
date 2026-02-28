"""
Fix the incorrect implicit FOC transaction FOC-20260127-012
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import FOCValueTransaction
from decimal import Decimal

def fix_implicit_foc():
    """Fix FOC-20260127-012"""
    print("\n" + "="*80)
    print("FIXING IMPLICIT FOC TRANSACTION")
    print("="*80 + "\n")
    
    try:
        txn = FOCValueTransaction.objects.get(transaction_number='FOC-20260127-012')
        
        print(f"Transaction: {txn.transaction_number}")
        print(f"Product: {txn.product.product_name}")
        print(f"\nCurrent Values:")
        print(f"  FOC Quantity: {txn.foc_quantity}")
        print(f"  Shop Price: Rs. {txn.shop_price_at_time:,.2f}")
        print(f"  FOC Value: Rs. {txn.foc_value:,.2f} ❌")
        
        # Get bill item to recalculate
        bill_item = txn.bill_item
        shop_price = txn.shop_price_at_time
        unit_price = bill_item.unit_price
        quantity = bill_item.quantity
        
        # Correct calculation
        implicit_foc_per_unit = shop_price - unit_price
        correct_foc_value = quantity * implicit_foc_per_unit
        
        print(f"\nCorrect Calculation:")
        print(f"  Shop Price: Rs. {shop_price:,.2f}")
        print(f"  Sold At: Rs. {unit_price:,.2f}")
        print(f"  Discount per Unit: Rs. {implicit_foc_per_unit:,.2f}")
        print(f"  Quantity: {quantity}")
        print(f"  Correct FOC Value: {quantity} × Rs. {implicit_foc_per_unit:,.2f} = Rs. {correct_foc_value:,.2f} ✅")
        
        # Update the transaction
        txn.foc_value = correct_foc_value
        txn.notes = f'Sold at Rs.{unit_price} (shop_price: Rs.{shop_price}) - Discount: Rs.{implicit_foc_per_unit}/unit [CORRECTED]'
        
        # Save with update_fields to bypass the save() auto-calculation
        txn.save(update_fields=['foc_value', 'notes'])
        
        print(f"\n✅ Transaction updated!")
        print(f"   Old FOC Value: Rs. 900.00")
        print(f"   New FOC Value: Rs. {correct_foc_value:,.2f}")
        
        # Update account balance
        txn.foc_account.update_balance()
        account = txn.foc_account
        
        print(f"\n📊 Updated Account Balance:")
        print(f"   Company: {account.company.company_name}")
        print(f"   FOC Received: Rs. {account.total_foc_received_value:,.2f}")
        print(f"   FOC Given: Rs. {account.total_foc_given_value:,.2f}")
        print(f"   Net FOC: Rs. {account.net_foc_value:,.2f}")
        print(f"   Utilization: {account.foc_utilization_percentage:.2f}%")
        
    except FOCValueTransaction.DoesNotExist:
        print("❌ Transaction not found")


if __name__ == '__main__':
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  FIX IMPLICIT FOC CALCULATION BUG".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    fix_implicit_foc()
    
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  FIX COMPLETE".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80 + "\n")
