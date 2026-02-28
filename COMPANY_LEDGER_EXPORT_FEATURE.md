# Company Ledger Export Feature

## Overview
Excel export functionality for company account ledgers, allowing users to download formatted transaction history with running balance and settlement details.

## Implementation Date
January 10, 2026

## Features

### 1. Export to Excel
- **Format**: XLSX (Excel 2007+)
- **Library**: openpyxl 3.1.2
- **File Naming**: `Ledger_CompanyName_YYYYMMDD.xlsx`
- **Example**: `Ledger_ABC_Distributors_20260110.xlsx`

### 2. Export Content

#### Workbook Structure
- **Sheet Name**: Company Name (truncated to 25 chars)
- **Title Row**: Company Account Ledger - Full Company Name
- **Info Rows**: Opening Balance, Current Balance, Filter Period
- **Data Section**: Transactions with running balance

#### Headers (9 Columns)
1. Date
2. Type (Purchase/Return/Payment/etc.)
3. Reference (GRN number, PR number, payment ref)
4. Method (Cash/Cheque/Bank Transfer/Credit)
5. Debit (Purchases, Debit Notes)
6. Credit (Returns, Payments, Credits)
7. Balance (Running balance)
8. Outstanding (Amount still owed on GRNs)
9. Notes

#### Data Rows
- **Opening Balance Row**: Shows opening date and amount
- **Transaction Rows**: All transactions in chronological order
- **Settlement Sub-rows**: Indented rows showing settlement details for returns
  - Format: "  ↪ Settlement Method"
  - Shows GRN number or credit note number
  - Shows settlement amount

### 3. Styling & Formatting

