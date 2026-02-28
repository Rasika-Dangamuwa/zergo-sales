from sales.models import CommissionTransaction, Return

print("=" * 80)
print("UPDATING EXISTING RETURN COMMISSIONS WITH return_ref")
print("=" * 80)

# Find all return_processed commissions without return_ref
return_comms = CommissionTransaction.objects.filter(
    transaction_type__in=['return_processed', 'return_cancelled'],
    return_ref__isnull=True
).order_by('id')

print(f"\nFound {return_comms.count()} return commissions without return_ref:")

updated = 0
not_found = 0

for comm in return_comms:
    # Extract return number from notes
    if "Return RN-" in comm.notes:
        # New format: "Return RN-20260126-011 processed for Fahad Stores"
        return_number = comm.notes.split()[1]  # RN-20260126-011
    elif "Return RET" in comm.notes:
        # Old format: "Return RET20260126001 processed"
        return_number = comm.notes.split()[1]  # RET20260126001
    else:
        print(f"  ⚠️  Commission #{comm.id}: Could not extract return number from notes: {comm.notes}")
        not_found += 1
        continue
    
    # Find the return
    return_obj = Return.objects.filter(return_number=return_number).first()
    
    if return_obj:
        comm.return_ref = return_obj
        comm.save(update_fields=['return_ref'])
        print(f"  ✅ Commission #{comm.id}: Linked to Return {return_number} ({return_obj.shop.shop_name})")
        updated += 1
    else:
        print(f"  ❌ Commission #{comm.id}: Return {return_number} not found in database")
        not_found += 1

print(f"\n{' =' * 40}")
print(f"SUMMARY:")
print(f"  Updated: {updated}")
print(f"  Not Found: {not_found}")
print(f"{'=' * 80}")
