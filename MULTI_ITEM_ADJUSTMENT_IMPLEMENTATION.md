# Multi-Item Product Status Adjustment Implementation

**Implementation Date**: January 9, 2026  
**Status**: ✅ COMPLETE

## Overview
Implemented multi-item support for Product Status Adjustments, allowing users to mark multiple products as damaged/expired/lost/etc. in a single adjustment transaction - similar to how Bills and Exchanges handle multiple line items.

## Key Features

### 1. **Multi-Item Support**
- Create one adjustment containing multiple products
- Each product can have different quantity
- All items share common fields: status_type, reason, stock_action, approval_status
- Follows established Bill→BillItem and Exchange→ExchangeItem pattern

### 2. **Backward Compatibility**
- Existing single-item adjustments automatically converted to multi-item format
- Old adjustments still display correctly
- Data migration preserves all historical data

### 3. **Dynamic UI**
- Add/remove items dynamically with JavaScript
- Real-time stock validation
- Total quantity calculation
- Mobile-responsive card-based layout

### 4. **Approval Workflow (Unchanged)**
- Still requires manager approval (admin/office users)
- Stock updated only after approval
- Tracks approval history per adjustment

## Technical Changes

### Models (`products/models.py`)

#### ProductStatusAdjustment (Updated)
```python
# Made product/quantity nullable for multi-item support
product = models.ForeignKey(..., null=True, blank=True)  # Legacy field
quantity = models.IntegerField(default=0)  # Legacy field

# New properties
@property
def total_items(self):
    """Total number of items in this adjustment"""
    return self.items.count() if hasattr(self, 'items') else (1 if self.product else 0)

@property
def total_quantity(self):
    """Total quantity across all items"""
    if hasattr(self, 'items') and self.items.exists():
        return sum(item.quantity for item in self.items.all())
    return self.quantity
```

#### ProductStatusAdjustmentItem (NEW)
```python
class ProductStatusAdjustmentItem(models.Model):
    adjustment = models.ForeignKey(ProductStatusAdjustment, related_name='items')
    product = models.ForeignKey(Product, related_name='adjustment_items')
    quantity = models.IntegerField()
    
    # Stock tracking (updated after approval)
    stock_updated = models.BooleanField(default=False)
    previous_resaleable = models.IntegerField(default=0)
    new_resaleable = models.IntegerField(default=0)
    previous_non_resaleable = models.IntegerField(default=0)
    new_non_resaleable = models.IntegerField(default=0)
    
    class Meta:
        unique_together = [['adjustment', 'product']]  # Prevent duplicates
```

### Views (`products/views.py`)

#### product_status_adjustment (Updated)
- Changed from accepting single product_id to accepting items JSON array
- Validates each item independently
- Creates ProductStatusAdjustmentItem records for each product
- JSON format: `[{product_id: 1, quantity: 5}, {product_id: 2, quantity: 10}]`

#### approve_status_adjustment (Updated)
- Loops through adjustment.items.all() instead of single product
- Updates stock for each item based on stock_action
- Tracks stock changes per item
- Provides summarized success message with item count

### Templates

#### `product_status_adjustment.html` (Redesigned)
- **Add Items Section**: Product dropdown + quantity input + Add button
- **Items List Table**: Shows added products with remove buttons
- **Common Fields**: Status type, stock action, reason (applied to all items)
- **JavaScript**: Dynamic item management, validation, JSON serialization
- **Total Calculation**: Live updates as items added/removed

#### `product_status_detail.html` (Updated)
- **Items Table**: Shows all products in adjustment with columns:
  - Product Code, Product Name, Quantity
  - Resaleable Before/After (if approved)
  - Non-Resaleable Before/After (if move_to_non_resaleable action)
- **Total Row**: Sum of all item quantities
- **Legacy Support**: Still displays single-item adjustments correctly

#### `product_status_history.html` (Updated)
- Desktop Table: Shows "X items (Y units)" for multi-item adjustments
- Mobile Cards: Displays item count and total quantity
- Handles both multi-item and legacy single-item format

### Admin (`products/admin.py`)

#### ProductStatusAdjustmentItemInline (NEW)
- Tabular inline for viewing/editing items in Django admin
- Shows stock impact per item (before/after values)

