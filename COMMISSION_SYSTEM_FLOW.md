# Commission System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    WORLD-CLASS COMMISSION SYSTEM                    │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                          USER LOGIN                                  │
│                              ↓                                       │
│                    Auto-detect User Role                            │
└──────────────────────────────────────────────────────────────────────┘
                                ↓
                    ┌───────────┴───────────┐
                    │                       │
        ┌───────────▼────────┐   ┌─────────▼──────────┐
        │  REGULAR USER      │   │  MANAGER           │
        │  (Sales Rep)       │   │  (Admin/Office)    │
        └───────────┬────────┘   └─────────┬──────────┘
                    │                       │
                    │                       │
        ┌───────────▼────────┐   ┌─────────▼──────────────────────────┐
        │                    │   │                                    │
        │  VIEW OWN          │   │  SEE DROPDOWN:                    │
        │  COMMISSION        │   │  "Select User to View Commission" │
        │  ONLY              │   │                                    │
        │                    │   │  Options:                          │
        │  viewing_user =    │   │  - All Users with Sales            │
        │  request.user      │   │  - User A (username_a)             │
        │  (LOCKED)          │   │  - User B (username_b)             │
        │                    │   │  - User C (username_c)             │
        │                    │   │                                    │
        └───────────┬────────┘   └─────────┬──────────────────────────┘
                    │                       │
                    └───────────┬───────────┘
                                ↓
                    ┌───────────────────────┐
                    │  COMMISSION DASHBOARD │
                    └───────────┬───────────┘
                                ↓
    ┌──────────────────────────────────────────────────────────────┐
    │                                                              │
    │  📊 STATS FOR viewing_user:                                 │
    │                                                              │
    │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
    │  │  COLLECTED │ │  RETURNS   │ │  PENDING   │ │   PAID   │ │
    │  │  Rs.900.00 │ │  Rs.90.00  │ │  Rs.40.50  │ │  Rs.0.00 │ │
    │  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
    │                                                              │
    │  📅 MONTHLY COMMISSION RECORDS:                             │
    │                                                              │
    │  ┌─────────┬───────────┬──────────┬─────┬────────┬─────────┐│
    │  │ MONTH   │ COLLECTED │ RETURNS  │RATE │ COMM.  │ STATUS  ││
    │  ├─────────┼───────────┼──────────┼─────┼────────┼─────────┤│
    │  │ Jan2026 │ Rs.900.00 │ Rs.90.00 │ 5%  │ Rs.40.50│PENDING ││
    │  │         │           │          │     │        │[DETAILS]││
    │  └─────────┴───────────┴──────────┴─────┴────────┴─────────┘│
    │                                                              │
    │  💳 RECENT PAYMENTS FROM viewing_user's BILLS:              │
    │  - Fahad Stores: Rs.900.00 (Cash) - 15 Jan 2026             │
    │                                                              │
    └──────────────────────────────────────────────────────────────┘
                                ↓
                        Click "Details"
                                ↓
                    ┌───────────────────────┐
                    │  COMMISSION DETAIL    │
                    │  (January 2026)       │
                    └───────────┬───────────┘
                                ↓
    ┌──────────────────────────────────────────────────────────────┐
    │                                                              │
    │  📊 SUMMARY METRICS:                                        │
    │  - Total Collected: Rs.900.00 (1 payment)                   │
    │  - Total Returns: Rs.90.00 (1 return)                       │
    │  - Commission Rate: 5%                                      │
    │  - Commission Amount: Rs.40.50                              │
    │                                                              │
    │  📋 DETAILED TRANSACTIONS:                                  │
    │                                                              │
    │  PAYMENTS:                                                  │
    │  ┌────────┬──────────────┬──────────┬────────┬──────────┐   │
    │  │ Date   │ Shop         │ Bill No. │ Method │ Amount   │   │
    │  ├────────┼──────────────┼──────────┼────────┼──────────┤   │
    │  │15Jan26 │Fahad Stores  │BILL-001  │ Cash   │ Rs.900.00│   │
    │  └────────┴──────────────┴──────────┴────────┴──────────┘   │
    │                                                              │
    │  RETURNS:                                                   │
    │  ┌────────┬──────────────┬──────────┬──────────┐            │
    │  │ Date   │ Shop         │ Return No│ Amount   │            │
    │  ├────────┼──────────────┼──────────┼──────────┤            │
    │  │18Jan26 │Fahad Stores  │RN-001    │ Rs.90.00 │            │
    │  └────────┴──────────────┴──────────┴──────────┘            │
    │                                                              │
    │  BILLS CREATED:                                             │
    │  ┌────────┬──────────────┬──────────┬──────────┐            │
    │  │ Date   │ Shop         │ Bill No. │ Total    │            │
    │  ├────────┼──────────────┼──────────┼──────────┤            │
    │  │15Jan26 │Fahad Stores  │BILL-001  │ Rs.900.00│            │
    │  └────────┴──────────────┴──────────┴──────────┘            │
    │                                                              │
    └──────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                     DATA FLOW ARCHITECTURE                       │
