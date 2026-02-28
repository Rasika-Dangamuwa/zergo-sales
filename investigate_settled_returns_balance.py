"""
Deep Investigation: Why balance isn't 0 when all returns/GRNs are settled
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import CompanyAccount, PurchaseReturn, PurchaseReturnSettlement, CompanyPayment, Purchase
from decimal import Decimal

print("=" * 120)
print("DEEP INVESTIGATION: SETTLED RETURNS & BALANCE DISCREPANCY")
print("=" * 120)

account = CompanyAccount.objects.first()

print(f"\n🏢 Company: {account.company.company_name}")
print(f"💰 Current Balance: Rs. {account.current_balance:,.2f}")
print(f"   Interpretation: {'They owe us (RECEIVABLE)' if account.current_balance < 0 else 'We owe them (PAYABLE)'}")

print("\n" + "=" * 120)
print("SECTION 1: WHAT DID WE PAY?")
print("=" * 120)

payments = CompanyPayment.objects.filter(company=account.company).order_by('payment_date')
total_paid = Decimal('0.00')

print("\nPayment | Date | Amount | Method")
print("-" * 60)
for p in payments:
    total_paid += p.total_amount
    print(f"{p.payment_number} | {p.payment_date.date()} | Rs. {p.total_amount:>10,.2f} | {p.get_payment_method_display()}")
print("-" * 60)
print(f"TOTAL PAID: Rs. {total_paid:,.2f}")

print("\n" + "=" * 120)
print("SECTION 2: WHAT DID WE RECEIVE?")
print("=" * 120)

grns = Purchase.objects.filter(company=account.company).order_by('grn_date')
total_purchased = Decimal('0.00')

print("\nGRN | Date | Amount | Status")
print("-" * 60)
for grn in grns:
    total_purchased += grn.total_amount
    status = "✅ Paid" if grn.amount_outstanding == 0 else f"⚠️  Outstanding: Rs. {grn.amount_outstanding:,.2f}"
    print(f"{grn.grn_number} | {grn.grn_date.date()} | Rs. {grn.total_amount:>10,.2f} | {status}")
print("-" * 60)
print(f"TOTAL PURCHASED: Rs. {total_purchased:,.2f}")

print("\n" + "=" * 120)
print("SECTION 3: WHAT DID WE RETURN?")
print("=" * 120)

returns = PurchaseReturn.objects.filter(company=account.company).order_by('return_date')
total_returned = Decimal('0.00')
total_cash_refund_settled = Decimal('0.00')
total_replacement_settled = Decimal('0.00')
total_unsettled = Decimal('0.00')

print("\nPR Number | Date | Amount | Status | Settlement")
print("-" * 100)
for pr in returns:
    total_returned += pr.total_amount
    
    # Check settlements
    settlements = PurchaseReturnSettlement.objects.filter(purchase_return=pr)
    settlement_info = []
    
    for s in settlements:
        if s.settlement_method == 'refund':
            total_cash_refund_settled += s.settlement_amount
            settlement_info.append(f"💵 Cash Refund: Rs. {s.settlement_amount:,.2f}")
        elif s.settlement_method == 'replacement':
            total_replacement_settled += s.settlement_amount
            settlement_info.append(f"📦 Replacement GRN: {s.replacement_grn.grn_number if s.replacement_grn else 'N/A'}")
    
    if not settlement_info:
        total_unsettled += pr.total_amount
        settlement_info.append("⏳ Pending Settlement")
    
    settlement_str = " | ".join(settlement_info)
    print(f"{pr.pr_number} | {pr.return_date.date()} | Rs. {pr.total_amount:>10,.2f} | {pr.status:20} | {settlement_str}")

print("-" * 100)
print(f"TOTAL RETURNED: Rs. {total_returned:,.2f}")
print(f"  • Settled via Cash Refund: Rs. {total_cash_refund_settled:,.2f}")
print(f"  • Settled via Replacement: Rs. {total_replacement_settled:,.2f}")
print(f"  • Unsettled (Pending): Rs. {total_unsettled:,.2f}")

print("\n" + "=" * 120)
print("SECTION 4: WHAT SHOULD THE BALANCE BE?")
print("=" * 120)

print("\n📊 CALCULATION METHOD 1: Simple Approach")
print("-" * 60)
print(f"Total Paid:      Rs. {total_paid:>12,.2f}")
print(f"Total Purchased: Rs. {total_purchased:>12,.2f}")
print(f"Total Returned:  Rs. {total_returned:>12,.2f}")
print(f"\nNet Purchase: {total_purchased} - {total_returned} = Rs. {total_purchased - total_returned:,.2f}")
print(f"Balance: {total_paid} - {total_purchased - total_returned} = Rs. {total_paid - (total_purchased - total_returned):,.2f}")

print("\n📊 CALCULATION METHOD 2: Considering Settlements")
print("-" * 60)
print(f"Total Paid:               Rs. {total_paid:>12,.2f}")
print(f"Total Purchased:          Rs. {total_purchased:>12,.2f}")
print(f"Cash Refund Received:     Rs. {total_cash_refund_settled:>12,.2f}")
print(f"\nWhat we gave them:  {total_paid} (cash)")
print(f"What we got back:   {total_purchased} (goods) + {total_cash_refund_settled} (cash refund)")
print(f"                  = Rs. {total_purchased + total_cash_refund_settled:,.2f}")
print(f"\nBalance: {total_paid} - ({total_purchased} + {total_cash_refund_settled})")
print(f"       = {total_paid} - {total_purchased + total_cash_refund_settled}")
print(f"       = Rs. {total_paid - (total_purchased + total_cash_refund_settled):,.2f}")

print("\n" + "=" * 120)
print("SECTION 5: CURRENT SYSTEM BEHAVIOR")
print("=" * 120)

print("\nHow the system currently handles settlements:")
print("-" * 60)
print("✅ Return Approved:")
print("   • Creates CompanyTransaction with negative amount")
print("   • Balance reduced (creates receivable)")
print("   • Example: Return Rs. 693 → Balance -693 (they owe us)")
print()
print("❌ Cash Refund Recorded:")
print("   • Creates PurchaseReturnSettlement record")
print("   • Does NOT create CompanyTransaction")
print("   • Does NOT change balance")
print("   • Result: Balance stays at -693 (still shows they owe us!)")
print()
print("🔍 THE PROBLEM:")
print("   If we actually RECEIVED the cash refund, balance should go back to 0")
print("   But system doesn't record the cash receipt as a transaction!")

print("\n" + "=" * 120)
print("SECTION 6: WHAT'S MISSING?")
print("=" * 120)

print("\n🚨 CRITICAL MISSING TRANSACTIONS:")
print("-" * 60)

missing_total = Decimal('0.00')
for pr in returns:
    settlements = PurchaseReturnSettlement.objects.filter(
        purchase_return=pr,
        settlement_method='refund'
    )
    
    for s in settlements:
        print(f"\n{pr.pr_number} - Cash Refund Rs. {s.settlement_amount:,.2f}")
        print(f"   ❌ Missing Transaction:")
        print(f"      Type: 'cash_refund_receipt' or 'settlement'")
        print(f"      Amount: +{s.settlement_amount:,.2f} (POSITIVE - we received cash)")
        print(f"      Effect: Reduces receivable by {s.settlement_amount:,.2f}")
        print(f"      Balance change: -{pr.total_amount:,.2f} → -{pr.total_amount - s.settlement_amount:,.2f}")
        missing_total += s.settlement_amount

print(f"\n💰 Total Missing Cash Receipts: Rs. {missing_total:,.2f}")

print("\n" + "=" * 120)
print("SECTION 7: CORRECTED BALANCE CALCULATION")
print("=" * 120)

print("\nIf we add the missing cash refund transactions:")
print("-" * 60)
print(f"Current Balance:             Rs. {account.current_balance:>12,.2f} (they owe us)")
print(f"Add Cash Refunds Received:   Rs. {total_cash_refund_settled:>12,.2f}")
print(f"Corrected Balance:           Rs. {account.current_balance + total_cash_refund_settled:>12,.2f}")
print()
if abs(account.current_balance + total_cash_refund_settled) < Decimal('0.01'):
    print("✅ CORRECTED BALANCE = Rs. 0.00 (SETTLED)")
else:
    print(f"⚠️  Remaining: Rs. {account.current_balance + total_cash_refund_settled:,.2f}")
    print(f"   This is: PR-20260118-003 (Rs. 693.00) - Pending Settlement")

print("\n" + "=" * 120)
print("SECTION 8: BUSINESS LOGIC ANALYSIS")
print("=" * 120)

print("""
🤔 TWO POSSIBLE INTERPRETATIONS:

