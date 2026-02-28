"""
Investigate commission transactions shown in the screenshot

Issues to check:
1. Settlement SET-20260125-041 shows both Payment Received and Payment Cancelled
2. Balance calculation seems inconsistent at 12:51 AM
3. Return RN-20260125-00 transaction
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction
from payments.models import SalesAccountSettlement
from sales.models import Return
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 80)
print("COMMISSION TRANSACTION INVESTIGATION")
print("=" * 80)
print()

# Get transactions from Jan 26, 2026
from datetime import datetime
from django.utils import timezone

start_date = datetime(2026, 1, 26, 0, 0, 0)
end_date = datetime(2026, 1, 26, 23, 59, 59)

transactions = CommissionTransaction.objects.filter(
    transaction_date__range=[start_date, end_date]
).order_by('-transaction_date', '-id')

print(f"Found {transactions.count()} transactions on Jan 26, 2026")
print()

# Focus on the specific settlements mentioned
settlement_041 = SalesAccountSettlement.objects.filter(
    settlement_number='SET-20260125-041'
).first()

if settlement_041:
    print("SETTLEMENT SET-20260125-041:")
    print(f"  Status: {settlement_041.settlement_status}")
    print(f"  Amount: Rs. {settlement_041.amount}")
    print(f"  Date: {settlement_041.settlement_date}")
    print(f"  Bill: {settlement_041.bill.bill_number if settlement_041.bill else 'None'}")
    print()
    
    # Get commission transactions for this settlement
    settlement_txns = CommissionTransaction.objects.filter(
        settlement=settlement_041
    ).order_by('transaction_date')
    
    print(f"  Commission Transactions ({settlement_txns.count()}):")
    for txn in settlement_txns:
        print(f"    {txn.transaction_date.strftime('%Y-%m-%d %H:%M:%S')}: "
              f"{txn.transaction_type}, "
              f"Amount: {txn.collected_amount}, "
              f"Commission: {txn.commission_earned}, "
              f"Balance: {txn.running_balance}")
    print()

# Check Settlement SET-20260125-036
settlement_036 = SalesAccountSettlement.objects.filter(
    settlement_number='SET-20260125-036'
).first()

if settlement_036:
    print("SETTLEMENT SET-20260125-036:")
    print(f"  Status: {settlement_036.settlement_status}")
    print(f"  Amount: Rs. {settlement_036.amount}")
    print(f"  Date: {settlement_036.settlement_date}")
    print()
    
    settlement_txns = CommissionTransaction.objects.filter(
        settlement=settlement_036
    ).order_by('transaction_date')
    
    print(f"  Commission Transactions ({settlement_txns.count()}):")
    for txn in settlement_txns:
        print(f"    {txn.transaction_date.strftime('%Y-%m-%d %H:%M:%S')}: "
              f"{txn.transaction_type}, "
              f"Amount: {txn.collected_amount}, "
              f"Commission: {txn.commission_earned}, "
              f"Balance: {txn.running_balance}")
    print()

# Check for Return RN-20260125-00
return_obj = Return.objects.filter(
    return_number__startswith='RN-20260125-00'
).first()

if return_obj:
    print(f"RETURN {return_obj.return_number}:")
    print(f"  Status: {return_obj.return_status}")
    print(f"  Amount: Rs. {return_obj.total_amount}")
    print(f"  Date: {return_obj.return_date}")
    print()
    
    # Check commission transactions for this return
    return_txns = CommissionTransaction.objects.filter(
        notes__contains=return_obj.return_number
    ).order_by('transaction_date')
    
    print(f"  Commission Transactions ({return_txns.count()}):")
    for txn in return_txns:
        print(f"    {txn.transaction_date.strftime('%Y-%m-%d %H:%M:%S')}: "
              f"{txn.transaction_type}, "
              f"Amount: {txn.collected_amount}, "
              f"Commission: {txn.commission_earned}, "
              f"Balance: {txn.running_balance}")
    print()

# Show all Jan 26 transactions in chronological order
print("=" * 80)
print("ALL JAN 26 TRANSACTIONS (Chronological)")
print("=" * 80)
for txn in transactions.order_by('transaction_date', 'id'):
    settlement_ref = f"Settlement: {txn.settlement.settlement_number}" if txn.settlement else "No settlement"
    bill_ref = f"Bill: {txn.bill.bill_number if txn.bill else txn.bill.sale_number if hasattr(txn.bill, 'sale_number') else 'Unknown'}" if txn.bill else "No bill"
    
    print(f"{txn.transaction_date.strftime('%Y-%m-%d %H:%M:%S')} | "
          f"{txn.transaction_type:20s} | "
          f"{settlement_ref:30s} | "
          f"Amt: {str(txn.collected_amount):>8s} | "
          f"Comm: {str(txn.commission_earned):>7s} | "
          f"Bal: {str(txn.running_balance):>8s}")

print()
print("=" * 80)
print("POTENTIAL ISSUES TO CHECK:")
print("=" * 80)

# Check for balance inconsistencies
prev_balance = None
for txn in transactions.order_by('transaction_date', 'id'):
    if prev_balance is not None:
        expected_balance = prev_balance + txn.commission_earned
        if abs(txn.running_balance - expected_balance) > 0.01:
            print(f"⚠️  Balance mismatch at {txn.transaction_date}: "
                  f"Expected {expected_balance}, Got {txn.running_balance}")
    prev_balance = txn.running_balance
