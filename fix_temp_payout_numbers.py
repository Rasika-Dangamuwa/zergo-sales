"""
Fix temporary payout numbers (CP-TEMP-001) to proper format
Run this once to update existing records
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.commission_schedule_models import CommissionPayoutHistory

def fix_temp_payout_numbers():
    """Update all records with CP-TEMP-001 to proper payout numbers"""
    
    # Find all records with temporary payout number
    temp_records = CommissionPayoutHistory.objects.filter(payout_number='CP-TEMP-001')
    
    count = temp_records.count()
    print(f"\nFound {count} record(s) with temporary payout number CP-TEMP-001")
    
    if count == 0:
        print("No records to fix!")
        return
    
    # Update each record
    for record in temp_records:
        old_number = record.payout_number
        
        # Temporarily set to None to trigger regeneration
        record.payout_number = None
        
        # Generate new number based on execution_date
        new_number = record.generate_payout_number()
        record.payout_number = new_number
        
        # Save without triggering save() override
        CommissionPayoutHistory.objects.filter(pk=record.pk).update(payout_number=new_number)
        
        print(f"  ✓ Updated record #{record.pk}: {old_number} → {new_number}")
        print(f"    Execution Date: {record.execution_date}")
        print(f"    Status: {record.get_status_display()}")
        print(f"    Amount: Rs. {record.total_amount_credited}")
        print()
    
    print(f"\n✅ Successfully updated {count} record(s)")
    print("You can now process manual payouts without conflicts!")

if __name__ == '__main__':
    fix_temp_payout_numbers()
