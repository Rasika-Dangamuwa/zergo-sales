# Product Exchange System Implementation

## Overview
**Date**: January 7, 2026  
**Purpose**: Allow shops to swap products within same category-size-price group without affecting sales figures

## Business Requirements

### What is a Product Exchange?
Shops can exchange damaged, expired, or slow-moving items for different products in the **same category, size, and price group**.

**Key Differences from Returns**:
- ❌ No financial calculations (returns reduce sales value)
- ❌ No payment settlements (purely inventory swap)
- ✅ Stock movements only (OUT items +stock, IN items -stock)
- ✅ Must be within same exchange group (category-size-price)

### Exchange Group Validation
All items in an exchange must match:
1. **Category** - Same product category (e.g., "Energy Drink")
2. **Size** - Same bottle/package size in ml (e.g., 250ml)
3. **Marked Price** - Same retail price (e.g., Rs.100)

**Example Valid Exchange**:
- OUT: Max Orange 250ml Rs.100 (5 units)
- IN: Max Nexta 250ml Rs.100 (5 units)
- ✅ Same group → Approved

**Example Invalid Exchange**:
- OUT: Max Orange 250ml Rs.100
- IN: Max Orange 500ml Rs.150  
- ❌ Different size & price → Rejected

## Database Schema

### Exchange Model
```python
Table: exchanges
Fields:
  - id (PK)
  - exchange_number VARCHAR(50) UNIQUE  # "EXC-20260107-001"
  - exchange_date TIMESTAMP
  - exchange_status VARCHAR(20)  # pending/approved/rejected
  - exchange_reason VARCHAR(20)  # damaged/expired/slow_moving/customer_request/other
  - shop_id FK → shops.shop
  - created_by_id FK → accounts.user
  - approved_by_id FK → accounts.user
  - notes TEXT
  - created_at TIMESTAMP
  - updated_at TIMESTAMP
  - approved_at TIMESTAMP
```

### ExchangeItem Model
```python
Table: exchange_items
Fields:
  - id (PK)
  - exchange_ref_id FK → exchanges.exchange
  - item_type VARCHAR(3)  # 'out' or 'in'
  - product_id FK → products.product
  - quantity DECIMAL(10,2)
  - foc_quantity DECIMAL(10,2)
  - unit_price DECIMAL(10,2)
  - notes TEXT
```

### StockMovement Integration
Added new movement type to `products.StockMovement`:
```python
MOVEMENT_TYPE_CHOICES = (
    # ... existing types
    ('exchange', 'Product Exchange'),  # NEW
)
```

## URL Routes
```python
# sales/urls.py
path('exchanges/', exchange_views.exchange_list, name='exchange_list')
path('exchanges/create/', exchange_views.create_exchange, name='create_exchange')
path('exchanges/create/step2/', exchange_views.create_exchange_step2, name='create_exchange_step2')
path('exchanges/<int:pk>/', exchange_views.exchange_detail, name='exchange_detail')
path('exchanges/<int:pk>/approve/', exchange_views.approve_exchange, name='approve_exchange')
path('exchanges/<int:pk>/reject/', exchange_views.reject_exchange, name='reject_exchange')
```

## Views (`sales/exchange_views.py`)

### 1. `exchange_list`
Lists all exchanges with filters (status, shop, search).

### 2. `create_exchange` (2-step process)
**Step 1**: Select OUT items (returning to stock)
- Choose shop, reason, notes
- Add products to return with quantities
- Save to session

**Step 2**: Select IN items (taking from stock)
- Display OUT items for review
- Show only products in same exchange group
- Create Exchange + ExchangeItem records
- Validate exchange group

### 3. `exchange_detail`
Display exchange information:
- Basic info (number, date, shop, status, reason)
- OUT items table (green background)
- IN items table (blue background)
- Exchange group display

### 4. `approve_exchange`
**Permissions**: Admin & Office only

