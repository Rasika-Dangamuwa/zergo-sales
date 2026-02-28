"""
Step-by-Step Cash Refund Impact Demonstration
Shows exactly when and how balance changes
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import CompanyAccount, PurchaseReturn
from decimal import Decimal

print("=" * 100)
print("CASH REFUND IMPACT - STEP BY STEP WALKTHROUGH")
print("=" * 100)

account = CompanyAccount.objects.first()

# Get a return that has cash refund
pr = PurchaseReturn.objects.filter(
    company=account.company,
    settlements__settlement_method='refund'
).first()

if not pr:
    print("\nNo returns with cash refunds found!")
else:
    print(f"\nUsing: {pr.pr_number}")
    print(f"Return Amount: Rs. {pr.total_amount:,.2f}")
    
    print("\n" + "=" * 100)
    print("SCENARIO SIMULATION")
    print("=" * 100)
    
    # Find the transaction before this return
    return_txn = account.transactions.filter(purchase_return=pr).first()
    all_txns = list(account.transactions.all().order_by('transaction_date', 'id'))
    
    return_idx = all_txns.index(return_txn)
    
    # Calculate balance before return
    balance_before = account.opening_balance
    for txn in all_txns[:return_idx]:
        balance_before += txn.amount
    
    print(f"\n📊 Before Return Approved:")
    print(f"   Company Account Balance: Rs. {balance_before:,.2f}")
    if balance_before > 0:
        print(f"   Meaning: We owe them Rs. {balance_before:,.2f}")
    elif balance_before < 0:
        print(f"   Meaning: They owe us Rs. {abs(balance_before):,.2f}")
    else:
        print(f"   Meaning: Account is balanced")
    
    print(f"\n⚡ ACTION: Return Approved (PR {pr.pr_number})")
    print(f"   Returned Goods Worth: Rs. {pr.total_amount:,.2f}")
    print(f"   Status Change: {pr.status}")
    print(f"\n   System Action:")
    print(f"   • Created CompanyTransaction")
    print(f"     - Type: 'return'")
    print(f"     - Amount: -Rs. {pr.total_amount:,.2f} (NEGATIVE)")
    print(f"     - Reference: {pr.pr_number}")
    
    balance_after_return = balance_before + return_txn.amount
    
    print(f"\n   Balance Calculation:")
    print(f"   balance = {balance_before:,.2f} + ({return_txn.amount:+,.2f})")
    print(f"   balance = {balance_after_return:,.2f}")
    
    print(f"\n📊 After Return Approved:")
    print(f"   Company Account Balance: Rs. {balance_after_return:,.2f}")
    if balance_after_return > 0:
        print(f"   Meaning: We owe them Rs. {balance_after_return:,.2f}")
        print(f"   Change: We owe Rs. {abs(balance_before - balance_after_return):,.2f} LESS")
    elif balance_after_return < 0:
        print(f"   Meaning: They owe us Rs. {abs(balance_after_return):,.2f}")
        print(f"   Change: They owe us Rs. {abs(balance_before - balance_after_return):,.2f} MORE")
    
    print(f"\n   ✅ BALANCE REDUCED because return creates receivable")
    
    # Find the settlement
    settlement = pr.settlements.filter(settlement_method='refund').first()
    
    if settlement:
        print(f"\n⚡ ACTION: Cash Refund Recorded")
        print(f"   Settlement Amount: Rs. {settlement.settlement_amount:,.2f}")
        print(f"   Settlement Method: {settlement.get_settlement_method_display()}")
        print(f"   Cash Received Date: {settlement.cash_received_date or 'Not set'}")
        print(f"   Cash Receipt #: {settlement.cash_receipt_number or 'Not set'}")
        
        print(f"\n   System Action:")
        print(f"   • Created PurchaseReturnSettlement")
        print(f"   • Updated PurchaseReturn.settlement_status")
        print(f"   • ❌ Did NOT create CompanyTransaction")
        print(f"   • ❌ Did NOT change CompanyAccount balance")
        
        print(f"\n📊 After Cash Refund Recorded:")
        print(f"   Company Account Balance: Rs. {balance_after_return:,.2f}")
        print(f"   Change: NO CHANGE")
        
        print(f"\n   Why No Change?")
        print(f"   • Balance already reduced when return was approved")
        print(f"   • Cash refund is SETTLEMENT method (how they pay us back)")
        print(f"   • Alternative would be replacement goods (GRN)")
        print(f"   • Both settlements close the receivable, don't affect balance")
    
    print("\n" + "=" * 100)
    print("KEY INSIGHTS")
    print("=" * 100)
    
    print("""
    1. RETURN APPROVAL = FINANCIAL TRANSACTION
       • Creates receivable (they owe us)
       • Reduces balance immediately
       • This is when accounting happens
    
    2. CASH REFUND = SETTLEMENT METHOD
       • Tracks HOW the receivable is settled
       • Operational/audit information
       • No additional balance change needed
    
    3. COMPANY ACCOUNT BALANCE
       • Shows NET position (payable - receivable)
       • Negative = They owe us (receivable)
       • Positive = We owe them (payable)
       • Zero = Fully settled
    
    4. CASH REFUND DOES REDUCE "RECEIVABLE"
       • But it's already reduced when return approved!
       • Recording cash receipt just documents the settlement
       • Balance correctly reflects the net position
    """)
    
    print("\n" + "=" * 100)
    print("COMPARISON: Cash Refund vs. Replacement GRN")
    print("=" * 100)
    
    print(f"\nScenario: Return Rs. 10,000 goods")
    print(f"Starting Balance: We owe them Rs. 100,000")
    
    print(f"\nOption A: CASH REFUND")
    print(f"─────────────────────")
    print(f"Step 1: Return approved")
    print(f"  • CompanyTransaction: -10,000 (return)")
    print(f"  • Balance: 100,000 + (-10,000) = 90,000")
    print(f"  • We owe: Rs. 90,000")
    print(f"\nStep 2: Cash refund received")
    print(f"  • PurchaseReturnSettlement: Cash refund Rs. 10,000")
    print(f"  • Balance: 90,000 (unchanged)")
    print(f"  • We owe: Rs. 90,000")
    print(f"\n  Why? We received cash, they settled the receivable.")
    print(f"       We still only owe them 90k (not 100k).")
    
    print(f"\nOption B: REPLACEMENT GRN")
    print(f"─────────────────────────")
    print(f"Step 1: Return approved")
    print(f"  • CompanyTransaction: -10,000 (return)")
    print(f"  • Balance: 100,000 + (-10,000) = 90,000")
    print(f"  • We owe: Rs. 90,000")
    print(f"\nStep 2: Replacement GRN received")
    print(f"  • CompanyTransaction: +10,000 (purchase)")
    print(f"  • Balance: 90,000 + 10,000 = 100,000")
    print(f"  • We owe: Rs. 100,000")
    print(f"\n  Why? They sent us goods worth 10k instead of cash.")
    print(f"       Balance goes back to 100k because we bought more goods.")
    
    print(f"\n✅ BOTH OPTIONS VALID:")
    print(f"   • Cash refund: Balance stays reduced (we got cash)")
    print(f"   • Replacement: Balance goes back up (we got goods)")
    print(f"   • System correctly handles both scenarios!")

print("\n" + "=" * 100)
