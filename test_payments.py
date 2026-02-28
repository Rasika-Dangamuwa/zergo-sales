import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from payments.models import OldPayment

# Test query
count = OldPayment.objects.count()
print(f"✅ SUCCESS! OldPayment table accessible")
print(f"   Records: {count}")
print(f"   Django can now query old_payments table")
