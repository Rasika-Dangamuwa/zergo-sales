# EOD Report System - Quick Start Guide

## 🎯 For Sales Representatives

### Step 1: Set Case Value (One-time)
📍 **Navigation:** Menu → Admin → EOD Settings  
OR **Direct URL:** `/sales/eod/settings/`

1. Enter **Case Value** (e.g., 2160.00)
2. Set **Effective Date** (today or future date)
3. Click **Save**

> **Note:** This is usually done by office staff. Ask your admin if you don't see this option.

---

### Step 2: Access Your EOD Reports
📍 **Navigation:** Menu → EOD Reports  
OR **Direct URL:** `/sales/eod/`

You'll see a list of all dates you've worked:
```
┌─────────────────────────────────────┐
│ 📅 January 30, 2026                │
│ 📍 Route: Wattala & Sedawatta      │
│ 💰 Total Sale: Rs. 45,680.00       │
│ 📄 Bills: 12                        │
└─────────────────────────────────────┘
```

---

### Step 3: View Detailed Report
Click on any date card to view full breakdown.

**First Time?** You'll be asked to enter your **route** for that day.

---

### Step 4: Review Your Report

#### 📊 Product Breakdown
```
250ML SOFT DRINK
┌──────┬─────┐
│ OR   │  24 │  (Orange)
│ NE   │  18 │  (Necto)
│ CS   │  12 │  (Crush)
└──────┴─────┘

500ML SOFT DRINK
┌──────┬─────┐
│ OR   │  36 │
│ NE   │  24 │
│ CO   │  12 │  (Coca Cola)
│ GB   │   6 │  (Ginger Beer)
└──────┴─────┘
```

#### 📈 Summary Metrics
- **TOTAL SALE:** Rs. 45,680.00
- **TOTAL PACK:** 21.15 (Sale ÷ Case Value)
- **P/C (Bill Count):** 12 bills
- **N/O (New Outlets):** 02 new shops registered
- **FOC VALUE:** Rs. 2,340.00

---

### Step 5: Share Your Report

Click **Share** button at top-right:

#### 📱 **Print** (Mobile/Desktop)
- Opens browser print dialog
- Clean layout without buttons
- Perfect for quick physical copies

#### 📄 **Export PDF**
- Professional formatted PDF
- Filename: `EOD_2026-01-30_yourname.pdf`
- Perfect for email, archiving

#### 📝 **Export Text**
- Plain text file (.txt)
- Filename: `EOD_2026-01-30_yourname.txt`
- **Best for WhatsApp/SMS sharing!**

Example Text Format:
```
DATE: 2026/01/30
AREA: colombo
ROUTE: wattala & sedawatta
Sales Rep: Your Name

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

---

### 🔄 Update Route

Need to change your route?

1. Open EOD report for any date
2. Click **Share** → **Change Route**
3. Enter new route
4. Save

---

## 🏢 For Office Staff / Admin

### Managing Case Values
📍 **Menu → Admin → EOD Settings**

**View:**
- Current active case value
- Historical case values with effective dates
- Who set each value and when

**Add New Case Value:**
1. Enter new case value
2. Set effective date (future dates allowed)
3. Add notes (optional)
4. Save

**Auto-deactivation:** Only one case value can be active at a time. Setting a new one automatically deactivates previous.

---

### Viewing All Sales Rep Reports
📍 **Menu → EOD Reports**

- View your own EOD reports (if you create bills)
- Each sales rep sees only their own reports
- Date list shows summary of bills/sales per date

---

## 📱 Mobile Tips

### Best Practices
- **Print from mobile:** Use browser print → Save as PDF
- **Share via WhatsApp:** Export Text → Share file
- **Quick access:** Bookmark `/sales/eod/` on your phone
- **Offline viewing:** PDFs can be viewed without internet

### Recommended Workflow
1. **Morning:** Access yesterday's date, set route if not already set
2. **Review:** Check product breakdown matches your van stock
3. **Export:** Generate text file
4. **Send:** WhatsApp to supervisor/office
5. **Archive:** Keep PDF copy on phone

---

## 🔍 Understanding Company Codes

| Code | Full Name     |
|------|---------------|
| OR   | Orange        |
| NE   | Necto         |
| CS   | Crush         |
| CO   | Coca Cola     |
| GB   | Ginger Beer   |
| MP   | Malt          |

---

## 📏 Product Sizes

Reports group products by these sizes:
- **220ML** - Small bottles
- **250ML** - Quarter liter
- **500ML** - Half liter
- **750ML** - Three-quarter liter
- **1000ML** - 1 liter
- **1500ML** - 1.5 liter
- **2200ML** - Family size

---

## ❓ Troubleshooting

### "Route not set" error
**Solution:** Click the date, enter your route when prompted

### Case value shows 0.00
**Solution:** Contact office staff to set case value in EOD Settings

### Product breakdown is empty
**Possible reasons:**
- No confirmed bills on that date
- Products don't have size/company assigned
- Check if bills are in "draft" status

### PDF download doesn't work
**Solution:** 
- Check internet connection
- Try Export Text instead
- Contact IT if issue persists

### Can't see EOD Reports menu
**Solution:** 
- Refresh page (Ctrl+F5)
- Clear browser cache
- Check with admin if feature is enabled for your account

---

## 🎓 Training Notes

### Key Concepts

**Total Pack = Total Sale ÷ Case Value**
- Example: Rs. 45,680 ÷ Rs. 2,160 = 21.15 packs
- Helps track performance in standardized units
- Makes comparison easier across different price points

**P/C = Purchase Count**
- Number of bills/invoices created
- More bills = more outlet coverage

**N/O = New Outlets**
- New shops registered that day
- Shows business expansion activity

**FOC Value**
- Free of Charge products given
- Tracked for promotional analysis
- Only includes explicit FOC (bottle giveaways)
- Doesn't include price discounts

---

## 🔒 Data Privacy

- Each sales rep sees **only their own** EOD reports
- Office staff can view all reports
- Reports include only confirmed bills (not drafts/cancelled)
- Returns are tracked separately in summary

---

## 💡 Pro Tips

1. **Set Route Early:** Enter route as soon as you start the day's work
2. **Verify Before Sharing:** Always review report before sending to supervisor
3. **Consistent Naming:** Use consistent route names (e.g., always "Wattala & Sedawatta", not "Wattala and Sedawatta")
4. **Daily Habit:** Make EOD review part of your end-of-day routine
5. **Save PDFs:** Keep weekly PDFs for your own records
6. **Compare Trends:** Look at multiple dates to spot patterns
7. **Route Codes:** If using route codes (R1, R2, etc.), stick to them consistently

---

## 📞 Support

**Technical Issues:**
- Contact: IT Support
- Email: support@zergo.com

**Business Questions:**
- Contact: Office Manager
- Ask about case value changes, route assignments

**Feature Requests:**
- Suggest improvements to development team
- Future features: charts, comparisons, weekly summaries

---

## 🚀 Coming Soon

- Mobile thermal printer support (Bluetooth)
- Weekly/Monthly aggregated reports
- Comparison with targets
- Performance charts
- Email automation
- Commission integration

---

**Last Updated:** January 31, 2026  
**System Version:** 1.0.0
