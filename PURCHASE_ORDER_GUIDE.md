# Purchase Order (PO) → GRN Integration Guide

## System Overview

Complete procurement workflow implemented: **Purchase Order → Goods Receipt Note → Payment**

## Key Features

✅ **Purchase Order Management**
- Create POs with multiple products
- Auto-generated PO numbers: `PO-20260113-001`
- Multi-product support with FOC tracking
- Status workflow: `draft` → `ordered` → `received` → `cancelled`

✅ **PO → GRN Linkage**
- Link GRNs to source Purchase Orders
- One PO can have multiple GRNs (partial receives)
- Direct purchases supported (no PO required)
- Auto-fill company from PO selection

✅ **Received Quantity Tracking**
- Track quantities received per PO item
- FOC quantities tracked separately
- View all GRNs created from each PO
- PO completion status visibility

## Workflow Steps

### 1. Create Purchase Order

**URL**: `/products/pos/create/`

**Fields**:
- Company (supplier)
- Order Date
- Expected Delivery Date (optional)
- Notes (optional)

**For Each Product**:
- Product selection
- Packs, Bottles per Pack, Total Bottles (auto-calculated)
- FOC Bottles
- Unit Price
- Discount Percentage
- Line Total (auto-calculated)

**Actions**:
- Add/Remove product items dynamically
- Real-time calculations
- Creates PO with status `draft`

### 2. Mark PO as Ordered

**URL**: `/products/pos/<id>/`

**Process**:
1. Review PO details
2. Click "Mark as Ordered" button
3. Status changes: `draft` → `ordered`
4. PO is now ready for receiving

**Validation**:
- Only `draft` POs can be marked as ordered
- Cannot revert to draft once ordered

### 3. Create GRN from PO (Option A: From PO Detail)

**URL**: `/products/pos/<id>/create-grn/`

**Process**:
1. From PO detail page, click "Create GRN" button
2. Redirects to GRN creation form with PO pre-selected
3. Company auto-filled from PO
4. Fill in GRN details (date, invoice, etc.)
5. Add products received
6. Submit to create GRN linked to PO

**Auto-Fill Behavior**:
- PO dropdown pre-selected
- Company dropdown auto-filled
- User can adjust received quantities

### 4. Create GRN with PO Selection (Option B: From GRN List)

**URL**: `/products/purchases/create/`

**Process**:
1. Go to "Purchases (GRN)" menu
2. Click "Create Purchase" button
3. Select PO from dropdown (shows ordered/draft POs)
4. Company auto-fills when PO selected
5. Complete GRN form
6. Submit to link GRN to selected PO

**PO Dropdown Shows**:
- PO Number (e.g., PO-20260113-001)
- Company Name
- Total Amount
- Option: "No PO (Direct Purchase)"

### 5. View PO with GRNs

**URL**: `/products/pos/<id>/`

**PO Detail Page Shows**:
- PO information (company, dates, status, created by)
- Items ordered (packs, bottles, FOC, unit price, discount)
- Received quantities per item
- All GRNs created from this PO:
  - GRN Number
  - GRN Date
  - Status
  - Total Amount
  - Link to GRN detail

**Status Badges**:
- Draft: Gray
- Ordered: Blue
- Received: Green
- Cancelled: Red

## Database Structure

### purchase_orders Table
```sql
id SERIAL PRIMARY KEY
po_number VARCHAR(50) UNIQUE -- Auto-generated: PO-YYYYMMDD-###
company_id INTEGER FK → companies
order_date DATE NOT NULL
expected_delivery_date DATE NULL
received_date DATE NULL
status VARCHAR(20) DEFAULT 'draft'
subtotal DECIMAL(12,2)
discount DECIMAL(12,2)
total DECIMAL(12,2)
notes TEXT
created_at TIMESTAMP DEFAULT NOW()
created_by_id INTEGER FK → users
```

### purchase_order_items Table
```sql
id SERIAL PRIMARY KEY
purchase_order_id INTEGER FK → purchase_orders ON DELETE CASCADE
product_id INTEGER FK → products
packs INTEGER
bottles_per_pack INTEGER
total_bottles INTEGER -- Calculated: packs × bottles_per_pack
foc_bottles INTEGER DEFAULT 0
unit_price DECIMAL(10,2)
value_before_discount DECIMAL(12,2)
discount_percentage DECIMAL(5,2) DEFAULT 0
discount_amount DECIMAL(12,2)
line_total DECIMAL(12,2)
received_quantity INTEGER DEFAULT 0 -- Tracks total received across GRNs
received_foc INTEGER DEFAULT 0
```

