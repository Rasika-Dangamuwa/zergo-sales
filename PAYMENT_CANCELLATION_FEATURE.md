# Payment Cancellation Feature

## Overview
Comprehensive payment cancellation system allowing sales representatives and office staff to cancel mistaken or incorrect payments with full audit trail and automatic bill balance recalculation.

## Business Rules

### Who Can Cancel Payments?

#### Sales Representatives
- **Can cancel**: Only their own payments (where `received_by == current_user`)
- **Cannot cancel**: 
  - Payments created by other sales reps
  - Return adjustment payments (must cancel the return instead)
  - Already cancelled payments

#### Office Staff & Admin
- **Can cancel**: Any payment in the system
- **Cannot cancel**: 
  - Return adjustment payments (must cancel the return instead)
  - Already cancelled payments

### Cancellation Restrictions

**No Time Restrictions**: Unlike the previous implementation (which only allowed same-day cancellations), payments can now be cancelled at any time, regardless of when they were created.

**Protected Payment Types**:
- **Return Adjustment Payments**: Cannot be cancelled directly. If a return adjustment payment needs to be reversed, the associated return must be cancelled instead.

## Technical Implementation

### Backend Logic (`payments/views.py`)

#### Cancel Payment View
Location: `payments/views.py` - Lines 193-271

**Key Features**:
1. **Permission Checking**:
   ```python
   if request.user.is_sales_rep:
       if payment.received_by != request.user:
           messages.error(request, 'You can only cancel your own payments.')
           return redirect('payments:detail', pk=payment.pk)
   ```

2. **Return Adjustment Protection**:
   ```python
   if payment.payment_method == 'return_adjustment' and payment.return_ref:
       messages.error(request, 'Cannot cancel return adjustment payments.')
       return redirect('payments:detail', pk=payment.pk)
   ```

3. **Automatic Bill Recalculation**:
   ```python
   payment.bill.calculate_totals()  # Recalculates paid_amount and balance_amount
   ```

4. **Audit Trail**:
   ```python
   payment.notes += f"\n\n[CANCELLED] {timestamp} by {user}: {reason}"
   ```

5. **Impact Calculation**:
   - Current bill balance
   - New bill balance after cancellation
   - Amount increase to bill balance

### Frontend Implementation

#### Payment Detail Page (`payment_detail.html`)
Location: Lines 620-670

**Cancel Button Logic**:
```django
{% if payment.status != 'cancelled' and payment.payment_method != 'return_adjustment' %}
    {% if request.user.is_sales_rep %}
        {% if payment.received_by == request.user %}
        <a href="{% url 'payments:cancel' payment.pk %}" class="btn btn-danger">
            <i class="fas fa-times me-1"></i> Cancel Payment
        </a>
        {% endif %}
    {% else %}
        {# Office and Admin can cancel any payment #}
        <a href="{% url 'payments:cancel' payment.pk %}" class="btn btn-danger">
            <i class="fas fa-times me-1"></i> Cancel Payment
        </a>
    {% endif %}
{% endif %}
```

**Display Rules**:
- Button only appears if payment is NOT already cancelled
- Button only appears if payment is NOT a return adjustment
- Sales reps only see button on their own payments
- Office/Admin see button on all eligible payments

#### Cancellation Confirmation Page (`cancel_payment.html`)

**World-Class Features**:

1. **Visual Warning Header**:
   - Animated warning icon
   - Clear danger-themed gradient background
   - Prominent title and description

2. **Payment Details Card**:
   - Payment number, bill number, shop name
   - Amount (highlighted in red)
   - Payment method and current status
   - Received by user and payment date

3. **Bill Impact Preview** (if payment is linked to a bill):
   ```
   What will happen to the bill?
   
   Current Bill Balance:     Rs. 5,000.00
   Payment Amount:          - Rs. 2,000.00
   ────────────────────────────────────
   New Bill Balance:         Rs. 7,000.00
   Balance Increase:        ↑ Rs. 2,000.00
   ```

4. **Warning Checklist**:
   - Payment will be marked as CANCELLED
   - Bill balance will increase
   - Bill payment status may change
   - Cancellation recorded with audit trail
   - Action cannot be undone

5. **Required Cancellation Reason**:
   - Textarea input field (required)
   - Reason is permanently stored in payment notes
   - Helps with auditing and accountability

6. **Double Confirmation**:
   - Form validation ensures reason is provided
   - JavaScript confirmation dialog before submission
   - Shows payment details in confirmation message

## User Workflows

### Sales Rep Cancels Own Payment

1. **Navigate to Payment**: Go to payment detail page
2. **Click Cancel**: See "Cancel Payment" button (only on own payments)
3. **Review Details**: Confirmation page shows:
   - Payment information
   - Bill balance impact
   - Warning checklist
4. **Enter Reason**: Type explanation (required)
5. **Confirm**: Click "Confirm Cancellation" → JavaScript confirmation → Submit
6. **Result**: 
   - Payment marked as cancelled
   - Bill balance updated automatically
   - Success message shows old and new balance
   - Redirected back to payment detail page

### Office Staff Cancels Any Payment

