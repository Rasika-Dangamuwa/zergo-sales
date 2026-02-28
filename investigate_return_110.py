from sales.models import Return, CommissionTransaction
from django.contrib.auth.models import User

print("=" * 80)
print("INVESTIGATING RETURN #110")
print("=" * 80)

# Get Return #110
try:
    return_obj = Return.objects.get(id=110)
    print(f"\n✅ Return Found:")
    print(f"  ID: {return_obj.id}")
    print(f"  Number: {return_obj.return_number}")
    print(f"  Shop: {return_obj.shop.shop_name}")
    print(f"  Created By: {return_obj.created_by.get_full_name()}")
    print(f"  Total Amount: Rs. {return_obj.total_amount}")
    print(f"  Settlement Method: {return_obj.settlement_method}")
    print(f"  Settlement Status: {return_obj.settlement_status}")
    print(f"  Created At: {return_obj.created_at}")
    
    # Check commission transactions for this return
    print(f"\n{'=' * 80}")
    print(f"COMMISSION TRANSACTIONS FOR THIS RETURN:")
    print(f"{'=' * 80}")
    
    commissions = CommissionTransaction.objects.filter(return_ref=return_obj)
    print(f"\nFound {commissions.count()} commission transactions:")
    
    for comm in commissions:
        print(f"\n  Commission #{comm.id}:")
        print(f"    Type: {comm.transaction_type}")
        print(f"    Sales Rep: {comm.sales_rep.get_full_name()}")
        print(f"    Return Amount: Rs. {comm.return_amount}")
        print(f"    Commission: Rs. {comm.commission_earned}")
        print(f"    Date: {comm.transaction_date}")
        print(f"    Notes: {comm.notes}")
    
    # Check ALL commission transactions for the sales rep
    print(f"\n{'=' * 80}")
    print(f"ALL COMMISSION TRANSACTIONS FOR {return_obj.created_by.get_full_name()}:")
    print(f"{'=' * 80}")
    
    all_comms = CommissionTransaction.objects.filter(
        sales_rep=return_obj.created_by
    ).order_by('-transaction_date')[:10]
    
    print(f"\nLast 10 transactions:")
    for comm in all_comms:
        print(f"  #{comm.id}: {comm.transaction_type} - Rs. {comm.commission_earned} - {comm.transaction_date.strftime('%Y-%m-%d %H:%M')}")
        if comm.return_ref:
            print(f"         Return: {comm.return_ref.return_number} ({comm.return_ref.shop.shop_name})")
        elif comm.bill:
            print(f"         Bill: {comm.bill.bill_number}")
    
except Return.DoesNotExist:
    print(f"\n❌ Return #110 NOT FOUND in database")

print(f"\n{'=' * 80}")