### purchases Table (Enhanced)
```sql
-- Existing fields plus:
purchase_order_id INTEGER FK → purchase_orders ON DELETE SET NULL
-- Null = direct purchase (no PO)
-- Not null = GRN linked to PO
```

## Navigation

**Menu Location**: INVENTORY section

```
INVENTORY
├── Stock Count
├── Purchase Orders ← NEW
├── Purchases (GRN)
└── Purchase Returns
```

**Access**: Admin and Office users only (not sales reps)

## URL Routes

| Route | View | Purpose |
|-------|------|---------|
| `/products/pos/` | po_list | List all POs |
| `/products/pos/create/` | create_po | Create new PO |
| `/products/pos/<id>/` | po_detail | View PO details |
| `/products/pos/<id>/mark-ordered/` | mark_po_ordered | Change status to ordered |
| `/products/pos/<id>/cancel/` | cancel_po | Cancel PO |
| `/products/pos/<id>/create-grn/` | create_grn_from_po | Create GRN from PO |
| `/products/purchases/create/?po_id=<id>` | create_purchase | Create GRN with PO pre-selected |

## Multi-GRN Support

**Scenario**: Large PO delivered in multiple shipments

**Example**:
1. Create PO for 1000 bottles
2. First delivery: Create GRN-001 for 600 bottles (linked to PO)
3. Second delivery: Create GRN-002 for 400 bottles (same PO)
4. PO detail shows both GRNs
5. PO items track total received: 1000 bottles

**Implementation**:
- PO.grns relationship: One-to-Many
- Each GRN has optional purchase_order FK
- PO detail lists all linked GRNs
- Received quantities aggregate across GRNs

## JavaScript Auto-Fill

**Function**: `loadPODetails()`

**Location**: `templates/products/create_purchase.html`

**Behavior**:
```javascript
// When PO dropdown changes:
1. Get selected PO's data-company attribute
2. Set company dropdown value to PO's company
3. If "No PO" selected, reset company dropdown
```

**Triggered By**: PO dropdown `onchange` event

## Status Workflow

```
draft ──────→ ordered ──────→ received
  │                │              
  │                │              
  └────────────────┴──→ cancelled
```

**State Transitions**:
- `draft` → `ordered`: Mark as Ordered button
- `ordered` → `received`: Automatic when GRN created
- Any → `cancelled`: Cancel button (except received)

**Business Rules**:
- Cannot cancel received POs
- Cannot revert to draft once ordered
- Cancelled POs cannot create GRNs

## Testing Checklist

- [ ] Create PO with 3 products
- [ ] Mark PO as Ordered
- [ ] Create GRN from PO detail page (auto-fill test)
- [ ] Verify company auto-filled
- [ ] Complete GRN creation
- [ ] Check PO detail shows GRN in list
- [ ] Create second GRN from same PO (multi-GRN test)
- [ ] Verify PO detail shows both GRNs
- [ ] Test direct purchase (no PO)
- [ ] Verify PO list filters (status, company)

## File Locations

**Models**: `products/models.py`
- PurchaseOrder (lines 13-126)
- PurchaseOrderItem (lines 128-192)
- Purchase.purchase_order FK (lines 558-565)

**Views**: `products/po_views.py` (232 lines)
- po_list, create_po, po_detail, mark_po_ordered, cancel_po, create_grn_from_po

**Enhanced Views**: `products/purchase_views.py`
- create_purchase (lines 58-155) - Enhanced with PO support

**Templates**:
- `templates/products/po_list.html` (195 lines)
- `templates/products/create_po.html` (207 lines)
- `templates/products/po_detail.html` (183 lines)
- `templates/products/create_purchase.html` (264 lines) - Enhanced

**URLs**: `products/urls.py` (lines 34-40)

**Navigation**: `templates/base.html` (lines 357-380)

## Next Steps (Optional Enhancements)

1. **Auto-Fill Products from PO**
   - When PO selected, pre-fill product items in GRN form
   - Show expected vs. actual quantities
   
2. **PO Completion Tracking**
   - Calculate percentage received
   - Show progress bar on PO detail
   - Auto-mark as "received" when 100%

3. **PO Analytics**
   - Dashboard widget for pending POs
   - Overdue deliveries report
   - Supplier performance metrics

4. **Email Notifications**
   - Send PO to supplier email
   - Notify when GRN created
   - Alert on overdue deliveries

5. **PDF Export**
   - Generate PO PDF for printing
   - Include company logo and terms
   - Email directly to supplier

## Support

**Documentation**:
- PROJECT_SUMMARY.md - Complete feature list
- QUICKSTART.md - Installation steps
- This guide - PO → GRN workflow

**Access**: http://127.0.0.1:8000/products/pos/

**Server**: Run with `python manage.py runserver`
