# Commission System Testing Guide

**Test Date:** January 23, 2026  
**System:** World-Class Commission Management  
**Status:** Ready for Testing

## Pre-Test Setup

### 1. Verify Test Users Exist

Run in Django shell:
```python
from accounts.models import User

# Check existing users
users = User.objects.all()
for u in users:
    print(f"{u.username} - {u.user_type} - {u.get_full_name()}")

# Create test users if needed
admin_user = User.objects.create_user(
    username='admin_test',
    password='test123',
    user_type='admin',
    first_name='Admin',
    last_name='Manager'
)

office_user = User.objects.create_user(
    username='office_test',
    password='test123',
    user_type='office',
    first_name='Office',
    last_name='Staff'
)

sales_user = User.objects.create_user(
    username='sales_test',
    password='test123',
    user_type='sales_rep',
    first_name='Sales',
    last_name='Rep'
)
```

### 2. Create Test Sales Data

```python
from sales.models import Bill, BillItem
from products.models import Product
from shops.models import Shop
from payments.models import OldPayment
from datetime import date

# Get or create shop
shop = Shop.objects.first()
if not shop:
    shop = Shop.objects.create(
        shop_code='SHOP000001',
        shop_name='Test Shop',
        contact_person='Test Contact'
    )

# Get or create product
product = Product.objects.first()

# Create bill for sales_user
sales_user = User.objects.get(username='sales_test')
bill = Bill.objects.create(
    bill_number='BILL-20260123-001',
    shop=shop,
    sales_rep=sales_user,
    bill_date=date.today(),
    total_amount=1000,
    bill_status='confirmed'
)

# Create payment
payment = OldPayment.objects.create(
    bill=bill,
    amount=1000,
    payment_date=date.today(),
    payment_method='cash',
    received_by=office_user,
    status='completed'
)

print(f"Created bill {bill.bill_number} for {sales_user.username}")
print(f"Payment: Rs.{payment.amount} via {payment.payment_method}")
```

### 3. Generate Commission Record

```python
from sales.models import CommissionRecord
from decimal import Decimal

# Create commission record
record, created = CommissionRecord.objects.get_or_create(
    month='2026-01',
    sales_rep=sales_user,
    defaults={'commission_rate': Decimal('5.00')}
)

# Calculate commission
record.calculate_commission()

print(f"Commission Record: {created and 'Created' or 'Updated'}")
print(f"Collected: Rs.{record.collected_amount}")
print(f"Returns: Rs.{record.returns_amount}")
print(f"Commission: Rs.{record.commission_amount}")
```

## Test Cases

### TEST 1: Regular User Access (Sales Rep)

**Login:** `sales_test` / `test123`

**Steps:**
1. Navigate to `/sales/commissions/`
2. Verify: Page loads successfully
3. Verify: **No dropdown** for user selection visible
4. Verify: Stats show only sales_test's data
5. Verify: Commission table shows only sales_test's records
6. Verify: January 2026 record shows Rs.50.00 commission (Rs.1000 × 5%)

**Expected Behavior:**
- ✅ Can see own commission dashboard
- ✅ Cannot see dropdown to select other users
- ✅ Stats match their sales only
- ❌ Cannot access `/sales/commissions/?user_id=X` (redirects to own)

**Test URL Tampering:**
1. Manually visit: `/sales/commissions/?user_id=2` (admin's ID)
2. Expected: Redirect to `/sales/commissions/` (own data)
3. Should see only sales_test's commission

**PASS CRITERIA:** Regular user locked to own data, no access to others

---

### TEST 2: Manager Access (Admin User)

**Login:** `admin_test` / `test123`

**Steps:**
1. Navigate to `/sales/commissions/`
2. Verify: **Dropdown visible** with label "Select User to View Commission"
3. Verify: Dropdown contains all users who made sales
4. Verify: Info box says "Manager View: Select any user..."
5. Select `sales_test` from dropdown
6. Verify: Page reloads with `?user_id=X` in URL
7. Verify: Header shows "Viewing: Sales Rep"
8. Verify: Stats show sales_test's commission (not admin's)

