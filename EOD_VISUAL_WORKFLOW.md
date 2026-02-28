# EOD Report System - Visual Workflow

## 🔄 Complete User Journey

```
┌─────────────────────────────────────────────────────────────────┐
│                    SALES REP DAILY WORKFLOW                      │
└─────────────────────────────────────────────────────────────────┘

🌅 MORNING
   │
   ├─► Load van with stock
   ├─► Start sales route
   └─► Create bills throughout the day
       └─► Bills auto-tracked with date/user/shop


🌆 END OF DAY
   │
   ├─► Open app: Menu → EOD Reports
   │   
   ├─► Click today's date card
   │   
   ├─► [First time?] → Enter route name
   │   └─► "Wattala & Sedawatta"
   │   
   ├─► Review EOD Report
   │   ├─► Product breakdown (by size & flavor)
   │   ├─► Total sale amount
   │   ├─► Total pack calculation
   │   ├─► Bill count
   │   ├─► New outlets
   │   └─► FOC value
   │
   ├─► Click "Share" button
   │   ├─► Option 1: Print (quick physical copy)
   │   ├─► Option 2: Export PDF (email to office)
   │   └─► Option 3: Export Text (WhatsApp to supervisor)
   │
   └─► Done! 🎉


📱 SHARING VIA WHATSAPP (Most Popular!)
   │
   ├─► Export Text from EOD report
   ├─► Download: EOD_2026-01-31_yourname.txt
   ├─► Open WhatsApp
   ├─► Select supervisor contact
   ├─► Attach text file
   ├─► Add message: "EOD report for Jan 31"
   └─► Send! ✓✓


🏢 OFFICE STAFF WORKFLOW
   │
   ├─► Receive EOD reports from all reps
   ├─► Review daily performance
   ├─► Check new outlets count
   ├─► Verify FOC usage
   ├─► Adjust case value if needed
   │   └─► Menu → Admin → EOD Settings
   └─► Generate consolidated reports
```

---

## 📊 Data Flow Diagram

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Sales Rep   │      │   System     │      │  Database    │
│  Creates     │─────►│  Tracks      │─────►│  Stores      │
│  Bills       │      │  Data        │      │  Records     │
└──────────────┘      └──────────────┘      └──────────────┘
                             │
                             ▼
                      ┌──────────────┐
                      │  EOD Report  │
                      │  Generation  │
                      └──────────────┘
                             │
                    ┌────────┼────────┐
                    ▼        ▼        ▼
              ┌─────────┬─────────┬─────────┐
              │  Print  │   PDF   │  Text   │
              │ Browser │  File   │  File   │
              └─────────┴─────────┴─────────┘
```

---

## 🗂️ Report Structure

```
┌───────────────────────────────────────────────────────────┐
│                   EOD REPORT HEADER                       │
├───────────────────────────────────────────────────────────┤
│ DATE:      2026/01/31                                     │
│ AREA:      colombo                                        │
│ ROUTE:     Wattala & Sedawatta                           │
│ Sales Rep: John Doe                                       │
└───────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────┐
│                  PRODUCT BREAKDOWN                        │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  250ML SOFT DRINK                                         │
│  ┌────────────────────────────────────┐                  │
│  │ OR (Orange)      │ 24 bottles      │                  │
│  │ NE (Necto)       │ 18 bottles      │                  │
│  │ CS (Crush)       │ 12 bottles      │                  │
│  └────────────────────────────────────┘                  │
│                                                           │
│  500ML SOFT DRINK                                         │
│  ┌────────────────────────────────────┐                  │
│  │ OR (Orange)      │ 36 bottles      │                  │
│  │ NE (Necto)       │ 24 bottles      │                  │
│  │ CO (Coca Cola)   │ 12 bottles      │                  │
│  │ GB (Ginger Beer) │  6 bottles      │                  │
│  └────────────────────────────────────┘                  │
│                                                           │
│  750ML SOFT DRINK                                         │
│  ┌────────────────────────────────────┐                  │
│  │ OR (Orange)      │ 12 bottles      │                  │
│  │ NE (Necto)       │ 12 bottles      │                  │
│  └────────────────────────────────────┘                  │
│                                                           │
└───────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────┐
│                      SUMMARY                              │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  TOTAL SALE        Rs. 45,680.00                         │
│  TOTAL PACK        21.15  (@ Rs. 2,160 per case)        │
│  P/C (Bills)       12                                    │
│  N/O (New Outlets) 02                                    │
│  FOC VALUE         Rs. 2,340.00                          │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## 🎨 Mobile UI Preview

