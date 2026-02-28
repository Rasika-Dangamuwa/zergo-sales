"""
Investigation: Check if return deletions create reversal commission transactions
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, CommissionTransaction
from django.utils import timezone

print("=" * 80)
print("RETURN DELETION COMMISSION REVERSAL INVESTIGATION")
print("=" * 80)

# Check all return_processed transactions
print("\n1. Checking all return_processed commission transactions...")
all_return_commissions = CommissionTransaction.objects.filter(
    transaction_type='return_processed'
).order_by('-transaction_date')

print(f"Total return_processed transactions: {all_return_commissions.count()}")

if all_return_commissions.exists():
    print(f"\nRecent return_processed transactions:")
    for txn in all_return_commissions[:10]:
        print(f"\n  ID {txn.id}: {txn.transaction_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Sales Rep: {txn.sales_rep.get_full_name()}")
        print(f"  Return Amount: Rs. {txn.return_amount}")
        print(f"  Commission: Rs. {txn.commission_earned} | Balance: Rs. {txn.running_balance}")
        print(f"  Notes: {txn.notes[:100] if txn.notes else 'No notes'}")
        
        # Try to find corresponding return by parsing return number from notes
        if txn.notes and 'RN-' in txn.notes:
            import re
            match = re.search(r'RN-\d{8}-\d+', txn.notes)
            if match:
                return_number = match.group()
                return_exists = Return.objects.filter(return_number=return_number).exists()
                if return_exists:
                    print(f"  ✅ Return {return_number} exists in database")
                else:
                    print(f"  ❌ Return {return_number} NOT FOUND - might have been deleted!")
        
        # Check if there's a reversal transaction
        reversal_exists = CommissionTransaction.objects.filter(
            transaction_type='return_cancelled',
            return_amount=-txn.return_amount,
            sales_rep=txn.sales_rep,
            transaction_date__gt=txn.transaction_date
        ).exists()
        
        if reversal_exists:
            print(f"  ✅ Reversal transaction exists")
        else:
            print(f"  ⚠️ NO REVERSAL transaction found")

# Check if any returns have been deleted by looking for gaps in return numbers
print("\n\n2. Checking for missing return numbers (potential deletions)...")
from sales.models import Return
from datetime import timedelta

all_returns = Return.objects.all().order_by('return_date')
if all_returns.exists():
    first_return = all_returns.first()
    last_return = all_returns.last()
    
    # Extract date from return number (format: RN-YYYYMMDD-###)
    total_returns = all_returns.count()
    print(f"Total returns in system: {total_returns}")
    print(f"First return: {first_return.return_number} on {first_return.return_date}")
    print(f"Last return: {last_return.return_number} on {last_return.return_date}")
    
    # Check today's returns
    today = timezone.now().date()
    todays_returns = Return.objects.filter(
        return_date__date=today
    ).order_by('return_number')
    
    if todays_returns.exists():
        print(f"\nToday's returns ({today}):")
        for ret in todays_returns:
            print(f"  - {ret.return_number}: Shop {ret.shop.shop_code} | Status: {ret.return_status}")
            
            # Check if commission transaction exists
            comm_txn = CommissionTransaction.objects.filter(
                return_ref=ret
            ).first()
            
            if comm_txn:
                print(f"    ✅ Commission transaction ID {comm_txn.id} exists")
            else:
                print(f"    ❌ NO commission transaction found!")

# Check if there's any signal handler for return deletion
print("\n\n3. Checking commission signal handlers...")
print("Signal handlers found in sales/commission_signals.py:")
print("  - post_save for Bill (creates commission on bill creation)")
print("  - post_save for SalesAccountSettlement (creates commission on payment/reverses on cancellation)")
print("  - post_save for Return (creates commission on return)")
print("  - post_save for BadDebtWriteOff (tracks write-offs)")
print("\n⚠️ NO pre_delete or post_delete handler found for Return model!")
print("This means when a return is deleted, the commission transaction is never reversed!")

# Check if return_cancelled transaction type is being used
print("\n\n4. Checking for any return_cancelled transactions...")
return_cancelled_txns = CommissionTransaction.objects.filter(
    transaction_type='return_cancelled'
)

if return_cancelled_txns.exists():
    print(f"✅ Found {return_cancelled_txns.count()} return_cancelled transactions")
    for txn in return_cancelled_txns[:5]:
        print(f"  - ID {txn.id}: {txn.transaction_date} | Commission: Rs. {txn.commission_earned}")
else:
    print("❌ NO return_cancelled transactions found in database!")
    print("This confirms that return deletions are NOT creating reversal transactions")

print("\n\n5. Checking settlement cancellation handler for returns...")
# When a return is deleted, return_adjustment settlements are auto-cancelled
# Check if those cancellations create reversal transactions
from payments.models import SalesAccountSettlement

cancelled_return_settlements = SalesAccountSettlement.objects.filter(
    settlement_method='return_adjustment',
    settlement_status='cancelled'
).order_by('-created_at')

print(f"Found {cancelled_return_settlements.count()} cancelled return_adjustment settlements")

if cancelled_return_settlements.exists():
    print(f"\nShowing first 5:")
    for settlement in cancelled_return_settlements[:5]:
        print(f"\n  Settlement: {settlement.settlement_number}")
        print(f"  Status: {settlement.settlement_status}")
        print(f"  Notes: {settlement.notes[:100] if settlement.notes else 'No notes'}")
        
        # Check if there are commission transactions for this settlement
        comm_txns = CommissionTransaction.objects.filter(
            settlement=settlement
        ).order_by('transaction_date')
        
        if comm_txns.exists():
            print(f"  Commission transactions ({comm_txns.count()}):")
            for txn in comm_txns:
                print(f"    - ID {txn.id}: {txn.transaction_type} | Rs. {txn.commission_earned}")
        else:
            print(f"  ⚠️ No commission transactions (return_adjustment doesn't create commission)")

print("\n\n" + "=" * 80)
print("FINDINGS SUMMARY")
print("=" * 80)
print("""
ISSUE IDENTIFIED:
1. When a return is created → commission_signals.py creates 'return_processed' transaction
2. When a return is DELETED → NO signal handler exists to reverse the commission
3. The return_processed commission transaction remains in the database
4. Running balances are NOT recalculated after return deletion
5. This causes commission balances to be INCORRECT

SOLUTION NEEDED:
Add a pre_delete signal handler for Return model to:
- Create a reversal transaction (return_cancelled) with negative commission
- Update running balances for subsequent transactions
""")