**Expected Behavior:**
- ✅ Can see dropdown with all users
- ✅ Can select any user
- ✅ URL updates with ?user_id parameter
- ✅ Stats update to show selected user's data
- ✅ Navigation preserves user_id parameter

**Test Filter Preservation:**
1. Select user: sales_test (user_id=X)
2. Change year filter to 2026
3. Verify URL: `/sales/commissions/?user_id=X&year=2026`
4. Change month filter to January
5. Verify URL: `/sales/commissions/?user_id=X&year=2026&month=1`

**PASS CRITERIA:** Manager can view any user, filters preserved

---

### TEST 3: Commission Detail View (Regular User)

**Login:** `sales_test` / `test123`

**Steps:**
1. Navigate to `/sales/commissions/`
2. Click "Details" on January 2026 record
3. Verify: URL is `/sales/commissions/2026-01/`
4. Verify: Header shows "Commission Details - January 2026"
5. Verify: **No** "Viewing: [User]" indicator
6. Verify: Summary shows:
   - Total Collected: Rs.1000.00 (1 payment)
   - Total Returns: Rs.0.00 (0 returns)
   - Commission Rate: 5%
   - Commission Amount: Rs.50.00
7. Verify: Payments table shows Test Shop payment
8. Verify: Bills table shows BILL-20260123-001
9. Click "Back" button
10. Verify: Returns to `/sales/commissions/`

**PASS CRITERIA:** Detail view shows only own transactions

---

### TEST 4: Commission Detail View (Manager)

**Login:** `admin_test` / `test123`

**Steps:**
1. Navigate to `/sales/commissions/`
2. Select user: `sales_test` from dropdown
3. Verify URL: `/sales/commissions/?user_id=X`
4. Click "Details" on January 2026 record
5. Verify URL: `/sales/commissions/2026-01/?user_id=X`
6. Verify: Header shows "Viewing: Sales Rep" indicator
7. Verify: Summary shows sales_test's data
8. Click "Recalculate"
9. Verify URL: `/sales/commissions/2026-01/?recalculate=true&user_id=X`
10. Verify: Success message and data recalculated
11. Click "Back"
12. Verify: Returns to `/sales/commissions/?user_id=X` (preserves user_id)

**PASS CRITERIA:** Manager can view/recalculate any user's commission, context preserved

---

### TEST 5: Generate Commission Records (Manager Only)

**Login:** `admin_test` / `test123`

**Steps:**
1. Navigate to office dashboard
2. Find "Generate Commission Records" form
3. Select month: January 2026
4. Click "Generate"
5. Verify: Success message shows count (e.g., "Generated 1 new records")
6. Navigate to `/sales/commissions/`
7. Verify: Commission record exists for all users with sales

**Login:** `sales_test` / `test123`

**Steps:**
1. Try to access `/sales/commissions/generate/` (POST)
2. Expected: Error message "Only office staff and administrators can generate..."
3. Redirect to commission dashboard

**PASS CRITERIA:** Only managers can generate, regular users blocked

---

### TEST 6: Multiple Users with Sales

**Setup:**
```python
# Create sales for office_user
office_user = User.objects.get(username='office_test')
bill2 = Bill.objects.create(
    bill_number='BILL-20260123-002',
    shop=shop,
    sales_rep=office_user,  # Office user makes sale
    bill_date=date.today(),
    total_amount=2000,
    bill_status='confirmed'
)

payment2 = OldPayment.objects.create(
    bill=bill2,
    amount=2000,
    payment_date=date.today(),
    payment_method='cash',
    received_by=office_user,
    status='completed'
)

# Generate commission
record2, _ = CommissionRecord.objects.get_or_create(
    month='2026-01',
    sales_rep=office_user,
    defaults={'commission_rate': Decimal('5.00')}
)
record2.calculate_commission()
```

