"""
Fix FOC Account Balances - Correct Business Logic
Run this script to recalculate all FOC account balances with the corrected logic.

Previous bug: FOC Restored was added to FOC Received (wrong!)
Correct logic: FOC Restored reduces FOC Given (returns reverse what we gave)
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import FOCValueAccount

def fix_foc_balances():
    """Recalculate all FOC account balances with correct logic"""
    
    print("=" * 60)
    print("FOC Account Balance Correction")
    print("=" * 60)
    print()
    
    accounts = FOCValueAccount.objects.all()
    
    if not accounts:
        print("No FOC accounts found.")
        return
    
    print(f"Found {accounts.count()} FOC account(s) to recalculate...\n")
    
    for account in accounts:
        print(f"Company: {account.company.company_name}")
        print(f"  Before:")
        print(f"    - FOC Received: Rs. {account.total_foc_received_value:,.2f}")
        print(f"    - FOC Given: Rs. {account.total_foc_given_value:,.2f}")
        print(f"    - Net Balance: Rs. {account.net_foc_value:,.2f}")
        
        # Recalculate using corrected logic
        account.update_balance()
        account.save()
        
        print(f"  After (CORRECTED):")
        print(f"    - FOC Received: Rs. {account.total_foc_received_value:,.2f}")
        print(f"    - FOC Given: Rs. {account.total_foc_given_value:,.2f}")
        print(f"    - Net Balance: Rs. {account.net_foc_value:,.2f}")
        print()
    
    print("=" * 60)
    print("✅ All FOC account balances recalculated successfully!")
    print("=" * 60)

if __name__ == '__main__':
    fix_foc_balances()