**Stock Updates**:
1. Validate exchange group one more time
2. For OUT items (returning to stock):
   - Create StockMovement with `movement_type='exchange'`
   - `quantity_change = +(quantity + foc_quantity)`
   - Update `Product.quantity_in_stock` (ADD)
3. For IN items (taking from stock):
   - Create StockMovement with `movement_type='exchange'`
   - `quantity_change = -(quantity + foc_quantity)`
   - Update `Product.quantity_in_stock` (SUBTRACT)
4. Set status to 'approved', save approved_by and approved_at

### 5. `reject_exchange`
**Permissions**: Admin & Office only
- Set status to 'rejected'
- No stock movements created

## Templates

### `templates/sales/exchange_list.html`
- Filter by status (pending/approved/rejected)
- Filter by shop
- Search by exchange number or shop name
- Table with columns: Exchange No., Date, Shop, Reason, Status, Created By, Approved By, Actions

### `templates/sales/create_exchange.html`
**Step 1 Form**:
- Shop selector
- Reason dropdown (damaged/expired/slow_moving/customer_request/other)
- Notes textarea
- Dynamic OUT items table (add/remove rows)
- JavaScript for row management

**Step 2 Form**:
- Display selected shop and exchange group info
- Summary of OUT items (read-only)
- Dynamic IN items table (filtered by exchange group)
- JavaScript for row management

### `templates/sales/exchange_detail.html`
- Exchange information card (number, date, shop, status, reason)
- Tracking information card (created by, approved by, timestamps)
- Exchange group alert (category-size-price)
- OUT items table (green header "Items Being Returned")
- IN items table (blue header "Items Being Taken")
- Approve/Reject buttons (conditional - pending only, admin/office only)

## Admin Panel
```python
# sales/admin.py

@admin.register(Exchange)
class ExchangeAdmin:
  - list_display: exchange_number, shop, date, status, reason, created_by
  - list_filter: status, reason, date
  - search_fields: exchange_number, shop__shop_name
  - inlines: ExchangeItemInline

class ExchangeItemInline:
  - TabularInline for ExchangeItem
  - Shows: item_type, product, quantity, foc_quantity, unit_price, notes
```

## Validation Logic

### `Exchange.validate_exchange_group()`
Located in `sales/models.py`:
```python
def validate_exchange_group(self):
    """Ensures all items match category-size-price"""
    items = self.items.all()
    if not items.exists():
        raise ValueError("Exchange must have items")
    
    # Get first item's exchange group
    first_product = items[0].product
    target_category = first_product.category
    target_size = first_product.size
    target_price = first_product.marked_price
    
    # Check all items match
    for item in items:
        if item.product.category != target_category:
            raise ValueError(f"Category mismatch: {item.product.product_name}")
        if item.product.size != target_size:
            raise ValueError(f"Size mismatch: {item.product.product_name}")
        if item.product.marked_price != target_price:
            raise ValueError(f"Price mismatch: {item.product.product_name}")
```

### `Exchange.get_exchange_group_display()`
Returns formatted string: "Energy Drink - 250ml - Rs.100"

## Stock Movement Flow

### Example Exchange:
```
Exchange EXC-20260107-001
OUT: Max Orange 250ml (10 units)
IN: Max Nexta 250ml (10 units)

Stock Movements Created:
1. Product: Max Orange 250ml
   Type: exchange
   Quantity Change: +10
   Reference: EXC-20260107-001
   Notes: "Exchange OUT: damaged"
   
2. Product: Max Nexta 250ml
   Type: exchange
   Quantity Change: -10
   Reference: EXC-20260107-001
   Notes: "Exchange IN: damaged"
```

## Session Data Storage
During 2-step creation, data stored in Django session:
```python
request.session['exchange_data'] = {
    'shop_id': '123',
    'reason': 'damaged',
    'notes': 'Bottles broken during transport',
    'out_items': [
        {'product_id': '45', 'quantity': '10', 'foc_quantity': '0'},
        # ... more items
    ]
}

request.session['exchange_group'] = {
    'category': 'Energy Drink',
    'size': '250',
    'price': '100.00'
}
```

