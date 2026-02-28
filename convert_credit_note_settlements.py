"""
Convert existing credit_note settlements to refund settlements.

Rationale: Credit note settlement is redundant because the purchase return
itself already acts as a credit. Settlement methods should only be for actual
transfers: cash refund or replacement goods.

This script converts credit_note settlements to refund type, preserving the
credit note number as the refund reference.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import PurchaseReturnSettlement

print("=" * 80)
print("Converting Credit Note Settlements to Cash Refunds")
print("=" * 80)

# Find all credit_note settlements
credit_note_settlements = PurchaseReturnSettlement.objects.filter(
    settlement_method='credit_note'
)

total = credit_note_settlements.count()
print(f"\nFound {total} credit note settlement(s)")

if total == 0:
    print("✅ No credit note settlements to convert.")
else:
    print("\nConverting to cash refunds...")
    print("-" * 80)
    
    for settlement in credit_note_settlements:
        print(f"\n{settlement.purchase_return.pr_number}:")
        print(f"  Amount: Rs. {settlement.settlement_amount:,.2f}")
        print(f"  Credit Note Number: {settlement.credit_note_number}")
        
        # Convert to refund
        settlement.settlement_method = 'refund'
        # Preserve credit note number as refund reference
        settlement.refund_reference = f"Credit Note: {settlement.credit_note_number}"
        settlement.save()
        
        print(f"  ✅ Converted to: Cash Refund (ref: {settlement.refund_reference})")
    
    print("\n" + "=" * 80)
    print(f"✅ Converted {total} settlement(s) successfully")
    print("=" * 80)
    
    # Verify
    remaining = PurchaseReturnSettlement.objects.filter(
        settlement_method='credit_note'
    ).count()
    
    refunds = PurchaseReturnSettlement.objects.filter(
        settlement_method='refund'
    ).count()
    
    print(f"\nVerification:")
    print(f"  Credit Note settlements remaining: {remaining}")
    print(f"  Total Cash Refund settlements: {refunds}")

print("\nNote: The return itself acts as a credit. Settlement methods are only for")
print("actual transfers (cash refund or replacement goods).")
