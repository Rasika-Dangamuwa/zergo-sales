"""
Create missing commission transactions for Bill #124 cancelled settlements
This handles the special case where settlements were cancelled but never had
the original payment_received commission created.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import transaction
from sales.models import Bill, CommissionTransaction
from payments.models import SalesAccountSettlement
from django.utils import timezone

def create_bill_124_commissions():
    print("\n" + "="*80)
    print("CREATING MISSING COMMISSION TRANSACTIONS FOR BILL #124")
    print("="*80)
    
    bill = Bill.objects.get(id=124)
    sales_rep = bill.sales_rep
    
    print(f"\nBill: {bill.bill_number}")
    print(f"Sales Rep: {sales_rep.get_full_name()}")
    print(f"Total: Rs. {bill.total_amount}")
    
    # 1. Create bill creation commission
    print(f"\n{'='*60}")
    print("1. BILL CREATION COMMISSION:")
    
    bill_commission_exists = CommissionTransaction.objects.filter(
        bill=bill,
        transaction_type='bill_created'
    ).exists()
    
    if not bill_commission_exists:
        with transaction.atomic():
            bill_commission = CommissionTransaction.create_for_bill(bill)
            print(f"   ✅ Created bill commission (ID: {bill_commission.id})")
            print(f"      Sales Amount: Rs. {bill_commission.sales_amount}")
            print(f"      Commission: Rs. {bill_commission.commission_earned}")
    else:
        print(f"   ⏭️ Bill commission already exists")
    
    # 2. Create cancellation tracking for each cancelled settlement
    print(f"\n{'='*60}")
    print("2. CANCELLED SETTLEMENT TRACKING:")
    
    cancelled_settlements = SalesAccountSettlement.objects.filter(
        bill=bill,
        settlement_status='cancelled'
    ).order_by('id')
    
    created_count = 0
    
    for settlement in cancelled_settlements:
        print(f"\n   Settlement #{settlement.id} - {settlement.settlement_number}")
        print(f"   Method: {settlement.settlement_method}, Amount: Rs. {settlement.amount}")
        
        # Check if already has commission transaction
        existing = CommissionTransaction.objects.filter(settlement=settlement).first()
        
        if existing:
            print(f"      ⏭️ Already has commission (ID: {existing.id}, Type: {existing.transaction_type})")
            continue
        
        # Create cancellation tracking transaction
        # For cancelled settlements that never had a payment_received, we create payment_cancelled directly
        with transaction.atomic():
            commission = CommissionTransaction.objects.create(
                transaction_type='payment_cancelled',
                transaction_date=settlement.settlement_date,  # Use original settlement date
                sales_rep=sales_rep,
                bill=bill,
                settlement=settlement,
                collected_amount=Decimal('0'),  # Nothing was collected
                return_amount=Decimal('0'),
                sales_amount=Decimal('0'),
                # applicable_rate will be set automatically in save()
                commission_earned=Decimal('0'),  # No commission earned or lost
                running_balance=Decimal('0'),  # Will be recalculated
                notes=f"Settlement {settlement.settlement_number} cancelled - No payment was completed before cancellation"
            )
            print(f"      ✅ Created cancellation tracking (ID: {commission.id})")
            print(f"         Type: {commission.transaction_type}")
            print(f"         Commission: Rs. {commission.commission_earned}")
            created_count += 1
    
    print(f"\n{'='*80}")
    print(f"SUMMARY:")
    print(f"  - Bill commission: {'Created' if not bill_commission_exists else 'Already exists'}")
    print(f"  - Cancellation tracking created: {created_count}")
    print(f"  - Total new transactions: {(0 if bill_commission_exists else 1) + created_count}")
    print("="*80 + "\n")

if __name__ == '__main__':
    from decimal import Decimal
    create_bill_124_commissions()
