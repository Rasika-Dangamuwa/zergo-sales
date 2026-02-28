"""
Debug script to check the Sales Representative's account and transactions
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from accounts.models import User
from accounts.money_account_models import UserMoneyAccount, MoneyTransaction
from decimal import Decimal

def debug_sales_rep_account():
    """Check Sales Rep's account in detail"""
    try:
        sales_rep = User.objects.get(username='rep')
        print(f"\n{'='*80}")
        print(f"User: {sales_rep.get_full_name()} (@{sales_rep.username})")
        print(f"{'='*80}\n")
        
        # Get account
        account = sales_rep.money_account
        print("ACCOUNT TOTALS:")
        print(f"  Opening Balance: Rs. {account.opening_balance:,.2f}")
        print(f"  Total Credited: Rs. {account.total_credited:,.2f}")
        print(f"  Total Debited: Rs. {account.total_debited:,.2f}")
        print(f"  Total Advance Given: Rs. {account.total_advance_given:,.2f}")
        print(f"  Total Advance Recovered: Rs. {account.total_advance_recovered:,.2f}")
        print(f"  Current Balance: Rs. {account.current_balance:,.2f}")
        print(f"  Outstanding Advance (property): Rs. {account.outstanding_advance:,.2f}")
        
        # Calculate outstanding from formula
        outstanding_calc = max(account.total_advance_given - account.total_advance_recovered, Decimal('0.00'))
        print(f"  Outstanding Advance (calculated): Rs. {outstanding_calc:,.2f}")
        
        print("\n" + "="*80)
        print("ALL TRANSACTIONS:")
        print("="*80)
        
        transactions = account.transactions.all().order_by('transaction_date', 'id')
        for txn in transactions:
            sign = ""
            if txn.transaction_type in ['credit', 'commission_payment', 'bonus', 'adjustment_credit', 'advance_recovery']:
                sign = "+"
            else:
                sign = "-"
            
            print(f"\n{txn.transaction_number}")
            print(f"  Date: {txn.transaction_date}")
            print(f"  Type: {txn.get_transaction_type_display()}")
            print(f"  Amount: {sign}Rs. {txn.amount:,.2f}")
            print(f"  Description: {txn.description}")
            if txn.advance_request:
                print(f"  Advance Request: {txn.advance_request.request_number}")
        
        print("\n" + "="*80)
        print("MANUAL BALANCE CALCULATION:")
        print("="*80)
        
        credits = transactions.filter(
            transaction_type__in=['credit', 'commission_payment', 'bonus', 'adjustment_credit']
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        debits = transactions.filter(
            transaction_type__in=['debit', 'payment', 'adjustment_debit']
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        advances_given = transactions.filter(
            transaction_type='advance_given'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        advances_recovered = transactions.filter(
            transaction_type='advance_recovery'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        from django.db import models
        
        print(f"Credits sum: Rs. {credits:,.2f}")
        print(f"Debits sum: Rs. {debits:,.2f}")
        print(f"Advances Given sum: Rs. {advances_given:,.2f}")
        print(f"Advances Recovered sum: Rs. {advances_recovered:,.2f}")
        
        manual_balance = account.opening_balance + credits - debits - advances_given + advances_recovered
        print(f"\nManual Balance = {account.opening_balance} + {credits} - {debits} - {advances_given} + {advances_recovered}")
        print(f"Manual Balance = Rs. {manual_balance:,.2f}")
        print(f"Stored Balance = Rs. {account.current_balance:,.2f}")
        print(f"Match: {'✅ YES' if manual_balance == account.current_balance else '❌ NO'}")
        
        print("\n" + "="*80)
        
    except User.DoesNotExist:
        print("Sales rep user not found")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_sales_rep_account()
