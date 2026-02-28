"""
Check which users should have commission tracking
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.contrib.auth import get_user_model
from payments.models import SalesAccountSettlement

User = get_user_model()

print("=" * 80)
print("USER COMMISSION TRACKING ANALYSIS")
print("=" * 80)
print()

# Get all users
users = User.objects.all()

for user in users:
    print(f"User: {user.username} ({user.get_full_name()})")
    print(f"  User Type: {user.user_type}")
    print(f"  Is Sales Rep: {user.is_sales_rep}")
    print(f"  Commission Transactions: {user.commission_transactions.count()}")
    
    # Check settlements received by this user
    settlements = SalesAccountSettlement.objects.filter(received_by=user)
    print(f"  Settlements Received: {settlements.count()}")
    
    # Check if this user should have commissions
    should_have_commissions = user.is_sales_rep
    has_commissions = user.commission_transactions.count() > 0
    
    if should_have_commissions and not has_commissions:
        print(f"  ⚠️  WARNING: Sales rep with no commission transactions!")
    elif not should_have_commissions and has_commissions:
        print(f"  ⚠️  WARNING: Non-sales-rep with commission transactions!")
    elif should_have_commissions and has_commissions:
        print(f"  ✓ Correct: Sales rep with commissions")
    else:
        print(f"  ✓ Correct: Non-sales-rep without commissions")
    
    print()
