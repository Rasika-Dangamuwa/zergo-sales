# Monthly Stock Count Feature

## Overview
Added monthly physical stock count feature to verify and improve the accuracy of flavor balance calculations in the hybrid flavor tracking system.

## What Was Added

### 1. MonthlyStockCount Model
**File**: `products/models.py`

```python
class MonthlyStockCount(models.Model):
    # Reference
    count_date = models.DateField()  # Month-end date
    product = models.ForeignKey(Product)
    
    # Count data
    physical_count = models.IntegerField()  # Actual counted quantity
    calculated_balance = models.IntegerField()  # System calculated balance
    variance = models.IntegerField()  # physical_count - calculated_balance
    
    # Adjustment tracking
    adjustment_made = models.BooleanField()
    adjustment_reason = models.TextField()
    
    # Audit
    counted_by = models.ForeignKey(User)
    created_at, updated_at = DateTimeField()
```

### 2. Monthly Stock Count Page
**URL**: `/products/monthly-stock-count/`
**File**: `templates/products/monthly_stock_count.html`

**Features**:
- Month selector (defaults to current month)
- Company filter
- Shows all products with their calculated balances
- Input fields for physical counts
- Real-time variance calculation (JavaScript)
- Color-coded variance badges:
  - 🟢 Green: Perfect match (0 variance)
  - 🟡 Yellow: Overage (+ve variance)
  - 🔴 Red: Shortage (-ve variance)

### 3. Enhanced Flavor Balance Report
**URL**: `/products/flavor-balance/`
**Enhancements**:
- Added "Monthly Stock Count" button in header
- Added month filter to view specific stock count data
- When month is selected, displays:
  - Physical Count column
  - Variance column with color coding
  - Adjustment status (checkmark if adjustment posted)

### 4. Admin Interface
**File**: `products/admin.py`

```python
@admin.register(MonthlyStockCount)
class MonthlyStockCountAdmin(admin.ModelAdmin):
    list_display = ['count_date', 'product', 'physical_count', 
                    'calculated_balance', 'variance', 'adjustment_made']
    list_filter = ['count_date', 'adjustment_made', 'product__company']
    search_fields = ['product__product_name', 'adjustment_reason']
```

## How to Use

### Step 1: Perform Monthly Stock Count
1. Go to `/products/monthly-stock-count/`
2. Select the month (usually current month-end)
3. Optionally filter by company
4. Enter physical counts for each product flavor
5. Watch real-time variance calculation
6. Click "Save Stock Count"

### Step 2: Review Variances
1. Go to `/products/flavor-balance/`
2. Enter the same month in "Stock Count Month" filter
3. Click "Apply Filter"
4. Review the Physical Count and Variance columns
5. Investigate any significant variances:
   - ❌ **Negative variance**: Stock shortage (theft, damage, unrecorded sales)
   - ✅ **Positive variance**: Stock overage (counting error, unrecorded receipts)
   - ✔️ **Zero variance**: Perfect match

### Step 3: Make Adjustments (If Needed)
1. Go to admin: `/admin/products/monthlystockcount/`
2. Find records with significant variances
3. Edit the record
4. Add adjustment reason (e.g., "2 bottles damaged", "Counting error")
5. Check "Adjustment made" checkbox
6. Save

## Benefits

### 1. Accuracy Verification
- Validates calculated flavor balances against physical reality
- Identifies discrepancies early

### 2. Inventory Correction
- Provides data to correct system records
- Documents reasons for variances (audit trail)

### 3. Loss Prevention
- Highlights unusual shortages that may indicate:
  - Theft
  - Unrecorded sales
  - Damage/wastage
  - Data entry errors

### 4. Process Improvement
- Historical variance data shows trends
- Helps improve data entry accuracy
- Identifies problematic products/locations

## Database Schema

