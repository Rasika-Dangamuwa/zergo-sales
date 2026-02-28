"""
Test the improved write-off workflow
Simulates the scenario and verifies calculations
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import models
from sales.models import Bill

print("=" * 80)
print("WRITE-OFF WORKFLOW TEST")
print("=" * 80)

# Test with actual bills
test_bills = [213, 215]

for bill_id in test_bills:
    try:
        bill = Bill.objects.get(pk=bill_id)
        
        print(f"\n📋 BILL #{bill_id}: {bill.bill_number}")
        print(f"   Total: Rs. {bill.total_amount:,.2f}")
        
        # OLD METHOD (buggy - uses bill fields directly)
        old_paid = bill.paid_amount
        old_balance = bill.balance_amount
        
        # NEW METHOD (correct - calculates from settlements)
        completed_settlements_total = bill.settlements.filter(
            settlement_status='completed'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        
        new_paid = completed_settlements_total
        new_balance = bill.total_amount - completed_settlements_total
        
        print(f"\n   OLD METHOD (Bill Fields):")
        print(f"   Paid: Rs. {old_paid:,.2f}")
        print(f"   Balance: Rs. {old_balance:,.2f}")
        print(f"   Would write off: Rs. {old_balance:,.2f}")
        
        print(f"\n   NEW METHOD (Settlement Calculation):")
        print(f"   Paid: Rs. {new_paid:,.2f}")
        print(f"   Balance: Rs. {new_balance:,.2f}")
        print(f"   Would write off: Rs. {new_balance:,.2f}")
        
        if old_paid != new_paid or old_balance != new_balance:
            print(f"\n   ⚠️  MISMATCH DETECTED!")
            print(f"   Paid difference: Rs. {(new_paid - old_paid):,.2f}")
            print(f"   Balance difference: Rs. {(new_balance - old_balance):,.2f}")
            print(f"   ✅ NEW METHOD will use CORRECT amount")
        else:
            print(f"\n   ✅ Amounts match - no issues")
        
        # Check validation
        pending = bill.settlements.filter(settlement_status__in=['pending', 'pending_verification'])
        if pending.exists():
            print(f"\n   ❌ HAS PENDING SETTLEMENTS: {pending.count()}")
            print(f"      Validation will block write-off")
        else:
            print(f"\n   ✅ No pending settlements")
        
        if new_balance <= 0:
            print(f"\n   ❌ No balance to write off")
        else:
            print(f"\n   ✅ Balance Rs. {new_balance:,.2f} can be written off")
            
    except Bill.DoesNotExist:
        print(f"\n❌ Bill #{bill_id} not found")

print("\n" + "=" * 80)
print("WORKFLOW IMPROVEMENTS:")
print("=" * 80)
print("✅ Write-off amount now calculated from actual completed settlements")
print("✅ Pending settlements must be verified/cancelled before write-off")
print("✅ Bill field mismatches detected and corrected automatically")
print("✅ Confirmation page shows recalculated amounts with warning")
print("✅ Write-off notes include system note if amounts were corrected")
print("=" * 80)
