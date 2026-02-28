# Purchase Return Status Logic - Proper Settlement Tracking

**Date:** January 24, 2026  
**Issue:** Status showed "Settled" (green badge) when only 38% settled - very confusing!

---

## The Problem

**Before Fix:**
```
PR-2026-0004:
- Approved Amount: Rs. 4,851.00
- Total Settled: Rs. 1,851.00 (38%)
- Status Badge: "Settled" ✅ GREEN  ← WRONG! Not fully settled!
- Settlement Status: "Pending"     ← Contradicts status badge
```

**User's valid concern:** "But this is not still full settled. How handle this?"

---

## Root Cause

The code had **incorrect status assignment logic**:

```python
# OLD BUGGY CODE:
if total_settled >= approved_amount:
    settlement_status = 'fully_settled'
elif total_settled > 0:
    settlement_status = 'partial'
else:
    settlement_status = 'pending'

status = 'settled'  # ❌ ALWAYS set to 'settled', even if partial!
```

**Problem:** Status changed to "settled" as soon as ANY settlement was recorded, even if only 1% settled!

---

## Proper Status Workflow

Purchase returns should follow this progression:

```
┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌─────────┐
│   Pending   │ →  │ Sent to Supplier │ →  │ Company Approved │ →  │ Settled │
└─────────────┘    └──────────────────┘    └──────────────────┘    └─────────┘
                                                   ↑                      ↑
                                              Stay here until      Only when
                                              fully settled!       100% done!
```

**Two-Field Tracking System:**

| Field | Purpose | Values |
|-------|---------|--------|
| **status** | Main workflow stage | pending → sent_to_supplier → company_approved → **settled** |
| **settlement_status** | Settlement completion | pending → partial → fully_settled |

**Critical Rule:** 
- `status='settled'` **ONLY** when `settlement_status='fully_settled'`
- Otherwise, keep `status='company_approved'` (even with partial settlements)

---

## The Fix

### 1. Updated Status Logic ✅

**File:** `products/purchase_views.py` (lines 902-916)

**NEW CORRECT CODE:**
```python
# Update settlement_status based on total settled
approved_amount = purchase_return.approved_amount or D('0')
total_settled = purchase_return.total_settled_amount

if total_settled >= approved_amount:
    purchase_return.settlement_status = 'fully_settled'
    purchase_return.status = 'settled'  # ✅ Only mark as settled when 100%
elif total_settled > 0:
    purchase_return.settlement_status = 'partial'
    purchase_return.status = 'company_approved'  # ✅ Keep as approved for partial
else:
    purchase_return.settlement_status = 'pending'
    purchase_return.status = 'company_approved'  # ✅ Keep as approved if no settlement

purchase_return.save()
```

**Logic:**
- **0% settled** → status: `company_approved`, settlement_status: `pending`
- **1-99% settled** → status: `company_approved`, settlement_status: `partial`
- **100% settled** → status: `settled`, settlement_status: `fully_settled`

### 2. Fixed Existing Data ✅

**PR-2026-0004** (your return):
- Was: `status='settled'` (wrong!)
- Now: `status='company_approved'` (correct!)
- Reason: Only 38% settled (Rs. 1,851 / Rs. 4,851)

**Migration Result:**
```
✅ Fixed 1 return with incorrect status
   PR-2026-0004: 'settled' → 'company_approved' (38% complete)
```

### 3. Button Visibility Logic (Already Correct) ✅

**Template Condition:**
```django
{% if purchase_return.status in 'company_approved,settled' and purchase_return.settlement_status != 'fully_settled' %}
    <button>Update Settlement</button>
    <small>Remaining: Rs. {{ remaining_to_settle }}</small>
{% endif %}
```

