# Billing Number Format Standardization

**Date Implemented:** January 10, 2026  
**Format Standard:** `PREFIX-YYYYMMDD-###` (Option A - With Dashes)

## Overview

All transaction numbers across the Zergo Distributors Sales Management System have been standardized to use a consistent format with dashes for better readability, data parsing, and user experience.

## Standardized Format

**Pattern:** `PREFIX-YYYYMMDD-###`

- **PREFIX**: 2-4 letter code identifying transaction type
- **YYYYMMDD**: Date in year-month-day format (e.g., 20260110 for January 10, 2026)
- **###**: Sequential number (001-999), resets daily

**Separator:** Hyphen `-` for visual clarity and easy parsing

## Transaction Number Formats

| Transaction Type | Format | Example | Model/Location |
|-----------------|--------|---------|----------------|
| **Sales Bills** | `SAL-YYYYMMDD-###` | `SAL-20260110-001` | `Sale.generate_sale_number()` in `sales/models.py` |
| **Old Bills** | `BILL-YYYYMMDD-###` | `BILL-20260110-001` | `Bill.generate_bill_number()` in `sales/models.py` |
| **Sales Returns** | `RN-YYYYMMDD-###` | `RN-20260110-001` | `Return.generate_return_number()` in `sales/models.py` |
| **Product Exchanges** | `EXC-YYYYMMDD-###` | `EXC-20260110-001` | `Exchange.generate_exchange_number()` in `sales/models.py` |
| **Cash Payment Vouchers** | `CPV-YYYYMMDD-###` | `CPV-20260110-001` | Generated in `sales/return_views.py` |
| **Regular Payments** | `PAY-YYYYMMDD-####` | `PAY-20260110-0001` | `OldPayment.generate_payment_number()` in `payments/models.py` |
| **Company Returns** | `CR-YYYYMMDD-###` | `CR-20260110-001` | `CompanyReturn.generate_return_number()` in `products/models.py` |
| **Shop Codes** | `SHOP######` | `SHOP000001` | No date component (sequential only) |

## Benefits of Standardization

### 1. **Improved Readability**
- Dashes separate components visually: `SAL-20260110-001` vs `SAL20260110001`
- Easier to read aloud: "SAL dash 2026-01-10 dash 001"
- Better for verbal communication between staff

### 2. **Easier Data Parsing**
```python
# Extract date component
number = "SAL-20260110-001"
date_part = number.split('-')[1]  # "20260110"

# Extract sequence number
seq_num = number.split('-')[-1]  # "001"
```

### 3. **Database Query Optimization**
```python
# Find all sales from a specific date
prefix = f"SAL-{date.strftime('%Y%m%d')}-"
sales = Sale.objects.filter(sale_number__startswith=prefix)
```

### 4. **Consistency**
- All transaction types follow the same pattern
- New developers can predict number formats
- Reduces confusion and documentation burden

### 5. **Professional Appearance**
- Modern, clean look on receipts and invoices
- Matches industry standards (e.g., invoice numbering)
- Easier for customers to reference transactions

## Implementation Details

### Files Modified

1. **sales/models.py** (3 methods updated)
   - `Sale.generate_sale_number()` - Line 79
   - `Bill.generate_bill_number()` - Line 215
   - `Return.generate_return_number()` - Already using dashed format ✓
   - `Exchange.generate_exchange_number()` - Already using dashed format ✓

2. **payments/models.py** (1 method updated)
   - `OldPayment.generate_payment_number()` - Line 68

3. **sales/views.py** (1 inline generator updated)
   - `add_payment()` view - Line 1061

4. **products/models.py** (1 method updated)
   - `CompanyReturn.generate_return_number()` - Line 574

5. **.github/copilot-instructions.md** (documentation updated)
   - Updated number format examples in "Key Domain Models" section

### Code Changes Summary

