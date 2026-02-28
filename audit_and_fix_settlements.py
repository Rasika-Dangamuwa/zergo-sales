import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill
from decimal import Decimal

print("=== BILL SETTLEMENT AUDIT & FIX ===\n")

# Get all confirmed bills
all_bills = Bill.objects.filter(bill_status='confirmed')
print(f"Total confirmed bills to audit: {all_bills.count()}\n")

mismatched_bills = []
fixed_bills = []

print("Scanning for paid_amount mismatches...\n")

for bill in all_bills:
    # Calculate expected paid amount from settlements
    completed_settlements = bill.settlements.filter(settlement_status='completed')
    expected_paid = sum(s.amount for s in completed_settlements)
    
    # Check if there's a mismatch
    if bill.paid_amount != expected_paid:
        mismatch_data = {
            'id': bill.id,
            'bill_number': bill.bill_number,
            'total_amount': bill.total_amount,
            'old_paid_amount': bill.paid_amount,
            'expected_paid_amount': expected_paid,
            'difference': bill.paid_amount - expected_paid,
            'old_balance': bill.balance_amount,
            'old_status': bill.settlement_status,
        }
        
        mismatched_bills.append(mismatch_data)
        
        print(f"MISMATCH FOUND - Bill {bill.bill_number} (ID: {bill.id})")
        print(f"  Total: Rs. {bill.total_amount}")
        print(f"  Old Paid: Rs. {bill.paid_amount} → Expected: Rs. {expected_paid}")
        print(f"  Difference: Rs. {mismatch_data['difference']}")
        print(f"  Old Balance: Rs. {bill.balance_amount}")
        print(f"  Settlements: {completed_settlements.count()} completed")
        
        # Fix the bill
        print(f"  → Recalculating totals...")
        bill.calculate_totals()
        
        print(f"  ✓ FIXED - New Paid: Rs. {bill.paid_amount}, New Balance: Rs. {bill.balance_amount}, Status: {bill.settlement_status}\n")
        
        mismatch_data['new_paid_amount'] = bill.paid_amount
        mismatch_data['new_balance'] = bill.balance_amount
        mismatch_data['new_status'] = bill.settlement_status
        fixed_bills.append(mismatch_data)

print("\n" + "="*60)
print("AUDIT SUMMARY")
print("="*60)
print(f"Total bills audited: {all_bills.count()}")
print(f"Bills with mismatches: {len(mismatched_bills)}")
print(f"Bills fixed: {len(fixed_bills)}")
print("="*60)

if fixed_bills:
    print("\nDETAILED FIX REPORT:")
    print("-" * 60)
    for bill_data in fixed_bills:
        print(f"\n{bill_data['bill_number']} (ID: {bill_data['id']})")
        print(f"  Total Amount: Rs. {bill_data['total_amount']}")
        print(f"  Paid Amount: Rs. {bill_data['old_paid_amount']} → Rs. {bill_data['new_paid_amount']}")
        print(f"  Balance: Rs. {bill_data['old_balance']} → Rs. {bill_data['new_balance']}")
        print(f"  Status: {bill_data['old_status']} → {bill_data['new_status']}")
        print(f"  Correction: {'+' if bill_data['difference'] > 0 else ''}{bill_data['difference']} removed from paid_amount")
else:
    print("\n✓ No mismatches found. All bills have accurate settlement calculations!")

print("\n" + "="*60)
print("AUDIT COMPLETE")
print("="*60)
