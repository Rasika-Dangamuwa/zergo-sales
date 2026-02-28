# Return System Testing Guide
**Implementation Date:** January 6, 2026  
**Server Status:** ✅ Running at https://192.168.1.4:8000

## What Was Implemented

### Mobile-Friendly Interfaces ✅
1. **Return List** - Card layout with color-coded status badges
2. **Return Detail** - Sticky action bar with role-based buttons
3. **Create Return** - Settlement method education with visual options
4. **Bill Payment** - Return credit selector with card layout

### Role-Based Access Control ✅
- **Sales Reps**: Create returns, view own returns, see status alerts
- **Office/Managers**: Approve, reject, delete, settle cash, view all returns

---

## Testing Checklist

### 1️⃣ Mobile Return List (Sales Rep View)
**URL:** `https://192.168.1.4:8000/sales/returns/`

**Test on Mobile Device:**
- [ ] Open URL on smartphone connected to same Wi-Fi
- [ ] Accept SSL certificate warning (self-signed cert)
- [ ] Login as sales rep user
- [ ] Verify card layout appears (not desktop table)
- [ ] Check color-coded borders:
  - 🟡 Yellow border = Pending
  - 🟢 Green border = Approved
  - 🔴 Red border = Rejected
- [ ] Tap "View Details" button (should be ≥44px touch target)
- [ ] Verify you only see YOUR returns (role filtering)

**Desktop Test:**
- [ ] Open same URL on desktop browser
- [ ] Verify table layout appears (hidden on mobile)
- [ ] Check statistics dashboard shows correct counts

---

### 2️⃣ Return Detail Page (Role-Based Actions)
**URL:** `https://192.168.1.4:8000/sales/returns/<return_id>/`

**As Sales Rep (Mobile):**
- [ ] Open a pending return you created
- [ ] Verify sticky action bar at bottom of screen
- [ ] Should see: "Return Status: Pending Approval" alert
- [ ] Should NOT see: Approve/Reject buttons
- [ ] Try to approve via POST (should get permission error)

**As Manager/Office (Desktop or Mobile):**
- [ ] Login as office/admin user
- [ ] Open a pending return
- [ ] Verify you SEE Approve/Reject/Delete buttons
- [ ] Test Approve action:
  - Click "Approve Return"
  - Check stock increased for returned items
  - Verify settlement_status changed (unsettled for cash, available for credit)
- [ ] Test Reject action:
  - Reject a pending return with reason
  - Verify status changed to rejected
  - Check if cash voucher was cancelled (if applicable)

---

### 3️⃣ Create Return Mobile
**URL:** `https://192.168.1.4:8000/sales/returns/create/`

**Mobile Test:**
- [ ] Open on smartphone
- [ ] Select a shop with existing bills
- [ ] Tap reason chips (should be large, ≥110px wide)
- [ ] Scroll to settlement method section
- [ ] Verify 3 visual option cards:
  - 💵 Cash Refund (with icon, title, description)
  - 📝 Credit Note
  - 📊 Next Bill Discount
- [ ] Tap each option - should highlight selected
- [ ] Select products and quantities
- [ ] Submit return
- [ ] Verify return created successfully

---

### 4️⃣ Bill Payment - Return Credit Selector
**URL:** `https://192.168.1.4:8000/sales/bills/<bill_id>/add-payment/`

**Prerequisites:**
1. Create and approve a return for credit (settlement_method = credit_note)
2. Find a bill for the same shop with balance due

**Desktop & Mobile Test:**
- [ ] Open add payment page for the bill
- [ ] Click "Return Adjustment" payment type
- [ ] Verify return cards appear (NOT dropdown)
- [ ] Check each card shows:
  - Return number (blue, bold)
  - Available amount (green badge)
  - Status badge (pending/approved)
  - Total return, applied amount, available balance
- [ ] Tap a return card to select it
- [ ] Verify card highlights (blue border, light blue background)
- [ ] Check payment amount auto-fills with available return amount
- [ ] If pending return: verify warning shows "Provisional payment"
- [ ] Submit payment
- [ ] Verify payment recorded with correct status

---

### 5️⃣ Cash Settlement Workflow
**As Office Staff:**

**Step 1: Rep Creates Cash Return**
- [ ] Rep creates return with settlement_method = "cash"
- [ ] Return status = pending
- [ ] Settlement status = unsettled

