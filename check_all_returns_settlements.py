"""
Check status of all returns and their settlements
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import PurchaseReturn, PurchaseReturnSettlement, CompanyTransaction

print("=" * 120)
print("ALL PURCHASE RETURNS AND SETTLEMENTS")
print("=" * 120)

returns = PurchaseReturn.objects.all().order_by('return_date')

for pr in returns:
    print(f"\n{pr.pr_number}:")
    print(f"  Amount: Rs. {pr.total_amount:,.2f}")
    print(f"  Status: {pr.status}")
    print(f"  Settlement Status: {pr.settlement_status}")
    
    # Check return transaction
    return_txns = CompanyTransaction.objects.filter(
        purchase_return=pr,
        transaction_type='return'
    )
    print(f"\n  Return Transactions:")
    if return_txns.exists():
        for txn in return_txns:
            print(f"    ✅ {txn.reference_number}: {txn.amount:+,.2f}")
    else:
        print(f"    ❌ No return transaction found!")
    
    # Check settlements
    settlements = PurchaseReturnSettlement.objects.filter(purchase_return=pr)
    print(f"\n  Settlements:")
    if settlements.exists():
        for s in settlements:
            print(f"    • Method: {s.get_settlement_method_display()}")
            print(f"      Amount: Rs. {s.settlement_amount:,.2f}")
            if s.settlement_method == 'replacement' and s.replacement_grn:
                print(f"      GRN: {s.replacement_grn.grn_number}")
            elif s.settlement_method == 'refund':
                print(f"      Cash Received: {s.cash_received_date or 'Not set'}")
                
                # Check if cash receipt transaction exists
                cash_txns = CompanyTransaction.objects.filter(
                    purchase_return=pr,
                    transaction_type='settlement'
                )
                if cash_txns.exists():
                    for txn in cash_txns:
                        print(f"      ✅ Cash Receipt Transaction: {txn.reference_number} (+Rs. {txn.amount:,.2f})")
                else:
                    print(f"      ❌ Missing cash receipt transaction!")
    else:
        print(f"    ⚠️  No settlements recorded")
    
    # Calculate expected balance impact
    return_amt = sum(txn.amount for txn in return_txns)
    settlement_txns = CompanyTransaction.objects.filter(
        purchase_return=pr,
        transaction_type='settlement'
    )
    settlement_amt = sum(txn.amount for txn in settlement_txns)
    
    net_impact = return_amt + settlement_amt
    
    print(f"\n  Balance Impact:")
    print(f"    Return transactions: {return_amt:+,.2f}")
    print(f"    Settlement transactions: {settlement_amt:+,.2f}")
    print(f"    Net impact: {net_impact:+,.2f}")
    
    if abs(net_impact) < 0.01:
        print(f"    Status: ✅ Balanced (settled)")
    else:
        print(f"    Status: ⚠️  Unbalanced by Rs. {abs(net_impact):,.2f}")

print("\n" + "=" * 120)
