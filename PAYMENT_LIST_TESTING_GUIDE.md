# Payment List Page - Testing Guide
**Date:** January 10, 2026  
**Tester:** QA Team / User Acceptance Testing  
**Page:** https://192.168.1.4:8000/payments/

---

## 🧪 Quick Start Testing

### Prerequisites
1. ✅ HTTPS server running (`run_stable_https.py`)
2. ✅ Database has payment records (at least 50+ for pagination testing)
3. ✅ Test users created:
   - Admin user (user_type='admin')
   - Office user (user_type='office')
   - Sales rep user (user_type='sales_rep')
4. ✅ Multiple shops exist with assigned sales reps

---

## 📋 Test Scenarios

### Test 1: Hero Header & Quick Actions
**Steps:**
1. Navigate to `/payments/`
2. Verify hero header displays:
   - ✅ Purple gradient background
   - ✅ "Payment Management" title with icon
   - ✅ Subtitle: "Comprehensive payment tracking..."
   - ✅ "Pending" button (with badge if pending payments exist)
   - ✅ "Export" button (green)

**Expected:**
- Header spans full width
- Gradient visible (purple to dark purple)
- Buttons aligned to right on desktop
- Buttons stack on mobile

---

### Test 2: Statistics Dashboard
**Steps:**
1. Check all 4 stat cards display:
   - ✅ Total Payments (purple border, receipt icon)
   - ✅ Completed (green border, check icon)
   - ✅ Pending (orange border, clock icon)
   - ✅ Bounced/Cancelled (red border, warning icon)

2. Hover over each card
3. Verify numbers match database counts

**Expected:**
- Cards show correct counts
- Amounts formatted as "Rs. X,XXX.XX"
- Hover lifts card up with shadow
- Background overlay visible (faint circle)

---

### Test 3: Analytics Section
**Steps:**
1. Verify analytics section appears (if payments exist)
2. Check method breakdown shows:
   - ✅ Cash (💵 icon)
   - ✅ Cheque (💳 icon)
   - ✅ Bank Transfer (🏦 icon)
   - ✅ Credit (📝 icon)
   - ✅ Return Adjustment (🔄 icon)

3. Hover over each chart
4. Verify totals + counts accurate

**Expected:**
- Only methods with data shown
- Totals formatted correctly
- Hover changes border to purple
- Grid layout responsive

---

### Test 4: Search Functionality
**Steps:**
1. Type in search box: "PAY-2026"
2. Wait 800ms (auto-submit)
3. Verify results filtered
4. Clear search
5. Type shop name
6. Verify shop-based filtering

**Test Cases:**
- ✅ Payment number: "PAY-20260110-001"
- ✅ Shop name: "Perera Store"
- ✅ Bill number: "SAL-20260110-001"
- ✅ Reference number: "CHQ123456"
- ✅ Notes: "partial payment"

**Expected:**
- Auto-submit after 800ms typing stops
- Table updates with matching results
- "No Payments Found" if no match
- Search icon visible in input

---

### Test 5: Quick Date Filters
**Steps:**
1. Click each quick filter:
   - ✅ All Time (default)
   - ✅ Today
   - ✅ Yesterday
   - ✅ This Week
   - ✅ This Month
   - ✅ Last Month

2. Verify active state (purple gradient)
3. Check results match date range

**Expected:**
- Active filter has purple background
- Date calculations accurate (timezone-aware)
- Results update instantly
- URL updates with `?quick_date=today`

---

### Test 6: Advanced Filters
**Steps:**
1. Click "Advanced" button
2. Verify collapsible section opens:
   - ✅ Shop dropdown (all shops or assigned for sales rep)
   - ✅ Status dropdown (pending, completed, cancelled, bounced)
   - ✅ Payment Method dropdown (5 options)
   - ✅ Sort By dropdown (5 sort options)
   - ✅ Date From input
   - ✅ Date To input
   - ✅ Apply Filters button
   - ✅ Reset button

3. Select various combinations:
   - Shop: "Perera Store"
   - Status: "pending"
   - Method: "cheque"
   - Sort: "Highest Amount"
   - Date From: "2026-01-01"
   - Date To: "2026-01-31"

4. Click "Apply Filters"
5. Verify results match criteria
6. Click "Reset"
7. Verify all filters cleared

**Expected:**
- Section hidden by default
- Toggle works smoothly
- All dropdowns populated correctly
- Sales rep sees only assigned shops
- Results accurate for filter combinations
- Reset clears ALL filters

---

### Test 7: Payment Table Display
**Steps:**
1. Verify table has 9 columns:
   - ✅ Payment #
   - ✅ Date & Time
   - ✅ Shop
   - ✅ Bill
   - ✅ Method (badge)
   - ✅ Status (badge)
   - ✅ Amount
   - ✅ Received By
   - ✅ Actions

