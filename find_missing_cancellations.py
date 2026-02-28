"""
Check if there are ANY recent cancellations that might not be showing reversal transactions
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from payments.models import SalesAccountSettlement
from django.utils import timezone
from datetime import timedelta

print("=" * 80)
print("CHECKING FOR RECENTLY CANCELLED SETTLEMENTS WITHOUT REVERSALS")
print("=" * 80)
print()

# Get all cancelled settlements from the last 24 hours
recent_time = timezone.now() - timedelta(hours=24)
cancelled_settlements = SalesAccountSettlement.objects.filter(
    settlement_status='cancelled',
    updated_at__gte=recent_time
).order_by('-updated_at')

print(f"Found {cancelled_settlements.count()} recently cancelled settlements")
print()

issues_found = 0

for settlement in cancelled_settlements:
    # Check for commission transactions
    payment_received = CommissionTransaction.objects.filter(
        settlement=settlement,
        transaction_type='payment_received'
    ).first()
    
    payment_cancelled = CommissionTransaction.objects.filter(
        settlement=settlement,
        transaction_type='payment_cancelled'
    ).first()
    
    has_issue = payment_received and not payment_cancelled
    
    if has_issue:
        issues_found += 1
        print(f"❌ ISSUE #{issues_found}: {settlement.settlement_number}")
        print(f"   Status: {settlement.settlement_status}")
        print(f"   Amount: Rs. {settlement.amount}")
        print(f"   Bill: {settlement.bill.bill_number if settlement.bill else 'None'}")
        print(f"   Received By: {settlement.received_by.username if settlement.received_by else 'None'}")
        print(f"   Updated: {settlement.updated_at}")
        print(f"   Has payment_received: YES (ID {payment_received.id})")
        print(f"   Has payment_cancelled: NO ❌")
        print()
        
        # Show the payment_received transaction details
        print(f"   Original Transaction:")
        print(f"     Date: {payment_received.transaction_date}")
        print(f"     Sales Rep: {payment_received.sales_rep.username}")
        print(f"     Commission: {payment_received.commission_earned}")
        print(f"     Balance: {payment_received.running_balance}")
        print()

if issues_found == 0:
    print("✓ No issues found - all cancelled settlements have proper reversals")
else:
    print("=" * 80)
    print(f"SUMMARY: Found {issues_found} cancelled settlements missing reversal transactions")
    print("=" * 80)
    print()
    print("These settlements were cancelled but the commission system didn't create")
    print("the reversal (payment_cancelled) transaction.")
    print()
    print("Possible causes:")
    print("1. Cancelled before commission signal system was implemented")
    print("2. Signal handler failed/errored during cancellation")
    print("3. Settlement cancelled directly in database bypassing Django ORM")
    print("4. Commission signal not connected at time of cancellation")