**Login:** `admin_test` / `test123`

**Steps:**
1. Navigate to `/sales/commissions/`
2. Verify: Dropdown shows:
   - Sales Rep (sales_test)
   - Office Staff (office_test)
3. Select "Office Staff"
4. Verify: Stats show Rs.2000 collected, Rs.100 commission
5. Select "Sales Rep"
6. Verify: Stats show Rs.1000 collected, Rs.50 commission

**PASS CRITERIA:** Dropdown shows ALL users with sales regardless of user_type

---

### TEST 7: No Sales User (Edge Case)

**Setup:**
```python
# Create user with no sales
no_sales_user = User.objects.create_user(
    username='nosales_test',
    password='test123',
    user_type='sales_rep',
    first_name='No',
    last_name='Sales'
)
```

**Login:** `admin_test` / `test123`

**Steps:**
1. Navigate to `/sales/commissions/`
2. Verify: Dropdown does **NOT** include "No Sales"
3. Reason: User has no bills (old_sales__isnull=False filter)

**Login:** `nosales_test` / `test123`

**Steps:**
1. Navigate to `/sales/commissions/`
2. Verify: Page loads (no error)
3. Verify: All stats show Rs.0.00
4. Verify: Commission table empty
5. Verify: Message: "No commission records found"

**PASS CRITERIA:** Users with no sales don't break system, show zeros

---

### TEST 8: Year/Month Filters

**Login:** `sales_test` / `test123`

**Steps:**
1. Navigate to `/sales/commissions/`
2. Change year to 2025
3. Verify: No records shown (no sales in 2025)
4. Change year to 2026
5. Verify: January 2026 record appears
6. Select month: January
7. Verify: URL includes `?year=2026&month=1`
8. Verify: Only January 2026 record shown

**Login:** `admin_test` / `test123`

