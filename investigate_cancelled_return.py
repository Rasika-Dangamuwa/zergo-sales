"""
Deep investigation of Return RN-20260125-014 (cancelled return)
Check for any issues with cancellation process
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return, CommissionTransaction
from products.models import StockMovement
from payments.models import SalesAccountSettlement

print("=" * 80)
print("INVESTIGATING CANCELLED RETURN RN-20260125-014")
print("=" * 80)

try:
    return_obj = Return.objects.get(return_number='RN-20260125-014')
    
    print(f"\n📋 RETURN DETAILS:")
    print(f"   Return Number: {return_obj.return_number}")
    print(f"   Shop: {return_obj.shop.shop_name}")
    print(f"   Settlement Status: {return_obj.settlement_status}")
    print(f"   Settlement Method: {return_obj.settlement_method}")
    print(f"   Is Verified: {return_obj.is_verified}")
    print(f"   Total Amount: Rs. {return_obj.total_amount}")
    print(f"   Created At: {return_obj.created_at}")
    print(f"   Notes: {return_obj.notes}")
    
    # Issue 1: Check if verify button should be hidden for cancelled returns
    print(f"\n❌ ISSUE 1: VERIFY BUTTON VISIBILITY")
    if return_obj.settlement_status == 'cancelled':
        print(f"   Return is CANCELLED but template might still show 'Verify' button")
        print(f"   Solution: Update template to hide verify button when cancelled")
    
    # Issue 2: Check stock reversal
    print(f"\n📦 ISSUE 2: STOCK REVERSAL CHECK")
    stock_movements = StockMovement.objects.filter(
        reference_number=return_obj.return_number
    ).order_by('created_at')
    
    if stock_movements.exists():
        print(f"   Found {stock_movements.count()} stock movements:")
        for mov in stock_movements:
            print(f"      - {mov.created_at.strftime('%Y-%m-%d %H:%M')} | {mov.movement_type:15} | {mov.product.product_name:30} | Qty: {mov.quantity:+4d} | Stock: {mov.previous_quantity} → {mov.new_quantity}")
        
        # Check if there's both addition and reversal
        has_return_movement = stock_movements.filter(movement_type='return').exists()
        has_reversal_movement = stock_movements.filter(movement_type='adjustment', notes__icontains='cancelled').exists()
        
        if has_return_movement and has_reversal_movement:
            print(f"   ✅ Stock properly reversed (both return and cancellation movements found)")
        elif has_return_movement and not has_reversal_movement:
            print(f"   ❌ PROBLEM: Return movement found but NO reversal movement!")
            print(f"      Stock was added but NOT reversed when cancelled")
        else:
            print(f"   ⚠️ Unusual stock movement pattern")
    else:
        print(f"   ❌ NO STOCK MOVEMENTS FOUND AT ALL!")
    
    # Issue 3: Check commission reversal
    print(f"\n💰 ISSUE 3: COMMISSION REVERSAL CHECK")
    commission_txns = CommissionTransaction.objects.filter(
        notes__contains=return_obj.return_number
    ).order_by('transaction_date')
    
    if commission_txns.exists():
        print(f"   Found {commission_txns.count()} commission transactions:")
        for txn in commission_txns:
            print(f"      - {txn.transaction_date.strftime('%Y-%m-%d %H:%M')} | {txn.transaction_type:20} | Commission: Rs. {txn.commission_earned:+7.2f} | Balance: Rs. {txn.running_balance:7.2f}")
        
        has_return_processed = commission_txns.filter(transaction_type='return_processed').exists()
        has_return_cancelled = commission_txns.filter(transaction_type='return_cancelled').exists()
        
        if has_return_processed and has_return_cancelled:
            print(f"   ✅ Commission properly reversed (both deduction and reversal found)")
        elif has_return_processed and not has_return_cancelled:
            print(f"   ❌ PROBLEM: Commission deducted but NOT reversed!")
            print(f"      Sales rep is missing commission restoration")
        else:
            print(f"   ⚠️ Unusual commission pattern")
    else:
        print(f"   ⚠️ NO COMMISSION TRANSACTIONS FOUND")
    
    # Issue 4: Check linked settlements
    print(f"\n💳 ISSUE 4: LINKED SETTLEMENTS CHECK")
    settlements = SalesAccountSettlement.objects.filter(
        return_ref=return_obj
    )
    
    if settlements.exists():
        print(f"   Found {settlements.count()} linked settlements:")
        for settlement in settlements:
            print(f"      - {settlement.settlement_number} | Method: {settlement.settlement_method:20} | Status: {settlement.settlement_status:15} | Amount: Rs. {settlement.settled_amount}")
            
            if settlement.settlement_status != 'cancelled':
                print(f"        ❌ PROBLEM: Settlement NOT cancelled when return was cancelled!")
    else:
        print(f"   ℹ️ No settlements linked to this return")
    
    # Issue 5: Check CPV (Cash Payment Voucher)
    print(f"\n💵 ISSUE 5: CASH PAYMENT VOUCHER CHECK")
    if return_obj.cash_receipt_number:
        print(f"   CPV Number: {return_obj.cash_receipt_number}")
        print(f"   ℹ️ CPV status cannot be checked (model not available)")
    else:
        print(f"   ℹ️ No CPV linked to this return")
    
    # Summary of issues found
    print(f"\n" + "=" * 80)
    print("SUMMARY OF ISSUES TO FIX:")
    print("=" * 80)
    
    issues = []
    
    # Check stock reversal issue
    if stock_movements.exists():
        has_return = stock_movements.filter(movement_type='return').exists()
        has_reversal = stock_movements.filter(movement_type='adjustment', notes__icontains='cancelled').exists()
        if has_return and not has_reversal:
            issues.append("1. Stock reversal missing - need to reverse stock")
    
    # Check commission reversal issue
    if commission_txns.exists():
        has_processed = commission_txns.filter(transaction_type='return_processed').exists()
        has_cancelled = commission_txns.filter(transaction_type='return_cancelled').exists()
        if has_processed and not has_cancelled:
            issues.append("2. Commission reversal missing - need to create return_cancelled transaction")
    
    # Check settlement cancellation
    if settlements.exists():
        uncancelled_settlements = settlements.exclude(settlement_status='cancelled')
        if uncancelled_settlements.exists():
            issues.append("3. Linked settlements not cancelled - need to cancel settlements")
    
    # Check CPV cancellation
    if return_obj.cash_receipt_number:
        # Cannot check CPV status (model not available)
        pass
    
    # Template issue (always present for cancelled returns)
    issues.append("5. Template shows 'Verify Return' button for cancelled returns - need to hide it")
    
    if issues:
        for issue in issues:
            print(f"   ❌ {issue}")
    else:
        print(f"   ✅ No issues found - cancellation process worked correctly!")
        print(f"   Note: Still need to hide 'Verify Return' button in template for cancelled returns")
    
except Return.DoesNotExist:
    print(f"\n❌ Return RN-20260125-014 not found!")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
