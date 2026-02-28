"""
Final verification: Check if there are any actual data integrity issues
or if this is purely a UX/display issue
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction, Bill
from payments.models import SalesAccountSettlement
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 80)
print("DATA INTEGRITY VERIFICATION")
print("=" * 80)
print()

# Check 1: Do all commission transactions have correct balances?
print("CHECK 1: Commission Transaction Balance Integrity")
print("-" * 80)

users = User.objects.filter(commission_transactions__isnull=False).distinct()
all_correct = True

for user in users:
    txns = CommissionTransaction.objects.filter(sales_rep=user).order_by('transaction_date', 'id')
    prev_balance = None
    errors = 0
    
    for txn in txns:
        if prev_balance is not None:
            expected = prev_balance + txn.commission_earned
            if abs(expected - txn.running_balance) > 0.01:
                errors += 1
                all_correct = False
    
        prev_balance = txn.running_balance
    
    if errors > 0:
        print(f"❌ {user.username}: {errors} balance mismatches found")
    else:
        print(f"✓ {user.username}: All {txns.count()} transactions have correct balances")

if all_correct:
    print("\n✓ PASS: All commission balances are mathematically correct")
else:
    print("\n❌ FAIL: Some commission balances are incorrect")

print()

# Check 2: Do all settlements have correct commission transactions?
print("CHECK 2: Settlement-Commission Linkage")
print("-" * 80)

settlements = SalesAccountSettlement.objects.filter(
    settlement_date__gte='2026-01-25'
).order_by('settlement_date')

linkage_issues = 0

for settlement in settlements:
    txns = CommissionTransaction.objects.filter(settlement=settlement)
    
    expected_count = 2 if settlement.settlement_status == 'cancelled' else 1
    
    if txns.count() != expected_count:
        print(f"❌ {settlement.settlement_number} ({settlement.settlement_status}): "
              f"Expected {expected_count} transactions, found {txns.count()}")
        linkage_issues += 1

if linkage_issues == 0:
    print(f"✓ PASS: All {settlements.count()} settlements have correct commission transactions")
else:
    print(f"❌ FAIL: {linkage_issues} settlements have linkage issues")

print()

# Check 3: Do cancelled settlements have reversal transactions?
print("CHECK 3: Cancelled Settlement Reversals")
print("-" * 80)

cancelled = SalesAccountSettlement.objects.filter(
    settlement_status='cancelled',
    settlement_date__gte='2026-01-25'
)

missing_reversals = 0

for settlement in cancelled:
    payment_received = CommissionTransaction.objects.filter(
        settlement=settlement,
        transaction_type='payment_received'
    ).first()
    
    payment_cancelled = CommissionTransaction.objects.filter(
        settlement=settlement,
        transaction_type='payment_cancelled'
    ).first()
    
    if payment_received and not payment_cancelled:
        print(f"❌ {settlement.settlement_number}: Has payment_received but no payment_cancelled")
        missing_reversals += 1
    elif payment_cancelled and not payment_received:
        print(f"⚠️  {settlement.settlement_number}: Has payment_cancelled but no payment_received (unusual)")

if missing_reversals == 0:
    print(f"✓ PASS: All {cancelled.count()} cancelled settlements have proper reversals")
else:
    print(f"❌ FAIL: {missing_reversals} cancelled settlements missing reversals")

print()

# Check 4: Bill payment amounts vs settlements
print("CHECK 4: Bill Paid Amounts vs Completed Settlements")
print("-" * 80)

bills = Bill.objects.filter(settlements__isnull=False).distinct()
amount_mismatches = 0

for bill in bills:
    completed_settlements = bill.settlements.filter(settlement_status='completed')
    expected_paid = sum(s.amount for s in completed_settlements)
    
    if abs(bill.paid_amount - expected_paid) > 0.01:
        print(f"❌ Bill #{bill.pk} ({bill.bill_number}): "
              f"Paid amount {bill.paid_amount} != Sum of completed settlements {expected_paid}")
        amount_mismatches += 1

if amount_mismatches == 0:
    print(f"✓ PASS: All {bills.count()} bills have correct paid amounts")
else:
    print(f"❌ FAIL: {amount_mismatches} bills have amount mismatches")

print()
print("=" * 80)
print("FINAL VERDICT")
print("=" * 80)

if all_correct and linkage_issues == 0 and missing_reversals == 0 and amount_mismatches == 0:
    print("✅ ALL CHECKS PASSED - NO DATA INTEGRITY ISSUES FOUND")
    print()
    print("Conclusion: The system is working correctly.")
    print("The screenshot shows normal behavior for cancelled settlements:")
    print("  1. Payment received transaction (when settlement was created)")
    print("  2. Payment cancelled transaction (when settlement was cancelled)")
    print("  3. Both show settlement status as 'Cancelled' (current state)")
    print()
    print("This is correct accounting - we preserve the audit trail.")
    print("UX Improvement: Could add visual distinction between original and reversal transactions.")
else:
    print("❌ DATA INTEGRITY ISSUES FOUND - SEE DETAILS ABOVE")
