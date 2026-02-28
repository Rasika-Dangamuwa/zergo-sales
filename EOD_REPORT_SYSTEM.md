# End of Day (EOD) Report System

**Created:** January 31, 2026  
**Status:** Complete ✅

## Overview

Professional EOD (End of Day) reporting system for sales representatives to generate daily sales summaries with product breakdowns, metrics, and multiple export formats.

## Features

### 1. Case Value Management
- **URL:** `/sales/eod/settings/`
- **Purpose:** Manage the case value (price per case) with historical tracking
- **Features:**
  - Add new case value with effective date
  - View historical case values
  - Only one active case value at a time
  - Used to calculate "Total Pack" = Total Sale / Case Value

### 2. EOD Date List
- **URL:** `/sales/eod/`
- **Purpose:** List all dates the sales rep worked (has confirmed bills)
- **Shows:**
  - Date
  - Route worked
  - Total sale amount
  - Bill count
- **Mobile-friendly:** Card-based responsive layout

### 3. Route Management
- **First Access:** When accessing a date's EOD report for the first time, user is prompted to enter their route
- **Update:** Route can be changed later via "Change Route" button in EOD detail
- **Editable:** Route is stored per user per date and can be updated anytime

### 4. EOD Detail Report
- **URL:** `/sales/eod/<date>/`
- **Purpose:** Comprehensive daily sales report

#### Report Header
- **DATE:** Selected date (YYYY/MM/DD format)
- **AREA:** From business settings (DistributorProfile.city)
- **ROUTE:** User's route for the day (e.g., "Wattala & Sedawatta")
- **Sales Rep:** User's full name

#### Product Breakdown
Products grouped by size (250ML, 500ML, 750ML, 1000ML, 1500ML) and then by company/flavor code:

**Example:**
```
250ML SOFT DRINK
  OR: 24    (Orange)
  NE: 18    (Necto)
  CS: 12    (Crush)

500ML SOFT DRINK
  OR: 36
  NE: 24
  CO: 12    (Coca Cola)
  GB: 6     (Ginger Beer)
```

#### Summary Metrics
- **TOTAL SALE:** Total revenue for the day (Rs.)
- **TOTAL PACK:** Total Sale / Case Value (calculated automatically)
- **P/C (Bills):** Number of bills created
- **N/O (New Outlets):** Number of new shops registered on this date
- **FOC VALUE:** Total Free of Charge value given
- **RETURNS:** Total return value (if any returns exist for the date)

### 5. Export Options

#### Print (Browser)
- **Action:** Standard browser print
- **Format:** Printer-friendly layout
- **Use:** Quick printing from desktop or mobile

#### PDF Export
- **URL:** `/sales/eod/<date>/export/pdf/`
- **Format:** Professional A4 PDF using ReportLab
- **Filename:** `EOD_YYYY-MM-DD_username.pdf`
- **Contains:**
  - Report header with all details
  - Product breakdown by size and company
  - Summary section with all metrics
  - Professional formatting with proper spacing

#### Text Export
- **URL:** `/sales/eod/<date>/export/text/`
- **Format:** Plain text (.txt file)
- **Filename:** `EOD_YYYY-MM-DD_username.txt`
- **Use:** Easy sharing via WhatsApp, SMS, email
- **Format Example:**
```
DATE: 2026/01/31
AREA: colombo
ROUTE: wattala & sedawatta
Sales Rep: John Doe

250ML SOFT DRINK
OR: 24
NE: 18
CS: 12

500ML SOFT DRINK
OR: 36
NE: 24

TOTAL SALE: 45680.00
TOTAL PACK: 21.15
P/C: 12
N/O: 02
FOC VALUE: 2340.00
```

## Database Models

### CaseValueSetting
```python
Fields:
- case_value: DecimalField (e.g., 2160.00)
- effective_date: DateField
- is_active: BooleanField (only one active at a time)
- created_by: ForeignKey(User)
- created_at: DateTimeField
- notes: TextField (optional)

Methods:
- get_active_case_value(for_date=None): Returns active case value for given date
- save(): Auto-deactivates other settings when marked active
```

### DailyRoute
```python
Fields:
- user: ForeignKey(User)
- date: DateField
- route: CharField(500) (e.g., "Wattala & Sedawatta")
- created_at: DateTimeField
- updated_at: DateTimeField

Meta:
- unique_together: ['user', 'date']
```

## URL Patterns

```python
path('eod/', eod_views.eod_date_list, name='eod_date_list'),
path('eod/settings/', eod_views.eod_settings, name='eod_settings'),
path('eod/<str:date>/', eod_views.eod_detail, name='eod_detail'),
path('eod/<str:date>/set-route/', eod_views.eod_set_route, name='eod_set_route'),
path('eod/<str:date>/update-route/', eod_views.eod_update_route, name='eod_update_route'),
path('eod/<str:date>/export/text/', eod_views.eod_export_text, name='eod_export_text'),
path('eod/<str:date>/export/pdf/', eod_views.eod_export_pdf, name='eod_export_pdf'),
```

## Files Created

### Models
- `sales/eod_models.py` (115 lines)

### Views
- `sales/eod_views.py` (516 lines)

