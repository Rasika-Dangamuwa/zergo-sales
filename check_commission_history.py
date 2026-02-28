"""
Check CommissionTransaction history for the sales rep
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from accounts.models import User

def check_commission_history():
    """Show all commission transactions for the sales rep"""
    
    reps = User.objects.filter(user_type='sales_rep')
    
    for rep in reps:
        print(f"\n=== Commission History for {rep.get_full_name()} ({rep.username}) ===\n")
        
        txns = CommissionTransaction.objects.filter(sales_rep=rep).order_by('transaction_date', 'created_at')
        
        if not txns.exists():
            print("No commission transactions found.\n")
            continue
        
        print(f"{'Date':<20} {'Type':<20} {'Commission':<15} {'Running Balance':<15} {'Notes'}")
        print("=" * 120)
        
        for txn in txns:
            print(f"{txn.transaction_date.strftime('%Y-%m-%d %H:%M'):<20} "
                  f"{txn.get_transaction_type_display():<20} "
                  f"{txn.commission_earned:>13.2f}   "
                  f"{txn.running_balance:>13.2f}   "
                  f"{txn.notes or ''[:50]}")
        
        print("=" * 120)
        
        current_balance = CommissionTransaction.get_rep_balance(rep)
        print(f"\nCurrent Balance: Rs. {current_balance:,.2f}\n")

if __name__ == '__main__':
    check_commission_history()
