"""
Test to verify "This Month" earnings are preserved after payout
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from accounts.models import User
from datetime import date
from decimal import Decimal

def test_month_earnings_preserved():
    """Verify that THIS MONTH earnings remain unchanged after payout"""
    
    print("\n=== Testing Month Earnings Preservation ===\n")
    
    rep = User.objects.get(username='rep')
    today = date.today()
    
    # Get this month's summary using the model method
    summary = CommissionTransaction.get_month_summary(rep, today.year, today.month)
    
    print(f"Sales Representative: {rep.get_full_name()}")
    print(f"Month: {today.strftime('%B %Y')}\n")
    
    print("Month Summary (Historical Earnings):")
    print(f"  Total Sales Amount: Rs. {summary['total_sales']:,.2f}")
    print(f"  Total Collected: Rs. {summary['total_collected']:,.2f}")
    print(f"  Total Returns: Rs. {summary['total_returns']:,.2f}")
    print(f"  Total Commission Earned: Rs. {summary['total_commission']:,.2f}")
    
    print(f"\nCurrent Balance (What is Owed):")
    current_balance = CommissionTransaction.get_rep_balance(rep)
    print(f"  Rs. {current_balance:,.2f}")
    
    print("\n" + "="*60)
    print("✅ Expected Behavior:")
    print("="*60)
    print("  • THIS MONTH: Rs. 162.00 (what was EARNED - never changes)")
    print("  • CURRENT BALANCE: Rs. 0.00 (what is OWED - cleared after payout)")
    print("="*60)
    
    # Verify the values
    if summary['total_commission'] == Decimal('162.00'):
        print("\n✅ SUCCESS: This month earnings correctly showing Rs. 162.00")
    else:
        print(f"\n⚠️  WARNING: This month showing Rs. {summary['total_commission']} (expected Rs. 162.00)")
    
    if current_balance == Decimal('0.00'):
        print("✅ SUCCESS: Current balance correctly cleared to Rs. 0.00")
    else:
        print(f"⚠️  WARNING: Current balance is Rs. {current_balance} (expected Rs. 0.00)")
    
    print("\n")

if __name__ == '__main__':
    test_month_earnings_preserved()
