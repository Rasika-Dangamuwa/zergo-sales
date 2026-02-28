# FOC Reset/Archive System

## Overview
The FOC Reset system allows admin and office staff to periodically archive all FOC (Free of Charge) transaction data while preserving complete historical records. This enables:
- Fresh start for new FOC tracking periods
- Complete audit trail of all FOC activity
- Period-over-period analysis
- Performance tracking across time

## Features

### 1. **Reset Execution**
- **Access**: Admin and Office staff only (not visible to sales reps)
- **Location**: FOC Dashboard → "Reset FOC Data" button
- **Confirmation**: Double confirmation required to prevent accidental resets
- **Action**: Archives all current FOC data and creates snapshot

### 2. **Reset Numbering**
Format: `FOCRST-YYYY-####`
- Examples: `FOCRST-2026-0001`, `FOCRST-2026-0002`
- Auto-increments per year
- Resets to 0001 each January 1st

### 3. **Data Archived**
Each reset captures:
- **Dashboard Totals**: Total FOC received, given, returned, net value, utilization
- **Company Accounts**: FOC breakdown per company
- **Product Summary**: FOC activity per product (received, given, implicit, returned)
- **Sales Rep Summary**: FOC usage per sales representative
- **Transaction Breakdown**: Count and value by transaction type
- **Individual Transactions**: Complete copy of all FOC transactions

### 4. **Reset List Page**
- **URL**: `/sales/foc/resets/`
- Shows all historical resets with summary cards
- Cumulative totals across all resets
- Quick access to detailed views

### 5. **Reset Detail Page**
- **URL**: `/sales/foc/resets/<reset_id>/`
- Tabbed interface showing:
  1. **Company Accounts**: FOC received/given per company
  2. **Products**: Detailed product-wise FOC breakdown
  3. **Sales Reps**: FOC usage by sales representative
  4. **Transaction Breakdown**: Summary by transaction type

## URLs

| Path | View | Description |
|------|------|-------------|
| `/sales/foc/` | `foc_dashboard` | Main FOC dashboard with reset button |
| `/sales/foc/reset/execute/` | `process_foc_reset` | POST endpoint to execute reset |
| `/sales/foc/resets/` | `foc_reset_list` | List all resets with cumulative totals |
| `/sales/foc/resets/<id>/` | `foc_reset_detail` | Detailed view of specific reset |

## Models

### FOCReset
Stores master reset record with snapshots.