## Migrations

### `products/migrations/0013_alter_stockmovement_movement_type.py`
Added 'exchange' choice to StockMovement.movement_type

### `sales/migrations/0019_exchange_exchangeitem.py`
Created:
- `exchanges` table
- `exchange_items` table

**Note**: Originally included `sale` FK in Exchange, but was removed due to PostgreSQL table name conflict with `sales` app.

## Testing Checklist

- [ ] Create exchange with OUT items
- [ ] Verify step 1 → step 2 transition with session data
- [ ] Verify IN items filtered by exchange group
- [ ] Try mixed categories - should fail validation
- [ ] Try mixed sizes - should fail validation
- [ ] Try mixed prices - should fail validation
- [ ] Approve exchange as admin - check stock movements created
- [ ] Verify `Product.quantity_in_stock` updated correctly (OUT +stock, IN -stock)
- [ ] Reject exchange - verify no stock movements
- [ ] Test permissions (sales_rep cannot approve)
- [ ] Check admin panel - Exchange and ExchangeItem visible

## Known Limitations

1. **No Sale Reference**: Exchange model does NOT have FK to Sale (removed due to table name conflict)
2. **No Print System**: Unlike Bills and Returns, Exchanges don't have mobile print functionality yet
3. **No Rollback**: Once approved, exchanges cannot be reversed (stock already updated)
4. **Manual Validation**: Exchange group validation happens on form submit, not real-time

## Future Enhancements

1. **Print Templates**: Add mobile print for exchange receipts
2. **Real-time Validation**: JavaScript validation in create form for exchange group matching
3. **Stock Warnings**: Alert if IN items have insufficient stock
4. **Exchange History**: Link exchanges to original sales (requires resolving table name issue)
5. **Audit Trail**: Detailed logging of who approved/rejected with timestamps

## Files Modified/Created

### Models
- `sales/models.py` - Added Exchange, ExchangeItem (lines 750-927)
- `products/models.py` - Updated StockMovement.MOVEMENT_TYPE_CHOICES (line 289)

### Views
- `sales/exchange_views.py` - NEW (308 lines)

### URLs
- `sales/urls.py` - Added 6 exchange routes

### Admin
- `sales/admin.py` - Added ExchangeAdmin, ExchangeItemInline

### Templates
- `templates/sales/exchange_list.html` - NEW
- `templates/sales/create_exchange.html` - NEW (2-step form)
- `templates/sales/exchange_detail.html` - NEW

### Migrations
- `products/migrations/0013_alter_stockmovement_movement_type.py`
- `sales/migrations/0019_exchange_exchangeitem.py`

### Documentation
- `.github/copilot-instructions.md` - Added exchange system section
- `EXCHANGE_SYSTEM.md` - THIS FILE

## Development Notes

### Debugging Tips
```python
# Check exchange group validation
exchange = Exchange.objects.get(pk=1)
exchange.validate_exchange_group()  # Raises ValueError if invalid

# Get OUT/IN items
out_items = exchange.get_outgoing_items()
in_items = exchange.get_incoming_items()

# Check stock movements
from products.models import StockMovement
movements = StockMovement.objects.filter(
    movement_type='exchange',
    reference_number='EXC-20260107-001'
)
```

### Common Errors
1. **"Exchange must have items"** - No ExchangeItem records created
2. **"Category mismatch"** - Items don't match category
3. **"Size mismatch"** - Items have different sizes
4. **"Price mismatch"** - Items have different marked prices
5. **"Session expired"** - Step 2 accessed without step 1 data

## References
- Print System: [PRINT_MANAGEMENT_REBUILD.md](PRINT_MANAGEMENT_REBUILD.md)
- Return System: [RETURN_SYSTEM_TERMINOLOGY_STANDARDIZATION.md](RETURN_SYSTEM_TERMINOLOGY_STANDARDIZATION.md)
- Stock Management: [FLAVOR_TRACKING_GUIDE.md](FLAVOR_TRACKING_GUIDE.md)
- Project Overview: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
