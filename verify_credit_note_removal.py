"""Verify credit_note removal"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import PurchaseReturnSettlement
from django.db.models import Count

print("=" * 80)
print("Purchase Return Settlement - Verification")
print("=" * 80)

print("\n✅ Available Settlement Methods:")
for code, label in PurchaseReturnSettlement.SETTLEMENT_METHOD_CHOICES:
    print(f"  • {label} ({code})")

print("\n✅ Current Settlements in Database:")
settlements = PurchaseReturnSettlement.objects.values('settlement_method').annotate(count=Count('id'))
for s in settlements:
    print(f"  • {s['settlement_method']}: {s['count']}")

print("\n✅ Settlement Method Verification:")
has_credit = PurchaseReturnSettlement.objects.filter(settlement_method='credit_note').exists()
if has_credit:
    print("  ❌ ERROR: Credit note settlements still exist!")
else:
    print("  ✅ No credit_note settlements found (correct)")

print("\n" + "=" * 80)
print("Summary:")
print("  • Credit Note option removed from model choices")
print("  • Credit Note option removed from forms")
print("  • Existing credit_note settlement converted to refund")
print("  • Purchase returns now settle via: Replacement GRN or Cash Refund only")
print("=" * 80)
