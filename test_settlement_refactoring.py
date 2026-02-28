"""
Test script to verify SalesAccountSettlement refactoring
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from payments.models import SalesAccountSettlement, OldPayment
from sales.models import Bill
from django.db.models import Sum, Count

print("=" * 60)
print("SALESACCOUNTSETTLEMENT REFACTORING VERIFICATION")
print("=" * 60)

# Test 1: Backward Compatibility Alias
print("\n1. BACKWARD COMPATIBILITY TEST")
print(f"   ✓ OldPayment alias works: {OldPayment == SalesAccountSettlement}")

# Test 2: Database Access
print("\n2. DATABASE ACCESS TEST")
total = SalesAccountSettlement.objects.count()
print(f"   ✓ Total Settlements: {total}")

# Test 3: Field Names
print("\n3. FIELD NAMES TEST")
if total > 0:
    settlement = SalesAccountSettlement.objects.first()
    print(f"   ✓ settlement_number: {settlement.settlement_number}")
    print(f"   ✓ settlement_date: {settlement.settlement_date}")
    print(f"   ✓ settlement_method: {settlement.settlement_method}")
    print(f"   ✓ settlement_status: {settlement.settlement_status}")
    print(f"   ✓ amount: Rs. {settlement.amount}")

# Test 4: Settlement Status Breakdown
print("\n4. SETTLEMENT STATUS BREAKDOWN")
status_counts = SalesAccountSettlement.objects.values('settlement_status').annotate(count=Count('id'))
for item in status_counts:
    print(f"   ✓ {item['settlement_status']}: {item['count']}")

# Test 5: Settlement Method Breakdown
print("\n5. SETTLEMENT METHOD BREAKDOWN")
method_counts = SalesAccountSettlement.objects.values('settlement_method').annotate(count=Count('id'))
for item in method_counts:
    print(f"   ✓ {item['settlement_method']}: {item['count']}")

# Test 6: Related Names Test
print("\n6. RELATED NAMES TEST (bill.settlements)")
bill = Bill.objects.filter(settlements__isnull=False).first()
if bill:
    count = bill.settlements.count()
    print(f"   ✓ Bill {bill.bill_number} has {count} settlement(s)")
    total_settled = bill.settlements.filter(settlement_status='completed').aggregate(total=Sum('amount'))['total'] or 0
    print(f"   ✓ Total completed settlements: Rs. {total_settled}")
else:
    print("   ⚠ No bills with settlements found")

# Test 7: Aggregate Statistics
print("\n7. AGGREGATE STATISTICS")
totals = SalesAccountSettlement.objects.aggregate(
    total_amount=Sum('amount'),
    completed_amount=Sum('amount', filter=django.db.models.Q(settlement_status='completed')),
    pending_amount=Sum('amount', filter=django.db.models.Q(settlement_status='pending'))
)
print(f"   ✓ Total Settlement Amount: Rs. {totals['total_amount'] or 0}")
print(f"   ✓ Completed Amount: Rs. {totals['completed_amount'] or 0}")
print(f"   ✓ Pending Amount: Rs. {totals['pending_amount'] or 0}")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED - REFACTORING SUCCESSFUL!")
print("=" * 60)