```
┌─────────────────────────────┐
│  ← EOD Reports              │  ← Back Button
├─────────────────────────────┤
│                             │
│  📅 January 31, 2026        │  ← Date Card
│  ───────────────────────    │
│  📍 Wattala & Sedawatta     │  ← Route
│  💰 Rs. 45,680.00           │  ← Total Sale
│  📄 12 bills                │  ← Bill Count
│                             │
├─────────────────────────────┤
│                             │
│  📅 January 30, 2026        │  ← Another Date
│  ───────────────────────    │
│  📍 Negombo & Katunayake    │
│  💰 Rs. 38,540.00           │
│  📄 10 bills                │
│                             │
├─────────────────────────────┤
│                             │
│  📅 January 29, 2026        │
│  ───────────────────────    │
│  📍 Wattala & Sedawatta     │
│  💰 Rs. 42,120.00           │
│  📄 11 bills                │
│                             │
└─────────────────────────────┘
       ↑ Tap any card to view full report
```

### Detailed Report View (Mobile)

```
┌─────────────────────────────┐
│  ← Back          Share ▼    │  ← Action Bar
├─────────────────────────────┤
│                             │
│  ┌───────────────────────┐  │
│  │ DATE: 2026/01/31      │  │  ← Report Header
│  │ AREA: colombo         │  │     (Gradient Blue)
│  │ ROUTE: Wattala...     │  │
│  │ Sales Rep: John Doe   │  │
│  └───────────────────────┘  │
│                             │
│  Product Breakdown          │
│  ──────────────────────     │
│                             │
│  250ML SOFT DRINK           │
│  ┌───┬───┬───┐             │  ← 3-Column Grid
│  │OR │NE │CS │             │
│  │24 │18 │12 │             │
│  └───┴───┴───┘             │
│                             │
│  500ML SOFT DRINK           │
│  ┌───┬───┬───┐             │
│  │OR │NE │CO │             │
│  │36 │24 │12 │             │
│  └───┴───┴───┘             │
│  ┌───┬───┬───┐             │
│  │GB │   │   │             │
│  │ 6 │   │   │             │
│  └───┴───┴───┘             │
│                             │
│  Summary                    │
│  ────────                   │
│  ┌─────────┬─────────┐      │  ← 2-Column Grid
│  │TOTAL    │TOTAL    │      │
│  │SALE     │PACK     │      │
│  │45,680   │21.15    │      │
│  └─────────┴─────────┘      │
│  ┌─────────┬─────────┐      │
│  │P/C      │N/O      │      │
│  │12       │02       │      │
│  └─────────┴─────────┘      │
│  ┌─────────┬─────────┐      │
│  │FOC VALUE│         │      │
│  │2,340    │         │      │
│  └─────────┴─────────┘      │
│                             │
│  ┌───────────────────┐      │
│  │   📱 Print        │      │  ← Print Button
│  └───────────────────┘      │
│                             │
└─────────────────────────────┘
```

---

## 🔐 Access Control Matrix

```
┌──────────────────┬───────────┬────────────┬──────────┐
│ Feature          │ Sales Rep │ Office     │ Admin    │
├──────────────────┼───────────┼────────────┼──────────┤
│ View own EODs    │    ✓      │     ✓      │    ✓     │
│ View all EODs    │    ✗      │     ✓      │    ✓     │
│ Set route        │    ✓      │     ✓      │    ✓     │
│ Update route     │    ✓      │     ✓      │    ✓     │
│ Export reports   │    ✓      │     ✓      │    ✓     │
│ Set case value   │    ✗      │     ✓      │    ✓     │
│ View settings    │    ✗      │     ✓      │    ✓     │
└──────────────────┴───────────┴────────────┴──────────┘
```