### Templates
- `templates/sales/eod_settings.html` - Case value management
- `templates/sales/eod_date_list.html` - Date list with summaries
- `templates/sales/eod_set_route.html` - Route entry form
- `templates/sales/eod_detail.html` - Main EOD report

### Migrations
- `sales/migrations/0042_casevaluesetting_dailyroute.py`

## Usage Workflow

### For Sales Representatives

1. **Set Case Value** (One-time/When changed)
   - Go to `/sales/eod/settings/`
   - Enter new case value and effective date
   - Save

2. **Access EOD Report**
   - Go to `/sales/eod/`
   - See list of all dates worked
   - Click on any date

3. **First Time Access**
   - System prompts to enter route
   - Enter route (e.g., "Wattala & Sedawatta")
   - Submit

4. **View Report**
   - See comprehensive breakdown
   - Review product sales by size and flavor
   - Check summary metrics

5. **Share Report**
   - Click "Share" dropdown
   - Choose export format:
     - Print: Browser print dialog
     - PDF: Professional formatted PDF
     - Text: Plain text for messaging
   - Download or share

6. **Update Route** (If needed)
   - Click "Share" → "Change Route"
   - Enter new route
   - Save

### For Office Staff

- Access all representatives' EOD reports
- Review daily sales performance
- Track new outlet acquisitions
- Monitor FOC value usage
- Verify route coverage

## Business Logic

### Product Grouping
```python
# Products grouped by size first
sizes = ['220ML', '250ML', '500ML', '750ML', '1000ML', '1500ML', '2200ML']

# Within each size, grouped by company code
company_codes = ['OR', 'NE', 'CS', 'CO', 'GB', 'MP']
# OR = Orange, NE = Necto, CS = Crush, 
# CO = Coca Cola, GB = Ginger Beer, MP = Malt

# Quantity summed per size+company combination
```

### Calculations
```python
# Total Sale: Sum of all bill.total_amount
total_sale = bills.aggregate(Sum('total_amount'))

# Total Pack: Sale divided by case value
total_pack = total_sale / case_value

# Bill Count: Number of confirmed bills
bill_count = bills.count()

# New Outlets: Shops created on this date by this user
new_outlets = Shop.objects.filter(
    created_by=user, 
    created_at__date=report_date
).count()

# FOC Value: Sum of explicit FOC transactions
foc_value = FOCValueTransaction.objects.filter(
    bill__created_by=user,
    bill__bill_date=report_date,
    foc_type='explicit'
).aggregate(Sum('foc_value'))
```

## Mobile Optimization

### Responsive Design
- **Desktop:** Full-width layout with grid columns
- **Tablet:** Adaptive column count (2-3 columns)
- **Mobile:** Single column card layout, larger touch targets

### Mobile-Specific Features
- Larger fonts for readability
- Touch-friendly buttons
- Optimized spacing
- Print button always visible
- Dropdown share menu

### Print Optimization
- Hides navigation and action buttons
- Removes shadows and colors for clean print
- Page break handling for long reports
- Optimized margins

## Future Enhancements

### Planned
- [ ] Mobile thermal printer integration (Bluetooth)
- [ ] WhatsApp direct sharing
- [ ] Email sending from app
- [ ] Weekly/Monthly summary reports
- [ ] Comparison with previous periods
- [ ] Target vs Actual analysis
- [ ] Commission calculation integration

### Considerations
- Multi-day date range reports
- Export to Excel format
- Automated daily report emails
- Dashboard widgets
- Performance charts

## Technical Notes

### Dependencies
- Django 5.0
- ReportLab (PDF generation)
- Bootstrap 5 (UI framework)
- Font Awesome (icons)

### Database Queries
- Optimized with `select_related()` and `prefetch_related()`
- Aggregation for totals
- Date-based filtering

### Performance
- Product breakdown uses efficient grouping
- Minimal database queries per report
- Caching opportunities for future optimization

## Testing Checklist

- [x] Settings page loads
- [x] Can add new case value
- [x] Case value history displays
- [x] Date list shows worked dates
- [x] Route entry form works
- [x] Route update works
- [x] EOD detail displays correctly
- [x] Product breakdown groups properly
- [x] Summary calculations accurate
- [x] PDF export generates
- [x] Text export formats correctly
- [x] Print layout optimized
- [x] Mobile responsive design
- [x] Database migrations applied

## Support & Maintenance

### Common Issues

**Q: Route not set error?**  
A: First time accessing a date requires route entry. Click the date and enter your route.

**Q: Case value shows 0.00?**  
A: Set active case value in EOD Settings page.

**Q: Product breakdown empty?**  
A: No confirmed bills on selected date, or products don't have size/company data.

**Q: PDF download fails?**  
A: Check ReportLab is installed: `pip install reportlab`

### Data Integrity

- Only confirmed bills included in reports
- Returns tracked separately
- FOC only includes explicit FOC (not implicit discounts)
- New outlets counted by creation date (not first bill date)

## Version History

**v1.0.0** - January 31, 2026
- Initial release
- Core EOD reporting functionality
- PDF and Text export
- Mobile-responsive design
- Case value management
- Route tracking
