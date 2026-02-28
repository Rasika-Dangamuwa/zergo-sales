"""
Verify payout number system is working correctly
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.commission_schedule_models import CommissionPayoutHistory

def verify_payout_numbers():
    """Check all payout numbers are valid"""
    
    print("\n=== Payout Number Verification ===\n")
    
    # Check for any temp numbers
    temp_count = CommissionPayoutHistory.objects.filter(payout_number='CP-TEMP-001').count()
    print(f"Records with CP-TEMP-001: {temp_count}")
    
    if temp_count > 0:
        print("⚠️  WARNING: Still have temporary payout numbers!")
    else:
        print("✅ No temporary payout numbers found")
    
    # Show all existing payout numbers
    all_payouts = CommissionPayoutHistory.objects.all().order_by('-execution_date')
    
    print(f"\nTotal payout records: {all_payouts.count()}")
    print("\nAll Payout Numbers:")
    print("-" * 80)
    
    for payout in all_payouts:
        status_icon = "✓" if payout.status == 'success' else "✗"
        manual_flag = "(MANUAL)" if payout.is_manual else "(AUTO)"
        print(f"{status_icon} {payout.payout_number:<20} {payout.execution_date.strftime('%Y-%m-%d %H:%M')} {manual_flag:10} Rs. {payout.total_amount_credited:>10,.2f}")
    
    print("-" * 80)
    print("\n✅ Verification complete!\n")

if __name__ == '__main__':
    verify_payout_numbers()
