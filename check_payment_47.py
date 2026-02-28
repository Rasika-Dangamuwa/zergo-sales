import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from payments.models import OldPayment

print("=" * 80)
print("CHECK Payment #47 Status")
print("=" * 80)

payment = OldPayment.objects.get(id=47)
print(f"\nPayment #{payment.id}")
print(f"Amount: Rs. {payment.amount}")
print(f"Method: {payment.payment_method}")
print(f"Status: {payment.status}")
print(f"Is Provisional: {payment.is_provisional}")
print(f"Return Ref: {payment.return_ref}")
if payment.return_ref:
    print(f"Return Status: {payment.return_ref.return_status}")

print(f"\n--- THE PROBLEM ---")
if payment.status != 'completed':
    print(f"⚠️ Payment status is '{payment.status}' but should be 'completed' for an approved return!")
    print(f"   Return status is '{payment.return_ref.return_status}'")
    print(f"   When return is approved, payment should also be completed")
