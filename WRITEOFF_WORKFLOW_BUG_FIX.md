# Write-Off Workflow Bug Fix - February 12, 2026

## Critical Bug Discovered

### The Problem
A workflow bug in the bad debt write-off system allowed write-offs to be created with incorrect amounts when pending settlements existed.

### How It Happened (Bill #215 Case Study)

**Sequence of Events:**
1. ✅ Bill created: Rs. 900 total
2. ✅ User created **PENDING** cheque settlement: Rs. 100 (NOT approved yet)
   - At this point, `bill.paid_amount` was still **Rs. 0** (pending settlements don't count yet)
3. ❌ **BUG**: User wrote off the "full balance" of Rs. 900
   - System calculated write-off as: Rs. 900 total - Rs. 0 paid = **Rs. 900 write-off**
4. ✅ User approved the pending settlement: Rs. 100
   - Now `bill.paid_amount` became **Rs. 100**
5. ❌ **RESULT**: Incorrect math
   - Total: Rs. 900
   - Paid: Rs. 100
   - Written off: Rs. 900
   - **Expected balance: -Rs. 100** (negative!)
   - **Actual balance: Rs. 800** (unchanged)

### Root Cause
The write-off system didn't check for pending settlements before allowing write-offs. This created a race condition where:
- Write-off amount is calculated at creation time based on current `paid_amount`
- But `paid_amount` can change later when pending settlements are approved
- No validation prevented this scenario

---

## Fix Implemented

### 1. Prevention - Added Validation (Code Changes)

**File:** `payments/views.py`

**Added to `write_off_confirm()` view (Line ~633):**
```python
# CRITICAL: Check for pending settlements that haven't been verified yet
pending_settlements = bill.settlements.filter(settlement_status='pending_verification')
if pending_settlements.exists():
    total_pending = sum(s.amount for s in pending_settlements)
    messages.error(
        request,
        f'Cannot write off this bill. There are pending settlements totaling Rs. {total_pending:,.2f} that must be verified or cancelled first. '
        f'Please approve or reject these settlements before writing off the debt.'
    )
    return redirect('sales:detail', pk=bill_pk)
```

**Added to `write_off_execute()` view (Line ~679):**
```python
# CRITICAL: Check for pending settlements that haven't been verified yet
pending_settlements = bill.settlements.filter(settlement_status='pending_verification')
if pending_settlements.exists():
    total_pending = sum(s.amount for s in pending_settlements)
    messages.error(
        request,
        f'Cannot write off this bill. There are pending settlements totaling Rs. {total_pending:,.2f} that must be verified or cancelled first. '
        f'Approve or reject these settlements before writing off the debt.'
    )
    return redirect('sales:detail', pk=bill_pk)
```

**What This Does:**
- Blocks write-off confirmation page if pending settlements exist
- Blocks write-off execution if pending settlements exist
- Forces user to approve/reject settlements BEFORE writing off
- Prevents the race condition completely

### 2. Correction - Fixed Bill #215

**Script:** `fix_bill_215_writeoff.py`

**Actions Taken:**
1. ✅ Reversed incorrect write-off (DISP-2026-0007) for Rs. 900
   - Marked as `executed=False`
   - Restored bill balance to Rs. 800
   - Restored shop balance (added back Rs. 900)
   - Added reversal note to write-off

2. ✅ Created correct write-off (DISP-2026-0008) for Rs. 800
   - Correct amount: Rs. 900 total - Rs. 100 paid = **Rs. 800**
   - Applied to bill (balance → Rs. 0)
   - Applied to shop balance (reduced by Rs. 800)
   - Maintained audit trail

**Final State:**
```
Bill #215 (BILL20260211004):
├─ Total: Rs. 900.00
├─ Paid: Rs. 100.00 (1 cheque settlement)
├─ Written Off: Rs. 800.00 (DISP-2026-0008)
└─ Balance: Rs. 0.00 ✅ CORRECT

Shop Balance: Rs. 100.00 (down from Rs. 900 before fix)

Write-Offs:
├─ DISP-2026-0007: Rs. 900 (REVERSED - incorrect)
└─ DISP-2026-0008: Rs. 800 (ACTIVE - correct)
```

---

## Testing

### How to Test the Fix

1. **Create a bill** with outstanding balance
2. **Create a PENDING settlement** (don't approve yet)
3. **Try to write off the bill**
4. **Expected Result:** ❌ Error message: "Cannot write off this bill. There are pending settlements..."

### What Changed

**BEFORE (Bug):**
- ✅ Could write off a bill even with pending settlements
- ❌ Write-off amount calculated wrong (didn't account for future approvals)
- ❌ Math breaks when pending settlements get approved later

**AFTER (Fix):**
- ✅ Cannot write off if pending settlements exist
- ✅ User MUST approve/reject settlements first
- ✅ Write-off amount is always correct (based on truly paid amount)
- ✅ No more race conditions

---

## Business Impact

### Data Integrity
- ✅ Prevents future incorrect write-offs
- ✅ Fixed the one existing incorrect write-off (Bill #215)
- ✅ Maintains accurate shop balances
- ✅ Maintains accurate bill balances

### Audit Trail
- ✅ All changes logged
- ✅ Original incorrect write-off preserved with reversal note
- ✅ New correct write-off created with explanation
- ✅ Complete transaction history maintained

### User Workflow
- ✅ Clear error messages guide users
- ✅ Enforces correct sequence: Approve settlements → Then write off
- ✅ Prevents accidental mistakes

---

## Technical Details

### Models Affected
- `Bill` (sales.models)
- `BadDebtWriteOff` (payments.models)
- `SalesAccountSettlement` (payments.models)
- `Shop` (shops.models)

### Views Modified
- `write_off_confirm()` - Added pending settlement check
- `write_off_execute()` - Added pending settlement check

### Settlement States
- `pending_verification` - Settlement not yet approved/rejected
- `completed` - Settlement approved and counted in `paid_amount`
- `cancelled` - Settlement rejected, not counted

### Write-Off Number Format
- `DISP-YYYY-####` (e.g., DISP-2026-0007)
- Auto-increments daily
- Same format as non-resaleable disposals

---

## Recommendations

### For Users
1. **Always verify/reject pending settlements BEFORE writing off**
2. **Check bill payment history before writing off**
3. **Review write-off confirmation page carefully** (shows current paid amount)

### For Developers
1. ✅ **Validation added** - No code changes needed
2. Consider adding similar checks for:
   - Bill cancellation with pending settlements
   - Return processing with pending bill settlements
3. Monitor for similar race conditions in other workflows

---

## Conclusion

**Status:** ✅ **FIXED**

- **Prevention:** Code validation added to both confirmation and execution views
- **Correction:** Bill #215 fixed with proper audit trail
- **Testing:** Manual testing shows validation works correctly
- **Impact:** No other bills affected (only Bill #215 had this issue)

The system is now protected against this workflow bug. Users will be forced to handle pending settlements before writing off debts, ensuring accurate calculations every time.

---

**Fix Date:** February 12, 2026 06:34 UTC  
**Fixed By:** AI Agent (GitHub Copilot)  
**Affected Bill:** #215 only  
**Code Files Modified:** `payments/views.py`  
**Scripts Created:** `fix_bill_215_writeoff.py`, `investigate_bill_215.py`
