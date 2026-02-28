import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from payments.models import SalesAccountSettlement
from sales.models import CommissionTransaction

# Get settlement #133
settlement = SalesAccountSettlement.objects.get(pk=133)
print(f'=== SETTLEMENT #{settlement.id} ===')
print(f'Number: {settlement.settlement_number}')
print(f'Method: {settlement.settlement_method}')
print(f'Amount: Rs. {settlement.amount}')
print(f'Status: {settlement.settlement_status}')
print(f'Bill: {settlement.bill.bill_number if settlement.bill else "None"}')
print(f'Shop: {settlement.shop.shop_name}')
print(f'Sales Rep: {settlement.bill.sales_rep if settlement.bill else "None"}')
print(f'Created: {settlement.created_at}')

# Check if commission transaction exists
print(f'\n=== COMMISSION TRANSACTIONS ===')
commissions = CommissionTransaction.objects.filter(settlement=settlement)
if commissions.exists():
    for comm in commissions:
        print(f'Transaction #{comm.id}:')
        print(f'  Type: {comm.transaction_type}')
        print(f'  Commission: Rs. {comm.commission_earned}')
        print(f'  Date: {comm.transaction_date}')
else:
    print('❌ NO COMMISSION TRANSACTION FOUND!')
    
    # Check why
    print(f'\n=== DIAGNOSIS ===')
    if settlement.settlement_status != 'completed':
        print(f'⚠️  Settlement status is "{settlement.settlement_status}" (not "completed")')
        print(f'   Commission only created for completed settlements')
    
    if not settlement.bill:
        print(f'⚠️  Settlement has no bill attached')
    elif not settlement.bill.sales_rep:
        print(f'⚠️  Bill has no sales rep assigned')
    else:
        print(f'✓ Settlement has bill with sales rep')
    
    # Check if bill has commission_eligible flag
    if settlement.bill:
        print(f'\nBill details:')
        print(f'  Sales rep: {settlement.bill.sales_rep}')
        print(f'  Bill status: {settlement.bill.bill_status}')
        
        # Manually create commission if missing
        print(f'\n=== CREATING MISSING COMMISSION ===')
        if settlement.settlement_status == 'completed':
            try:
                CommissionTransaction.create_for_payment(
                    payment=settlement,
                    bill=settlement.bill
                )
                print(f'✅ Commission transaction created!')
            except Exception as e:
                print(f'❌ Error creating commission: {e}')
        else:
            print(f'⚠️  Cannot create commission - settlement not completed')
