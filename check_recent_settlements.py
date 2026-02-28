import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_distributors.settings')
django.setup()

from sales.models import SalesAccountSettlement, CommissionTransaction
from django.db.models import Q

print("=" * 80)
print("CHECKING RECENT SETTLEMENTS AND COMMISSION TRACKING")
print("=" * 80)

# Get all settlements from the last 7 days
from datetime import datetime, timedelta
recent_date = datetime.now() - timedelta(days=7)

settlements = SalesAccountSettlement.objects.filter(
    created_at__gte=recent_date
).order_by('-id')[:20]

print(f"\nFound {settlements.count()} settlements in last 7 days:")
print(f"{'ID':<6} {'Bill':<12} {'Method':<20} {'Amount':<12} {'Status':<12} {'Commission?'}")
print("-" * 80)

for settlement in settlements:
    # Check if commission exists for this settlement
    commission = CommissionTransaction.objects.filter(
        Q(settlement_ref=settlement) | Q(notes__icontains=f"Settlement #{settlement.id}")
    ).first()
    
    has_commission = "✅ YES" if commission else "❌ NO"
    
    print(f"{settlement.id:<6} {settlement.bill.sale_number:<12} {settlement.settlement_method:<20} "
          f"Rs. {settlement.amount:>8} {settlement.status:<12} {has_commission}")
    
    if commission:
        print(f"       → Commission: {commission.transaction_type}, Rs. {commission.commission_earned}")

print("\n" + "=" * 80)
print("CHECKING ALL COMMISSION TRANSACTIONS")
print("=" * 80)

all_commissions = CommissionTransaction.objects.all().order_by('-id')[:20]
print(f"\nLast 20 commission transactions:")
print(f"{'ID':<6} {'Type':<25} {'Bill':<12} {'Amount':<12} {'Commission':<12} {'Date'}")
print("-" * 80)

for comm in all_commissions:
    bill_num = comm.bill.sale_number if comm.bill else "N/A"
    print(f"{comm.id:<6} {comm.transaction_type:<25} {bill_num:<12} "
          f"Rs. {comm.transaction_amount:>8} Rs. {comm.commission_earned:>8} {comm.transaction_date}")

print("\n" + "=" * 80)
