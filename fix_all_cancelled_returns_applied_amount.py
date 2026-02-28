"""
Find all cancelled returns with non-zero applied_amount and fix them
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return
from decimal import Decimal

# Find all cancelled returns with applied_amount > 0
cancelled_returns = Return.objects.filter(
    settlement_status='cancelled',
    applied_amount__gt=0
)

print(f"Found {cancelled_returns.count()} cancelled returns with non-zero applied_amount:")
print()

for ret in cancelled_returns:
    print(f"Return #{ret.pk}: {ret.return_number}")
    print(f"  Shop: {ret.shop.shop_name}")
    print(f"  Applied Amount: Rs. {ret.applied_amount:,.2f}")
    print(f"  Total Amount: Rs. {ret.total_amount:,.2f}")
    
    # Fix it
    ret.applied_amount = Decimal('0')
    ret.save()
    print(f"  ✅ Fixed - Applied amount reset to 0")
    print()

if cancelled_returns.count() == 0:
    print("✅ No cancelled returns with non-zero applied_amount found")
else:
    print(f"✅ Fixed {cancelled_returns.count()} returns")
