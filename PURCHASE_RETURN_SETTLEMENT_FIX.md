# Purchase Return Settlement System - Credit Note Removal & Button Fix

**Date:** January 24, 2026  
**Issue:** User couldn't see "Update Settlement" button to settle remaining balance, and credit_note option was not needed.

---

## Problems Identified

### 1. Missing "Update Settlement" Button
**Root Cause:** Button visibility was checking `status == 'company_approved'`, but once first settlement was recorded, status changed to `'credited'`, hiding the button even though settlement_status was only `38%` complete.

**Scenario:**
- PR-2026-0004: Rs. 4,851 approved
- Rs. 1,851 settled (38%) → Status changed to 'credited'
- Rs. 3,000 remaining → Button disappeared
- User couldn't add more settlements

### 2. Unwanted Credit Note Option
**Business Requirement:** Company only settles purchase returns via:
- **Cash Refund** - Supplier pays cash back
- **Replacement GRN** - Offset against supplier invoice

Credit Note option was unnecessary complexity.

---

## Changes Implemented

### 1. Fixed Button Visibility Logic ✅

**File:** `templates/products/purchase_return_detail.html`

**Before:**
```html
{% if purchase_return.status == 'company_approved' %}
<button>Update Settlement</button>
{% endif %}
```

**After:**
```html
{% if purchase_return.status in 'company_approved,credited' and purchase_return.settlement_status != 'fully_settled' %}
<button>Update Settlement</button>
<small>Remaining: Rs. {{ remaining_to_settle }}</small>
{% endif %}
```

**Result:**
- Button now shows when status is `company_approved` OR `credited`
- Button hides ONLY when `settlement_status == 'fully_settled'`
- Shows remaining amount to settle
- Allows **partial settlements** to continue until fully settled

---

### 2. Removed Credit Note Option ✅

#### A. Model Changes
**File:** `products/models.py`

**Before:**
```python
SETTLEMENT_TYPE_CHOICES = (
    ('credit_note', 'Credit Note'),      # REMOVED
    ('replacement', 'Replacement Products'),
    ('refund', 'Cash Refund'),
)
settlement_type = models.CharField(default='credit_note')  # OLD DEFAULT
```

**After:**
```python
SETTLEMENT_TYPE_CHOICES = (
    ('replacement', 'Replacement Products'),
    ('refund', 'Cash Refund'),
)
settlement_type = models.CharField(default='refund')  # NEW DEFAULT
```

#### B. View Changes
**File:** `products/purchase_views.py`

Changed default from `'credit_note'` to `'refund'` when creating new purchase returns.

#### C. Template Changes
**File:** `templates/products/purchase_return_detail.html`

Removed credit_note handling from JavaScript:
```javascript
// REMOVED this block:
} else if (method === 'credit_note') {
    referenceCell.innerHTML = `<input placeholder="CN-YYYYMMDD-###">`;
```

#### D. Database Migration
**File:** `products/migrations/0038_remove_credit_note_option.py`

```python
operations = [
    migrations.AlterField(
        model_name='purchasereturn',
        name='settlement_type',
        field=models.CharField(
            choices=[
                ('replacement', 'Replacement Products'),
                ('refund', 'Cash Refund')
            ],
            default='refund',
            max_length=20
        ),
    ),
]
```

**Applied:** ✅ Migration applied successfully

---

## Settlement Modal Now Shows

When clicking "Update Settlement" button:

```
┌─────────────────────────────────────────┐
│  Update Settlement Details              │
├─────────────────────────────────────────┤
│  Approved: Rs. 4,851.00                 │
│  Settled:  Rs. 1,851.00                 │
│  Remaining: Rs. 3,000.00                │
├─────────────────────────────────────────┤
│  Method         Amount      Reference   │
│  [Dropdown]     [Input]     [Input]     │
│                                          │
│  Dropdown Options:                      │
│  • Replacement GRN                      │
│  • Cash Refund                          │
│                                          │
│  [+ Add Settlement Method]              │
│  [Update Settlement]                    │
└─────────────────────────────────────────┘
```

**Features:**
- Can settle partial amounts (e.g., Rs. 1,000 now, Rs. 2,000 later)
- Can mix methods (e.g., Rs. 2,000 replacement + Rs. 1,000 cash)
- Can add multiple settlement rows in one go
- Validates total doesn't exceed approved amount
- GRN selection shows only non-PO purchases with outstanding balance

---

## Validation Results

✅ **No existing credit_note settlements found** - All historical settlements use 'replacement' or 'refund'  
✅ **Migration applied successfully** - Database updated  
✅ **Button visibility fixed** - Shows for partially settled returns  
✅ **Dropdown simplified** - Only 2 options (replacement, refund)

---

## How to Settle Remaining Balance (PR-2026-0004)

**Current State:**
- Approved: Rs. 4,851.00
- Settled: Rs. 1,851.00 (465 cash + 693 GRN + 693 GRN)
- Remaining: Rs. 3,000.00

**Steps:**
1. Refresh the purchase return detail page
2. Click **"Update Settlement"** button (now visible!)
3. Choose settlement method:
   - **Replacement GRN**: Select GRN from dropdown, enter amount
   - **Cash Refund**: Enter amount and optional reference
4. Click "Update Settlement"
5. settlement_status will auto-update:
   - `pending` → `partial` (if still balance remaining)
   - `partial` → `fully_settled` (if total equals approved amount)

**You can repeat step 1-4 multiple times until Rs. 3,000 is fully settled!**

---

## Files Modified

1. ✅ `templates/products/purchase_return_detail.html` - Button visibility + dropdown + JavaScript
2. ✅ `products/models.py` - SETTLEMENT_TYPE_CHOICES + default
3. ✅ `products/purchase_views.py` - Default value in view
4. ✅ `products/migrations/0038_remove_credit_note_option.py` - Database migration

**Total Changes:** 4 files  
**Migration:** Applied successfully  
**Status:** Production-ready ✅

---

## Testing Checklist

- [✅] Migration applied without errors
- [✅] No existing credit_note settlements (verified via script)
- [✅] Button visibility logic updated
- [✅] Dropdown only shows 2 options
- [✅] Default value changed to 'refund'
- [ ] **USER TEST:** Refresh PR-2026-0004 page and verify button appears
- [ ] **USER TEST:** Click button and verify modal shows 2 options only
- [ ] **USER TEST:** Add settlement and verify it works correctly

---

**Next Step:** Refresh the purchase return detail page for PR-2026-0004. The "Update Settlement" button should now be visible below the "Settlement Status: Pending" badge, showing "Remaining: Rs. 3,000.00".
