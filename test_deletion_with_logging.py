"""
Test return deletion signal with proper logging
"""

import os
import django
import logging

# Setup logging BEFORE django.setup()
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, CommissionTransaction
from accounts.models import User

print("=" * 80)
print("TESTING RETURN DELETION WITH LOGGING")
print("=" * 80)

# Find a return that can be deleted
print("\n1. Finding a return that can be deleted...")
test_return = Return.objects.filter(
    is_verified=False  # Only unverified returns can be deleted
).exclude(
    settlement_method='return_adjustment'  # Exclude returns linked to settlements
).first()

if not test_return:
    print("❌ No suitable return found for testing")
    print("All returns are either verified or linked to settlements")
    exit(1)

print(f"✅ Found return: {test_return.return_number}")
print(f"   Shop: {test_return.shop.shop_code}")
print(f"   Created by: {test_return.created_by.get_full_name()}")
print(f"   Amount: Rs. {test_return.total_amount}")
print(f"   Verified: {test_return.is_verified}")

# Check if commission transaction exists
print("\n2. Checking for existing commission transaction...")
original_commission = CommissionTransaction.objects.filter(
    transaction_type='return_processed',
    notes__contains=test_return.return_number
).first()

if original_commission:
    print(f"✅ Found original commission transaction:")
    print(f"   ID: {original_commission.id}")
    print(f"   Return Amount: Rs. {original_commission.return_amount}")
    print(f"   Commission: Rs. {original_commission.commission_earned}")
    print(f"   Sales Rep: {original_commission.sales_rep.get_full_name()}")
else:
    print(f"❌ No commission transaction found")
    print("This return was created before commission tracking was implemented")

# Count return_cancelled before
return_cancelled_before = CommissionTransaction.objects.filter(
    transaction_type='return_cancelled'
).count()

print(f"\n3. Return_cancelled transactions before deletion: {return_cancelled_before}")

# DELETE THE RETURN
print(f"\n4. Deleting return {test_return.return_number}...")
print("   Watch for signal logging above...")
print("-" * 80)

return_number = test_return.return_number
return_total = test_return.total_amount

test_return.delete()

print("-" * 80)
print(f"✅ Return {return_number} deleted successfully")

# Check if reversal was created
print(f"\n5. Checking for reversal transaction...")

return_cancelled_after = CommissionTransaction.objects.filter(
    transaction_type='return_cancelled'
).count()

print(f"   Return_cancelled transactions after deletion: {return_cancelled_after}")

if return_cancelled_after > return_cancelled_before:
    print(f"\n✅ SUCCESS! Reversal transaction created!")
    
    reversal = CommissionTransaction.objects.filter(
        transaction_type='return_cancelled'
    ).order_by('-id').first()
    
    if reversal:
        print(f"\n   Reversal Details:")
        print(f"   ID: {reversal.id}")
        print(f"   Return Amount: Rs. {reversal.return_amount}")
        print(f"   Commission: Rs. {reversal.commission_earned}")
        print(f"   Balance: Rs. {reversal.running_balance}")
        print(f"   Sales Rep: {reversal.sales_rep.get_full_name()}")
        print(f"   Notes: {reversal.notes}")
else:
    print(f"\n❌ FAILURE! No reversal transaction created!")
    print("\nCheck the signal logging output above to see what went wrong")

print("\n" + "=" * 80)
