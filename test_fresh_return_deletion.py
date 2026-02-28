"""
Create a fresh return, then delete it to test signal
"""

import os
import django
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, ReturnItem, CommissionTransaction
from shops.models import Shop
from accounts.models import User
from products.models import Product
from django.utils import timezone
from decimal import Decimal

print("=" * 80)
print("FULL TEST: CREATE RETURN → DELETE RETURN → CHECK REVERSAL")
print("=" * 80)

# Get test data
sales_rep = User.objects.filter(user_type='sales_rep').first()
shop = Shop.objects.first()
product = Product.objects.first()

if not (sales_rep and shop and product):
    print("❌ Missing test data")
    exit(1)

# Step 1: Create a new return
print("\n1. Creating test return...")
test_return = Return(
    shop=shop,
    created_by=sales_rep,
    return_date=timezone.now(),
    return_reason='other',
    settlement_method='cash',
    settlement_status='unsettled',
    notes="TEST RETURN - Will be deleted"
)
test_return.save()  # This triggers post_save signal

print(f"✅ Created return: {test_return.return_number}")

# Add a return item
item = ReturnItem.objects.create(
    return_record=test_return,
    product=product,
    quantity=Decimal('1.00'),
    unit_price=Decimal('100.00'),
    line_total=Decimal('100.00')
)

# Update total
test_return.total_amount = Decimal('100.00')
test_return.save()

print(f"   Total Amount: Rs. {test_return.total_amount}")

# Step 2: Check if commission transaction was created
print("\n2. Checking if return_processed transaction was created...")
commission_txn = CommissionTransaction.objects.filter(
    transaction_type='return_processed',
    notes__contains=test_return.return_number
).first()

if commission_txn:
    print(f"✅ Commission transaction created:")
    print(f"   ID: {commission_txn.id}")
    print(f"   Return Amount: Rs. {commission_txn.return_amount}")
    print(f"   Commission: Rs. {commission_txn.commission_earned}")
else:
    print("❌ No commission transaction created")

# Step 3: Count return_cancelled before deletion
return_cancelled_before = CommissionTransaction.objects.filter(
    transaction_type='return_cancelled'
).count()

print(f"\n3. Return_cancelled count before deletion: {return_cancelled_before}")

# Step 4: DELETE THE RETURN
print(f"\n4. Deleting return {test_return.return_number}...")
print("   📋 Watch for signal logs:")
print("-" * 80)

return_number = test_return.return_number
test_return.delete()

print("-" * 80)
print(f"✅ Return {return_number} deleted")

# Step 5: Check if reversal was created
print(f"\n5. Checking for reversal transaction...")

return_cancelled_after = CommissionTransaction.objects.filter(
    transaction_type='return_cancelled'
).count()

print(f"   Return_cancelled count after deletion: {return_cancelled_after}")

if return_cancelled_after > return_cancelled_before:
    print(f"\n✅ SUCCESS! New reversal transaction created!")
    
    reversal = CommissionTransaction.objects.filter(
        transaction_type='return_cancelled',
        notes__contains=return_number
    ).first()
    
    if reversal:
        print(f"\n   Reversal Details:")
        print(f"   ID: {reversal.id}")
        print(f"   Return Amount: Rs. {reversal.return_amount}")
        print(f"   Commission: Rs. {reversal.commission_earned}")
        print(f"   Balance: Rs. {reversal.running_balance}")
        print(f"   Sales Rep: {reversal.sales_rep.get_full_name()}")
        
        print(f"\n6. ✅ SIGNAL HANDLER IS WORKING CORRECTLY!")
        
        # Clean up the test reversal
        print(f"\n7. Cleaning up test data...")
        reversal.delete()
        if commission_txn:
            commission_txn.delete()
        print(f"   ✅ Test data cleaned up")
    else:
        print(f"   ❌ Couldn't find reversal by return number")
else:
    print(f"\n❌ FAILURE! No new reversal created!")
    print("\nThe signal handler is NOT working!")

print("\n" + "=" * 80)