2. Check each row displays:
   - ✅ Payment number (bold)
   - ✅ Provisional badge (if applicable)
   - ✅ Date (M d, Y format)
   - ✅ Time (h:i A format, gray)
   - ✅ Shop name + code
   - ✅ Bill link (or "Direct")
   - ✅ Method badge (gradient)
   - ✅ Status badge (gradient)
   - ✅ Amount (Rs. X,XXX.XX, large, primary color)
   - ✅ Received by name
   - ✅ Verified by (if verified, small gray text)

3. Hover over rows
4. Click bill links
5. Click action buttons

**Expected:**
- Header has purple gradient background
- Header text is white, uppercase, small
- Rows have light blue hover background
- Hover scales row slightly (1.01)
- Bill links work (navigate to bill detail)
- Badges have correct gradient colors:
  - Cash: Green gradient
  - Cheque: Cyan gradient
  - Bank Transfer: Purple gradient
  - Credit: Orange gradient (black text)
  - Return Adjustment: Pink gradient
  - Pending: Orange (black text)
  - Completed: Green
  - Cancelled: Red
  - Bounced: Gray

---

### Test 8: Action Buttons (Permissions)
**Test as Sales Rep:**
1. Login as sales rep user
2. Navigate to payments list
3. Verify only "View" button visible

**Test as Office/Admin:**
1. Login as office user
2. Navigate to payments list
3. For pending cheques, verify:
   - ✅ "View" button (eye icon)
   - ✅ "Clear" button (check icon, green)
4. For pending bank transfers, verify:
   - ✅ "View" button
   - ✅ "Confirm" button (check icon, green)
5. For completed/bounced payments:
   - ✅ Only "View" button

**Expected:**
- Sales reps cannot clear/confirm
- Office/admin see action buttons
- Buttons only show for pending payments
- Correct button per payment method

---

### Test 9: Pagination
**Setup:** Create 50+ payments in database

**Steps:**
1. Verify pagination controls appear at bottom
2. Check "Showing X to Y of Z payments" displays
3. Verify per-page selector shows:
   - ✅ 10 per page
   - ✅ 20 per page (default, selected)
   - ✅ 50 per page
   - ✅ 100 per page

4. Click page numbers:
   - ✅ First page (double-left arrow)
   - ✅ Previous (single-left arrow)
   - ✅ Page number (2, 3, etc.)
   - ✅ Next (single-right arrow)
   - ✅ Last page (double-right arrow)

5. Change per-page to 50
6. Verify more rows displayed
7. Verify URL updates: `?page=2&per_page=50`
8. Apply filters + paginate
9. Verify filters preserved across pages

**Expected:**
- Default 20 per page
- Page numbers show ±2 from current
- Active page has purple gradient
- Hover changes page link to purple
- Navigation arrows work correctly
- Per-page selector changes results
- Filters preserved in pagination URLs
- "Showing X to Y of Z" accurate

---

### Test 10: CSV Export
**Steps:**
1. Apply some filters:
   - Quick date: "This Month"
   - Status: "completed"
2. Click "Export" button
3. Verify CSV downloads
4. Open CSV file
5. Check headers:
   - ✅ Payment Number
   - ✅ Date
   - ✅ Shop
   - ✅ Bill
   - ✅ Method
   - ✅ Status
   - ✅ Amount
   - ✅ Received By
   - ✅ Verified By
   - ✅ Reference Number
   - ✅ Bank Name
   - ✅ Cheque Date
   - ✅ Notes

6. Verify data matches filtered results
7. Check filename: `payments_export_YYYYMMDD_HHMMSS.csv`

**Expected:**
- CSV downloads immediately
- Filename has timestamp
- All filtered data included
- Headers match OldPayment model
- Data properly escaped (commas, quotes)
- Amounts formatted correctly

---

### Test 11: Empty State
**Steps:**
1. Apply filters that return no results:
   - Shop: "Nonexistent Shop"
   - Status: "bounced"
2. Verify empty state displays:
   - ✅ Large receipt icon (gray)
   - ✅ "No Payments Found" heading
   - ✅ Descriptive message
   - ✅ "Clear Filters" button

3. Click "Clear Filters"
4. Verify redirects to `/payments/` (no filters)

