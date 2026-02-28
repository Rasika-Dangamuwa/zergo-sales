"""
Fix Return #90 - Reset applied_amount to 0 for cancelled return
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return
from decimal import Decimal

# Get return 90
return_obj = Return.objects.get(pk=90)

print(f"Return: {return_obj.return_number}")
print(f"Settlement Status: {return_obj.settlement_status}")
print(f"Applied Amount (before): Rs. {return_obj.applied_amount:,.2f}")

if return_obj.settlement_status == 'cancelled':
    return_obj.applied_amount = Decimal('0')
    return_obj.save()
    print(f"Applied Amount (after): Rs. {return_obj.applied_amount:,.2f}")
    print("✅ Fixed! Applied amount reset to 0")
else:
    print(f"❌ Return is not cancelled (status: {return_obj.settlement_status})")
