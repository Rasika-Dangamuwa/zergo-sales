from sales.models import Return, CommissionTransaction

print("=" * 80)
print("CREATING MISSING COMMISSION FOR RETURN #110")
print("=" * 80)

return_obj = Return.objects.get(id=110)

print(f"\nReturn Details:")
print(f"  Number: {return_obj.return_number}")
print(f"  Shop: {return_obj.shop.shop_name}")
print(f"  Amount: Rs. {return_obj.total_amount}")
print(f"  Created By: {return_obj.created_by.get_full_name()}")
print(f"  Created At: {return_obj.created_at}")

# Check if commission already exists
existing = CommissionTransaction.objects.filter(return_ref=return_obj).first()

if existing:
    print(f"\n✅ Commission already exists (ID: {existing.id})")
else:
    print(f"\n⚠️  No commission found - creating now...")
    
    # Create the commission using the model method
    comm = CommissionTransaction.create_for_return(return_obj)
    
    print(f"\n✅ Created commission transaction:")
    print(f"  ID: {comm.id}")
    print(f"  Type: {comm.transaction_type}")
    print(f"  Sales Rep: {comm.sales_rep.get_full_name()}")
    print(f"  Return Amount: Rs. {comm.return_amount}")
    print(f"  Commission Rate: {comm.applicable_rate}%")
    print(f"  Commission Earned: Rs. {comm.commission_earned}")
    print(f"  Running Balance: Rs. {comm.running_balance}")
    print(f"  Notes: {comm.notes}")

print(f"\n{'=' * 80}")
print(f"DONE")
print(f"{'=' * 80}")
