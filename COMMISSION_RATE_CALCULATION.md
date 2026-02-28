# Commission Rate Calculation Logic

## Business Rule

**Commission is calculated based on the rate active when the BILL WAS CREATED, not when payment was received.**

## Why This Matters

Consider this scenario:

1. **January 26, 2026 00:01 - January 27, 2026 23:59**: Commission rate is 5%
2. **January 28, 2026 onwards**: Commission rate changes to 7%

### Example Transaction:
- **Bill Created**: January 26, 2026 at 10:00 AM (Rate: 5%)
- **Payment Received**: January 28, 2026 at 2:00 PM (Rate: 7%)
- **Commission Calculation**: Uses 5% rate (from bill creation date)

## Implementation

### Code Location: `sales/models.py` - CommissionTransaction.save()

```python
def save(self, *args, **kwargs):
    """Calculate commission and running balance on save"""
    
    # Get applicable rate based on BILL CREATION DATE (not transaction date)
    if not self.applicable_rate:
        if self.bill:
            # Use bill's creation date for payment/return transactions
            rate_date = self.bill.bill_date.date()
        else:
            # Fallback to transaction date for transactions without bill reference
            rate_date = self.transaction_date.date()
        
        self.applicable_rate = CommissionRateHistory.get_rate_for_date(rate_date)
    
    # Calculate commission based on transaction type
    if self.transaction_type == 'payment_received':
        self.commission_earned = (self.collected_amount * self.applicable_rate) / 100
    
    elif self.transaction_type == 'return_processed':
        self.commission_earned = -(self.return_amount * self.applicable_rate) / 100
    
    # ... rest of calculation logic
```

## How It Works

### 1. **Payment Received Transaction**
- Transaction Date: When payment was received (e.g., Jan 28)
- Rate Lookup Date: **Bill's creation date** (e.g., Jan 26)
- Applicable Rate: Rate active on Jan 26 (5%)
- Commission: Payment amount × 5%

### 2. **Return Processed Transaction**
- Transaction Date: When return was created (e.g., Jan 30)
- Rate Lookup Date: **Original bill's creation date** (e.g., Jan 26)
- Applicable Rate: Rate active on Jan 26 (5%)
- Commission: -(Return amount × 5%)

### 3. **Bill Created Transaction**
- Transaction Date: When bill was created
- Rate Lookup Date: Bill's creation date
- Commission: Rs. 0.00 (no commission until payment received)

## Rate History Management

### Setting a New Rate

```python
from sales.models import CommissionRateHistory
from datetime import date

# Set new rate starting from tomorrow
CommissionRateHistory.set_new_rate(
    rate=7.00,  # 7%
    effective_from=date(2026, 1, 28),
    notes="Rate increase for new promotion period"
)
```

### How Rates Are Applied (**MILLISECOND PRECISION**)

The system uses `CommissionRateHistory.get_rate_for_date(target_datetime)` which:

1. Accepts a **full datetime** (with hours, minutes, seconds, milliseconds)
2. Finds the rate where `created_at <= target_datetime`
3. Orders by `created_at DESC` to get the **most recent** rate active at that time
4. Returns the rate percentage
5. Fallback: 5% if no rates defined

**CRITICAL**: The system now uses **PRECISE TIMESTAMPS**, allowing multiple rate changes on the same day!

### Multiple Rates on Same Day (Supported!)

**Example**: Jan 26, 2026
- 4.00% created at 09:53 AM
- 5.00% created at 10:22 AM

**Result**:
- Bills created at 10:00 AM → Use 4.00% (latest rate before 10:00)
- Bills created at 10:30 AM → Use 5.00% (latest rate before 10:30)
- Bills created at 11:00 AM → Use 5.00% (latest rate before 11:00)

**Implementation**:
```python
# Bill created at 10:00 AM on Jan 26
bill_datetime = datetime(2026, 1, 26, 10, 0, 0)  # 10:00 AM
rate = CommissionRateHistory.get_rate_for_date(bill_datetime)
# Returns: 4.00% (because 5.00% wasn't created until 10:22 AM)

# Bill created at 10:30 AM on Jan 26
bill_datetime = datetime(2026, 1, 26, 10, 30, 0)  # 10:30 AM
rate = CommissionRateHistory.get_rate_for_date(bill_datetime)
# Returns: 5.00% (because 5.00% was created at 10:22 AM)
```

## Example Timeline

```
Jan 23 ─────────┬───────────────┬───────────────┬──────────────►
                │               │               │
             Rate 5%      Bill Created   Payment Received
           starts here    (Jan 26)        (Jan 28)
                          Uses 5%         Still uses 5%
                          rate            from bill date
```

### With Rate Change Mid-Period

```
Jan 23 ─────────┬───────────────┬───────────────┬──────────────►
                │               │               │
             Rate 5%      Rate changes     Payment Received
           (Jan 23-27)      to 7%          (Jan 28)
                         (Jan 28+)
                
Bill created Jan 26 → Uses 5%
Payment received Jan 28 → Still uses 5% (from bill creation)
Bill created Jan 28 → Uses 7%
Payment received Jan 30 → Uses 7% (from bill creation)
```

## Database Schema

### CommissionTransaction Table
- `applicable_rate`: DecimalField - Stores the rate used for calculation
- `bill`: ForeignKey - Links to original bill (used for rate lookup)
- `transaction_date`: DateTimeField - When this transaction occurred
- `commission_earned`: DecimalField - Calculated commission amount

### CommissionRateHistory Table
- `rate`: DecimalField - Commission percentage (e.g., 5.00 for 5%)
- `effective_from`: DateField - Start date of this rate
- `effective_to`: DateField (nullable) - End date of this rate
- `is_active`: BooleanField - Currently active rate

## Testing

Run the test script to verify:

```bash
python manage.py shell < test_rate_fix.py
```

This will show:
- Bill creation date and rate on that date
- Payment date and rate on that date
- Commission calculation using bill's rate (not payment's rate)

## Migration Impact

### Existing Data
Existing commission transactions will continue to use the rate they were calculated with (stored in `applicable_rate` field). This is correct because they were calculated at the time they were created.

### New Transactions
All new payment and return transactions will automatically use the bill's creation date for rate lookup, ensuring consistent commission calculation regardless of when payment is received.

## Important Notes

1. **Returns**: Returns also use the original bill's creation date for rate lookup, ensuring consistent commission reversal
2. **Write-offs**: No commission impact (Rs. 0.00) since no payment was collected
3. **Cancellations**: Payment cancellations reverse the commission using the same rate as the original transaction
4. **Bill Creation**: Bills themselves have Rs. 0.00 commission (only tracking, not earning)

## Summary

✅ **Correct**: Bill created Jan 26 (5% rate) → Payment received Jan 28 (7% rate active) → Commission: 5%

❌ **Wrong**: Bill created Jan 26 (5% rate) → Payment received Jan 28 (7% rate active) → Commission: 7%

This ensures sales reps are fairly compensated based on the business conditions when they made the sale, not when the customer happened to pay.
