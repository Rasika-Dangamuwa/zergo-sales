# Purchase/GRN System User Guide

## 📋 Overview
The Purchase/GRN (Goods Received Note) system manages all procurement operations from suppliers/companies. It tracks incoming stock, handles FOC (Free of Charge) items, manages purchase returns, and integrates with the main inventory system.

## ✅ System Status
**Status**: ✅ Fully Operational  
**Server**: http://127.0.0.1:8000/  
**Access**: Admin and Office users only  
**Database**: Ready (1 company, 27 products, 0 purchases)

## 🎯 Key Features

### 1. Goods Received Notes (GRN)
- **Auto-numbering**: GRN-20260113-001 (daily sequence)
- **Multi-product support**: Add multiple products per GRN
- **Pack/bottle tracking**: Automatic quantity calculation
- **FOC tracking**: Separate field for free items, both added to main stock
- **Batch/expiry tracking**: Track product batches and expiry dates
- **Payment status**: Track unpaid/partially_paid/paid
- **Two-step stock update**: Create GRN → Receive & Update Stock

### 2. Purchase Returns (PR)
- **Auto-numbering**: PR-20260113-001 (daily sequence)
- **Return reasons**: damaged/expired/quality/wrong_product/excess_qty/other
- **Settlement types**: credit_note/replacement/refund
- **Approval workflow**: Pending → Approved → Sent → Credited
- **Stock integration**: Auto-reduces stock upon approval

### 3. Stock Movement Integration
- **Purchase Type**: Adds stock when GRN is received
- **Purchase Return Type**: Reduces stock when return is approved
- **Full audit trail**: All stock changes tracked in StockMovement table

## 📱 Navigation

### Access Points
1. **Sidebar Menu** → INVENTORY section:
   - **Purchases (GRN)** - View all goods received notes
   - **Purchase Returns** - View all returns to suppliers

2. **Admin Panel** → /admin/products/:
   - Purchase, PurchaseItem, PurchaseReturn, PurchaseReturnItem

## 🔧 How to Use

### Creating a GRN (Goods Received Note)

**Step 1: Navigate to Purchases**
- Click **Purchases (GRN)** in sidebar
- Click the **+** FAB button (bottom right)

**Step 2: Enter Basic Information**
- **Company**: Select the supplier (required)
- **Invoice Date**: Date on supplier's invoice (optional)
- **Supplier Invoice Number**: Supplier's invoice reference (optional)
- **Notes**: Any additional information (optional)

**Step 3: Add Products**
- Click **Add Product** button
- For each product:
  - **Product**: Select from dropdown
  - **Packs**: Number of packs/cases received
  - **Bottles per Pack**: Auto-fills from product settings (editable)
  - **Quantity**: Auto-calculated (packs × bottles_per_pack)
  - **FOC Quantity**: Free bottles received
  - **Unit Price**: Price per bottle
  - **Discount %**: Discount percentage (optional)
  - **Batch Number**: Product batch identifier (optional)
  - **Expiry Date**: Product expiry date (optional)

**Step 4: Review Summary**
- **Total Items**: Number of product lines
- **Total Bottles**: Sum of all quantities
- **Total FOC**: Sum of all FOC quantities
- **Grand Total**: Total purchase amount

**Step 5: Save**
- Click **Create Purchase** button
- GRN number is auto-generated (e.g., GRN-20260113-001)
- Status set to **draft**
- Stock **NOT updated yet**

### Receiving Goods (Updating Stock)

**After creating GRN:**
1. Go to purchase detail page
2. Verify all information is correct
3. Click **Receive & Update Stock** button

**What happens:**
- Stock updated: `quantity_in_stock += (quantity + foc_quantity)`
- Status changed to **received**
- Stock movement record created (type='purchase')
- Received by user recorded
- **Receive & Update Stock** button disappears

### Creating a Purchase Return

**Step 1: Navigate to Purchase Returns**
- Click **Purchase Returns** in sidebar
- Click the **+** FAB button

**Step 2: Enter Return Information**
- **Company**: Select supplier
- **Return Reason**: damaged/expired/quality/wrong_product/excess_qty/other
- **Settlement Type**: credit_note/replacement/refund
- **Detailed Reason**: Explain the return (optional)

**Step 3: Add Products to Return**
- Click **Add Product** button
- For each product:
  - **Product**: Select product (shows current stock)
  - **Quantity**: Number of bottles returning
  - **Unit Price**: Price per bottle
  - **Batch Number**: Product batch (optional)
  - **Expiry Date**: Product expiry (optional)
  - **Item Reason**: Specific reason for this item (optional)

**Step 4: Review Summary**
- **Total Items**: Number of product lines
- **Total Quantity**: Sum of all quantities
- **Total Amount**: Total return value

**Step 5: Save**
- Click **Create Purchase Return** button
- PR number is auto-generated (e.g., PR-20260113-001)
- Status set to **pending**
- Stock **NOT updated yet**

### Approving Purchase Returns

**After creating return:**
1. Go to purchase return detail page
2. Verify all information is correct
3. Click **Approve & Update Stock** button

**What happens:**
- Stock reduced: `quantity_in_stock -= quantity`
- Status changed to **approved**
- Stock movement record created (type='purchase_return')
- Approved by user and timestamp recorded
- **Approve & Update Stock** button disappears

