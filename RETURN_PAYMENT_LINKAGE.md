# Return-to-Payment Linkage Implementation

## Overview
Implemented a complete system to apply approved returns as payment adjustments against bills, allowing shops to use their return credits to pay off outstanding balances.

## Features Implemented

### 1. Database Changes
**New Fields in `Return` Model:**
- `is_applied` (Boolean): Whether return has been applied to payments
- `applied_amount` (Decimal): Total amount already used in payments

**New Fields in `OldPayment` Model:**
- `return_ref` (ForeignKey): Link to Return used for this payment
- Added `return_adjustment` to payment method choices

**Migrations Created:**
- `sales/migrations/0008_return_applied_amount_return_is_applied.py`
- `payments/migrations/0004_oldpayment_return_ref_and_more.py`

### 2. Backend Logic (sales/views.py - add_payment)

**GET Request:**
- Fetches approved returns for the shop
- Excludes fully applied returns
- Calculates available amount for each return
- Passes `available_returns` to template

**POST Request - Return Adjustment:**
- Validates return belongs to same shop
- Validates return is approved
- Validates return has available balance
- Creates payment record with return reference
- Updates return's `applied_amount`
- Marks return as `is_applied` when fully used
- Immediately reduces bill balance (like cash)

### 3. UI Changes

**Add Payment Page (templates/sales/add_payment.html):**
- Added "Return Adjustment" payment type button
- Return selection dropdown with available returns
- Real-time display of return details:
  - Return number and date
  - Total return amount
  - Already applied amount
  - Available amount
- Auto-fills payment amount when return is selected
- Max validation based on available return amount

**Bill Summary Page (templates/sales/bill_summary.html):**
- Shows return adjustment payments with purple badge
- Displays linked return number next to payment
- Indicates payment was made via return credit

## User Workflow

### Creating a Return
1. Sales rep records return from shop (existing flow)
2. Office approves the return
3. Return is now available for payment application

### Applying Return to Bill
1. Navigate to bill detail page
2. Click "Add Payment"
3. Select "Return Adjustment" payment type
4. Choose approved return from dropdown
5. Amount auto-fills with available return balance
6. Can adjust amount (partial application)
7. Submit payment
8. Bill balance reduced immediately
9. Return's applied amount updated

### Viewing Applied Returns
1. Bill summary shows payment with "Return Adjustment" badge
2. Return number displayed next to payment
3. Payment history clearly shows which return was used

## Business Logic

**Return Tracking:**
- Returns can be partially applied across multiple bills
- `applied_amount` tracks total used so far
- `is_applied = True` when `applied_amount >= total_amount`
- Only approved returns can be applied

**Payment Processing:**
- Return adjustments are immediate (like cash)
- Bill paid_amount increases immediately
- Payment status updates automatically
- Shop balance reduced by return amount

**Validation:**
- Return must belong to same shop as bill
- Return must be approved
- Payment amount cannot exceed available return balance
- Payment amount cannot exceed bill balance

## Security & Validation

✅ Shop validation (return matches bill's shop)  
✅ Status validation (only approved returns)  
✅ Amount validation (not exceeding available balance)  
✅ Permission checks (existing add_payment permissions)  
✅ Transaction safety (atomic operations)

## Benefits

1. **Automated Accounting**: Return credits automatically offset bill amounts
2. **Full Traceability**: Every payment links back to specific return
3. **Flexible Application**: Partial or full return amounts
4. **Real-time Updates**: Bill balances update immediately
5. **Audit Trail**: Complete history of return usage

## Testing Checklist

- [ ] Create return and get it approved
- [ ] Apply full return amount to a bill
- [ ] Apply partial return amount to a bill
- [ ] Verify return shows as partially/fully applied
- [ ] Check bill balance updates correctly
- [ ] Verify payment receipt shows return number
- [ ] Test with multiple returns on same bill
- [ ] Ensure unapproved returns don't appear
- [ ] Test return from different shop doesn't work
- [ ] Verify amount validation works

## Future Enhancements

- Return credit dashboard for shops
- Bulk return application to multiple bills
- Return aging report
- Auto-suggest returns when adding payment
