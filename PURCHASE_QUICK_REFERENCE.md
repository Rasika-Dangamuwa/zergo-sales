# Purchase System Quick Reference

## 🚀 Quick Start

### Create a GRN (3 steps)
```
1. Sidebar → Purchases (GRN) → Click + button
2. Select Company → Add Products → Fill quantities & FOC
3. Click "Create Purchase"
```

### Receive Goods (Update Stock)
```
1. Open GRN detail page
2. Verify information
3. Click "Receive & Update Stock"
```

### Create Purchase Return (3 steps)
```
1. Sidebar → Purchase Returns → Click + button
2. Select Company → Add Products → Fill quantities
3. Click "Create Purchase Return"
```

### Approve Return (Reduce Stock)
```
1. Open PR detail page
2. Verify information
3. Click "Approve & Update Stock"
```

## 📋 Number Formats
- **GRN**: `GRN-20260113-001`
- **PR**: `PR-20260113-001`

## 🎯 Status Flow

### Purchase Status
```
draft → received → cancelled
```

### Return Status
```
pending → approved → sent → credited
         ↘ rejected
```

## 💰 Payment Status
```
unpaid → partially_paid → paid
```

## 🔒 Access Control
- ❌ **Sales Reps**: No access
- ✅ **Office**: Full access
- ✅ **Admin**: Full access

## 🎨 Color Codes

### Purchase Stats Card
Purple gradient (#667eea → #764ba2)

### Return Stats Card
Pink/Red gradient (#f093fb → #f5576c)

### Status Badges
- **draft**: Gray
- **received**: Green
- **cancelled**: Red
- **pending**: Yellow
- **approved**: Blue
- **sent**: Purple
- **credited**: Green
- **rejected**: Red

## 📊 Stock Impact

### When Creating
- ❌ GRN created (draft) → NO stock change
- ❌ PR created (pending) → NO stock change

### When Receiving/Approving
- ✅ GRN received → Stock += (quantity + foc_quantity)
- ✅ PR approved → Stock -= quantity

## 🧮 Calculations

### GRN
```javascript
quantity = packs × bottles_per_pack
discount_amount = (quantity × unit_price × discount_%) / 100
line_total = (quantity × unit_price) - discount_amount
total_bottles = sum(all quantities)
total_foc = sum(all foc_quantities)
grand_total = sum(all line_totals)
```

### Purchase Return
```javascript
line_total = quantity × unit_price
total_quantity = sum(all quantities)
total_amount = sum(all line_totals)
```

## 🔍 Quick Filters

### Purchase List
- Status: draft/received/cancelled
- Company: All companies
- Payment Status: unpaid/partially_paid/paid

### Return List
- Status: pending/approved/sent/credited/rejected
- Company: All companies

## 📱 Navigation

### Main Menu
```
INVENTORY
├── Stock Count
├── Purchases (GRN) ← NEW
└── Purchase Returns ← NEW
```

### URLs
```
/products/purchases/                    → List GRNs
/products/purchases/create/             → Create GRN
/products/purchases/<id>/               → GRN detail
/products/purchases/<id>/update-stock/  → Receive goods

/products/purchase-returns/             → List returns
/products/purchase-returns/create/      → Create return
/products/purchase-returns/<id>/        → Return detail
/products/purchase-returns/<id>/approve/ → Approve return
```

## ⚠️ Important Rules

1. **Two-Step Process**: Create → Receive/Approve
2. **FOC Added to Main Stock**: Both quantity and FOC increase resaleable stock
3. **Cannot Edit After Stock Update**: Once received/approved, stock is committed
4. **Admin/Office Only**: Sales reps cannot access purchase system
5. **Company Required**: All purchases/returns must have a company
6. **Product Must Exist**: Only existing products can be added

## 💡 Tips

- ✅ Verify GRN before clicking "Receive & Update Stock"
- ✅ Use batch numbers for better tracking
- ✅ Add expiry dates to prevent expired stock sales
- ✅ Use detailed_reason field for return context
- ✅ Check stock levels before creating returns
- ✅ Use filters to find specific GRNs/returns quickly

## 🎯 Common Scenarios

### Scenario 1: Receiving New Stock
```
1. Create GRN with product quantities
2. Add FOC if any (company gives free items)
3. Add batch numbers and expiry dates
4. Save GRN
5. Receive & Update Stock
→ Stock increases immediately
```

### Scenario 2: Damaged Products Received
```
1. Create GRN normally
2. Receive & Update Stock (adds to inventory)
3. Create Purchase Return for damaged items
4. Approve return
→ Stock reduced, return tracked
```

### Scenario 3: Wrong Product Delivered
```
1. Create GRN (do NOT receive yet)
2. Cancel GRN (set status to cancelled)
3. Create Purchase Return (reason: wrong_product)
4. Contact supplier for replacement
→ No stock impact, issue documented
```

## 📈 Stats Dashboard

### Purchase Stats
- Total GRNs
- Total Value (Rs.)
- Unpaid count
- Pending Stock Update count

### Return Stats
- Total Returns
- Pending count
- Total Value (Rs.)

## 🎨 UI Elements

### FAB Button
Floating + button (bottom right) → Quick create

### Cards
Hover effect with left border highlight

### Summary Box
Real-time calculations as you type

### Action Buttons
- Blue: View/Details
- Green: Receive/Approve
- Gray: Disabled (already processed)

---
**Print this page for quick reference!**
