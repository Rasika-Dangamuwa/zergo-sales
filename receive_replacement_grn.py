"""
Receive the replacement GRN to complete the settlement and bring balance to 0
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Purchase, CompanyAccount
from decimal import Decimal as D

print("=" * 120)
print("RECEIVE REPLACEMENT GRN TO COMPLETE SETTLEMENT")
print("=" * 120)

try:
    grn = Purchase.objects.get(grn_number='GRN-20260118-008')
    
    print(f"\n📦 GRN: {grn.grn_number}")
    print(f"   Company: {grn.company.company_name}")
    print(f"   Amount: Rs. {grn.total_amount:,.2f}")
    print(f"   Current Status: {grn.status}")
    print(f"   Stock Updated: {grn.stock_updated}")
    
    if grn.status == 'draft':
        print(f"\n⚡ Marking GRN as received...")
        
        # Get current balance
        account = CompanyAccount.objects.get(company=grn.company)
        print(f"\n   Balance before: Rs. {account.current_balance:,.2f}")
        
        # Mark as received (this will auto-create transaction)
        grn.status = 'received'
        grn.save()
        
        print(f"   ✅ GRN marked as received")
        print(f"   ✅ Company transaction auto-created")
        
        # Refresh and show new balance
        account.refresh_from_db()
        print(f"   Balance after: Rs. {account.current_balance:,.2f}")
        
        if abs(account.current_balance) < D('0.01'):
            print(f"\n   🎉 SUCCESS! Balance is now Rs. 0.00")
            print(f"   ✅ All returns and GRNs are settled!")
        else:
            print(f"\n   ⚠️  Balance is still Rs. {account.current_balance:,.2f}")
    else:
        print(f"\n   ℹ️  GRN already received, status: {grn.status}")
        
except Purchase.DoesNotExist:
    print(f"\n❌ GRN-20260118-008 not found")

print("\n" + "=" * 120)