#### ProductStatusAdjustmentAdmin (Updated)
- Changed list_display to show total_items, total_quantity
- Added inline for items
- Updated search fields to use adjustment_number instead of product

### Migrations

#### Migration 0017
- Made ProductStatusAdjustment.product nullable
- Made ProductStatusAdjustment.quantity default to 0
- Created ProductStatusAdjustmentItem model

#### Migration 0018 (Data Migration)
- Converted 2 existing adjustments to multi-item format
- Created corresponding ProductStatusAdjustmentItem for each old adjustment
- Preserves all historical data (previous_stock, new_stock)
- Reversible (can rollback if needed)

## Usage Examples

### Creating Multi-Item Adjustment

1. **Navigate to**: Products → New Status Adjustment
2. **Select Common Fields**:
   - Status Type: Damaged
   - Stock Action: Move to Non-Resaleable
   - Reason: "Water damage during storage"
3. **Add Items**:
   - Select Product A, Quantity 5, Click Add
   - Select Product B, Quantity 10, Click Add
   - Select Product C, Quantity 3, Click Add
4. **Review**: Items table shows 3 products, total 18 units
5. **Submit**: Creates adjustment ADJ-20260109-001 with pending status

### Approval Process (Manager)

1. **View History**: See adjustment with "3 items (18 units)"
2. **Click Details**: View all 3 products with quantities
3. **Approve**: Stock updated for all 3 products simultaneously
   - Product A: Resaleable -5, Non-Resaleable +5
   - Product B: Resaleable -10, Non-Resaleable +10
   - Product C: Resaleable -3, Non-Resaleable +3
4. **Confirmation**: "Adjustment approved for 3 items. Product A: R50→45, NR0→5; Product B: R100→90, NR5→15; Product C: R20→17, NR0→3"

## Benefits

1. **Efficiency**: Mark 10 damaged products in one transaction instead of 10 separate adjustments
2. **Consistency**: All items share same reason, approval workflow, stock action
3. **Audit Trail**: One adjustment number covers all related changes
4. **Mobile Friendly**: Dynamic UI works on phones with card-based layout
5. **Backward Compatible**: All existing adjustments still work

## Testing Checklist

- ✅ Create multi-item adjustment with 3+ products
- ✅ Validation: Prevent duplicate products in same adjustment
- ✅ Validation: Check insufficient stock error
- ✅ Approval workflow: Approve multi-item adjustment
- ✅ Stock updates: Verify all items' stock changed correctly
- ✅ Rejection workflow: Reject multi-item adjustment (no stock change)
- ✅ History display: Desktop table shows item count
- ✅ History display: Mobile cards show item count
- ✅ Detail view: Items table with stock impact
- ✅ Django Admin: View adjustment with items inline
- ✅ Legacy adjustments: Old single-item adjustments still display
- ✅ Migration: Existing adjustments converted successfully

## Database Changes

**New Table**: `product_status_adjustment_items`
- Columns: id, adjustment_id (FK), product_id (FK), quantity, stock_updated, previous_resaleable, new_resaleable, previous_non_resaleable, new_non_resaleable
- Constraints: UNIQUE(adjustment_id, product_id)

**Modified Table**: `product_status_adjustments`
- Made product_id nullable (was required)
- Made quantity default to 0 (was required with no default)

## Future Enhancements (Optional)

1. **Quick Fill Buttons**: "Add all low stock", "Add all expired" batch add
2. **Copy Items**: Duplicate adjustment items to new adjustment
3. **Edit Items**: Allow editing pending adjustment items before approval
4. **Bulk Approval**: Approve multiple adjustments at once
5. **Excel Export**: Export multi-item adjustment details to spreadsheet
6. **Stock Alerts**: Show warning if adding item would exceed available stock

## Notes

- All items in one adjustment must be approved/rejected together
- Cannot mix different stock actions in one adjustment
- Product dropdown still follows display_order, product_name sorting
- JavaScript validates stock availability before adding item
- Total quantity shown in badges across all views
- Adjustment number format unchanged: ADJ-YYYYMMDD-XXX

## Migration Safety

- ✅ Reversible: Can rollback migration 0018 (removes items, restores nulls)
- ✅ Data Preservation: All old adjustment data preserved in items
- ✅ No Data Loss: Legacy product/quantity fields still exist
- ✅ Validation: System check identified 0 issues after implementation
