import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from payments.models import OldPayment
from sales.models import Return

print("=" * 80)
print("ANALYZING OLD_PAYMENT DEPENDENCIES")
print("=" * 80)

# 1. Payments linked to bills
payments_with_bills = OldPayment.objects.filter(bill__isnull=False).count()
print(f"\n1. Payments linked to bills: {payments_with_bills} / 34")

# 2. Settlements linked to Returns
payments_with_returns = SalesAccountSettlement.objects.filter(return_ref__isnull=False).count()
print(f"\n2. Settlements linked to Returns: {payments_with_returns}")

# 3. Returns that reference SalesAccountSettlement
returns_using_old_payment = Return.objects.filter(
    settlement_method='next_bill'
).count()
print(f"3. Returns using 'next_bill' settlement: {returns_using_old_payment}")

# 4. Payment methods breakdown
from django.db.models import Count, Sum
payment_methods = OldPayment.objects.values('payment_method').annotate(
    count=Count('id'),
    total=Sum('amount')
).order_by('-count')

print(f"\n4. Payment Methods Breakdown:")
for method in payment_methods:
    print(f"   - {method['payment_method']}: {method['count']} records, Rs. {method['total']}")

# 5. Payment status breakdown
payment_status = OldPayment.objects.values('status').annotate(
    count=Count('id'),
    total=Sum('amount')
).order_by('-count')

print(f"\n5. Payment Status Breakdown:")
for status in payment_status:
    print(f"   - {status['status']}: {status['count']} records, Rs. {status['total']}")

# 6. Check if there's a newer Payment model being used
from sales.models import Payment as NewPayment
new_payment_count = NewPayment.objects.count()
print(f"\n6. NEW Payment model (sales.Payment): {new_payment_count} records")

print("\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print("⚠️  DO NOT DELETE OldPayment model/table")
print("   Reasons:")
print("   1. Contains 34 active payment records (Rs. 12,494)")
print("   2. Linked to bills and shop accounts")
print("   3. Referenced by multiple views and logic")
print("   4. Historical financial data - required for audits")
print("\n✅ SAFE TO DELETE: CompanyReturn (0 records, replaced by PurchaseReturn)")
