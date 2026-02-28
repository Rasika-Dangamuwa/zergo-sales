# Commission System - Testing Checklist ✅

**Testing Date:** January 25, 2026  
**Server:** Running at http://127.0.0.1:8000  
**Status:** Ready for Testing

---

## 🔐 Prerequisites

- [ ] Django server is running (`python manage.py runserver`)
- [ ] Database migration 0030 applied
- [ ] ReportLab installed (v4.4.7)
- [ ] User credentials ready (admin/office/sales_rep)

---

## 📊 Dashboard Testing (Feature #2)

**URL:** http://127.0.0.1:8000/sales/commissions/

### As Sales Rep:
- [ ] Login as sales rep user
- [ ] Dashboard loads successfully
- [ ] See own commission data only (no user selector)
- [ ] 7 statistics cards display correctly:
  - [ ] Current Balance
  - [ ] Total Commission
  - [ ] Amount Collected
  - [ ] Returns Impact
  - [ ] Bills Count
  - [ ] Commission Rate
  - [ ] Total Transactions
- [ ] Chart.js graph displays daily commission trend
- [ ] Transaction history table shows (up to 100 records)
- [ ] Month selector works (last 12 months dropdown)
- [ ] Click on bill number navigates to bill detail
- [ ] Export buttons visible (CSV and PDF)

### As Office Staff:
- [ ] Login as office user
- [ ] User selector dropdown appears
- [ ] Can select different sales reps from dropdown
- [ ] Stats update when changing user
- [ ] Month filter works correctly
- [ ] Can view all sales reps' commission data

---

## 📥 CSV Export Testing (Feature #4a)

**URL:** http://127.0.0.1:8000/sales/commissions/export/csv/

### Basic Export:
- [ ] Click "Export CSV" button on dashboard
- [ ] File downloads immediately
- [ ] Filename format: `commission_statement_YYYY-MM-DD.csv`
- [ ] Open file in Excel/Notepad
- [ ] Verify 11 columns present:
  1. Date
  2. Type
  3. Bill Number
  4. Shop Name
  5. Sales Amount
  6. Collected Amount
  7. Return Amount
  8. Rate (%)
  9. Commission Earned
  10. Running Balance
  11. Notes

### With Filters:
- [ ] Test date range filter (from_date and to_date)
- [ ] Test user filter (office staff only)
- [ ] Test transaction type filter (all, bill, payment, return, writeoff)
- [ ] Verify filtered data matches expectations
- [ ] Sales reps can only export own data (permission check)

---

## 📄 PDF Export Testing (Feature #4b)

**URL:** http://127.0.0.1:8000/sales/commissions/export/pdf/

### Basic Export:
- [ ] Click "Export PDF" button on dashboard
- [ ] File downloads successfully
- [ ] Filename format: `commission_statement_YYYY-MM-DD.pdf`
- [ ] Open PDF in viewer
- [ ] Verify professional formatting:
  - [ ] Header with company name
  - [ ] Sales rep name and date range
  - [ ] Summary section with totals
  - [ ] Transaction table with color coding
  - [ ] Page numbers (if multiple pages)

### Content Verification:
- [ ] Summary shows correct totals
- [ ] Transaction table has all columns
- [ ] Color-coded rows (green for positive, red for negative)
- [ ] Limit to 100 transactions enforced
- [ ] Date formatting correct
- [ ] Amount formatting with commas and decimals

---

## 🔒 Reliability Testing

### Duplicate Prevention:
- [ ] Create bill → Verify single commission transaction created
- [ ] Record payment → Verify no duplicate payment transactions
- [ ] Process return → Verify single return transaction
- [ ] Check database: No duplicate commission transactions exist

### Running Balance Accuracy:
- [ ] Create sequential transactions
- [ ] Verify running balance increments correctly
- [ ] Check that balance = previous balance + current commission
- [ ] No gaps or errors in balance calculation

### Database Constraints:
- [ ] Try to create duplicate bill commission (should fail gracefully)
- [ ] Check logs for proper error handling
- [ ] Verify constraint names in database:
  - [ ] `unique_bill_commission`
  - [ ] `unique_payment_commission`
  - [ ] `idx_commission_balance_calc`
  - [ ] `idx_commission_type_filter`

### Signal Reliability:
- [ ] Create bill → Commission transaction auto-created
- [ ] Record payment → Commission transaction auto-created
- [ ] Process return → Negative commission auto-created
- [ ] Check Django logs for commission events (no print statements)

---

## 🧪 Scenario Testing

### Scenario 1: New Bill Created
1. [ ] Create a new bill for Rs. 10,000
2. [ ] Verify commission transaction created with type='bill_created'
3. [ ] Verify commission_earned = Rs. 0 (no commission until payment)
4. [ ] Check dashboard updates

### Scenario 2: Payment Received
1. [ ] Record payment of Rs. 5,000 on the bill
2. [ ] Verify commission transaction created with type='payment_received'
3. [ ] Verify commission_earned = Rs. 5,000 × rate% (e.g., 5% = Rs. 250)
4. [ ] Verify running_balance updates correctly
5. [ ] Dashboard shows updated balance

### Scenario 3: Return Processed
1. [ ] Process return for Rs. 2,000
2. [ ] Verify commission transaction created with type='return_processed'
3. [ ] Verify commission_earned is negative (e.g., -Rs. 100 for 5% rate)
4. [ ] Verify running_balance decreases
5. [ ] Dashboard reflects return impact

### Scenario 4: Monthly Summary
1. [ ] Select specific month from dropdown
2. [ ] Verify stats show only that month's data
3. [ ] Chart shows daily breakdown for the month
4. [ ] Transaction history filters correctly

---

## 🔍 Error Handling Testing

### Permission Tests:
- [ ] Sales rep cannot access other reps' data
- [ ] Sales rep cannot export other reps' data
- [ ] Office staff can access all data
- [ ] Unauthenticated users redirected to login

### Edge Cases:
- [ ] No transactions exist (dashboard shows zeros)
- [ ] No rate configured (defaults or shows error)
- [ ] Export with no data (empty CSV/PDF)
- [ ] Very large transaction count (pagination/limit works)

### Database Errors:
- [ ] Server handles database connection issues gracefully
- [ ] Migration rollback doesn't break system
- [ ] Constraint violations logged properly

---

## 📱 Cross-Browser Testing

- [ ] Chrome/Edge (Windows)
- [ ] Firefox
- [ ] Mobile browser (if applicable)
- [ ] Chart renders correctly in all browsers
- [ ] Export downloads work in all browsers

---

## 📊 Performance Testing

- [ ] Dashboard loads in < 2 seconds
- [ ] CSV export for 1000 transactions completes quickly
- [ ] PDF export doesn't timeout
- [ ] Chart renders smoothly
- [ ] No memory leaks on repeated page loads

---

## ✅ Final Verification

- [ ] All features work as expected
- [ ] No console errors in browser
- [ ] No Django errors in terminal
- [ ] Documentation is accurate
- [ ] Code follows project conventions
- [ ] Database integrity maintained

---

## 🐛 Bug Tracking

If you find any issues during testing, document them here:

| Issue # | Description | Severity | Status |
|---------|-------------|----------|--------|
| 1 | | | |
| 2 | | | |

---

## 📝 Sign-Off

**Tested By:** ___________________  
**Date:** ___________________  
**Result:** ☐ PASS  ☐ FAIL (see bugs)  
**Notes:** ___________________

---

**Next Steps After Testing:**
1. Deploy to staging environment
2. User acceptance testing
3. Production deployment
4. Monitor Django logs for commission events
5. Set up automated backups
