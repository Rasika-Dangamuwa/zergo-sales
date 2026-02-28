"""
Investigate Return RN-20260125-016 (#90) - Cancelled but showing bill applications
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return
from payments.models import SalesAccountSettlement
from decimal import Decimal

# Get return 90
return_obj = Return.objects.filter(pk=90).select_related('shop', 'created_by').first()

if not return_obj:
    print("Return #90 not found")
    exit()

print(f"\n{'='*100}")
print(f"RETURN #{return_obj.pk}: {return_obj.return_number}")
print(f"{'='*100}")
print(f"Shop: {return_obj.shop.shop_name} ({return_obj.shop.shop_code})")
print(f"Created By: {return_obj.created_by.get_full_name()}")
print(f"Return Date: {return_obj.return_date}")
print(f"Settlement Method: {return_obj.get_settlement_method_display()} ({return_obj.settlement_method})")
print(f"Settlement Status: {return_obj.get_settlement_status_display()} ({return_obj.settlement_status})")
print()
print(f"Total Amount: Rs. {return_obj.total_amount:,.2f}")
print(f"Applied Amount: Rs. {return_obj.applied_amount:,.2f}")
print(f"Remaining: Rs. {return_obj.total_amount - return_obj.applied_amount:,.2f}")

# Get all settlements linked to this return
settlements = SalesAccountSettlement.objects.filter(
    return_ref=return_obj
).select_related('bill', 'shop').order_by('settlement_date')

print(f"\n{'='*100}")
print(f"BILL APPLICATIONS ({settlements.count()})")
print(f"{'='*100}")

for i, settlement in enumerate(settlements, 1):
    print(f"\n{i}. Settlement ID: {settlement.pk}")
    print(f"   Number: {settlement.settlement_number}")
    print(f"   Date: {settlement.settlement_date}")
    print(f"   Bill: {settlement.bill.bill_number if settlement.bill else 'N/A'}")
    print(f"   Amount: Rs. {settlement.amount:,.2f}")
    print(f"   Method: {settlement.get_settlement_method_display()} ({settlement.settlement_method})")
    print(f"   Status: {settlement.get_settlement_status_display()} ({settlement.settlement_status})")
    if settlement.notes:
        print(f"   Notes: {settlement.notes}")

print(f"\n{'='*100}")
print("ANALYSIS:")
print(f"{'='*100}")

if return_obj.settlement_status == 'cancelled':
    print("✅ Return is CANCELLED")
    
    active_settlements = settlements.filter(settlement_status__in=['pending', 'completed'])
    if active_settlements.exists():
        print(f"❌ PROBLEM: {active_settlements.count()} active bill applications still exist!")
        print("   These should have been auto-cancelled when return was cancelled.")
        
        print("\n🔧 FIX: Cancel these settlements and reverse bill payments")
        for settlement in active_settlements:
            print(f"   - {settlement.settlement_number}: Rs. {settlement.amount:,.2f} to {settlement.bill.bill_number}")
    else:
        print("✅ All bill applications are already cancelled (correct)")
    
    if return_obj.applied_amount > 0:
        print(f"❌ PROBLEM: applied_amount is Rs. {return_obj.applied_amount:,.2f} (should be 0 for cancelled returns)")
        print("🔧 FIX: Reset applied_amount to 0")
    else:
        print("✅ applied_amount is 0 (correct)")
else:
    print(f"Return status is '{return_obj.settlement_status}' (not cancelled)")

print()
