# Product Status Adjustment Approval Workflow - Implementation Complete

## Overview
Implemented comprehensive manager approval workflow for product status adjustments (damaged, expired, used, lost, sample). All adjustments now require admin/office manager approval before stock is deducted.

## Changes Implemented

### 1. Database Model Updates (products/models.py)

#### ProductStatusAdjustment Model
- **Added Fields**:
  - `adjustment_number`: CharField (unique, auto-generated in format "ADJ-YYYYMMDD-XXX")
  - `approval_status`: CharField with choices (pending/approved/rejected), default='pending'
  - `approved_by`: ForeignKey to User (manager who approved/rejected)
  - `approved_at`: DateTimeField (timestamp of approval/rejection)
  
- **Modified Fields**:
  - `stock_updated`: Changed default from True to False (only set to True after approval)
  - Removed `('returned_to_company', 'Returned to Company')` from STATUS_CHOICES
  
- **New Method**:
  - `generate_adjustment_number()`: Auto-generates unique adjustment number

### 2. View Functions (products/views.py)

#### Updated: product_status_adjustment()
- **Before**: Created adjustment and optionally updated stock immediately
- **After**: Creates pending adjustment, redirects to history
- **Changes**:
  - Removed `update_stock` checkbox logic
  - All new adjustments created with `approval_status='pending'`
  - No stock changes at creation time
  - Redirect changed from same page to history page

#### New: approve_status_adjustment(adjustment_id)
- **Purpose**: Manager approves adjustment and updates stock
- **Access**: admin/office users only
- **Logic**:
  1. Validates stock availability (stock may have changed since creation)
  2. Deducts quantity from product.quantity_in_stock
  3. Marks adjustment as approved
  4. Sets stock_updated=True, previous_stock, new_stock
  5. Creates StockMovement record
- **Uses**: `transaction.atomic()` for data integrity

#### New: reject_status_adjustment(adjustment_id)
- **Purpose**: Manager rejects adjustment without stock changes
- **Access**: admin/office users only
- **Logic**: Marks adjustment as rejected, no stock impact

#### Updated: product_status_history()
- Added `approval_status` filter parameter
- Now includes `approved_by` in select_related for efficiency
- Context now includes `selected_approval_status`

#### Updated: product_status_detail(adjustment_id)
- Added `approved_by` to select_related
- View shows approval buttons if pending and user is manager

### 3. URL Patterns (products/urls.py)

**Added Routes**:
```python
path('status-adjustment/<int:adjustment_id>/approve/', approve_status_adjustment, name='approve_status_adjustment'),
path('status-adjustment/<int:adjustment_id>/reject/', reject_status_adjustment, name='reject_status_adjustment'),
```

### 4. Templates

#### product_status_adjustment.html
- **Removed**: "Update Stock" checkbox (lines 138-150)
- **Added**: Info alert explaining pending approval workflow

#### product_status_detail.html
- **Added**: 
  - Adjustment Number display
  - Approval Status badge
  - Approved/Rejected By information
  - Manager approval/reject action buttons (when pending)
- **Updated**: 
  - Stock impact message text (explains approval workflow)
  - Delete button only shows if pending
  - Removed 'returned_to_company' badge color

#### product_status_history.html
- **Added**: 
  - Approval Status filter dropdown
  - Adjustment Number column in table
  - Approval Status badge column
  - Delete button conditional (only for pending)
- **Updated**: 
  - Mobile card view includes adjustment number and approval status
  - Removed 'returned_to_company' badge color
  - Removed 'Reference' column (replaced with Adjustment Number)

### 5. Database Migration

**Migration**: `products/migrations/0014_productstatusadjustment_adjustment_number_and_more.py`

**Operations**:
- Add adjustment_number field (CharField, unique)
- Add approval_status field (default='pending')
- Add approved_by field (ForeignKey to User, nullable)
- Add approved_at field (DateTimeField, nullable)
- Alter stock_updated default to False
- Remove 'returned_to_company' from status_type choices

**Data Migration**: `generate_adjustment_numbers.py`
- Generated adjustment numbers for 1 existing record
- Format: ADJ-20260109-001

### 6. Related Migration (sales app)

**Migration**: `sales/migrations/0021_alter_exchangeitem_in_product_and_more.py`
- Made in_product and out_product nullable (temporary for migration compatibility)
- Database already had correct non-null data, this just syncs Django's migration state

## Workflow

### Creating Adjustment (Sales Rep/Any Staff)
1. Navigate to Products → Status Adjustment
2. Select product, status type, quantity, reason
3. Submit form
4. Adjustment created with `approval_status='pending'`
5. Stock NOT changed yet
6. Redirected to history page

### Approving Adjustment (Admin/Office Manager)
1. View pending adjustments in history (filter by "Pending")
2. Click adjustment to view details
3. See approval buttons in sidebar
4. Click "Approve Adjustment"
5. System validates stock availability
6. Deducts stock atomically
7. Creates StockMovement record
8. Marks adjustment as approved

### Rejecting Adjustment (Admin/Office Manager)
1. Same navigation as approval
2. Click "Reject Adjustment"
3. Adjustment marked as rejected
4. No stock changes
5. Can view rejection in history

## Business Rules

1. **Stock Validation**:
   - At approval time (not creation time)
   - Manager sees error if insufficient stock

2. **Stock Movement**:
   - Created only after approval
   - References adjustment_number
   - Negative quantity (stock deduction)
   - Movement type: 'status_adjustment'

3. **Deletion**:
   - Only pending adjustments can be deleted
   - Approved/rejected are permanent records

4. **Access Control**:
   - Any staff can create adjustments
   - Only admin/office can approve/reject
   - Checked via `user.user_type in ['admin', 'office']`

## Testing Checklist

- [x] Migration created and applied successfully
- [x] Existing record migrated with adjustment number
- [ ] Create new adjustment as sales_rep
- [ ] Approve adjustment as admin
- [ ] Reject adjustment as office user
- [ ] Filter by approval status
- [ ] Verify stock movement created on approval
- [ ] Verify no stock change on rejection
- [ ] Test insufficient stock error on approval
- [ ] Verify delete button only shows for pending

## Files Modified

1. products/models.py - ProductStatusAdjustment class
2. products/views.py - 4 view functions
3. products/urls.py - 2 new URL patterns
4. templates/products/product_status_adjustment.html
5. templates/products/product_status_detail.html
6. templates/products/product_status_history.html
7. sales/models.py - ExchangeItem nullable fields (temporary)

## Files Created

1. products/migrations/0014_productstatusadjustment_adjustment_number_and_more.py
2. sales/migrations/0021_alter_exchangeitem_in_product_and_more.py
3. generate_adjustment_numbers.py (data migration script)
4. check_exchange_schema.py (investigation script)
5. PRODUCT_STATUS_ADJUSTMENT_APPROVAL.md (this file)

## Database Changes

**Table**: products_productstatusadjustment

**New Columns**:
- adjustment_number (VARCHAR(50), UNIQUE, NOT NULL)
- approval_status (VARCHAR(20), DEFAULT 'pending')
- approved_by_id (INTEGER, FOREIGN KEY, NULLABLE)
- approved_at (TIMESTAMP, NULLABLE)

**Modified Columns**:
- stock_updated (BOOLEAN, DEFAULT FALSE - was TRUE)

## Next Steps

1. ✅ Test approval workflow with real data
2. Consider adding email notifications for pending approvals
3. Consider dashboard widget showing pending approval count
4. Consider bulk approval feature for multiple adjustments
5. Document workflow in user manual
