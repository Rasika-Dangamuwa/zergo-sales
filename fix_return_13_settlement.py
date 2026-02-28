"""
Fix settlement for return #13 that was settled with multiple GRNs but only last one was saved
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import PurchaseReturn, PurchaseReturnSettlement, Purchase
from django.contrib.auth import get_user_model

User = get_user_model()

# Get return #13
return_13 = PurchaseReturn.objects.get(pk=13)

print(f"Return: {return_13.pr_number}")
print(f"Status: {return_13.status}")
print(f"Total Amount: Rs. {return_13.total_amount}")
print(f"Approved Amount: Rs. {return_13.approved_amount}")
print(f"Current replacement_grn: {return_13.replacement_grn}")
print(f"Current replacement_received_value: Rs. {return_13.replacement_received_value}")

# Clear existing settlements
return_13.settlements.all().delete()
print("\nCleared existing settlements")

# You said you settled with GRN 18 and GRN 17
# Let's check if they exist
try:
    grn_18 = Purchase.objects.get(pk=18)
    grn_17 = Purchase.objects.get(pk=17)
    print(f"\nFound GRN-18: {grn_18.grn_number} - Rs. {grn_18.total_amount}")
    print(f"Found GRN-17: {grn_17.grn_number} - Rs. {grn_17.total_amount}")
    
    # Get admin user for created_by
    admin_user = User.objects.filter(user_type='admin').first()
    
    # Reset return status to allow re-settlement
    return_13.status = 'company_approved'
    return_13.settlement_status = 'pending'
    return_13.replacement_grn = None
    return_13.replacement_received_value = 0
    return_13.replacement_received = False
    return_13.save()
    
    print("\nReset return #13 status to 'company_approved'")
    print("You can now go to the page and settle it again using the settlement modal")
    print("The new system will properly track both GRN-18 and GRN-17")
    
except Purchase.DoesNotExist as e:
    print(f"\nError: One or both GRNs not found - {e}")