## 📊 Understanding the Dashboard

### Purchase List View
**Stats Card** (Purple gradient):
- **Total GRNs**: Number of all purchases
- **Total Value**: Sum of all purchase amounts
- **Unpaid**: Number of unpaid GRNs
- **Pending Stock Update**: Number of GRNs not yet received

**Filters**:
- **Status**: draft/received/cancelled
- **Company**: Filter by supplier
- **Payment Status**: unpaid/partially_paid/paid

**Card Information**:
- GRN number (clickable)
- Company name
- GRN date
- Invoice number
- Total amount
- Status badge
- Payment status badge
- Created by user
- Stock updated status

**Actions**:
- **View Details**: See full GRN information
- **Receive & Update Stock**: Update inventory (if not yet received)

### Purchase Return List View
**Stats Card** (Pink/Red gradient):
- **Total Returns**: Number of all returns
- **Pending**: Number of pending approvals
- **Total Value**: Sum of all return amounts

**Filters**:
- **Status**: pending/approved/sent/credited/rejected
- **Company**: Filter by supplier

**Status Badge Colors**:
- **Pending**: Yellow (awaiting approval)
- **Approved**: Blue (approved by admin/office)
- **Sent**: Purple (sent to supplier)
- **Credited**: Green (credit received from supplier)
- **Rejected**: Red (return rejected)

## 💡 Business Rules

### FOC (Free of Charge) Logic
- FOC bottles are tracked separately: `foc_quantity` field
- Both regular quantity and FOC are added to main stock
- Example: 
  - Packs: 10
  - Bottles per pack: 24
  - Quantity: 240
  - FOC: 20
  - **Total added to stock**: 260 bottles

### Stock Movement Types
1. **purchase**: Stock added when GRN is received
2. **purchase_return**: Stock reduced when return is approved

### Payment Tracking
- **Unpaid**: No payment recorded
- **Partially Paid**: Some payment received
- **Paid**: Fully paid
- Note: Payment recording UI is pending (use admin panel for now)

### Multi-GRN Support
- Architecture supports multiple GRNs from single PO
- PurchaseOrder FK is ready (currently commented out)
- Can be activated when PO system is implemented

## 🔒 Access Control
- **Sales Reps**: ❌ No access (redirected to dashboard)
- **Office Staff**: ✅ Full access (create, view, approve)
- **Admins**: ✅ Full access (all operations)

## 🎨 UI/UX Features
- **Card-based layout**: Clean, modern design
- **Hover effects**: Visual feedback on hover
- **FAB button**: Quick create access (floating + button)
- **Gradient stats**: Purple for purchases, pink/red for returns
- **Real-time calculations**: JavaScript-powered totals
- **Mobile responsive**: Works on all screen sizes
- **Status badges**: Color-coded for quick recognition

## 🔍 Finding Information

### View All Purchases
1. Sidebar → **Purchases (GRN)**
2. Use filters to narrow down results
3. Click any GRN to view details

### View Purchase Details
1. Click GRN number or **View Details**
2. See all items, batch numbers, expiry dates
3. View summary: items, bottles, FOC, total

### View All Returns
1. Sidebar → **Purchase Returns**
2. Use filters to narrow down results
3. Click any PR to view details

### View Return Details
1. Click PR number or **View Details**
2. See all items being returned
3. View return reason and settlement type

## ⚠️ Important Notes

### Before Using the System
✅ Ensure companies are added (via Admin Panel)  
✅ Ensure products are configured (via Admin Panel)  
✅ Login with admin or office user account

### Two-Step Process
1. **GRN Creation**: Creates record, does NOT update stock
2. **Receive Goods**: Updates stock, creates stock movement

This prevents accidental stock updates and allows verification before committing.

### Stock Safety
- GRNs in **draft** status do NOT affect stock
- Only **received** GRNs update stock
- Purchase returns in **pending** status do NOT affect stock
- Only **approved** returns reduce stock

### Number Format
All purchase-related numbers follow the standard:
- **GRN**: GRN-YYYYMMDD-###
- **PR**: PR-YYYYMMDD-###

Example: GRN-20260113-001 (first GRN on January 13, 2026)

## 🚀 Next Steps (Optional Enhancements)

### Pending Features
1. **Payment Recording UI**: Currently use admin panel
2. **PurchaseOrder Integration**: Activate PO FK when PO system exists
3. **GRN Printing**: Print-friendly GRN format
4. **Return Receipt Printing**: Print return documentation
5. **Supplier Account Statements**: Track payables
6. **Batch Tracking Reports**: Track products by batch
7. **Expiry Alert System**: Warn before products expire

## 📞 Support
- **Admin Panel**: /admin/ (for direct database access)
- **Documentation**: See PROJECT_SUMMARY.md for full system details
- **Print System**: See PRINT_MANAGEMENT_REBUILD.md for printing features

## 🎉 You're Ready!
The Purchase/GRN system is fully operational. Start by:
1. ✅ Logging in at http://127.0.0.1:8000/
2. ✅ Click **Purchases (GRN)** in sidebar
3. ✅ Create your first GRN
4. ✅ Receive goods to update stock
5. ✅ Track all procurement operations

---
**Last Updated**: January 13, 2026  
**System Version**: Django 6.0  
**Status**: Production Ready