1. **Navigate to Payment**: Can access any payment in system
2. **Click Cancel**: See "Cancel Payment" button (on all non-cancelled, non-return-adjustment payments)
3. **Review Details**: Same confirmation page with bill impact
4. **Enter Reason**: Type explanation (required)
5. **Confirm**: Double confirmation process
6. **Result**: Same as sales rep workflow

### Attempting to Cancel Protected Payment

**Return Adjustment Payment**:
```
Error: Cannot cancel return adjustment payments. 
Please cancel the return instead.
```

**Already Cancelled Payment**:
```
Warning: This payment is already cancelled.
```

**Other User's Payment (Sales Rep)**:
```
Error: You can only cancel your own payments.
```

## Database Changes

### Payment Model Updates

**Status Change**:
```python
status: 'pending' or 'completed' → 'cancelled'
```

**Notes Field Update**:
```
Original notes (if any)

[CANCELLED] 2026-01-23 14:35 by John Doe: Entered wrong amount, should be Rs. 5,000 not Rs. 3,000
```

### Bill Model Recalculation

When `bill.calculate_totals()` is called:

1. **Paid Amount Recalculation**:
   ```python
   self.paid_amount = sum(
       payment.amount 
       for payment in self.payments.all() 
       if payment.status != 'cancelled'  # Excludes cancelled payments
   )
   ```

2. **Balance Amount Update**:
   ```python
   self.balance_amount = self.total_amount - self.paid_amount
   ```

3. **Payment Status Update**:
   ```python
   if self.paid_amount == 0:
       self.payment_status = 'unpaid'
   elif self.paid_amount >= self.total_amount:
       self.payment_status = 'paid'
   else:
       self.payment_status = 'partial'
   ```

## URL Configuration

**Route**: `/payments/<payment_id>/cancel/`

**View**: `payments.views.cancel_payment`

**Name**: `payments:cancel`

**Methods**: GET (show form), POST (process cancellation)

## Success Messages

### With Bill Impact:
```
Payment PAY-20260123-001 cancelled successfully. 
Bill SAL-20260123-001 balance updated from Rs. 5,000.00 to Rs. 7,000.00
```

### Without Bill:
```
Payment PAY-20260123-001 cancelled successfully.
```

## Audit Trail

Every cancellation creates a permanent record:

**Payment Notes Field**:
```
[CANCELLED] 2026-01-23 14:35 by Jane Smith: Customer paid cash instead of cheque, re-recording payment
```

**Includes**:
- [CANCELLED] tag
- ISO timestamp
- User's full name
- Cancellation reason

## Security Considerations

1. **@login_required**: Only authenticated users can access
2. **@transaction.atomic**: Database consistency (all changes succeed or all fail)
3. **Permission checks**: Role-based access control
4. **Audit logging**: Full trail of who cancelled what and why
5. **Double confirmation**: JavaScript + Django form validation

## Mobile Responsive Design

**Desktop View**:
- Two-column layout for details
- Side-by-side action buttons
- Full-width impact section

**Mobile View** (<768px):
- Stacked single-column layout
- Full-width action buttons
- Larger touch targets
- Responsive typography
- Compact spacing

## Error Handling

### Permission Denied (Sales Rep on Others' Payment):
```python
messages.error(request, 'You can only cancel your own payments.')
return redirect('payments:detail', pk=payment.pk)
```

### Already Cancelled:
```python
messages.warning(request, 'This payment is already cancelled.')
return redirect('payments:detail', pk=payment.pk)
```

### Return Adjustment Protection:
```python
messages.error(request, 'Cannot cancel return adjustment payments. Please cancel the return instead.')
return redirect('payments:detail', pk=payment.pk)
```

## Testing Checklist

- [ ] Sales rep can cancel own payment
- [ ] Sales rep cannot cancel other rep's payment
- [ ] Office staff can cancel any payment
- [ ] Admin can cancel any payment
- [ ] Cannot cancel already-cancelled payment
- [ ] Cannot cancel return adjustment payment
- [ ] Bill balance updates correctly
- [ ] Bill payment status updates correctly
- [ ] Cancellation reason is saved in notes
- [ ] Audit trail includes user and timestamp
- [ ] Success message shows correct balance change
- [ ] Mobile layout displays properly
- [ ] JavaScript confirmation works
- [ ] Form validation requires reason
- [ ] Database transaction is atomic (all-or-nothing)

## Future Enhancements

1. **Cancellation Reports**: Generate reports of all cancelled payments
2. **Reversal Workflow**: Allow uncancelling payments with admin approval
3. **Email Notifications**: Notify shop owner when payment is cancelled
4. **Bulk Cancellation**: Cancel multiple payments at once
5. **Cancellation Categories**: Predefined cancellation reason dropdown
6. **Dashboard Widget**: Show recently cancelled payments on dashboard
7. **Export Cancelled Payments**: CSV export of cancellation history

## Related Files

- `payments/views.py` (Lines 193-271)
- `payments/urls.py` (cancel route)
- `templates/payments/payment_detail.html` (Cancel button)
- `templates/payments/cancel_payment.html` (Confirmation page)
- `sales/models.py` (Bill.calculate_totals() method)
- `payments/models.py` (OldPayment model)

## Implementation Date

**January 23, 2026** - Complete redesign removing same-day restriction and adding comprehensive features

---

**Document Version**: 1.0  
**Last Updated**: January 23, 2026  
**Author**: AI Agent with User Requirements
