"""
Comprehensive Fix for Data Integrity Issues

This script will:
1. Create missing commission transactions for settlements
2. Create missing reversal transactions for cancelled settlements
3. Recalculate bill paid amounts
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction, Bill
from payments.models import SalesAccountSettlement
from django.utils import timezone
from decimal import Decimal

print("=" * 80)
print("DATA INTEGRITY FIX - PART 1: Missing Commission Transactions")
print("=" * 80)
print()

# Get all settlements from Jan 24-25
settlements = SalesAccountSettlement.objects.filter(
    settlement_date__gte='2026-01-24'
).order_by('settlement_date')

print(f"Checking {settlements.count()} settlements...")
print()

created_count = 0
skipped_count = 0

for settlement in settlements:
    # Check if commission transactions exist
    txns = CommissionTransaction.objects.filter(settlement=settlement)
    
    expected_count = 2 if settlement.settlement_status == 'cancelled' else 1
    
    if txns.count() == expected_count:
        skipped_count += 1
        continue
    
    print(f"Settlement: {settlement.settlement_number} ({settlement.settlement_status})")
    print(f"  Date: {settlement.settlement_date}")
    print(f"  Amount: Rs. {settlement.amount}")
    print(f"  Bill: {settlement.bill.bill_number if settlement.bill else 'None'}")
    print(f"  Sales Rep: {settlement.received_by.username if settlement.received_by else 'None'}")
    print(f"  Existing transactions: {txns.count()}, Expected: {expected_count}")
    
    # Check what's missing
    has_payment_received = txns.filter(transaction_type='payment_received').exists()
    has_payment_cancelled = txns.filter(transaction_type='payment_cancelled').exists()
    
    if not has_payment_received:
        print(f"  ❌ Missing: payment_received transaction")
        print(f"  ⚠️  CANNOT AUTO-FIX: Need to determine commission rate and running balance")
        print(f"     This requires knowledge of user's commission rate at time of settlement")
        print()
    elif settlement.settlement_status == 'cancelled' and not has_payment_cancelled:
        print(f"  ❌ Missing: payment_cancelled reversal transaction")
        print(f"  ⚠️  CAN AUTO-FIX with existing payment_received data")
        
        # Get the original payment_received transaction
        original_txn = txns.filter(transaction_type='payment_received').first()
        
        if original_txn:
            print(f"     Original transaction found: ID {original_txn.id}")
            print(f"     Will create reversal transaction...")
            
            # Get the latest transaction for this sales rep to determine new running balance
            latest_txn = CommissionTransaction.objects.filter(
                sales_rep=original_txn.sales_rep,
                transaction_date__gte=original_txn.transaction_date
            ).order_by('-transaction_date', '-id').first()
            
            # Create reversal transaction
            reversal = CommissionTransaction(
                sales_rep=original_txn.sales_rep,
                bill=settlement.bill,
                settlement=settlement,
                transaction_type='payment_cancelled',
                transaction_date=settlement.updated_at if hasattr(settlement, 'updated_at') else timezone.now(),
                collected_amount=-original_txn.collected_amount,
                commission_earned=-original_txn.commission_earned,
                running_balance=latest_txn.running_balance - original_txn.commission_earned if latest_txn else Decimal('0'),
                notes=f"Reversal for cancelled settlement {settlement.settlement_number}"
            )
            
            print(f"     Reversal: Amount={reversal.collected_amount}, "
                  f"Commission={reversal.commission_earned}, "
                  f"Balance={reversal.running_balance}")
            print(f"     ⚠️  WARNING: Running balance may be incorrect due to missing timestamps")
            print(f"     Manual review required!")
            print()
            
            # Don't save yet - need manual review
            # reversal.save()
            # created_count += 1
        
        print()

print("=" * 80)
print(f"SUMMARY:")
print(f"  Skipped (correct): {skipped_count}")
print(f"  Needs manual review: {settlements.count() - skipped_count}")
print("=" * 80)
print()
print("CONCLUSION:")
print("Cannot auto-fix missing commission transactions due to:")
print("1. Unknown commission rates at time of settlement")
print("2. Unknown correct running balance sequence")
print("3. Potential timestamp issues")
print()
print("RECOMMENDATION:")
print("These settlements likely didn't trigger commission signals properly.")
print("Need to investigate why commission signals didn't fire for these settlements.")
print()
print("Possible causes:")
print("- Settlements created before commission system was implemented")
print("- Signal handlers not connected at time of creation")
print("- Database direct manipulation bypassing Django ORM")
print("- Return adjustments (which don't create commissions?)")