**Fields**:
- `reset_number`: Auto-generated (FOCRST-YYYY-####)
- `reset_date`: Timestamp of reset
- `reset_by`: User who performed reset
- `total_foc_received`, `total_foc_given`, `total_foc_returned`, `net_foc_value`: Financial totals
- `avg_utilization`: Average FOC utilization percentage
- `total_transactions`, `total_products`, `total_sales_reps`: Activity counts
- `company_accounts_snapshot`: JSON - Company FOC accounts data
- `product_summary_snapshot`: JSON - Product-wise FOC breakdown
- `sales_rep_summary_snapshot`: JSON - Sales rep FOC usage
- `transaction_types_breakdown`: JSON - Transaction type counts/values
- `notes`: Optional reset notes

### FOCResetTransaction
Archives individual FOC transactions.

**Fields**:
- `reset`: ForeignKey to FOCReset
- `transaction_type`, `transaction_date`: Transaction metadata
- `company_name`, `product_name`, `product_size`: Product/company details
- `shop_name`, `sales_rep_name`: Shop/rep details
- `foc_quantity`, `foc_value`: Transaction amounts
- `shop_price_at_time`: Historical price
- `reference_number`: Source document number
- `notes`: Transaction notes

## Workflow

### Performing a Reset

1. **Navigate**: Go to `/sales/foc/` (FOC Dashboard)
2. **Access**: Only admin/office users see "Reset FOC Data" button
3. **Confirm**: Click button → Confirmation dialog appears
4. **Execute**: Confirm → System performs reset:
   - Queries all active (non-archived) FOC transactions
   - Calculates dashboard totals
   - Snapshots company accounts data
   - Snapshots product summary data
   - Snapshots sales rep summary data
   - Creates FOCReset record with all snapshots
   - Copies all transactions to FOCResetTransaction
   - Marks all original transactions as `is_archived=True`
5. **Redirect**: Automatically redirects to reset list page
6. **Success**: Shows reset number and transaction count

### Viewing Reset History

1. **Navigate**: FOC Dashboard → "Reset History" button
2. **List View**: Shows all resets with:
   - Cumulative totals across all resets
   - Individual reset cards with summaries
   - "View Details" button per reset
3. **Detail View**: Click any reset to see:
   - Complete snapshot data in tabbed interface
   - Company accounts breakdown
   - Product-wise FOC activity
   - Sales rep FOC usage
   - Transaction type breakdown

## Technical Details

### Reset Execution Logic

```python
# Process FOC reset (sales/foc_reset_views.py)
1. Check user permissions (admin/office only)
2. Verify active transactions exist
3. Calculate totals:
   - total_foc_received (transaction_type='foc_received')
   - total_foc_given (transaction_type IN ['foc_given', 'implicit_foc'])
   - total_foc_returned (transaction_type='return_foc_restored')
   - net_foc_value = received - given + returned
4. Snapshot company accounts from FOCValueAccount.objects.all()
5. Snapshot product summary using same logic as foc_product_report
6. Snapshot sales rep summary using same logic as foc_sales_rep_report
7. Create FOCReset record with all snapshots
8. Archive transactions:
   - Copy each FOCValueTransaction → FOCResetTransaction
   - Mark original as is_archived=True
9. Return success with reset_number
```

### JSON Snapshot Structure

**company_accounts_snapshot**:
```json
[
  {
    "company": "Company Name",
    "foc_received": 150000.00,
    "foc_given": 120000.00,
    "net_value": 30000.00,
    "utilization": 80.0
  }
]
```

**product_summary_snapshot**:
```json
[
  {
    "product": "Product Name - Size",
    "company": "Company Name",
    "foc_received_qty": 100.0,
    "foc_given_qty": 80.0,
    "foc_returned_qty": 5.0,
    "foc_received_value": 50000.00,
    "foc_given_value": 40000.00,
    "implicit_foc_value": 5000.00,
    "foc_returned_value": 2500.00
  }
]
```

**sales_rep_summary_snapshot**:
```json
[
  {
    "sales_rep": "John Doe",
    "foc_given_qty": 80.0,
    "foc_returned_qty": 5.0,
    "foc_given_value": 40000.00,
    "implicit_foc_value": 5000.00,
    "foc_returned_value": 2500.00,
    "bills_count": 45
  }
]
```

**transaction_types_breakdown**:
```json
[
  {
    "type": "foc_received",
    "count": 25,
    "total_value": 150000.00
  },
  {
    "type": "foc_given",
    "count": 120,
    "total_value": 100000.00
  }
]
```

## Access Control

**Role Permissions**:
- **Admin**: Full access - can execute resets, view history
- **Office**: Full access - can execute resets, view history
- **Sales Rep**: No access - buttons/pages not visible

**Template Logic**:
```django
{% if user.user_type == 'admin' or user.user_type == 'office' %}
    <!-- Reset buttons visible -->
{% else %}
    <!-- Back to Dashboard button only -->
{% endif %}
```

**View Permissions**:
```python
@login_required
def foc_reset_view(request):
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    # ... rest of view
```

## Database Schema

### Tables Created

1. **sales_foc_resets**: Master reset records
   - Indexes: reset_date, reset_by
   - Unique constraint: reset_number

2. **sales_foc_reset_transactions**: Archived transactions
   - Indexes: reset_id, company_name, sales_rep_name
   - Foreign key: reset → sales_foc_resets

### Migration

Generated: `sales/migrations/0040_focreset_focresettransaction.py`

Applied: `python manage.py migrate`

## Testing

### Manual Test Checklist

- [ ] Only admin/office users see reset buttons
- [ ] Sales reps do NOT see reset buttons
- [ ] Reset confirmation dialog appears
- [ ] Reset captures all FOC data correctly
- [ ] Reset list shows cumulative totals
- [ ] Reset detail shows all snapshot tabs
- [ ] Company accounts data matches dashboard
- [ ] Product summary data matches product report
- [ ] Sales rep summary data matches sales rep report
- [ ] Transactions properly marked as archived
- [ ] Reset number auto-increments correctly
- [ ] Year rollover creates FOCRST-YYYY-0001

### Sample Test

1. Create FOC transactions (purchases with FOC, bills with FOC, returns)
2. Visit `/sales/foc/` as admin
3. Click "Reset FOC Data"
4. Confirm reset
5. Verify redirect to reset list
6. Check reset detail page shows correct data
7. Return to FOC dashboard
8. Verify old transactions not shown (is_archived=True)
9. Create new FOC transactions
10. Verify new transactions appear in dashboard
11. Perform second reset
12. Verify FOCRST-2026-0002 created
13. Check cumulative totals include both resets

## Future Enhancements

### Planned Features
- [ ] Export reset data to PDF/CSV
- [ ] Compare feature (reset A vs reset B)
- [ ] Rollback capability (restore from reset)
- [ ] Scheduled automatic resets (monthly/quarterly)
- [ ] Email notifications on reset
- [ ] Reset approval workflow (request → approve)

### Potential Improvements
- Add reset categories (monthly, quarterly, yearly, manual)
- Include period start/end dates in reset record
- Add financial year support for reset numbering
- Create reset summary dashboard with charts
- Add comments/notes field during reset
- Support partial resets (by company, product, date range)

## Troubleshooting

### Reset Button Not Visible
**Issue**: Admin/office user doesn't see reset button
**Solution**: Check template rendering, verify user.user_type value

### Reset Fails with "No active transactions"
**Issue**: All transactions already archived
**Solution**: Create new FOC transactions before reset

### Reset Number Not Auto-Incrementing
**Issue**: Duplicate reset numbers
**Solution**: Check `generate_reset_number()` method in FOCReset model

### Snapshot Data Empty
**Issue**: Reset created but JSON snapshots are empty
**Solution**: Verify FOCValueTransaction.objects.filter(is_archived=False) returns data

### Permission Denied Error
**Issue**: User gets "Access denied" message
**Solution**: Ensure user.user_type is 'admin' or 'office'

## Related Files

### Models
- `sales/foc_reset_models.py` - FOCReset, FOCResetTransaction models
- `products/models.py` - FOCValueAccount, FOCValueTransaction (is_archived field)

### Views
- `sales/foc_reset_views.py` - Reset execution, list, detail views
- `sales/foc_views.py` - FOC dashboard, reports (query active transactions only)

### Templates
- `templates/sales/foc_dashboard.html` - Reset button + confirmation JS
- `templates/sales/foc_reset_list.html` - Reset list with cumulative totals
- `templates/sales/foc_reset_detail.html` - Tabbed detail view

### URLs
- `sales/urls.py` - Reset URL patterns

### Migrations
- `sales/migrations/0040_focreset_focresettransaction.py` - Initial reset models

## Documentation References
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Complete project overview
- [RETURN_SYSTEM_TERMINOLOGY_STANDARDIZATION.md](RETURN_SYSTEM_TERMINOLOGY_STANDARDIZATION.md) - Return system docs
- [COMMISSION_PAYOUT_SCHEDULER.md](COMMISSION_PAYOUT_SCHEDULER.md) - Similar auto-numbering pattern

## Version History
- **January 10, 2026**: Initial implementation
  - Created FOCReset and FOCResetTransaction models
  - Implemented reset execution logic
  - Built reset list and detail pages
  - Added reset button to FOC dashboard
  - Applied migration 0040
