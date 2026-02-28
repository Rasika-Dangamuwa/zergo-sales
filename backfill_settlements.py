from sales.models import CommissionTransaction
from payments.models import SalesAccountSettlement

# Backfill settlement references
updated = 0
payment_txns = CommissionTransaction.objects.filter(
    transaction_type='payment_received',
    settlement__isnull=True
).select_related('bill')

print(f"Backfilling {payment_txns.count()} transactions...")

for txn in payment_txns:
    settlement = SalesAccountSettlement.objects.filter(
        bill=txn.bill,
        amount=txn.collected_amount,
        settlement_date__date=txn.transaction_date.date()
    ).first()
    
    if settlement:
        txn.settlement = settlement
        txn.save(update_fields=['settlement'])
        updated += 1

print(f"✓ Updated {updated} commission transactions")
print(f"Remaining without settlement: {CommissionTransaction.objects.filter(transaction_type='payment_received', settlement__isnull=True).count()}")
