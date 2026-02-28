from sales.models import SalesAccountSettlement, CommissionTransaction
from datetime import datetime, timedelta
from django.db.models import Q

print("=" * 80)
print("CHECKING RECENT SETTLEMENTS AND COMMISSION TRACKING")
print("=" * 80)

# Get all settlements from the last 7 days
recent_date = datetime.now() - timedelta(days=7)

settlements = SalesAccountSettlement.objects.filter(
    created_at__gte=recent_date
).order_by('-id')[:30]

print(f"\nFound {settlements.count()} settlements in last 7 days:")
print(f"{'ID':<6} {'Bill':<12} {'Method':<20} {'Amount':<12} {'Status':<12} {'Commission?'}")
print("-" * 80)

missing = []

for settlement in settlements:
    # Check if commission exists for this settlement
    commission = CommissionTransaction.objects.filter(
        Q(settlement=settlement) | Q(notes__icontains=f"Settlement #{settlement.id}")
    ).first()
    
    has_commission = "✅ YES" if commission else "❌ NO"
    
    bill_num = settlement.bill.bill_number if hasattr(settlement.bill, 'bill_number') else settlement.bill.sale_number
    print(f"{settlement.id:<6} {bill_num:<12} {settlement.settlement_method:<20} "
          f"Rs. {settlement.amount:>8} {settlement.settlement_status:<12} {has_commission}")
    
    if not commission and settlement.settlement_status == 'completed':
        missing.append(settlement)

print(f"\n{'=' * 80}")
print(f"MISSING COMMISSIONS: {len(missing)} completed settlements without commission tracking")
print(f"{'=' * 80}")

if missing:
    print("\nSettlements that need commission tracking:")
    for s in missing:
        bill_num = s.bill.bill_number if hasattr(s.bill, 'bill_number') else s.bill.sale_number
        print(f"  - Settlement #{s.id}: Bill {bill_num}, {s.settlement_method}, Rs. {s.amount}")

print("\n" + "=" * 80)
print("LAST 20 COMMISSION TRANSACTIONS")
print("=" * 80)

all_commissions = CommissionTransaction.objects.all().order_by('-id')[:20]
print(f"{'ID':<6} {'Type':<25} {'Bill':<12} {'Amount':<12} {'Commission':<12} {'Date'}")
print("-" * 80)

for comm in all_commissions:
    bill_num = "N/A"
    if comm.bill:
        bill_num = comm.bill.bill_number if hasattr(comm.bill, 'bill_number') else comm.bill.sale_number
    print(f"{comm.id:<6} {comm.transaction_type:<25} {bill_num:<12} "
          f"Rs. {comm.transaction_amount:>8} Rs. {comm.commission_earned:>8} {comm.transaction_date.strftime('%Y-%m-%d')}")
