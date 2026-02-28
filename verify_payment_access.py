import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from payments.models import OldPayment
from django.db import models
from decimal import Decimal

# Query payments
payments = OldPayment.objects.all()[:5]
total_amount = OldPayment.objects.aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

print("✅ Payment System Status")
print("=" * 50)
print(f"Total Payments: {OldPayment.objects.count()}")
print(f"Total Amount: Rs. {total_amount:,.2f}")
print(f"\nRecent Payments:")
for p in payments:
    print(f"  {p.payment_number} - {p.shop.shop_name if p.shop else 'N/A'} - Rs. {p.amount}")

print("\n✅ Database connection restored!")
print("   Website should now work correctly.")
