# Provisional Payment System - Implementation Summary

## Problem Solved
Sales reps in the field receive returns from shops but cannot use them for bill payments until office approves the return. This creates workflow bottlenecks when the office is unavailable.

## Solution: Provisional Payments
Reps can now use **PENDING** returns immediately for bill payments. The payment is marked as "Provisional" and automatically confirmed when the return is approved by office.

---

## How It Works

### 1. **Rep Creates Return**
- Rep visits shop, receives damaged/expired products
- Creates return in system → Status: **Pending**
- Return is NOT yet approved by office

### 2. **Rep Creates New Bill**
- Same shop wants to purchase new products
- Rep creates bill as usual

### 3. **Rep Uses Pending Return for Payment**
- Goes to Add Payment page
- Clicks **Return Adjustment** button
- Sees list of returns with status badges:
  - ⏳ **Pending** (yellow badge)
  - ✓ **Approved** (green badge)
- Can select **either** pending or approved return
- System shows warning: "This is a PENDING return. Payment will be marked as Provisional"

### 4. **Provisional Payment Created**
- Payment is recorded with:
  - Method: Return Adjustment
  - Status: **Pending**
  - Flag: **is_provisional = True**
- Shop's balance is NOT updated yet
- Return shows as partially/fully used

### 5. **Office Reviews Return**

**If APPROVED:**
- Return status changes to "Approved"
- Provisional payment automatically becomes "Completed"
- Shop balance is updated (bill.paid_amount increased)
- System shows: "Return approved! 1 provisional payment automatically confirmed"

**If REJECTED:**
- Return status changes to "Rejected"
- Provisional payment automatically becomes "Cancelled"
- Return's applied_amount is reversed
- System shows: "Return rejected. 1 provisional payment cancelled"

---

## Database Changes

### OldPayment Model
```python
is_provisional = BooleanField(default=False)
# True when payment uses pending return
# False when payment uses approved return or other methods
```

### Return Model (Already Exists)
```python
is_applied = BooleanField(default=False)
applied_amount = DecimalField(default=0)
# Tracks how much of return has been used for payments
```

### Migration
- `payments/migrations/0005_add_is_provisional.py` - Added is_provisional field

---

## User Interface

### Add Payment Page
**Payment Method Buttons:**
1. Cash
2. Cheque
3. Bank Transfer
4. **Return Adjustment** (NEW)

**Return Selection:**
- Dropdown shows all available returns
- Each return has status badge:
  - ⏳ Pending (yellow)
  - ✓ Approved (green)
- Warning message for pending returns
- Amount auto-fills from return balance

### Bill Detail Page
**Payment Display:**
- Badge: **Return Adjustment** (blue)
- Return number badge: e.g., "RET20260103001"
- **Provisional badge** (yellow) if using pending return
- Status badge: Pending/Completed

---

## Business Logic

### Payment Creation Logic
```python
if payment_method == 'return_adjustment':
    if return is pending:
        payment.status = 'pending'
        payment.is_provisional = True
        bill.paid_amount NOT updated (stays same)
    else:  # return is approved
        payment.status = 'completed'
        payment.is_provisional = False
        bill.paid_amount += amount
```

### Return Approval Logic
```python
when return is approved:
    1. Change return.return_status to 'approved'
    2. Find all provisional payments using this return
    3. For each provisional payment:
       - Change status to 'completed'
       - Change is_provisional to False
       - Update bill.paid_amount
    4. Show success message with count
```

### Return Rejection Logic
```python
when return is rejected:
    1. Change return.return_status to 'rejected'
    2. Find all provisional payments using this return
    3. For each provisional payment:
       - Change status to 'cancelled'
       - Reverse return.applied_amount
    4. Show warning message with count
```

---

## Benefits

### For Sales Reps:
✅ No need to wait for office approval
✅ Can complete transactions immediately
✅ Better customer service
✅ No phone calls/messages to office

### For Office:
✅ Review returns at convenient time
✅ Clear visibility of provisional payments
✅ Automatic confirmation/cancellation
✅ Audit trail maintained

### For Shop Owners:
✅ Faster service
✅ Returns immediately credited
✅ No delays in purchasing new stock

---

## Safety Features

### Validation:
1. Return must belong to same shop as bill
2. Return must have available amount
3. Amount cannot exceed return balance
4. Clear warning shown for pending returns

### Tracking:
1. is_provisional flag on payment
2. Return reference stored
3. Status tracking (pending → completed/cancelled)
4. Automatic updates on approval/rejection

### Audit Trail:
1. All payments show provisional status
2. Return number visible on payment
3. Status history tracked
4. Approved/rejected by user recorded

---

## Example Workflow

**Scenario:** Rep visits "ABC Store"

1. **9:00 AM** - Rep receives return of 10 damaged bottles
   - Creates Return RET20260103001
   - Total: Rs. 5,000
   - Status: **Pending**

2. **9:15 AM** - ABC Store wants to buy new stock
   - Rep creates Bill BILL20260103042
   - Total: Rs. 15,000

3. **9:20 AM** - Rep adds payment
   - Selects "Return Adjustment"
   - Selects RET20260103001 (⏳ Pending)
   - System warns: "Provisional payment"
   - Amount: Rs. 5,000
   - Payment created: **Pending, Provisional**
   - Remaining balance: Rs. 10,000

4. **2:00 PM** - Office reviews return
   - Approves RET20260103001
   - System automatically:
     - Changes payment status to **Completed**
     - Updates bill paid amount
     - Shows message: "1 provisional payment confirmed"
   - Bill balance now: Rs. 10,000 (confirmed)

**Alternative:** If office rejects return:
- Payment automatically cancelled
- Shop balance unchanged
- Rep needs to collect Rs. 15,000 in full

---

## Files Modified

### Models:
- `payments/models.py` - Added is_provisional field
- `sales/models.py` - Uses existing is_applied, applied_amount

### Views:
- `sales/views.py` - add_payment() updated to handle pending returns
- `sales/return_views.py` - approve_return() auto-confirms provisional payments
- `sales/return_views.py` - reject_return() auto-cancels provisional payments

### Templates:
- `templates/sales/add_payment.html` - Shows pending returns with warnings
- `templates/sales/bill_summary.html` - Shows provisional badge

### Migrations:
- `payments/migrations/0005_add_is_provisional.py`

---

## Testing Checklist

✅ Create return (pending status)
✅ Use pending return for payment
✅ Verify provisional badge shown
✅ Verify bill balance NOT updated
✅ Approve return
✅ Verify payment auto-confirmed
✅ Verify bill balance updated
✅ Create another pending return
✅ Use for payment
✅ Reject return
✅ Verify payment cancelled
✅ Verify return amount released

---

## Next Steps (Optional Enhancements)

1. **Notifications:**
   - Alert office when provisional payment created
   - Alert rep when provisional payment confirmed/cancelled

2. **Reports:**
   - Show all provisional payments report
   - Filter by pending returns needing review

3. **Limits:**
   - Set maximum provisional amount per rep
   - Require supervisor approval above threshold

4. **Mobile App:**
   - Push notifications for status changes
   - Offline mode for provisional payments

---

## Support

For questions or issues, contact development team.

**Version:** 1.0
**Date:** January 3, 2026
**Status:** Production Ready ✓
