# FOC Transaction Cancellation Handling

**Date:** January 27, 2026  
**Issue:** FOC transactions remain active when bills/returns are cancelled  
**Status:** ✅ FIXED

## Problem Statement

When bills or returns are cancelled, the system correctly reverses inventory and shop balances, but FOC (Free of Charge) value transactions remain active. This causes incorrect FOC account balances and misleading utilization percentages.

**Example:** FOC-20260127-003 (FOC Restored transaction) remained active even though Return RN-20260127-004 was cancelled.

## Solution Implemented

### 1. Bill Cancellation (sales/views.py:669-720)

Added FOC transaction reversal in `cancel_bill()` function:

```python
# Reverse FOC transactions for this bill
from products.models import FOCValueTransaction
foc_transactions = FOCValueTransaction.objects.filter(
    bill_item__bill=bill,
    is_archived=False
)
for foc_txn in foc_transactions:
    foc_txn.is_archived = True
    foc_txn.notes = f"{foc_txn.notes or ''}\\n[CANCELLED] Bill {bill.sale_number} cancelled on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
    foc_txn.save()
    # Update account balance
    if hasattr(foc_txn, 'foc_account') and foc_txn.foc_account:
        foc_txn.foc_account.update_balance()
```

### 2. Return Cancellation (sales/return_views.py:215-280)

Added FOC transaction reversal in return cancellation logic:

```python
# Reverse FOC transactions for this return
from products.models import FOCValueTransaction
foc_transactions = FOCValueTransaction.objects.filter(
    return_item__return_ref=return_obj,
    is_archived=False
)
for foc_txn in foc_transactions:
    foc_txn.is_archived = True
    foc_txn.notes = f"{foc_txn.notes or ''}\\n[CANCELLED] Return {return_obj.return_number} cancelled on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
    foc_txn.save()
    # Update account balance
    if hasattr(foc_txn, 'foc_account') and foc_txn.foc_account:
        foc_txn.foc_account.update_balance()
```

### 3. Balance Calculation Update (products/models.py:1972-2040)

Modified `FOCValueAccount.update_balance()` to exclude archived transactions:

```python
# Only include active (non-archived) transactions
active_txns = self.transactions.filter(is_archived=False)

# FOC received from suppliers/companies ONLY (what we GET)
received_txns = active_txns.filter(
    transaction_type='foc_received'
).aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
```

### 4. Utilization Calculation Update (products/models.py:2020-2040)

Modified `foc_utilization_percentage` to exclude archived transactions:

```python
# Calculate GROSS FOC given (before returns) - only active transactions
gross_given = self.transactions.filter(
    transaction_type__in=['foc_given', 'implicit_foc'],
    is_archived=False
).aggregate(total=models.Sum('foc_value'))['total'] or Decimal('0')
```

### 5. Dashboard Query Updates (sales/foc_views.py)

All dashboard queries already filter `is_archived=False`:

- Recent transactions (line 43): `.filter(is_archived=False)`
- Transaction breakdown (line 51): `.filter(is_archived=False)`
- Company detail (line 88): `.filter(is_archived=False)`
- Product report (line 160): `.filter(is_archived=False)`
- Sales rep report (line 209): `.filter(is_archived=False)`

## Testing

### Test Script: test_foc_cancellation.py

Created comprehensive test script that:
1. Checks specific transaction FOC-20260127-003
2. Scans all cancelled bills for active FOC transactions
3. Scans all cancelled returns for active FOC transactions
4. Verifies account balance accuracy

### Fix Script: fix_foc_cancellation.py

Created migration script that:
1. Finds all cancelled returns with active FOC transactions
2. Archives those transactions
3. Recalculates FOC account balances
4. Verifies fix success

**Result:** Fixed 1 FOC transaction (FOC-20260127-003)

## Before vs After

### Before Fix:
- FOC Received: Rs. 2,160.00
- FOC Given: Rs. 0.00 (900 given - 900 restored)
- Net FOC: Rs. 2,160.00
- **BUG:** Return RN-20260127-004 cancelled but FOC-20260127-003 (restoration) still active

### After Fix:
- FOC Received: Rs. 2,160.00
- FOC Given: Rs. 900.00 (restoration cancelled)
- Net FOC: Rs. 1,260.00
- ✅ FOC-20260127-003 properly archived

## Business Logic Validation

### Cancellation Flow:
1. **Bill Cancelled:**
   - Inventory reversed (products added back to stock) ✅
   - Shop balance reversed ✅
   - FOC transactions archived (foc_given, implicit_foc) ✅
   - Account balance recalculated ✅

2. **Return Cancelled:**
   - Stock movements reversed ✅
   - Settlements auto-cancelled ✅
   - FOC transactions archived (return_foc_restored) ✅
   - Account balance recalculated ✅

### Transaction States:
- **Active:** `is_archived=False` - Counted in balances and reports
- **Archived:** `is_archived=True` - Excluded from all calculations
- **Note Appended:** "[CANCELLED] Bill/Return {number} cancelled on {datetime}"

## Files Modified

1. **sales/views.py** (Line 669-720)
   - Added FOC transaction reversal to `cancel_bill()`

2. **sales/return_views.py** (Line 215-280)
   - Added FOC transaction reversal to return cancellation

3. **products/models.py** (Line 1972-2040)
   - Updated `update_balance()` to exclude archived transactions
   - Updated `foc_utilization_percentage` to exclude archived transactions

4. **sales/foc_views.py** (All queries)
   - Already filtering `is_archived=False` ✅

## Testing Commands

```powershell
# Test current state
python test_foc_cancellation.py

# Fix historical data
python fix_foc_cancellation.py

# Verify dashboard calculations
# Navigate to /sales/foc-value-usage/ and check Max Beverages account
```

## Future Considerations

### GRN Cancellation
Currently, GRN (Goods Received Notes) do not have cancellation functionality. If implemented in the future, similar FOC transaction reversal logic should be added:

```python
# Hypothetical GRN cancellation code
foc_transactions = FOCValueTransaction.objects.filter(
    purchase_item__purchase=grn,
    is_archived=False
)
for foc_txn in foc_transactions:
    foc_txn.is_archived = True
    foc_txn.notes = f"{foc_txn.notes or ''}\\n[CANCELLED] GRN {grn.grn_number} cancelled on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
    foc_txn.save()
    if foc_txn.foc_account:
        foc_txn.foc_account.update_balance()
```

## Key Insights

1. **Archival vs Deletion:** Transactions are archived (not deleted) to maintain audit trail
2. **Automatic Recalculation:** Account balances automatically recalculate when transactions are archived
3. **Dashboard Consistency:** All dashboard views already filter archived transactions
4. **Utilization Accuracy:** Utilization percentage now correctly excludes cancelled transactions
5. **Audit Trail:** Cancellation reason and timestamp appended to transaction notes

## Verification Checklist

- [x] FOC-20260127-003 archived
- [x] Return RN-20260127-004 FOC transactions cleared
- [x] Max Beverages account balance corrected (Rs. 1,260 net)
- [x] No remaining active FOC transactions on cancelled returns
- [x] Dashboard queries exclude archived transactions
- [x] Utilization percentage calculation updated
- [x] Balance calculation updated
- [x] Test script created
- [x] Fix script created
- [x] Documentation complete

---

**Author:** GitHub Copilot  
**Last Updated:** January 27, 2026  
**Next Review:** When implementing GRN cancellation feature
