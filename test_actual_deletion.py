"""
Test actual return deletion to see if signal fires
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, CommissionTransaction, Bill
from shops.models import Shop
from accounts.models import User
from products.models import Product
from django.utils import timezone
from decimal import Decimal

print("=" * 80)
print("TESTING ACTUAL RETURN DELETION SIGNAL")
print("=" * 80)

# Create a test return that we can safely delete
print("\n1. Creating a test return...")

try:
    # Get test data
    sales_rep = User.objects.filter(user_type='sales_rep').first()
    shop = Shop.objects.first()
    
    if not sales_rep or not shop:
        print("❌ Missing test data (sales rep or shop)")
        exit(1)
    
    # Create a test return
    test_return = Return.objects.create(
        shop=shop,
        created_by=sales_rep,
        return_date=timezone.now(),
        return_status='pending',
        settlement_method='cash',
        settlement_status='unsettled',
        total_amount=Decimal('100.00')
    )
    
    print(f"✅ Created test return: {test_return.return_number}")
    print(f"   Shop: {shop.shop_code}")
    print(f"   Sales Rep: {sales_rep.get_full_name()}")
    print(f"   Amount: Rs. {test_return.total_amount}")
    
    # Check if commission transaction was created
    commission_txn = CommissionTransaction.objects.filter(
        transaction_type='return_processed',
        notes__contains=test_return.return_number
    ).first()
    
    if commission_txn:
        print(f"\n2. ✅ Commission transaction created:")
        print(f"   ID: {commission_txn.id}")
        print(f"   Commission: Rs. {commission_txn.commission_earned}")
        print(f"   Balance: Rs. {commission_txn.running_balance}")
    else:
        print(f"\n2. ⚠️ No commission transaction created (might be normal if return amount is from notes)")
    
    # Get count before deletion
    return_cancelled_count_before = CommissionTransaction.objects.filter(
        transaction_type='return_cancelled'
    ).count()
    
    print(f"\n3. Return_cancelled transactions before deletion: {return_cancelled_count_before}")
    
    # NOW DELETE THE RETURN
    print(f"\n4. Deleting test return {test_return.return_number}...")
    return_number = test_return.return_number
    return_amount = test_return.total_amount
    
    test_return.delete()
    
    print(f"   ✅ Return deleted")
    
    # Check if reversal was created
    print(f"\n5. Checking for reversal transaction...")
    
    return_cancelled_count_after = CommissionTransaction.objects.filter(
        transaction_type='return_cancelled'
    ).count()
    
    print(f"   Return_cancelled transactions after deletion: {return_cancelled_count_after}")
    
    if return_cancelled_count_after > return_cancelled_count_before:
        print(f"   ✅ New return_cancelled transaction created!")
        
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
            print(f"   Notes: {reversal.notes}")
            
            # Clean up
            print(f"\n6. Cleaning up test data...")
            reversal.delete()
            if commission_txn:
                commission_txn.delete()
            print(f"   ✅ Test data cleaned up")
        else:
            print(f"   ⚠️ return_cancelled transaction exists but couldn't find it by return number")
    else:
        print(f"   ❌ NO reversal transaction created!")
        print(f"\n   ROOT CAUSE FOUND: Signal handler is registered but NOT executing!")
        
        # Check Django logs or errors
        print(f"\n   Checking if there's an exception in the signal handler...")
        print(f"   The signal handler might be failing silently")
        
        # Clean up
        if commission_txn:
            print(f"\n6. Cleaning up test commission transaction...")
            commission_txn.delete()
            print(f"   ✅ Cleaned up")
        
except Exception as e:
    print(f"❌ Error during test: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

if return_cancelled_count_after > return_cancelled_count_before:
    print("\n✅ Signal handler is working correctly!")
    print("The issue must be elsewhere (perhaps returns deleted before signal was added)")
else:
    print("\n❌ Signal handler is NOT working!")
    print("\nPossible causes:")
    print("1. Signal handler has an exception that's being caught")
    print("2. Transaction atomic block is rolling back")
    print("3. Signal handler logic has a bug")
    print("\nNext step: Add debug logging to the signal handler")

print("\n" + "=" * 80)