---

## 📈 Metrics Calculation Logic

### Total Pack Formula
```
Total Pack = Total Sale Amount ÷ Active Case Value

Example:
  Total Sale = Rs. 45,680.00
  Case Value = Rs. 2,160.00
  
  Total Pack = 45,680 ÷ 2,160
             = 21.148148...
             = 21.15 (rounded to 2 decimals)
```

### Bill Count (P/C)
```
P/C = Purchase Count
    = Number of confirmed bills for the date
    
Only counts bills with status = 'confirmed'
Excludes: draft, cancelled bills
```

### New Outlets (N/O)
```
N/O = Count of shops where:
      - created_by = current user
      - created_at date = report date
      
Shows business expansion activity
```

### FOC Value
```
FOC Value = Sum of FOCValueTransaction where:
            - bill created by current user
            - bill date = report date
            - bill status = confirmed
            - foc_type = 'explicit'
            
Note: Only explicit FOC (bottle giveaways)
      Does NOT include implicit FOC (price discounts)
```

---

## 🎯 Performance Indicators

### Good Performance Indicators
```
✓ High Total Pack (>20 packs/day)
✓ Multiple bills (>10 P/C)
✓ New outlets acquired (N/O > 0)
✓ Balanced product mix across sizes
✓ FOC within budget (<5% of sale)
```

### Areas to Improve
```
⚠ Low Total Pack (<15 packs/day)
⚠ Few bills (<8 P/C)
⚠ No new outlets for extended period
⚠ Heavy concentration on single product
⚠ Excessive FOC usage (>7% of sale)
```

---

## 🔄 Integration Points

```
┌──────────────────────────────────────────────────────┐
│              EOD REPORT ECOSYSTEM                    │
└──────────────────────────────────────────────────────┘

    Bill System ──────┐
                      │
    Shop System ──────┼─────► EOD Report Generator
                      │
    Product System ───┤             │
                      │             │
    FOC System ───────┘             ▼
                              
                         ┌─────────────────┐
                         │  Report Output  │
                         └─────────────────┘
                                  │
                         ┌────────┼────────┐
                         ▼        ▼        ▼
                      Print     PDF      Text
                      
Connected to:
├─► Money Account (future: commission calculation)
├─► Dashboard (future: performance charts)
├─► Notifications (future: automated sharing)
└─► Analytics (future: trend analysis)
```

---

## 📱 Technology Stack

```
Frontend:
├─► Bootstrap 5 (responsive design)
├─► Font Awesome (icons)
├─► Custom CSS (mobile optimization)
└─► Vanilla JavaScript (print functionality)

Backend:
├─► Django 5.0 (web framework)
├─► PostgreSQL (database)
├─► ReportLab (PDF generation)
└─► Python datetime (date handling)

Export Formats:
├─► Browser Print (CSS @media print)
├─► PDF (ReportLab library)
└─► Text (plain string formatting)
```

---

## 🚀 Future Roadmap

### Phase 2 (Planned)
```
□ Mobile thermal printer (Bluetooth)
□ WhatsApp direct integration
□ Email sending from app
□ Weekly/monthly summaries
```

### Phase 3 (Consideration)
```
□ Target vs actual comparison
□ Performance charts/graphs
□ Commission integration
□ Multi-rep comparison
□ Excel export format
```

### Phase 4 (Long-term)
```
□ Automated daily reports
□ Dashboard widgets
□ Real-time alerts
□ AI-powered insights
□ Route optimization
```

---

**Visual Guide Version:** 1.0.0  
**Last Updated:** January 31, 2026  
**Companion Document:** EOD_QUICK_START.md