**Why it includes both:**
- `company_approved`: Catches partial settlements (0-99%)
- `settled`: Safety net (shouldn't happen with new logic, but handles legacy data)
- `settlement_status != 'fully_settled'`: Final guard to hide button when 100% done

---

## Status Display Examples

### Example 1: Partially Settled (Your Case)
```
PR-2026-0004:
┌─────────────────────────────────────┐
│ Status Badge: Approved by Company   │  ← Correct! Not "Settled"
│ Settlement Status: Pending          │  ← Shows partial/pending
│ Settlement Progress: 38%            │  ← Shows exact progress
│ Remaining: Rs. 3,000.00             │  ← Clear remaining amount
│ [Update Settlement] button: Visible │  ← Can continue settling
└─────────────────────────────────────┘
```

### Example 2: Fully Settled
```
PR-2026-0003:
┌─────────────────────────────────────┐
│ Status Badge: Settled               │  ← Green badge, 100% done
│ Settlement Status: Fully Settled    │  ← Matches main status
│ Settlement Progress: 100%           │  ← Complete!
│ Remaining: Rs. 0.00                 │  ← Nothing left
│ [Update Settlement] button: Hidden  │  ← No more actions needed
└─────────────────────────────────────┘
```

### Example 3: Approved, No Settlement Yet
```
PR-20260119-002:
┌─────────────────────────────────────┐
│ Status Badge: Approved by Company   │  ← Approved but not settled
│ Settlement Status: Pending          │  ← No settlements recorded
│ Settlement Progress: 0%             │  ← Nothing settled yet
│ Remaining: Rs. 138.60               │  ← Full amount remaining
│ [Update Settlement] button: Visible │  ← Can start settling
└─────────────────────────────────────┘
```

---

## Status Reference Guide

### Main Status Field

| Value | Display | Meaning | Next Action |
|-------|---------|---------|-------------|
| `pending` | Pending | Return created, not yet sent | Send to Supplier |
| `sent_to_supplier` | Sent to Supplier | Items shipped back | Record Company Approval |
| `company_approved` | Approved by Company | Company approved, **settlement 0-99%** | Update Settlement |
| `settled` | Settled | **Settlement 100% complete** | None (done!) |
| `rejected` | Rejected | Company rejected return | None |

### Settlement Status Field

| Value | Meaning | Status Should Be |
|-------|---------|------------------|
| `pending` | No settlements recorded (0%) | `company_approved` |
| `partial` | Some settled, more to go (1-99%) | `company_approved` |
| `fully_settled` | 100% complete | `settled` |

---

## Files Modified

1. ✅ `products/purchase_views.py` (line 902-916)
   - Changed status assignment logic
   - Only sets `status='settled'` when `settlement_status='fully_settled'`
   - Keeps `status='company_approved'` for partial settlements

2. ✅ Database: PR-2026-0004
   - Status changed from `'settled'` → `'company_approved'`
   - Reflects true state (38% settled)

---

## What You'll See Now

**After Refreshing PR-2026-0004 Page:**

1. **Top Right Badge:** 
   - Before: 🟢 "Settled" (misleading!)
   - After: 🔵 "Approved by Company" (accurate!)

2. **Settlement Status Card:**
   - Status: "Pending" or "Partial" (depending on settlement_status field update)
   - Progress: 38%
   - Remaining: Rs. 3,000.00

3. **Update Settlement Button:**
   - Still visible ✅
   - Still shows remaining amount ✅

4. **After Settling Remaining Rs. 3,000:**
   - Status will auto-change to "Settled" ✅
   - Settlement Status: "Fully Settled" ✅
   - Button will disappear ✅

---

## Status Progression Flowchart

```
Return Created
      ↓
┌──────────┐
│ PENDING  │ ← Created by sales rep
└────┬─────┘
     │ Send to Supplier
     ↓
┌──────────────────┐
│ SENT TO SUPPLIER │ ← Items shipped back
└────┬─────────────┘
     │ Record Company Approval
     ↓
┌──────────────────┐
│ COMPANY APPROVED │ ← Approval recorded
└────┬─────────────┘
     │
     ├─ Add Settlement (partial) ───┐
     │                               │
     │    ┌──────────────────────┐   │
     │    │ COMPANY APPROVED     │ ←─┘ Stay here until 100%
     │    │ settlement: partial  │     Can add more settlements
     │    │ Progress: 1-99%      │
     │    └──────┬───────────────┘
     │           │
     │           │ Add more settlements...
     │           │
     └─ Add Final Settlement (100%) ─┐
                                     │
     ┌──────────────────────┐        │
     │ SETTLED              │ ←──────┘ Only when 100%!
     │ settlement: fully    │          No more actions
     │ Progress: 100%       │
     └──────────────────────┘
```

---

## Summary

**Before Fix:**
- ❌ Status = "Settled" when only 38% settled (confusing!)
- ❌ Status changed too early (as soon as first settlement)
- ❌ Contradicted settlement_status field

**After Fix:**
- ✅ Status = "Approved by Company" for partial settlements (0-99%)
- ✅ Status = "Settled" ONLY when 100% complete
- ✅ Status matches settlement_status properly
- ✅ Clear, logical workflow progression
- ✅ User can track progress accurately

**Your PR-2026-0004 Now:**
- Status: "Approved by Company" (correct!)
- Can continue adding settlements until Rs. 3,000 settled
- Will auto-change to "Settled" when you complete the final settlement

---

**The status badges now accurately reflect the true state of settlement completion!** 🎉
