import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from payments.models import OldPayment
from products.models import CompanyReturn

print("=" * 80)
print("CHECKING LEGACY TABLES DATA")
print("=" * 80)

# Check OldPayment
old_payment_count = OldPayment.objects.count()
print(f"\n1. OldPayment (old_payments table): {old_payment_count} records")
if old_payment_count > 0:
    print(f"   First created: {OldPayment.objects.order_by('created_at').first().created_at}")
    print(f"   Last created: {OldPayment.objects.order_by('-created_at').first().created_at}")
    print(f"   Total amount: Rs. {OldPayment.objects.aggregate(total=django.db.models.Sum('amount'))['total']}")

# Check CompanyReturn
company_return_count = CompanyReturn.objects.count()
print(f"\n2. CompanyReturn (company_returns table): {company_return_count} records")
if company_return_count > 0:
    print(f"   First created: {CompanyReturn.objects.order_by('created_at').first().created_at}")
    print(f"   Last created: {CompanyReturn.objects.order_by('-created_at').first().created_at}")
    print(f"   Total amount: Rs. {CompanyReturn.objects.aggregate(total=django.db.models.Sum('total_amount'))['total']}")

# Check PaymentAttachment
from payments.models import PaymentAttachment
attachment_count = PaymentAttachment.objects.count()
print(f"\n3. PaymentAttachment: {attachment_count} records")

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)
if old_payment_count == 0 and company_return_count == 0:
    print("✅ SAFE TO REMOVE: Both tables are empty")
else:
    print("⚠️  WARNING: Tables contain data!")
    print(f"   - OldPayment: {old_payment_count} records")
    print(f"   - CompanyReturn: {company_return_count} records")
    print("   - Consider data migration before removal")