#### Colors
- **Header**: Dark blue background (#366092), white text
- **Title**: Bold, size 14
- **Headers**: Bold, size 12, centered

#### Number Formatting
- All monetary values: `#,##0.00` (thousands separator with 2 decimals)
- Example: `1500` → `1,500.00`

#### Column Widths
- Date: 12
- Type: 15
- Reference: 18
- Method: 15
- Debit/Credit/Balance/Outstanding: 12 each
- Notes: 30

#### Borders
- Thin borders on all header cells

## Implementation Files

### 1. View Function
**File**: `products/company_account_views.py`
**Function**: `export_company_ledger(request, pk)`
**Lines**: 427-560 (approximately 133 lines)

**Key Logic**:
```python
# 1. Get account and filter transactions
account = get_object_or_404(CompanyAccount, pk=pk)
transactions = account.transactions.select_related(...)
# Apply date filters from GET params

# 2. Create Excel workbook
wb = Workbook()
ws = wb.active

# 3. Add title and account info
ws['A1'] = f"Company Account Ledger - {account.company.company_name}"
ws['A2'] = f"Opening Balance: Rs. {account.opening_balance:,.2f}"
ws['A3'] = f"Current Balance: Rs. {account.current_balance:,.2f}"

# 4. Add headers with styling
headers = ['Date', 'Type', 'Reference', ...]
for col_num, header in enumerate(headers, 1):
    cell = ws.cell(row=6, column=col_num)
    cell.value = header
    cell.font = header_font
    cell.fill = header_fill

# 5. Add opening balance row
ws.cell(row=7, column=1).value = account.opening_date
ws.cell(row=7, column=7).value = float(account.opening_balance)

# 6. Add transaction rows with running balance
balance = account.opening_balance
for txn in transactions:
    # Main transaction row
    row_num += 1
    # ... populate cells
    
    # Calculate running balance
    if txn.transaction_type in ['purchase', 'debit']:
        balance += txn.amount
    else:
        balance -= txn.amount
    
    # Settlement sub-rows (for returns)
    if txn.purchase_return:
        settlements = PurchaseReturnSettlement.objects.filter(...)
        for settlement in settlements:
            row_num += 1
            # ... add indented settlement row

# 7. Format columns and return response
response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
wb.save(response)
```

### 2. URL Route
**File**: `products/urls.py`
**Route**: `path('company-accounts/<int:pk>/export/', company_account_views.export_company_ledger, name='export_company_ledger')`
**Line**: 67

### 3. Template Button
**File**: `templates/products/company_account_detail.html`
**Location**: Filter section (lines 102-107)

```html
<a href="{% url 'products:export_company_ledger' account.pk %}?from_date={{ from_date }}&to_date={{ to_date }}" 
   class="btn btn-success">
    <i class="fas fa-file-excel me-1"></i>Export to Excel
</a>
```

**Features**:
- Passes current filter parameters (from_date, to_date)
- Green button with Excel icon
- Positioned next to Filter/Clear buttons

### 4. Dependency
**File**: `requirements.txt`
**Added**: `openpyxl==3.1.2`
**Line**: 12

## Usage

### User Workflow
1. Navigate to Company Account Detail page
2. **Optional**: Apply date filters (From Date / To Date)
3. Click "Export to Excel" button
4. Browser downloads XLSX file
5. Open in Excel/LibreOffice/Google Sheets

### Exported Data
- **Respects Filters**: Only exports transactions within selected date range
- **Includes Summary**: Opening/Current balance, period totals
- **Detailed Breakdown**: All settlements shown as sub-rows
- **Professional Format**: Ready for printing or sharing with accountants

## Technical Details

### Performance Considerations
- **Query Optimization**: Uses `select_related()` to minimize database queries
- **Efficient Processing**: Calculates running balance in single pass
- **Memory Efficient**: Streams directly to response (no temp file)

### Access Control
- **Permissions**: Admin and office staff only
- **Validation**: Same access control as detail view
- **Error Handling**: Returns 404 if account not found

### Browser Compatibility
- **Content-Type**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **Content-Disposition**: `attachment; filename="..."`
- **Works With**: All modern browsers (Chrome, Firefox, Edge, Safari)

## Data Mapping

### Transaction Types → Debit/Credit
| Transaction Type | Debit | Credit |
|-----------------|-------|--------|
| Purchase        | ✓     |        |
| Debit Note      | ✓     |        |
| Return          |       | ✓      |
| Payment         |       | ✓      |
| Credit Note     |       | ✓      |
| Settlement      |       | ✓      |

### Settlement Display
For each purchase return with settlements:
```
Main Row: PR-001 | Return | Rs. 1,386 (credit)
Sub-row:   ↪ Replacement GRN | GRN-002 | Rs. 693
Sub-row:   ↪ Cash Refund | Cash | Rs. 693
```

## Example Output

### Excel File Structure
```
Row 1:  [Merged A1:I1] Company Account Ledger - ABC Distributors
Row 2:  Opening Balance: Rs. 50,000.00
Row 3:  Current Balance: Rs. 20,000.00
Row 4:  Period: 2025-01-01 to 2026-01-10
Row 5:  [Empty]
Row 6:  [Headers with blue background]
Row 7:  2025-01-01 | Opening Balance | | | | | 50,000.00 | | Opening notes...
Row 8:  2025-01-05 | Purchase | GRN-001 | Cash | 30,000.00 | | 80,000.00 | 15,000.00 | ...
Row 9:  2025-01-10 | Return | PR-001 | Replacement | | 1,386.00 | 78,614.00 | | ...
Row 10:   ↪ Replacement GRN | GRN-002 | | | 693.00 | | | Settlement detail
Row 11:   ↪ Cash Refund | Cash | | | 693.00 | | | Settlement detail
...
```

### Number Formatting
- **In Code**: `50000.0`, `1386.5`
- **In Excel**: `50,000.00`, `1,386.50`
- **Thousands Separator**: Comma (,)
- **Decimals**: Always 2 digits

## Future Enhancements

### Potential Improvements
1. **PDF Export**: Add ReportLab-based PDF export option
2. **Chart Generation**: Add summary charts (Excel charts API)
3. **Custom Columns**: Allow users to select which columns to export
4. **Multiple Formats**: Support CSV for simpler data import
5. **Email**: Send ledger directly via email
6. **Scheduled Reports**: Automatic monthly ledger emails
7. **Pivot Tables**: Pre-built pivot tables for analysis
8. **Currency Format**: Support multiple currencies

### Priority 2 Enhancements (From COMPANY_ACCOUNT_SYSTEM_ANALYSIS.md)
- **Payment Allocation Details**: Show which payments applied to which GRNs
- **Aging Report**: 30/60/90 days buckets for outstanding amounts
- **Running Balance in DB**: Store instead of calculating on-the-fly

## Testing

### Test Cases
1. **Export with no filters**: Should include all transactions
2. **Export with date filter**: Should only include filtered transactions
3. **Export with settlements**: Should show settlement sub-rows
4. **Export empty account**: Should show only opening balance
5. **Large export**: Test with 1000+ transactions
6. **Special characters**: Company names with quotes, commas
7. **Download success**: Verify file downloads correctly
8. **Excel compatibility**: Open in MS Excel, LibreOffice, Google Sheets

### Manual Test Scenario
```bash
# 1. Filter transactions
From Date: 2025-01-01
To Date: 2025-12-31

# 2. Click "Export to Excel"

# 3. Verify downloaded file
Filename: Ledger_ABC_Distributors_20260110.xlsx
Size: ~20 KB (depends on data)

# 4. Open in Excel
- Title row merged and centered
- Headers dark blue with white text
- Numbers formatted with commas
- Running balance calculated correctly
- Settlement sub-rows indented
```

## Troubleshooting

### Common Issues

#### 1. Import Error: "No module named 'openpyxl'"
**Solution**: Install openpyxl
```powershell
.\venv\Scripts\pip.exe install openpyxl==3.1.2
```

#### 2. File Download Blocked
**Cause**: Browser security settings
**Solution**: Check downloads folder, allow download in browser

#### 3. Excel Shows "File is corrupted"
**Cause**: Incomplete file generation
**Solution**: 
- Check transaction data for null values
- Ensure all Decimal conversions use `float()`
- Verify workbook saved before return

#### 4. Missing Settlement Details
**Cause**: Query not fetching related objects
**Solution**: Ensure `select_related('replacement_grn')` in settlements query

#### 5. Incorrect Running Balance
**Cause**: Wrong debit/credit logic
**Solution**: Verify transaction_type checks:
- Debit: `['purchase', 'debit']` → balance += amount
- Credit: `['return', 'payment', 'credit', 'settlement']` → balance -= amount

## Related Documentation
- [COMPANY_ACCOUNT_SYSTEM_ANALYSIS.md](COMPANY_ACCOUNT_SYSTEM_ANALYSIS.md) - System architecture and improvement roadmap
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Full project documentation
- [PAYMENT_MANAGEMENT_SUMMARY.md](PAYMENT_MANAGEMENT_SUMMARY.md) - Payment system details

## Change Log

### Version 1.0 (January 10, 2026)
- Initial implementation
- Excel export with openpyxl
- Styled headers and number formatting
- Settlement details sub-rows
- Date filter support
- Running balance calculation