**Before (No Dashes):**
```python
prefix = f"SAL{today.strftime('%Y%m%d')}"
last_number = int(last_sale.sale_number[-3:])
return f"{prefix}{new_number:03d}"  # SAL20260110001
```

**After (With Dashes):**
```python
prefix = f"SAL-{today.strftime('%Y%m%d')}-"
last_number = int(last_sale.sale_number.split('-')[-1])
return f"{prefix}{new_number:03d}"  # SAL-20260110-001
```

## Backward Compatibility

### Existing Records
- **No migration required** - existing records remain unchanged
- Old format numbers: `SAL20251222001`, `BILL20251222001`
- New format numbers: `SAL-20260110-001`, `BILL-20260110-001`
- Both formats coexist in database without issues

### Query Compatibility
```python
# Queries still work for both formats
Sale.objects.filter(sale_number__contains='20260110')  # Finds both formats
Sale.objects.filter(sale_number__icontains='SAL')      # Finds both formats
```

### Display Consistency
- Templates display both formats correctly
- No UI changes needed - both formats are human-readable

## Testing Recommendations

1. **Create New Transactions**
   - Create a new bill → Verify format is `SAL-20260110-001`
   - Create a return → Verify format is `RN-20260110-001`
   - Create an exchange → Verify format is `EXC-20260110-001`
   - Add a payment → Verify format is `PAY-20260110-0001`

2. **Daily Reset Verification**
   - Verify sequence resets to 001 at midnight
   - Check multiple transactions on same day increment correctly

3. **Search/Filter Testing**
   - Search for old format numbers (should still work)
   - Search for new format numbers (should work)
   - Date range filters should work for both formats

4. **Print/PDF Testing**
   - Generate bill PDF → Verify number displays correctly
   - Print thermal receipt → Verify number fits on paper
   - Export to Excel → Verify numbers aren't corrupted

## Migration Strategy

### Phase 1: Completed ✓
- Code updated to generate new format numbers
- Documentation updated
- No database changes required

### Phase 2: Monitoring (Next 30 days)
- Monitor for any issues with new format
- Verify all number generation working correctly
- Check for any hardcoded format assumptions in code

### Phase 3: Optional Cleanup (Future)
- If desired, can run migration to update old format to new format
- Not required - both formats work fine together
- Only do this if there's a business need for consistency

## Developer Notes

### Adding New Transaction Types

When creating new transaction number formats, follow this pattern:

```python
def generate_transaction_number(self):
    """Generate unique transaction number: PREFIX-YYYYMMDD-###"""
    today = timezone.now()
    prefix = f"PREFIX-{today.strftime('%Y%m%d')}-"
    
    last_transaction = Model.objects.filter(
        transaction_number__startswith=prefix
    ).order_by('-transaction_number').first()
    
    if last_transaction:
        last_number = int(last_transaction.transaction_number.split('-')[-1])
        new_number = last_number + 1
    else:
        new_number = 1
    
    return f"{prefix}{new_number:03d}"
```

### Common Pitfalls to Avoid

❌ **Don't use:**
- `number[-3:]` to extract sequence (won't work with dashes)
- Hardcoded date parsing without splits
- Format assumptions in templates

✅ **Do use:**
- `number.split('-')[-1]` to extract sequence
- `number.split('-')[1]` to extract date component
- Format-agnostic string operations

## Summary

The billing number standardization to `PREFIX-YYYYMMDD-###` format brings consistency, readability, and professionalism to the Zergo Distributors Sales Management System. All new transactions will use this format, while existing records remain compatible.

**Benefits:**
- ✅ Consistent across all transaction types
- ✅ Easier to read and communicate
- ✅ Better for data parsing and queries
- ✅ Professional appearance on documents
- ✅ Backward compatible with existing data
- ✅ No database migration required

**Next Steps:**
- Monitor new transactions for correct formatting
- Update any hardcoded format assumptions in custom reports
- Train staff on new number format (if needed)
