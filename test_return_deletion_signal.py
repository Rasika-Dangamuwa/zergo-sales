"""
Test if the pre_delete signal for Return is working
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, CommissionTransaction
from django.db.models.signals import pre_delete
from django.dispatch import receiver
import logging

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 80)
print("TESTING RETURN PRE_DELETE SIGNAL")
print("=" * 80)

# Check if signal receivers are registered
print("\n1. Checking registered signal receivers for Return pre_delete...")
receivers = pre_delete._live_receivers(Return)
print(f"Number of receivers registered: {len(list(receivers))}")

for idx, receiver in enumerate(receivers, 1):
    print(f"  Receiver {idx}: {receiver}")

# Check all signal receivers for Return
from django.db.models.signals import post_save, pre_save, post_delete

print("\n2. Checking all signal types for Return model:")
print(f"  pre_save receivers: {len(list(pre_save._live_receivers(Return)))}")
print(f"  post_save receivers: {len(list(post_save._live_receivers(Return)))}")
print(f"  pre_delete receivers: {len(list(pre_delete._live_receivers(Return)))}")
print(f"  post_delete receivers: {len(list(post_delete._live_receivers(Return)))}")

# Import the signal handlers explicitly
print("\n3. Importing commission_signals module...")
try:
    import sales.commission_signals as sig_module
    print(f"✅ Module imported successfully")
    print(f"Module attributes:")
    for attr in dir(sig_module):
        if not attr.startswith('_'):
            print(f"  - {attr}")
except Exception as e:
    print(f"❌ Error importing: {e}")

# Check again after explicit import
print("\n4. Re-checking pre_delete receivers after import...")
receivers = list(pre_delete._live_receivers(Return))
print(f"Number of receivers: {len(receivers)}")

if receivers:
    for idx, receiver in enumerate(receivers, 1):
        receiver_func = receiver[1]()
        if receiver_func:
            print(f"  Receiver {idx}:")
            print(f"    Function: {receiver_func.__name__}")
            print(f"    Module: {receiver_func.__module__}")
            print(f"    Doc: {receiver_func.__doc__[:100] if receiver_func.__doc__ else 'No doc'}")
else:
    print("⚠️ NO PRE_DELETE RECEIVERS FOUND!")

# Find an existing return that we can test with
print("\n5. Finding a return for testing...")
test_return = Return.objects.filter(return_status='pending').first()

if test_return:
    print(f"Found test return: {test_return.return_number}")
    print(f"  Shop: {test_return.shop.shop_code}")
    print(f"  Created by: {test_return.created_by.get_full_name()}")
    print(f"  Total: Rs. {test_return.total_amount}")
    print(f"  Status: {test_return.return_status}")
    
    # Check if commission transaction exists
    existing_commission = CommissionTransaction.objects.filter(
        transaction_type='return_processed',
        notes__contains=test_return.return_number
    ).first()
    
    if existing_commission:
        print(f"\n  ✅ Commission transaction exists:")
        print(f"     ID: {existing_commission.id}")
        print(f"     Commission: Rs. {existing_commission.commission_earned}")
    else:
        print(f"\n  ⚠️ No commission transaction found")
    
    # Don't actually delete - just simulate
    print("\n6. Simulating deletion (sending pre_delete signal)...")
    print("   (Not actually deleting - just testing signal)")
    
    # Manually trigger the signal to test
    pre_delete.send(sender=Return, instance=test_return)
    
    # Check if reversal was created
    reversal = CommissionTransaction.objects.filter(
        transaction_type='return_cancelled',
        notes__contains=test_return.return_number
    ).first()
    
    if reversal:
        print(f"\n✅ SUCCESS! Reversal transaction created:")
        print(f"   ID: {reversal.id}")
        print(f"   Commission: Rs. {reversal.commission_earned}")
        print(f"   Balance: Rs. {reversal.running_balance}")
        
        # Clean up the test reversal
        print("\n   Cleaning up test reversal...")
        reversal.delete()
        print("   ✅ Test reversal deleted")
    else:
        print(f"\n❌ FAILURE! No reversal transaction created")
        print("   The signal handler did not execute or failed")
else:
    print("❌ No pending returns found for testing")

print("\n" + "=" * 80)
print("DIAGNOSIS")
print("=" * 80)

if len(list(pre_delete._live_receivers(Return))) == 0:
    print("\n❌ ROOT CAUSE: No pre_delete signal receivers registered for Return!")
    print("\nPossible reasons:")
    print("1. The signal decorator might not be working")
    print("2. The signals module might not be imported at startup")
    print("3. There might be an import error preventing signal registration")
    print("\nSOLUTION: Check sales/apps.py ready() method and signal decorator syntax")
elif len(list(pre_delete._live_receivers(Return))) > 0:
    print(f"\n✅ Signal receiver is registered ({len(list(pre_delete._live_receivers(Return)))} receiver(s))")
    if reversal:
        print("✅ Signal handler executes correctly")
        print("\nThe issue might be:")
        print("1. Returns are being deleted via raw SQL")
        print("2. Returns are being deleted with skip_signals flag")
        print("3. Check the return_views.py deletion code")
    else:
        print("❌ Signal handler registered but not executing")
        print("\nThe issue might be:")
        print("1. Signal handler has an error that's being caught")
        print("2. Signal handler logic has a bug")
        print("3. Check Django logs for errors")

print("\n" + "=" * 80)