**Step 2: Manager Approves**
- [ ] Manager approves return
- [ ] Stock increases
- [ ] Settlement status = unsettled (waiting for cash)

**Step 3: Office Settles Cash**
- [ ] Office staff opens return detail
- [ ] Clicks "Settle Cash" button
- [ ] Verify CPV voucher generated (CPV-YYYYMMDD-XXX)
- [ ] Settlement status = settled_cash
- [ ] Cash paid by = current user
- [ ] Print CPV receipt

---

### 6️⃣ Provisional Payment System
**Test Pending Returns in Payments:**

**Step 1: Create Pending Return for Credit**
- [ ] Rep creates return with settlement_method = credit_note
- [ ] Return status = pending (not yet approved)

**Step 2: Use in Bill Payment**
- [ ] Open bill payment page for same shop
- [ ] Select "Return Adjustment"
- [ ] Pending return should appear with ⏳ Pending badge
- [ ] Select pending return
- [ ] Warning should show: "Provisional payment until return approved"
- [ ] Submit payment
- [ ] Payment status = pending (not completed)
- [ ] Bill balance NOT reduced yet

**Step 3: Approve Return**
- [ ] Manager approves the return
- [ ] Payment status should change to completed
- [ ] Bill balance should now be reduced

---

## Role Permission Testing

### Sales Rep Restrictions
**Should FAIL with permission errors:**
```
❌ Approve returns created by others
❌ Reject any returns
❌ Delete returns created by others
❌ Settle cash for any returns
❌ View returns created by other reps
```

**Should SUCCEED:**
```
✅ Create returns for own route shops
✅ View own returns only
✅ Delete own pending returns
✅ See status alerts (not action buttons)
```

### Office/Manager Permissions
**Should SUCCEED for all:**
```
✅ Approve any pending return
✅ Reject any pending return with reason
✅ Delete any pending return
✅ Settle cash for approved cash returns
✅ View all returns (all reps)
✅ Filter by shop, status, date
```

---

## Mobile Responsive Breakpoints

### Desktop View (≥768px)
- Table layout for return list
- Desktop navigation bar
- Full sidebar filters

### Mobile View (<768px)
- Card layout for return list
- Sticky mobile action bar
- Touch targets ≥44px
- Single column layouts

**Test Responsiveness:**
- [ ] Resize browser from 1920px → 320px
- [ ] Check layout switches at 768px
- [ ] Verify no horizontal scrolling on mobile
- [ ] Test on actual devices:
  - [ ] Android phone
  - [ ] iPhone
  - [ ] Tablet

---

## Error Message Validation

**Test Permission Errors Show Friendly Messages:**

1. **Rep tries to approve:**
   > "You do not have permission to approve returns. Only office staff and managers can approve returns."

2. **Rep tries to reject:**
   > "You do not have permission to reject returns. Only office staff and managers can reject returns."

3. **Rep tries to settle cash:**
   > "You do not have permission to settle cash returns. Only office staff can process cash settlements."

4. **Rep tries to delete other's return:**
   > "You do not have permission to delete this return. You can only delete your own pending returns."

---

## Quick Test URLs

### Mobile (from phone on same Wi-Fi)
```
https://192.168.1.4:8000/sales/returns/
https://192.168.1.4:8000/sales/returns/create/
https://192.168.1.4:8000/sales/returns/<id>/
https://192.168.1.4:8000/sales/bills/<id>/add-payment/
```

### Desktop (localhost)
```
https://127.0.0.1:8000/sales/returns/
https://127.0.0.1:8000/admin/sales/return/
```

---

## Known Issues (Expected)
- ⚠️ SSL certificate warnings (self-signed cert - accept to continue)
- ⚠️ RuntimeWarnings for model reloading (development only, not production issue)

## Server Control
**Start Server:**
```powershell
.\venv\Scripts\python.exe manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:8000
```

**Stop Server:** `Ctrl+C` or `Ctrl+Break`

**Current Status:** 🟢 Running on https://192.168.1.4:8000

---

## Next Steps After Testing
1. ✅ Fix any bugs found during testing
2. ✅ Adjust mobile layouts if needed
3. ✅ Test on production-like data volumes
4. ✅ User acceptance testing with actual field reps
5. ✅ Deploy to production server

---

**Testing Started:** January 6, 2026  
**Implementation Status:** ✅ Complete - Ready for Testing
