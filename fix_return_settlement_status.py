#!/usr/bin/env python
"""
Data Migration: Fix inconsistent settlement_status for returns
This script fixes approved returns that have incorrect settlement_status values
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return
from django.db import transaction

@transaction.atomic
def fix_return_settlement_status():
    """
    Fix settlement_status for returns based on business rules:
    
    1. Cash settlement method:
       - If approved + has cash_receipt_number -> settled_cash
       - If approved + no cash_receipt_number -> unsettled (awaiting payment)
       - If pending + has cash_receipt_number -> unsettled (awaiting approval)
       - If pending + no cash_receipt_number -> unsettled
       - If rejected -> cancelled (if cash was paid) or unsettled
    
    2. Credit note settlement method:
       - If approved -> available (credit available for use)
       - If pending -> unsettled
       - If rejected -> unsettled
    
    3. Next bill settlement method:
       - If approved -> available
       - If pending -> unsettled
       - If rejected -> unsettled
    """
    
    print("Starting settlement_status migration...\n")
    
    # Get all returns
    all_returns = Return.objects.all()
    total = all_returns.count()
    fixed_count = 0
    
    print(f"Total returns to check: {total}\n")
    print("="*80)
    
    for ret in all_returns:
        old_status = ret.settlement_status
        new_status = None
        
        # Determine correct settlement_status
        if ret.settlement_method == 'cash':
            if ret.return_status == 'approved':
                if ret.cash_receipt_number:
                    new_status = 'settled_cash'
                else:
                    new_status = 'unsettled'  # Approved but not paid yet
            elif ret.return_status == 'pending':
                new_status = 'unsettled'  # Always unsettled when pending
            elif ret.return_status == 'rejected':
                if ret.cash_receipt_number:
                    new_status = 'cancelled'  # Cash was paid but return rejected
                else:
                    new_status = 'unsettled'
                    
        elif ret.settlement_method == 'credit_note':
            if ret.return_status == 'approved':
                # Check if credit has been applied
                if ret.applied_amount > 0:
                    if ret.applied_amount >= ret.total_amount:
                        new_status = 'fully_applied'
                    else:
                        new_status = 'partially_applied'
                else:
                    new_status = 'available'  # Credit available for use
            else:  # pending or rejected
                new_status = 'unsettled'
                
        elif ret.settlement_method == 'next_bill':
            if ret.return_status == 'approved':
                # Check if applied to bill
                if ret.applied_amount > 0:
                    if ret.applied_amount >= ret.total_amount:
                        new_status = 'fully_applied'
                    else:
                        new_status = 'partially_applied'
                else:
                    new_status = 'available'
            else:  # pending or rejected
                new_status = 'unsettled'
        
        # Update if status changed
        if new_status and new_status != old_status:
            ret.settlement_status = new_status
            ret.save(update_fields=['settlement_status'])
            fixed_count += 1
            
            print(f"Return #{ret.id} - {ret.return_number}")
            print(f"  Status: {ret.return_status}")
            print(f"  Settlement Method: {ret.settlement_method}")
            print(f"  OLD Settlement Status: {old_status}")
            print(f"  NEW Settlement Status: {new_status}")
            if ret.cash_receipt_number:
                print(f"  Cash Receipt: {ret.cash_receipt_number}")
            if ret.applied_amount > 0:
                print(f"  Applied Amount: Rs. {ret.applied_amount} / Rs. {ret.total_amount}")
            print()
    
    print("="*80)
    print(f"\nMigration Complete!")
    print(f"Total returns checked: {total}")
    print(f"Returns updated: {fixed_count}")
    print(f"Returns unchanged: {total - fixed_count}")
    
    # Show summary by settlement_status
    print("\n" + "="*80)
    print("UPDATED SETTLEMENT STATUS BREAKDOWN")
    print("="*80)
    
    from django.db.models import Count, Sum
    settlement_counts = Return.objects.values('settlement_status').annotate(
        count=Count('id'), 
        total=Sum('total_amount')
    ).order_by('settlement_status')
    
    for s in settlement_counts:
        print(f"{s['settlement_status'].upper()}: {s['count']} returns, Total Rs. {s['total'] or 0}")

if __name__ == '__main__':
    try:
        fix_return_settlement_status()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