INTERPRETATION A: "Return Creates Credit Note" (Current Implementation)
────────────────────────────────────────────────────────────────────────
Return Approved:
  • Creates receivable (they owe us)
  • Balance: -693 (credit note issued)

Cash Refund Settled:
  • Just documents HOW they settled
  • No additional transaction needed
  • Balance stays: -693 (receivable remains)

Problem: ❌ If they gave us cash, why does balance show they still owe us?
         ❌ Balance never goes back to 0 even when fully settled


INTERPRETATION B: "Cash Refund is Actual Cash Receipt" (User's Expectation)
────────────────────────────────────────────────────────────────────────
Return Approved:
  • Creates receivable (they owe us)
  • Balance: -693 (they owe us cash)

Cash Refund Received:
  • We physically received cash
  • Creates "cash receipt" transaction: +693
  • Balance: -693 + 693 = 0 ✅
  • Receivable settled!

Result: ✅ Balance correctly shows 0 when cash received
        ✅ Balance only stays negative if settlement pending


🎯 CORRECT INTERPRETATION: B

Why? Because "Cash Refund SETTLEMENT" means we RECEIVED the cash!
If we received cash, our receivable should be settled (balance = 0).
The current system is treating it like a credit note that never gets closed.
""")

print("\n" + "=" * 120)
print("RECOMMENDATION")
print("=" * 120)

print("""
✅ FIX REQUIRED: Create transaction when cash refund is recorded

When PurchaseReturnSettlement with method='refund' is created:
  1. Create CompanyTransaction:
     - type: 'settlement' or 'cash_refund_receipt'
     - amount: +settlement_amount (POSITIVE - we received cash)
     - reference: settlement record ID or receipt number
     - description: "Cash refund received for {pr_number}"
  
  2. Update CompanyAccount balance:
     - Current: -2,979.90 (receivable)
     - Add cash received: +2,286.90
     - New balance: -693.00 (only unsettled return remaining)

Expected Final State:
  • Settled returns: Balance impact = 0
  • Unsettled returns: Balance shows receivable
  • Total balance: Rs. -693.00 (PR-20260118-003 pending)
  • When PR-003 is settled: Balance → 0.00 ✅
""")

print("\n" + "=" * 120)