**Expected:**
- Icon size: 5rem
- Icon color: light gray (#dee2e6)
- Centered layout
- Button visible only when filters active
- Button works (clears all filters)

---

### Test 12: Mobile Responsive
**Setup:** Resize browser to mobile width (375px)

**Steps:**
1. Verify hero header:
   - ✅ Title smaller (1.75rem)
   - ✅ Buttons stack vertically
2. Verify stats dashboard:
   - ✅ 2 columns (instead of 4)
3. Verify quick filters:
   - ✅ Stack vertically (column layout)
   - ✅ Full width buttons
4. Verify table:
   - ✅ Horizontal scroll container
   - ✅ All columns visible
5. Verify action buttons:
   - ✅ Stack vertically
   - ✅ Full width

**Expected:**
- No horizontal overflow
- Touch targets 44px minimum
- Readable text sizes
- Easy to navigate
- Pagination controls responsive

---

### Test 13: Performance
**Steps:**
1. Open browser DevTools → Network tab
2. Navigate to `/payments/`
3. Measure page load time
4. Check database queries (Django Debug Toolbar if installed)

**Expected Metrics:**
- ✅ Page load: <300ms
- ✅ Database queries: 1 main + 2 aggregates = 3 total
- ✅ No N+1 queries (select_related used)
- ✅ Template render: <50ms
- ✅ Total page size: <50KB

**Optimization:**
- Queries use select_related('shop', 'bill', 'received_by', 'verified_by')
- Pagination limits data (20 default)
- Aggregates calculated once

---

### Test 14: Security & Permissions
**Test Sales Rep Access:**
1. Login as sales rep
2. Navigate to `/payments/`
3. Verify:
   - ✅ Only sees payments from assigned shops
   - ✅ Shop filter shows only assigned shops
   - ✅ Cannot see other reps' payments
   - ✅ No Clear/Confirm buttons visible

**Test Office/Admin Access:**
1. Login as office user
2. Navigate to `/payments/`
3. Verify:
   - ✅ Sees all payments (all shops)
   - ✅ Shop filter shows all shops
   - ✅ Can clear cheques
   - ✅ Can confirm transfers

**Test Direct URL Access:**
1. As sales rep, try accessing another shop's payment:
   - `https://192.168.1.4:8000/payments/3/` (not their shop)
2. Verify:
   - ✅ Permission denied or 404
   - ✅ Cannot access other shops' data

**Expected:**
- Sales reps have limited access
- Office/admin have full access
- Permission checks enforced
- No data leakage

---

### Test 15: Browser Compatibility
**Test in:**
- ✅ Chrome (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Edge (latest)
- ✅ Mobile Chrome (Android)
- ✅ Mobile Safari (iOS)

**Check:**
- Gradient renders correctly
- Animations smooth
- Hover states work
- Forms submit properly
- Pagination works
- CSV export downloads

**Expected:**
- Consistent across browsers
- No layout breaks
- All features functional

---

## 🐛 Known Issues / Edge Cases

### Edge Case 1: No Payments in Database
**Expected:** Empty state displays with no filters applied

### Edge Case 2: All Payments Same Date
**Expected:** Quick filters still work, some return no results

### Edge Case 3: Very Long Shop Names
**Expected:** Text wraps or truncates with ellipsis

### Edge Case 4: 1000+ Payments
**Expected:** Pagination handles large datasets, export may take 2-3 seconds

### Edge Case 5: Special Characters in Search
**Expected:** Search handles quotes, commas, apostrophes correctly (escaped)

---

## ✅ Acceptance Criteria

All tests must pass before marking as **Production Ready**:

- [ ] All 15 test scenarios pass
- [ ] No console errors (JavaScript)
- [ ] No server errors (500)
- [ ] No database errors
- [ ] Mobile responsive works
- [ ] All browsers supported
- [ ] Performance metrics met
- [ ] Security checks pass
- [ ] Documentation complete
- [ ] User acceptance approved

---

## 📝 Test Report Template

```
Test Date: __________
Tester: __________
Browser: __________
Device: __________

Test Results:
✅ Test 1: Hero Header - PASS
✅ Test 2: Stats Dashboard - PASS
✅ Test 3: Analytics - PASS
✅ Test 4: Search - PASS
✅ Test 5: Quick Filters - PASS
✅ Test 6: Advanced Filters - PASS
✅ Test 7: Table Display - PASS
✅ Test 8: Action Buttons - PASS
✅ Test 9: Pagination - PASS
✅ Test 10: CSV Export - PASS
✅ Test 11: Empty State - PASS
✅ Test 12: Mobile - PASS
✅ Test 13: Performance - PASS
✅ Test 14: Security - PASS
✅ Test 15: Browser Compatibility - PASS

Overall: ✅ PASS / ❌ FAIL

Notes:
_______________________________
_______________________________
```

---

## 🚀 Deployment Checklist

Before deploying to production:

- [ ] All tests pass
- [ ] Code reviewed
- [ ] Database migrations applied (none required for this feature)
- [ ] CSS/JS minified (for production)
- [ ] CDN configured (FontAwesome, etc.)
- [ ] Backup database
- [ ] Monitor server logs
- [ ] Test on production-like environment
- [ ] User training completed
- [ ] Documentation updated

---

## 📞 Support

If issues found during testing:
1. Document exact steps to reproduce
2. Take screenshots/screencasts
3. Check browser console for errors
4. Check server logs
5. Contact development team

**Status:** Ready for Testing ✅
