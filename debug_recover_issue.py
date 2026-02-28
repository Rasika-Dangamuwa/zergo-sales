"""
Debug the recover advance issue - check account state when accessing the page
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from accounts.models import User
from accounts.money_account_models import UserMoneyAccount, MoneyTransaction, AdvanceRequest
from decimal import Decimal

def debug_recover_issue():
    """Debug the sales rep account state"""
    try:
        sales_rep = User.objects.get(username='rep')
        print(f"\n{'='*80}")
        print(f"Checking account for: {sales_rep.get_full_name()}")
        print(f"{'='*80}\n")
        
        # Simulate what the view does
        print("Step 1: get_or_create account")
        account, created = UserMoneyAccount.objects.get_or_create(
            user=sales_rep,
            defaults={'created_by': sales_rep}
        )
        print(f"  Created: {created}")
        print(f"  total_advance_given: {account.total_advance_given}")
        print(f"  total_advance_recovered: {account.total_advance_recovered}")
        print(f"  outstanding_advance (property): {account.outstanding_advance}")
        
        print("\nStep 2: refresh_from_db()")
        account.refresh_from_db()
        print(f"  total_advance_given: {account.total_advance_given}")
        print(f"  total_advance_recovered: {account.total_advance_recovered}")
        print(f"  outstanding_advance (property): {account.outstanding_advance}")
        
        print("\nStep 3: Call update_balance() manually")
        account.update_balance()
        print(f"  total_advance_given: {account.total_advance_given}")
        print(f"  total_advance_recovered: {account.total_advance_recovered}")
        print(f"  outstanding_advance (property): {account.outstanding_advance}")
        
        print("\nStep 4: Check transactions directly from DB")
        advances_given = MoneyTransaction.objects.filter(
            account=account,
            transaction_type='advance_given'
        )
        
        advances_recovered = MoneyTransaction.objects.filter(
            account=account,
            transaction_type='advance_recovery'
        )
        
        print(f"  Advances given transactions: {advances_given.count()}")
        for adv in advances_given:
            print(f"    - {adv.transaction_number}: Rs. {adv.amount}")
        
        print(f"  Advances recovered transactions: {advances_recovered.count()}")
        for adv in advances_recovered:
            print(f"    - {adv.transaction_number}: Rs. {adv.amount}")
        
        from django.db.models import Sum
        total_given = advances_given.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_recovered = advances_recovered.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        print(f"\n  Sum of advances given: Rs. {total_given}")
        print(f"  Sum of advances recovered: Rs. {total_recovered}")
        print(f"  Calculated outstanding: Rs. {total_given - total_recovered}")
        
        print(f"\n{'='*80}")
        
        # Check all advance requests
        print("\nAdvance Requests:")
        all_requests = AdvanceRequest.objects.filter(user=sales_rep)
        for req in all_requests:
            print(f"  {req.request_number}: Rs. {req.approved_amount if req.approved_amount else req.requested_amount}")
            print(f"    Status: {req.status}")
            if req.status == 'paid':
                print(f"    Paid at: {req.paid_at}")
        
        print(f"{'='*80}\n")
        
    except User.DoesNotExist:
        print("Sales rep not found")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_recover_issue()
