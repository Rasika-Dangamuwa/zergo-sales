"""Analyze Purchase Return #17 settlement status"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import PurchaseReturn, PurchaseReturnSettlement
from decimal import Decimal

# Get PR #17
pr = PurchaseReturn.objects.get(pk=17)

print("=" * 80)
print(f"PURCHASE RETURN #17 ANALYSIS")
print("=" * 80)
print(f"\nPR Number: {pr.pr_number}")
print(f"Company: {pr.company.company_name}")
print(f"Status: {pr.status}")
print(f"Settlement Status: {pr.settlement_status}")

print(f"\n--- FINANCIAL DETAILS ---")
print(f"Total Amount: Rs. {pr.total_amount:,.2f}")
print(f"Approved Amount: Rs. {pr.approved_amount:,.2f}")
print(f"Credit Amount: Rs. {pr.credit_amount:,.2f}")

print(f"\n--- REPLACEMENT DETAILS ---")
print(f"Replacement Expected: {pr.replacement_expected}")
print(f"Replacement Received: {pr.replacement_received}")
print(f"Replacement Value Expected: Rs. {pr.replacement_value_expected:,.2f}")
print(f"Replacement Value Received: Rs. {pr.replacement_received_value:,.2f}")
if pr.replacement_grn:
    print(f"Replacement GRN: {pr.replacement_grn.grn_number}")
else:
    print("Replacement GRN: None")

print(f"\n--- SETTLEMENT RECORDS (New Model) ---")
settlements = PurchaseReturnSettlement.objects.filter(purchase_return=pr)
if settlements.exists():
    total_settled = Decimal('0')
    for i, settlement in enumerate(settlements, 1):
        print(f"\n{i}. Method: {settlement.get_settlement_method_display()}")
        print(f"   Amount: Rs. {settlement.settlement_amount:,.2f}")
        if settlement.replacement_grn:
            print(f"   Replacement GRN: {settlement.replacement_grn.grn_number}")
            print(f"   GRN Total: Rs. {settlement.replacement_grn.total_amount:,.2f}")
            print(f"   GRN Outstanding: Rs. {settlement.replacement_grn.amount_outstanding:,.2f}")
        if settlement.credit_note_number:
            print(f"   Credit Note: {settlement.credit_note_number}")
        if settlement.refund_reference:
            print(f"   Refund Ref: {settlement.refund_reference}")
        print(f"   Created: {settlement.created_at.strftime('%Y-%m-%d %H:%M')}")
        total_settled += settlement.settlement_amount
    
    print(f"\nTotal Settled: Rs. {total_settled:,.2f}")
    print(f"Approved Amount: Rs. {pr.approved_amount:,.2f}")
    print(f"Match: {'✅ YES' if total_settled == pr.approved_amount else '❌ NO'}")
else:
    print("No settlement records found in PurchaseReturnSettlement table")

print(f"\n--- SETTLEMENT STATUS LOGIC ---")
print(f"Current settlement_status field: '{pr.settlement_status}'")

# Analyze why it's marked as fully_settled
reasons = []
if pr.settlement_status == 'fully_settled':
    if settlements.exists():
        total_settled = sum(s.settlement_amount for s in settlements)
        if total_settled >= pr.approved_amount:
            reasons.append(f"✅ Total settlements (Rs. {total_settled:,.2f}) >= Approved amount (Rs. {pr.approved_amount:,.2f})")
        else:
            reasons.append(f"❌ Total settlements (Rs. {total_settled:,.2f}) < Approved amount (Rs. {pr.approved_amount:,.2f}) - INCONSISTENT!")
    
    if pr.replacement_received:
        reasons.append(f"✅ Replacement marked as received (value: Rs. {pr.replacement_received_value:,.2f})")
    
    if pr.credit_amount > 0:
        reasons.append(f"✅ Credit amount recorded: Rs. {pr.credit_amount:,.2f}")

print("\nReasons for 'fully_settled' status:")
for reason in reasons:
    print(f"  {reason}")

print(f"\n--- RELATED TRANSACTIONS ---")
transactions = pr.account_transactions.all()
if transactions.exists():
    for txn in transactions:
        print(f"\n- Type: {txn.get_transaction_type_display()}")
        print(f"  Amount: Rs. {txn.amount:,.2f}")
        print(f"  Date: {txn.transaction_date}")
        print(f"  Reference: {txn.reference_number}")
        print(f"  Description: {txn.description}")
else:
    print("No company transactions linked to this return")

print("\n" + "=" * 80)