**Steps:**
1. Navigate to `/sales/commissions/?user_id=X` (sales_test's ID)
2. Change year to 2026
3. Verify URL: `?user_id=X&year=2026`
4. Select month: January
5. Verify URL: `?user_id=X&year=2026&month=1`
6. Change user to office_test
7. Verify URL: `?user_id=Y&year=2026&month=1` (preserves year/month)

**PASS CRITERIA:** Filters work correctly, parameters preserved

---

## Performance Tests

### TEST 9: Large Dataset Performance

**Setup:**
```python
import random
from datetime import timedelta

# Create 100 users with sales
for i in range(100):
    user = User.objects.create_user(
        username=f'user_{i}',
        password='test123',
        first_name=f'User',
        last_name=f'{i}'
    )
    
    # Create 10 bills per user
    for j in range(10):
        bill = Bill.objects.create(
            bill_number=f'BILL-2026-{i}-{j}',
            shop=shop,
            sales_rep=user,
            bill_date=date.today() - timedelta(days=random.randint(0, 30)),
            total_amount=random.randint(500, 5000),
            bill_status='confirmed'
        )
        
        OldPayment.objects.create(
            bill=bill,
            amount=bill.total_amount,
            payment_date=bill.bill_date,
            payment_method='cash',
            received_by=office_user,
            status='completed'
        )
```

**Login:** `admin_test` / `test123`

**Steps:**
1. Navigate to `/sales/commissions/`
2. Verify: Page loads in < 3 seconds
3. Verify: Dropdown shows 100+ users
4. Select a user
5. Verify: Page loads in < 2 seconds
6. Open browser DevTools → Network tab
7. Verify: No N+1 query issues (check Django Debug Toolbar)

**Optimization Check:**
```python
# Views should use select_related/prefetch_related
payments.select_related('bill', 'bill__shop', 'bill__sales_rep')
bills.select_related('shop')
```

**PASS CRITERIA:** System handles 100+ users efficiently

---

## Security Tests

### TEST 10: SQL Injection Prevention

**Steps:**
1. Try URL: `/sales/commissions/?user_id=1'OR'1'='1`
2. Expected: Error or redirect (invalid user ID)
3. Try URL: `/sales/commissions/?user_id=<script>alert(1)</script>`
4. Expected: Error or redirect
5. Try URL: `/sales/commissions/?user_id=-1`
6. Expected: 404 or redirect to own dashboard

**PASS CRITERIA:** No SQL injection, XSS, or invalid ID access

---

### TEST 11: Permission Bypass Attempts

**Login:** `sales_test` / `test123`

**Attempt 1: Access manager endpoint**
```
POST /sales/commissions/generate/
month=2026-01
```
Expected: Error "Only office staff and administrators..."

**Attempt 2: View other user's commission**
```
GET /sales/commissions/?user_id=999
```
Expected: Redirect to own commission dashboard

**Attempt 3: Recalculate other user's commission**
```
GET /sales/commissions/2026-01/?user_id=999&recalculate=true
```
Expected: Redirect or recalculates own commission only

**PASS CRITERIA:** All permission bypass attempts fail gracefully

---

## Regression Tests

### TEST 12: Existing Functionality

Verify these still work:
- ✅ Bill creation (sales_rep field set correctly)
- ✅ Payment creation (bill FK works)
- ✅ Return creation (created_by field set)
- ✅ CommissionRecord.calculate_commission() accuracy
- ✅ Dashboard stats calculations
- ✅ Office dashboard access

**PASS CRITERIA:** No existing features broken

---

## Test Results Template

Copy this to document your test run:

```
======================================
COMMISSION SYSTEM TEST RESULTS
Date: _______________
Tester: _______________
======================================

TEST 1: Regular User Access
□ PASS  □ FAIL
Notes: ___________________________

TEST 2: Manager Access
□ PASS  □ FAIL
Notes: ___________________________

TEST 3: Commission Detail (Regular)
□ PASS  □ FAIL
Notes: ___________________________

TEST 4: Commission Detail (Manager)
□ PASS  □ FAIL
Notes: ___________________________

TEST 5: Generate Commission Records
□ PASS  □ FAIL
Notes: ___________________________

TEST 6: Multiple Users with Sales
□ PASS  □ FAIL
Notes: ___________________________

TEST 7: No Sales User (Edge Case)
□ PASS  □ FAIL
Notes: ___________________________

TEST 8: Year/Month Filters
□ PASS  □ FAIL
Notes: ___________________________

TEST 9: Large Dataset Performance
□ PASS  □ FAIL
Notes: ___________________________

TEST 10: SQL Injection Prevention
□ PASS  □ FAIL
Notes: ___________________________

TEST 11: Permission Bypass Attempts
□ PASS  □ FAIL
Notes: ___________________________

TEST 12: Existing Functionality
□ PASS  □ FAIL
Notes: ___________________________

OVERALL RESULT: □ PASS  □ FAIL

Critical Issues Found:
1. ___________________________
2. ___________________________

Recommendations:
1. ___________________________
2. ___________________________

Sign-off: _______________
Date: _______________
```

## Known Limitations

1. **Date Range Filtering**: Currently only year/month, not custom date ranges
2. **Commission Payment**: No "Mark as Paid" button yet (Phase 2)
3. **Export**: No Excel/PDF export yet (Phase 2)
4. **Email Notifications**: Not implemented (Phase 2)
5. **Commission Adjustments**: No manual adjustment UI (Phase 3)

## Recommended Next Steps After Testing

1. ✅ Fix any bugs found
2. ✅ Add "Mark as Paid" button for managers
3. ✅ Add commission payment history log
4. ✅ Add Excel export for reports
5. ✅ Create monthly auto-generation cron job
6. ✅ Add email notifications
7. ✅ Create commission payment approval workflow

---

**Status:** Ready for comprehensive testing  
**Estimated Test Time:** 2-3 hours  
**Required Test Environments:** Development, Staging
