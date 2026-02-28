"""
Update existing return_cancelled transactions to have correct commission
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from django.db import transaction
from decimal import Decimal

print("=" * 80)
print("UPDATING RETURN_CANCELLED TRANSACTIONS")
print("=" * 80)

# Get all return_cancelled transactions (should be 3)
return_cancelled_txns = CommissionTransaction.objects.filter(
    transaction_type='return_cancelled'
).order_by('id')

print(f"\nFound {return_cancelled_txns.count()} return_cancelled transactions\n")

for txn in return_cancelled_txns:
    print(f"{'=' * 80}")
    print(f"Transaction ID: {txn.id}")
    print(f"Sales Rep: {txn.sales_rep.get_full_name()}")
    print(f"Return Amount: Rs. {txn.return_amount}")
    print(f"Current Commission: Rs. {txn.commission_earned}")
    print(f"Current Balance: Rs. {txn.running_balance}")
    print(f"Rate: {txn.applicable_rate}%")
    
    # Calculate what commission should be
    # return_amount is negative (e.g., -90.00)
    # Formula: -(return_amount * rate) / 100 = -(-90.00 * 5.00) / 100 = 4.50
    expected_commission = -(txn.return_amount * txn.applicable_rate) / 100
    print(f"Expected Commission: Rs. {expected_commission}")
    
    if txn.commission_earned == expected_commission:
        print("✅ Commission already correct")
    else:
        print("⚠️ Commission needs update")
        
        try:
            with transaction.atomic():
                # Get all transactions for this sales rep to recalculate balances
                all_txns = CommissionTransaction.objects.filter(
                    sales_rep=txn.sales_rep
                ).select_for_update().order_by('transaction_date', 'created_at')
                
                running_balance = Decimal('0.00')
                updated = False
                
                for t in all_txns:
                    # Recalculate commission for return_cancelled type
                    if t.id == txn.id:
                        old_commission = t.commission_earned
                        t.commission_earned = -(t.return_amount * t.applicable_rate) / 100
                        updated = True
                        print(f"Updating commission: Rs. {old_commission} → Rs. {t.commission_earned}")
                    
                    # Update running balance
                    running_balance += t.commission_earned
                    if t.running_balance != running_balance:
                        old_balance = t.running_balance
                        t.running_balance = running_balance
                        t.save(update_fields=['commission_earned', 'running_balance'])
                        if t.id == txn.id:
                            print(f"Updating balance: Rs. {old_balance} → Rs. {t.running_balance}")
                
                if updated:
                    print("✅ Transaction updated and balances recalculated")
                
        except Exception as e:
            print(f"❌ Error updating: {e}")

print("\n" + "=" * 80)
print("FINAL VERIFICATION")
print("=" * 80)

# Verify all return_cancelled transactions
final_check = CommissionTransaction.objects.filter(
    transaction_type='return_cancelled'
).order_by('id')

all_correct = True
for txn in final_check:
    expected = -(txn.return_amount * txn.applicable_rate) / 100
    if txn.commission_earned != expected:
        print(f"❌ ID {txn.id}: Commission Rs. {txn.commission_earned}, expected Rs. {expected}")
        all_correct = False

if all_correct:
    print("✅ All return_cancelled transactions have correct commission!")
else:
    print("⚠️ Some transactions still have incorrect commission")

print("\n" + "=" * 80)
