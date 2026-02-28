"""
Find and create missing commissions for completed settlements
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import transaction
from payments.models import SalesAccountSettlement
from sales.models import CommissionTransaction
from decimal import Decimal

def find_missing_commissions():
    """Find all completed settlements without commission transactions"""
    
    print("\n" + "="*80)
    print("FINDING SETTLEMENTS WITHOUT COMMISSIONS")
    print("="*80)
    
    # Get all completed settlements
    completed_settlements = SalesAccountSettlement.objects.filter(
        settlement_status='completed'
    ).order_by('id')
    
    print(f"\nTotal completed settlements: {completed_settlements.count()}")
    
    missing = []
    has_commission = []
    
    for settlement in completed_settlements:
        # Check if commission exists
        commission = CommissionTransaction.objects.filter(
            settlement=settlement
        ).first()
        
        if not commission:
            missing.append(settlement)
            print(f"\n❌ MISSING: Settlement #{settlement.id}")
            print(f"   Bill: {settlement.bill.bill_number or settlement.bill.sale_number}")
            print(f"   Method: {settlement.settlement_method}")
            print(f"   Amount: Rs. {settlement.amount}")
            print(f"   Date: {settlement.created_at.strftime('%Y-%m-%d')}")
        else:
            has_commission.append(settlement)
    
    print(f"\n" + "="*80)
    print(f"SUMMARY:")
    print(f"  Total completed settlements: {completed_settlements.count()}")
    print(f"  With commission: {len(has_commission)}")
    print(f"  Missing commission: {len(missing)}")
    print("="*80)
    
    if missing:
        print(f"\n{'='*80}")
        print("CREATING MISSING COMMISSIONS")
        print("="*80)
        
        created_count = 0
        for settlement in missing:
            try:
                with transaction.atomic():
                    # Use the classmethod to create commission
                    commission = CommissionTransaction.create_for_payment(
                        payment=settlement,
                        bill=settlement.bill
                    )
                    print(f"\n✅ Created commission for Settlement #{settlement.id}")
                    print(f"   Commission ID: {commission.id}")
                    print(f"   Earned: Rs. {commission.commission_earned}")
                    created_count += 1
            except Exception as e:
                print(f"\n❌ Error creating commission for Settlement #{settlement.id}: {e}")
        
        print(f"\n{'='*80}")
        print(f"Created {created_count} commission transactions")
        print("="*80 + "\n")

if __name__ == '__main__':
    find_missing_commissions()
