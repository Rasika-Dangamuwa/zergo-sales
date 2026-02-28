# Three-Level Shop Access Control System

## Implementation Summary

### Database Schema
**New Model: `ShopAccess`**
- `shop` (ForeignKey to Shop)
- `sales_rep` (ForeignKey to User, limited to sales_rep)
- `access_level` (Integer: 1, 2, or 3)
- `granted_at` (DateTime - auto)
- `granted_by` (ForeignKey to User - who granted access)
- `notes` (TextField - optional notes)
- `is_active` (Boolean - to revoke without deleting)
- Unique constraint on (`shop`, `sales_rep`)

### Access Levels

#### Level 1 - View Only
**Permissions:**
- ✅ See shop in list
- ✅ See shop on map
- ✅ Call shop phone number
- ❌ Cannot view shop details page
- ❌ Cannot create bills
- ❌ Cannot see any activities

**Use Case:** Area awareness for reps who might need to know about shops but don't service them directly.

#### Level 2 - Standard Access
**Permissions:**
- ✅ See shop in list and map
- ✅ View shop details page
- ✅ Create bills, returns, payments
- ✅ Record visits
- ✅ See own engagement only (own bills, payments, returns, exchanges)
- ❌ Cannot see other reps' activities with this shop

**Use Case:** Coverage reps or backup reps who handle the shop occasionally.

#### Level 3 - Full Access
**Permissions:**
- ✅ Unlimited access to everything
- ✅ See all engagement (all reps' bills, payments, returns, visits)
- ✅ Full shop history visibility

**Auto-Grant:** Automatically given to the sales rep who creates the shop
**Multiple Owners:** A shop can have multiple Level 3 users

**Use Case:** Primary shop owner or team leads who need full visibility.

### How It Works

#### Auto-Grant on Shop Creation
When a sales rep creates a new shop, they automatically receive Level 3 access:
```python
# In Shop.save()
if is_new and self.created_by:
    ShopAccess.grant_creator_access(self, self.created_by)
```

#### Access Check in Views
```python
# Check if rep can view details (Level 2+)
access_level = ShopAccess.get_rep_access_level(shop, request.user)
if access_level == 1:
    # Redirect - cannot view details
    
# Filter data based on access
if access_level == 2:
    # Show only this rep's engagement
    bills = bills.filter(created_by=request.user)
elif access_level == 3:
    # Show all engagement
```

#### Template Display
```html
{% if shop.user_access_level == 1 %}
    <!-- Show "View Only" badge, disable detail links -->
{% elif shop.user_access_level == 2 %}
    <!-- Show "Standard" badge, allow activities but filtered data -->
{% elif shop.user_access_level == 3 %}
    <!-- Show "Full Access" badge, show everything -->
{% endif %}
```

### Management Interface

**URL:** `/shops/<shop_id>/access/`

**Features:**
- View all current access grants for a shop
- Grant new access to sales reps (select rep + level)
- Update existing access levels
- Revoke access
- Add notes for each access grant
- Admin/Office staff only

**Template:** `templates/shops/manage_access.html`

### Migration Applied
```bash
python manage.py makemigrations shops
python manage.py migrate shops
```

**Migration:** `shops/migrations/0003_shopaccess.py`

### Files Modified

1. **shops/models.py**
   - Added `ShopAccess` model with access level logic
   - Updated `Shop.save()` to auto-grant Level 3 to creator
   - Helper methods: `get_rep_access_level()`, `has_access()`, `grant_creator_access()`

2. **shops/views.py**
   - Updated `shop_list()` to add access_level to each shop
   - Updated `shop_detail()` to check access level and filter data
   - Added `manage_shop_access()` view for access management

3. **shops/urls.py**
   - Added `path('<int:pk>/access/', views.manage_shop_access, name='manage_access')`

4. **templates/shops/shop_list.html**
   - Added access level badges
   - Disabled detail links for Level 1
   - Disabled "Create Bill" for Level 1

5. **templates/shops/manage_access.html** (NEW)
   - Access management interface
   - Grant/revoke access
   - Visual explanation of levels

### Usage Examples

#### Grant Access via Management Interface
1. Navigate to shop details
2. Click "Manage Access" (admin only)
3. Select sales rep, choose level, add optional notes
4. Click "Grant Access"

#### Check Access in Code
```python
from shops.models import ShopAccess

# Get access level
level = ShopAccess.get_rep_access_level(shop, sales_rep)

# Check minimum access
has_access = ShopAccess.has_access(shop, sales_rep, required_level=2)
```

### Benefits

1. **Flexible Team Management**: Multiple reps can work with same shop at different levels
2. **Security**: Level 1 prevents accidental changes while maintaining visibility
3. **Privacy**: Level 2 prevents confusion by showing only rep's own work
4. **Transparency**: Level 3 for primary owners to see complete history
5. **Audit Trail**: Tracks who granted access and when
6. **Scalable**: Can add more levels in future if needed

### Future Enhancements (Not Implemented)

- Bulk access management (assign access to multiple shops at once)
- Access expiration dates (temporary access)
- Access request workflow (reps request, admin approves)
- Access history/audit log
- Territory-based auto-assignment of access levels
