# ============================================================================
# BILL #89 DEEP INVESTIGATION - Run in Django Shell
# ============================================================================
# Command: python manage.py shell
# Then: exec(open('investigate_bill_89.py').read())
# ============================================================================

from sales.models import Bill, CommissionTransaction
from payments.models import SalesAccountSettlement
from decimal import Decimal
from django.utils import timezone

print("\n" + "="*100)
print(" "*35 + "BILL #89 INVESTIGATION")
print("="*100 + "\n")

# ============================================================================
# PART 1: BILL DETAILS
# ============================================================================
try:
    bill = Bill.objects.get(id=89)
    
    print("┌─ BILL DETAILS " + "─"*84)
    print(f"│ Number:          {bill.bill_number}")
    print(f"│ Date:            {bill.bill_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"│ Shop:            {bill.shop.shop_name} (ID: {bill.shop_id})")
    print(f"│ Sales Rep:       {bill.sales_rep.get_full_name()} (ID: {bill.sales_rep_id})")
    print(f"│ Total Amount:    Rs. {bill.total_amount:,.2f}")
    print(f"│ Paid Amount:     Rs. {bill.paid_amount:,.2f}")
    print(f"│ Balance:         Rs. {bill.balance_amount:,.2f}")
    print(f"│ Bill Status:     {bill.bill_status.upper()}")
    print(f"│ Settlement:      {bill.settlement_status.upper()}")
    print("└" + "─"*99)
    
except Bill.DoesNotExist:
    print("❌ ERROR: Bill #89 does not exist!")
    exit()

# ============================================================================
# PART 2: SETTLEMENTS ANALYSIS
# ============================================================================
print("\n┌─ SETTLEMENTS " + "─"*85)

settlements = SalesAccountSettlement.objects.filter(bill=bill).order_by('settlement_date')
completed_total = Decimal('0.00')
pending_total = Decimal('0.00')

if settlements.exists():
    print(f"│ Total Settlements Found: {settlements.count()}\n│")
    
    for idx, s in enumerate(settlements, 1):
        status_icon = "✓" if s.settlement_status == 'completed' else "⏳" if s.settlement_status == 'pending' else "✗"
        print(f"│ [{idx}] {status_icon} {s.settlement_number}")
        print(f"│     Date:     {s.settlement_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"│     Method:   {s.get_settlement_method_display()}")
        print(f"│     Amount:   Rs. {s.amount:,.2f}")
        print(f"│     Status:   {s.settlement_status.upper()}")
        
        if s.received_by:
            print(f"│     Received: {s.received_by.get_full_name()}")
        if s.verified_by:
            print(f"│     Verified: {s.verified_by.get_full_name()} at {s.verified_at.strftime('%Y-%m-%d %H:%M')}")
        if s.notes:
            print(f"│     Notes:    {s.notes[:70]}")
        
        if s.settlement_status == 'completed':
            completed_total += s.amount
        elif s.settlement_status == 'pending':
            pending_total += s.amount
        
        print("│")
    
    print(f"│ ──────────────────────────────")
    print(f"│ Completed Settlements: Rs. {completed_total:,.2f}")
    print(f"│ Pending Settlements:   Rs. {pending_total:,.2f}")
    print(f"│ Bill Paid Amount:      Rs. {bill.paid_amount:,.2f}")
    
    # Discrepancy check
    if abs(completed_total - bill.paid_amount) > Decimal('0.01'):
        diff = completed_total - bill.paid_amount
        print(f"│")
        print(f"│ ⚠️  DISCREPANCY DETECTED!")
        print(f"│     Difference: Rs. {diff:,.2f}")
        print(f"│     Expected: Completed settlements ({completed_total}) = Bill paid_amount ({bill.paid_amount})")
else:
    print("│ ❌ No settlements found for this bill")

print("└" + "─"*99)

# ============================================================================
# PART 3: COMMISSION TRANSACTIONS
# ============================================================================
print("\n┌─ COMMISSION TRANSACTIONS " + "─"*73)

transactions = CommissionTransaction.objects.filter(bill=bill).order_by('transaction_date', 'created_at')

if transactions.exists():
    print(f"│ Total Transactions Found: {transactions.count()}\n│")
    
    bill_created_txn = None
    payment_txns = []
    total_commission = Decimal('0.00')
    
    for idx, txn in enumerate(transactions, 1):
        type_icon = "📄" if txn.transaction_type == 'bill_created' else "💰" if txn.transaction_type == 'payment_received' else "🔄"
        print(f"│ [{idx}] {type_icon} {txn.get_transaction_type_display().upper()}")
        print(f"│     Date:            {txn.transaction_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"│     Sales Rep:       {txn.sales_rep.get_full_name()}")
        
        if txn.transaction_type == 'bill_created':
            print(f"│     Sales Amount:    Rs. {txn.sales_amount:,.2f}")
            bill_created_txn = txn
        elif txn.transaction_type == 'payment_received':
            print(f"│     Collected:       Rs. {txn.collected_amount:,.2f}")
            payment_txns.append(txn)
        
        print(f"│     Rate:            {txn.applicable_rate}%")
        print(f"│     Commission:      Rs. {txn.commission_earned:,.2f}")
        print(f"│     Running Balance: Rs. {txn.running_balance:,.2f}")
        
        if txn.notes:
            print(f"│     Notes:           {txn.notes[:65]}")
        
        total_commission += txn.commission_earned
        print("│")
    
    # Analysis
    print(f"│ ──────────────────────────────")
    print(f"│ COMMISSION ANALYSIS:")
    print(f"│   Bill Created Transaction:  {'YES ✓' if bill_created_txn else 'NO ✗ (MISSING!)'}")
    print(f"│   Payment Transactions:      {len(payment_txns)}")
    
    if payment_txns:
        total_collected_in_txns = sum(t.collected_amount for t in payment_txns)
        total_commission_earned = sum(t.commission_earned for t in payment_txns)
        
        print(f"│   Total Collected (Txns):    Rs. {total_collected_in_txns:,.2f}")
        print(f"│   Total Commission:          Rs. {total_commission_earned:,.2f}")
        
        # Verify calculation
        rate = payment_txns[0].applicable_rate
        expected_commission = (total_collected_in_txns * rate) / 100
        print(f"│   Expected Commission (@{rate}%): Rs. {expected_commission:,.2f}")
        
        if abs(total_commission_earned - expected_commission) > Decimal('0.01'):
            print(f"│   ⚠️  CALCULATION MISMATCH: Rs. {total_commission_earned - expected_commission:,.2f}")
    
    # Cross-check with settlements
    completed_settlements = settlements.filter(settlement_status='completed')
    print(f"│")
    print(f"│ SETTLEMENT vs COMMISSION CHECK:")
    print(f"│   Completed Settlements:     {completed_settlements.count()}")
    print(f"│   Payment Transactions:      {len(payment_txns)}")
    
    if completed_settlements.count() != len(payment_txns):
        missing = completed_settlements.count() - len(payment_txns)
        print(f"│   ⚠️  MISMATCH: {abs(missing)} transaction(s) {'missing' if missing > 0 else 'extra'}!")
        
        # Show which settlements don't have commission transactions
        if missing > 0:
            print(f"│")
            print(f"│   Settlements without commission transactions:")
            for s in completed_settlements:
                # Check if this settlement has a corresponding commission transaction
                has_txn = any(
                    abs(txn.collected_amount - s.amount) < Decimal('0.01') and
                    txn.transaction_date.date() == s.settlement_date.date()
                    for txn in payment_txns
                )
                if not has_txn:
                    print(f"│     - {s.settlement_number}: Rs. {s.amount:,.2f} on {s.settlement_date.strftime('%Y-%m-%d')}")
    
else:
    print("│ ❌ No commission transactions found!")
    print("│ ⚠️  EXPECTED: At least 1 'bill_created' transaction should exist")

print("└" + "─"*99)

# ============================================================================
# PART 4: VERIFICATION SUMMARY
# ============================================================================
print("\n┌─ VERIFICATION CHECKLIST " + "─"*74)

checks = []

# Check 1: Bill created transaction
bill_created_exists = transactions.filter(transaction_type='bill_created').exists()
checks.append(("Bill Created Transaction Exists", bill_created_exists, "Commission system tracking bill"))

# Check 2: Settlements match paid amount
settlements_match = abs(completed_total - bill.paid_amount) < Decimal('0.01')
checks.append(("Completed Settlements = Paid Amount", settlements_match, f"Rs. {completed_total} vs Rs. {bill.paid_amount}"))

# Check 3: Commission transactions match settlements
completed_count = settlements.filter(settlement_status='completed').count()
payment_count = transactions.filter(transaction_type='payment_received').count()
txns_match = (completed_count == payment_count)
checks.append(("Payment Transactions = Completed Settlements", txns_match, f"{payment_count} vs {completed_count}"))

# Check 4: Balance calculation
expected_balance = bill.total_amount - bill.paid_amount
balance_correct = abs(bill.balance_amount - expected_balance) < Decimal('0.01')
checks.append(("Balance Calculation Correct", balance_correct, f"Rs. {bill.balance_amount} vs Rs. {expected_balance}"))

# Check 5: Settlement status correct
status_correct = (
    (bill.paid_amount == 0 and bill.settlement_status == 'unsettled') or
    (bill.paid_amount >= bill.total_amount and bill.settlement_status == 'settled') or
    (0 < bill.paid_amount < bill.total_amount and bill.settlement_status == 'partial_settled')
)
checks.append(("Settlement Status Correct", status_correct, f"Status: {bill.settlement_status}"))

for check_name, passed, detail in checks:
    icon = "✓" if passed else "✗"
    status = "PASS" if passed else "FAIL"
    print(f"│ [{icon}] {status:5} │ {check_name:45} │ {detail}")

print("└" + "─"*99)

# ============================================================================
# PART 5: RECOMMENDATIONS
# ============================================================================
issues_found = sum(1 for _, passed, _ in checks if not passed)

if issues_found > 0:
    print(f"\n{'='*100}")
    print(f" ⚠️  ISSUES FOUND: {issues_found} verification(s) failed")
    print(f"{'='*100}\n")
    
    print("RECOMMENDED ACTIONS:")
    
    if not bill_created_exists:
        print("  1. Create missing 'bill_created' commission transaction:")
        print(f"     CommissionTransaction.create_for_bill(bill, created_by=bill.sales_rep)")
    
    if not settlements_match:
        print("  2. Recalculate bill paid_amount from completed settlements:")
        print("     bill.calculate_totals()")
    
    if not txns_match:
        print("  3. Manually create missing commission transactions for completed settlements")
        print("     Use: CommissionTransaction.create_for_payment(settlement, bill)")
    
    print()
else:
    print(f"\n{'='*100}")
    print(f" ✓ ALL CHECKS PASSED - Bill #89 is properly tracked")
    print(f"{'='*100}\n")

print()
