# Fix Bill #89 Issues - Run in Django shell
# Command: python manage.py shell
# Then: exec(open('fix_bill_89_issues.py').read())

from sales.models import Bill, CommissionTransaction
from payments.models import SalesAccountSettlement
from decimal import Decimal
from django.db import transaction

print("\n" + "="*80)
print("FIXING BILL #89 ISSUES")
print("="*80 + "\n")

bill = Bill.objects.get(id=89)
print(f"Working on Bill: {bill.bill_number}\n")

# ============================================================================
# FIX 1: Ensure bill_created transaction exists
# ============================================================================
print("FIX 1: Checking bill_created transaction...")
bill_created = CommissionTransaction.objects.filter(
    bill=bill,
    transaction_type='bill_created'
).first()

if not bill_created:
    print("  ⚠️  Missing! Creating bill_created transaction...")
    with transaction.atomic():
        bill_created = CommissionTransaction.create_for_bill(bill, created_by=bill.sales_rep)
        print(f"  ✓ Created: {bill_created}")
else:
    print(f"  ✓ Already exists: {bill_created}")

# ============================================================================
# FIX 2: Create missing commission transactions for completed settlements
# ============================================================================
print("\nFIX 2: Checking commission transactions for completed settlements...")
completed_settlements = SalesAccountSettlement.objects.filter(
    bill=bill,
    settlement_status='completed'
).order_by('settlement_date')

missing_count = 0
for settlement in completed_settlements:
    # Check if commission transaction exists for this settlement
    existing = CommissionTransaction.objects.filter(
        transaction_type='payment_received',
        bill=bill,
        collected_amount=settlement.amount,
        transaction_date__date=settlement.settlement_date.date()
    ).first()
    
    if not existing:
        print(f"  ⚠️  Missing transaction for {settlement.settlement_number} (Rs. {settlement.amount})")
        print(f"     Creating commission transaction...")
        with transaction.atomic():
            txn = CommissionTransaction.create_for_payment(settlement, bill)
            print(f"     ✓ Created: {txn}")
            missing_count += 1
    else:
        print(f"  ✓ Transaction exists for {settlement.settlement_number}")

if missing_count == 0:
    print("  ✓ All completed settlements have commission transactions")
else:
    print(f"\n  ✓ Fixed {missing_count} missing commission transaction(s)")

# ============================================================================
# FIX 3: Recalculate bill paid_amount from completed settlements
# ============================================================================
print("\nFIX 3: Verifying bill paid_amount...")
completed_total = sum(s.amount for s in completed_settlements)
print(f"  Completed settlements total: Rs. {completed_total}")
print(f"  Current bill.paid_amount: Rs. {bill.paid_amount}")

if abs(completed_total - bill.paid_amount) > Decimal('0.01'):
    print(f"  ⚠️  Discrepancy detected! Fixing...")
    with transaction.atomic():
        old_paid = bill.paid_amount
        bill.paid_amount = completed_total
        bill.balance_amount = bill.total_amount - bill.paid_amount
        
        # Update settlement status
        if bill.paid_amount == 0:
            bill.settlement_status = 'unsettled'
        elif bill.paid_amount >= bill.total_amount:
            bill.settlement_status = 'settled'
        else:
            bill.settlement_status = 'partial_settled'
        
        bill.save(update_fields=['paid_amount', 'balance_amount', 'settlement_status'])
        print(f"  ✓ Updated paid_amount: Rs. {old_paid} → Rs. {bill.paid_amount}")
        print(f"  ✓ Updated balance_amount: Rs. {bill.balance_amount}")
        print(f"  ✓ Updated settlement_status: {bill.settlement_status}")
else:
    print(f"  ✓ Bill paid_amount is correct")

# ============================================================================
# FIX 4: Recalculate all running balances for this sales rep
# ============================================================================
print("\nFIX 4: Recalculating running balances...")
print(f"  Sales Rep: {bill.sales_rep.get_full_name()}")

with transaction.atomic():
    # Get all transactions for this sales rep in order
    all_txns = CommissionTransaction.objects.filter(
        sales_rep=bill.sales_rep
    ).select_for_update().order_by('transaction_date', 'created_at')
    
    running_balance = Decimal('0.00')
    updated_count = 0
    
    for txn in all_txns:
        running_balance += txn.commission_earned
        if txn.running_balance != running_balance:
            txn.running_balance = running_balance
            txn.save(update_fields=['running_balance'])
            updated_count += 1
    
    if updated_count > 0:
        print(f"  ✓ Updated {updated_count} running balances")
    else:
        print(f"  ✓ All running balances are correct")

# ============================================================================
# FINAL VERIFICATION
# ============================================================================
print("\n" + "="*80)
print("FINAL VERIFICATION")
print("="*80 + "\n")

# Reload bill from database
bill.refresh_from_db()

# Check all conditions
checks = [
    ("Bill created transaction exists", CommissionTransaction.objects.filter(bill=bill, transaction_type='bill_created').exists()),
    ("Completed settlements = paid_amount", abs(completed_total - bill.paid_amount) < Decimal('0.01')),
    ("Payment transactions = completed settlements", CommissionTransaction.objects.filter(bill=bill, transaction_type='payment_received').count() == completed_settlements.count()),
    ("Balance calculation correct", abs(bill.balance_amount - (bill.total_amount - bill.paid_amount)) < Decimal('0.01')),
    ("Settlement status correct", 
     (bill.paid_amount == 0 and bill.settlement_status == 'unsettled') or
     (bill.paid_amount >= bill.total_amount and bill.settlement_status == 'settled') or
     (0 < bill.paid_amount < bill.total_amount and bill.settlement_status == 'partial_settled'))
]

all_passed = True
for check_name, passed in checks:
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"  {status}: {check_name}")
    if not passed:
        all_passed = False

if all_passed:
    print("\n" + "="*80)
    print("✓ ALL FIXES APPLIED SUCCESSFULLY - Bill #89 is now properly tracked!")
    print("="*80 + "\n")
else:
    print("\n" + "="*80)
    print("⚠️  Some issues remain - Manual intervention required")
    print("="*80 + "\n")
