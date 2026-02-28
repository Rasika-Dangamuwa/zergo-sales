"""
Test shop balance display in create bill page
Verifies 4-tier balance calculation
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from shops.models import Shop
from payments.models import SalesAccountSettlement
from django.db.models import Sum
from decimal import Decimal

print("=" * 80)
print("SHOP BALANCE 4-TIER CALCULATION TEST")
print("=" * 80)

# Get a shop (Fahad Stores from the screenshot)
fahad_shop = Shop.objects.filter(shop_name__icontains='fahad').first()

if not fahad_shop:
    print("❌ Fahad Stores not found. Testing with first active shop...")
    fahad_shop = Shop.objects.filter(is_active=True).first()

if not fahad_shop:
    print("❌ No active shops found in database")
    exit()

print(f"\n📍 Testing Shop: {fahad_shop.shop_name}")
print(f"   Owner: {fahad_shop.owner_name}")
print(f"   Shop Code: {fahad_shop.shop_code}")
print("-" * 80)

# Calculate 4-tier balance (same logic as in views.py)

# Tier 1: Total Debt (from shop.current_balance)
tier1_total_debt = fahad_shop.current_balance
print(f"\n💰 Tier 1 - Total Debt (shop.current_balance)")
print(f"   Rs. {tier1_total_debt:,.2f}")

# Tier 2: Pending Verification (settlements awaiting approval)
pending_settlements = SalesAccountSettlement.objects.filter(
    shop=fahad_shop,
    settlement_status__in=['pending', 'pending_verification']
)
tier2_pending = pending_settlements.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
print(f"\n⏳ Tier 2 - Pending Verification")
print(f"   Count: {pending_settlements.count()} settlements")
print(f"   Amount: Rs. {tier2_pending:,.2f}")
if pending_settlements.count() > 0:
    print(f"   Details:")
    for settlement in pending_settlements[:5]:
        print(f"   - {settlement.settlement_number}: Rs. {settlement.amount:,.2f} ({settlement.settlement_method}, {settlement.settlement_status})")

# Tier 3: Cash Due Now (Total Debt - Pending)
tier3_cash_due = tier1_total_debt - tier2_pending
print(f"\n💵 Tier 3 - Cash Due Now (Tier 1 - Tier 2)")
print(f"   Rs. {tier3_cash_due:,.2f}")

# Tier 4: Total Paid (Cleared) - Completed settlements
completed_settlements = SalesAccountSettlement.objects.filter(
    shop=fahad_shop,
    settlement_status='completed'
)
tier4_total_cleared = completed_settlements.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
print(f"\n✅ Tier 4 - Total Paid (Cleared)")
print(f"   Count: {completed_settlements.count()} completed settlements")
print(f"   Amount: Rs. {tier4_total_cleared:,.2f}")

# Credit Limit
print(f"\n🎯 Credit Limit")
print(f"   Rs. {fahad_shop.credit_limit:,.2f}")
print(f"   Available Credit: Rs. {(fahad_shop.credit_limit - tier3_cash_due):,.2f}")

print("\n" + "=" * 80)
print("SUMMARY (What user will see in Create Bill page)")
print("=" * 80)
print(f"Total Debt:            Rs. {tier1_total_debt:,.2f}")
print(f"Pending Verification:  Rs. {tier2_pending:,.2f}")
print(f"Cash Due Now:          Rs. {tier3_cash_due:,.2f}  ⬅️ HIGHLIGHTED")
print(f"Total Paid (Cleared):  Rs. {tier4_total_cleared:,.2f}")
print(f"Credit Limit:          Rs. {fahad_shop.credit_limit:,.2f}")
print("=" * 80)

# Verify data integrity
print("\n🔍 Data Integrity Check:")
all_settlements = SalesAccountSettlement.objects.filter(shop=fahad_shop)
print(f"   Total settlements: {all_settlements.count()}")
print(f"   - Pending: {all_settlements.filter(settlement_status='pending').count()}")
print(f"   - Pending Verification: {all_settlements.filter(settlement_status='pending_verification').count()}")
print(f"   - Completed: {all_settlements.filter(settlement_status='completed').count()}")
print(f"   - Cancelled: {all_settlements.filter(settlement_status='cancelled').count()}")
print(f"   - Bounced: {all_settlements.filter(settlement_status='bounced').count()}")

print("\n✅ Test completed successfully!")