└──────────────────────────────────────────────────────────────────┘

1. BILL CREATION
   User → Creates Bill → bill.sales_rep = User (who created it)
   
2. PAYMENT RECEIVED
   Office → Creates OldPayment → payment.bill = Bill
                                → commission earned by bill.sales_rep
   
3. RETURN CREATED  
   User → Creates Return → return.created_by = User
                        → reduces User's commission
   
4. COMMISSION CALCULATION
   CommissionRecord.calculate_commission():
   
   ┌─────────────────────────────────────────────────────┐
   │                                                     │
   │  collected_amount = SUM(                            │
   │    OldPayment.amount                                │
   │    WHERE bill.sales_rep = User                      │
   │    AND payment_date IN month                        │
   │    AND status = 'completed'                         │
   │  )                                                  │
   │                                                     │
   │  returns_amount = SUM(                              │
   │    Return.total_amount                              │
   │    WHERE created_by = User                          │
   │    AND created_at IN month                          │
   │  )                                                  │
   │                                                     │
   │  commission_amount =                                │
   │    (collected_amount - returns_amount) × 5%         │
   │                                                     │
   └─────────────────────────────────────────────────────┘
```

## Security Model

```
┌──────────────────────────────────────────────────────────────────┐
│                      SECURITY LAYERS                             │
└──────────────────────────────────────────────────────────────────┘

LAYER 1: LOGIN REQUIRED
   ↓
   All commission views require authentication
   @login_required decorator

LAYER 2: ROLE DETECTION
   ↓
   is_manager = user.is_admin OR user.is_office_staff
   
LAYER 3: VIEWING USER SELECTION
   ↓
   IF is_manager:
       viewing_user = User from ?user_id parameter OR request.user
   ELSE:
       viewing_user = request.user (LOCKED)
   
LAYER 4: DATA FILTERING
   ↓
   ALL queries filtered by viewing_user:
   - CommissionRecord.objects.filter(sales_rep=viewing_user)
   - OldPayment.objects.filter(bill__sales_rep=viewing_user)
   - Return.objects.filter(created_by=viewing_user)
   - Bill.objects.filter(sales_rep=viewing_user)

LAYER 5: TEMPLATE SECURITY
   ↓
   Regular users: No user dropdown shown
   Managers: Can select any user with sales
   
   {% if is_manager %}
       Show dropdown + management controls
   {% else %}
       Show only own data
   {% endif %}
```

## URL Parameter Flow

```
REGULAR USER ACCESS:
/sales/commissions/
   → viewing_user = request.user
   → Shows only their commission

/sales/commissions/?user_id=123  ← BLOCKED
   → Redirected to /sales/commissions/
   → Cannot access other users

MANAGER ACCESS:
/sales/commissions/
   → viewing_user = request.user
   → Shows dropdown with all users
   → Can select any user

/sales/commissions/?user_id=5
   → viewing_user = User(id=5)
   → Shows User 5's commission
   → All filters preserve user_id

/sales/commissions/2026-01/?user_id=5
   → viewing_user = User(id=5)
   → Shows User 5's January 2026 details
   
/sales/commissions/2026-01/?user_id=5&recalculate=true
   → Recalculates User 5's commission
   → Redirects back with user_id preserved
```

## Key Success Factors

✅ Universal Access - Any user who makes sales earns commission
✅ Role-Based Views - Auto-detects and shows appropriate interface
✅ Data Security - Regular users locked to own data
✅ Manager Oversight - Full visibility and control
✅ Context Preservation - user_id maintained across navigation
✅ Clean URLs - RESTful parameter passing
✅ Scalable - Works with 10 users or 10,000 users
✅ Maintainable - Clear separation of concerns
✅ User-Friendly - Intuitive dropdowns and navigation
✅ Production-Ready - No migrations, no breaking changes