### monthly_stock_counts Table
```sql
CREATE TABLE monthly_stock_counts (
    id BIGINT PRIMARY KEY,
    count_date DATE NOT NULL,
    product_id BIGINT NOT NULL REFERENCES products(id),
    physical_count INT NOT NULL,
    calculated_balance INT,
    variance INT,  -- Auto-calculated
    adjustment_made BOOLEAN DEFAULT FALSE,
    adjustment_reason TEXT,
    counted_by_id BIGINT REFERENCES users(id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(count_date, product_id)  -- One count per product per month
);
```

## Workflow Example

### Month-End Stock Count (January 31, 2025)

**Before Count**:
```
250ML Max Orange
- PO Received: 120 bottles
- Sales: 85 bottles
- Calculated Balance: 35 bottles
```

**Physical Count**:
```
Counted: 33 bottles
Variance: 33 - 35 = -2 bottles (shortage)
```

**Investigation**:
```
Found: 2 bottles damaged during transport (not recorded)
Action: Create damage record in system
Adjustment: Mark adjustment_made = True
Reason: "2 bottles damaged in transport on Jan 28"
```

**Result**:
- System updated with damage record
- Calculated balance now matches physical: 33 bottles
- Audit trail preserved

## Best Practices

### 1. Regular Schedule
- Perform counts monthly (last day of month)
- Same date each month for consistency
- Assign specific staff for counting

### 2. Accuracy
- Count in a systematic order (by SKU, then flavor)
- Use two-person verification for high-value items
- Recount items with large variances

### 3. Documentation
- Always document variance reasons
- Include date when issue occurred (if known)
- Attach photos if relevant (damage, etc.)

### 4. Follow-up
- Review variance trends monthly
- Train staff if data entry errors are common
- Investigate recurring shortages
- Update minimum stock levels based on actual usage

## Integration with Existing System

### Hybrid Flavor Tracking Architecture

```
┌─────────────────────────────────────────────┐
│          HYBRID FLAVOR TRACKING             │
├─────────────────────────────────────────────┤
│                                             │
│  1. SKU Level (Size-Price)                  │
│     └─ Aggregate stock only                 │
│                                             │
│  2. Transaction Level (Flavor Details)      │
│     ├─ Purchase Orders (received flavors)   │
│     └─ Sales (sold flavors)                 │
│                                             │
│  3. Calculated Balances (Reports)           │
│     └─ PO Received - Sales = Balance        │
│                                             │
│  4. ✨ PHYSICAL VERIFICATION (NEW)          │
│     ├─ Monthly physical counts              │
│     ├─ Variance detection                   │
│     └─ System accuracy improvement          │
└─────────────────────────────────────────────┘
```

### Data Flow

```
Purchase Order → Record Flavors → Calculate Balance
                                         ↓
Sales → Record Flavors → Update Balance
                                         ↓
                            Monthly Physical Count
                                         ↓
                            Compare: Physical vs Calculated
                                         ↓
                                    Variance?
                                    ↙     ↘
                                  Yes      No
                                   ↓        ↓
                          Investigate    ✅ Good!
                          Document
                          Adjust
```

## Files Modified

### New Files
1. `products/migrations/0005_add_monthly_stock_count.py`
2. `templates/products/monthly_stock_count.html`
3. `MONTHLY_STOCK_COUNT_GUIDE.md` (this file)

### Modified Files
1. `products/models.py` - Added MonthlyStockCount model
2. `products/admin.py` - Added MonthlyStockCountAdmin
3. `products/views.py` - Added monthly_stock_count view, enhanced flavor_balance_report
4. `products/urls.py` - Added monthly-stock-count/ URL
5. `templates/products/flavor_balance_report.html` - Added month filter, stock count columns

## Quick Reference

### URLs
- **Stock Count Page**: `/products/monthly-stock-count/`
- **Flavor Balance Report**: `/products/flavor-balance/`
- **Admin**: `/admin/products/monthlystockcount/`

### Navigation
From Products page → Click "Flavor Balance Report" → Click "Monthly Stock Count"

### Filters
- Company: Filter by specific company
- Month: Select which month's count to view/edit

### Reports
- Variance Report: In Flavor Balance Report with month filter
- Historical Trends: Query MonthlyStockCount model in admin
