"""
Fix Bill #215 Write-Off Issue
Problem: Write-off for Rs. 900 was created when bill had Rs. 100 pending settlement.
         After settlement was approved, balance became -Rs. 100 (incorrect).
Solution: Reverse the incorrect write-off and recreate with correct amount (Rs. 800).
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.utils import timezone
from sales.models import Bill
from payments.models import BadDebtWriteOff

def fix_bill_215():
    print("=" * 80)
    print("FIXING BILL #215 WRITE-OFF ISSUE")
    print("=" * 80)
    
    bill = Bill.objects.get(pk=215)
    print(f"\n📋 Bill: {bill.bill_number}")
    print(f"   Shop: {bill.shop.shop_name}")
    print(f"   Total: Rs. {bill.total_amount:,.2f}")
    print(f"   Paid: Rs. {bill.paid_amount:,.2f}")
    print(f"   Balance: Rs. {bill.balance_amount:,.2f}")
    
    # Get the incorrect write-off
    writeoff = BadDebtWriteOff.objects.filter(bill=bill, executed=True).first()
    if not writeoff:
        print("\n❌ No executed write-off found!")
        return
    
    print(f"\n💸 Current Write-Off: {writeoff.write_off_number}")
    print(f"   Amount: Rs. {writeoff.write_off_amount:,.2f} ❌ INCORRECT")
    print(f"   Should be: Rs. 800.00 (balance after Rs. 100 payment)")
    
    print(f"\n🔧 STARTING FIX...")
    
    # Step 1: Reverse bill updates from incorrect write-off
    print(f"\n   Step 1: Reversing bill updates...")
    old_balance = bill.total_amount - bill.paid_amount
    bill.balance_amount = old_balance
    bill.settlement_status = 'partially_settled' if bill.paid_amount > 0 else 'unsettled'
    
    # Remove write-off note from bill
    if writeoff.write_off_number in bill.notes:
        # Find and remove the write-off section
        lines = bill.notes.split('\n')
        cleaned_lines = []
        skip = False
        for line in lines:
            if '=== BAD DEBT WRITE-OFF ===' in line:
                skip = True
            elif skip and '========================' in line:
                skip = False
                continue
            elif not skip:
                cleaned_lines.append(line)
        bill.notes = '\n'.join(cleaned_lines).strip()
    
    bill.save()
    print(f"      ✅ Bill balance reset to Rs. {bill.balance_amount:,.2f}")
    
    # Step 2: Reverse shop balance update
    print(f"\n   Step 2: Reversing shop balance...")
    bill.shop.refresh_from_db()
    old_shop_balance = bill.shop.current_balance
    bill.shop.current_balance += writeoff.write_off_amount  # Add back the incorrect write-off
    
    # Remove write-off note from shop
    if writeoff.write_off_number in bill.shop.notes:
        lines = bill.shop.notes.split('\n')
        cleaned_lines = [line for line in lines if writeoff.write_off_number not in line]
        bill.shop.notes = '\n'.join(cleaned_lines).strip()
    
    bill.shop.save()
    print(f"      ✅ Shop balance: Rs. {old_shop_balance:,.2f} → Rs. {bill.shop.current_balance:,.2f}")
    
    # Step 3: Mark old write-off as cancelled/reversed
    print(f"\n   Step 3: Marking write-off as reversed...")
    writeoff.executed = False
    writeoff.bill_updated = False
    writeoff.shop_balance_updated = False
    writeoff.detailed_notes += f"\n\n[REVERSED on {timezone.now().strftime('%Y-%m-%d %H:%M')}] This write-off was incorrect (created before pending settlement was approved). Amount should have been Rs. 800.00, not Rs. 900.00."
    writeoff.save()
    print(f"      ✅ Write-off {writeoff.write_off_number} marked as reversed")
    
    # Step 4: Create correct write-off for Rs. 800
    print(f"\n   Step 4: Creating correct write-off...")
    correct_writeoff = BadDebtWriteOff.objects.create(
        bill=bill,
        shop=bill.shop,
        original_amount=bill.total_amount,
        paid_amount=bill.paid_amount,  # Rs. 100
        write_off_amount=Decimal('800.00'),  # Correct amount
        reason=writeoff.reason,
        detailed_notes=f"Corrected write-off (original {writeoff.write_off_number} was Rs. 900 but Rs. 100 was already paid).\n\nOriginal notes: {writeoff.detailed_notes.split('[REVERSED')[0].strip()}",
        requested_by=writeoff.requested_by,
        approved_by=writeoff.approved_by,
        approval_status='approved',
        approval_date=writeoff.approval_date,
        executed=True,
        executed_at=timezone.now()
    )
    print(f"      ✅ New write-off created: {correct_writeoff.write_off_number}")
    print(f"         Amount: Rs. {correct_writeoff.write_off_amount:,.2f}")
    
    # Step 5: Apply correct write-off to bill
    print(f"\n   Step 5: Applying correct write-off to bill...")
    bill.notes = (bill.notes or '') + f"\n\n=== BAD DEBT WRITE-OFF ===\nWrite-Off Number: {correct_writeoff.write_off_number}\nDate: {timezone.now().strftime('%Y-%m-%d %H:%M')}\nAmount: Rs. {correct_writeoff.write_off_amount:,.2f}\nReason: {correct_writeoff.get_reason_display()}\nApproved by: {correct_writeoff.approved_by.get_full_name()}\nNote: Corrected write-off (previous {writeoff.write_off_number} was incorrect)\n========================"
    bill.balance_amount = Decimal('0')
    bill.settlement_status = 'settled'
    bill.save()
    correct_writeoff.bill_updated = True
    correct_writeoff.save()
    print(f"      ✅ Bill balance: Rs. {bill.balance_amount:,.2f}")
    print(f"      ✅ Bill status: {bill.settlement_status}")
    
    # Step 6: Apply correct write-off to shop
    print(f"\n   Step 6: Applying correct write-off to shop...")
    bill.shop.current_balance -= correct_writeoff.write_off_amount
    if bill.shop.current_balance < 0:
        bill.shop.current_balance = Decimal('0')
    bill.shop.notes = (bill.shop.notes or '') + f"\n\nBad debt write-off: Rs. {correct_writeoff.write_off_amount:,.2f} on {timezone.now().strftime('%Y-%m-%d')} ({correct_writeoff.write_off_number}) - Corrected write-off"
    bill.shop.save()
    correct_writeoff.shop_balance_updated = True
    correct_writeoff.save()
    print(f"      ✅ Shop balance: Rs. {bill.shop.current_balance:,.2f}")
    
    # Final verification
    print(f"\n✅ FIX COMPLETED!")
    print(f"\n📊 FINAL STATE:")
    bill.refresh_from_db()
    bill.shop.refresh_from_db()
    print(f"   Bill Total: Rs. {bill.total_amount:,.2f}")
    print(f"   Bill Paid: Rs. {bill.paid_amount:,.2f}")
    print(f"   Bill Written Off: Rs. {correct_writeoff.write_off_amount:,.2f}")
    print(f"   Bill Balance: Rs. {bill.balance_amount:,.2f}")
    print(f"   Bill Status: {bill.settlement_status}")
    print(f"   Shop Balance: Rs. {bill.shop.current_balance:,.2f}")
    
    print(f"\n✅ Verification:")
    expected_balance = bill.total_amount - bill.paid_amount - correct_writeoff.write_off_amount
    print(f"   Rs. {bill.total_amount:,.2f} (total) - Rs. {bill.paid_amount:,.2f} (paid) - Rs. {correct_writeoff.write_off_amount:,.2f} (writeoff) = Rs. {expected_balance:,.2f}")
    print(f"   Match: {'✅ YES' if bill.balance_amount == expected_balance else '❌ NO'}")

if __name__ == '__main__':
    fix_bill_215()
