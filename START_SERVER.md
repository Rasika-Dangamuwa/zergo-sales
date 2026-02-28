# QUICK START GUIDE - Updated 2026-01-12

## Server is Not Running - Fix This First!

### STEP 1: Create Database Migrations (REQUIRED!)
The new ItemExchange models need to be added to the database:

```bash
cd "c:\Users\LENOVO\Desktop\My Projects\zergo_distributors_sales_app"
python manage.py makemigrations sales
python manage.py migrate
```

### STEP 2: Start the Server

**Option A - Use existing HTTPS script:**
```powershell
.\run_https_stable.ps1
```

**Option B - Simple HTTP server:**
```bash
python manage.py runserver 192.168.1.4:8000
```

**Option C - Local only:**
```bash
python manage.py runserver
```

Then access: `http://192.168.1.4:8000/` or `https://192.168.1.4:8000/`

---

## What Was Just Implemented

### 1. ✅ Item Exchange System
- **Purpose**: Direct exchange of damaged/expired products without return approval
- **URL**: `/sales/exchanges/`
- **Features**:
  - Create exchanges instantly
  - Track resellable vs non-resellable items
  - Automatic stock movements
  - Mobile-friendly interface

### 2. ✅ Color Scheme Update (#1f43b4)
Updated pages with consistent blue color:
- Bills list page
- Returns list page
- Exchange list page

### 3. ✅ Amount Formatting
All monetary values display with commas (already implemented via `intcomma` filter)

---

## New Features Available After Migration

### Item Exchange Flow:
1. Field rep visits shop
2. Shop has damaged/expired products
3. Rep creates exchange (no approval needed)
4. Selects returned product & replacement product
5. Marks if returned items are resellable
6. System automatically:
   - Creates exchange record
   - Adjusts stock levels
   - Tracks non-resellable quantities
   - Completes immediately

### Access:
- **Sales Reps**: Can create & view their own exchanges
- **Managers**: Can view all exchanges and cancel if needed

---

## Files Modified/Created

### Models (`sales/models.py`)
- ✅ Added `ItemExchange` model
- ✅ Added `ExchangeItem` model

### Views (`sales/exchange_views.py`)
- ✅ Created `exchange_list`
- ✅ Created `create_exchange`
- ✅ Created `exchange_detail`
- ✅ Created `cancel_exchange`
- ✅ Created `exchange_print`

### URLs (`sales/urls.py`)
- ✅ Added exchange routes

### Templates
- ✅ `templates/sales/exchange_list.html`
- ⏳ Still need: `create_exchange.html`, `exchange_detail.html`, `exchange_print.html`

### Style Updates
- ✅ `templates/sales/bill_list.html` - Updated to #1f43b4
- ✅ `templates/sales/return_list.html` - Updated to #1f43b4

---

## Troubleshooting

### Error: "No such table: item_exchanges"
**Fix**: Run migrations:
```bash
python manage.py makemigrations sales
python manage.py migrate
```

### Error: "Connection refused"
**Fix**: Server is not running. Start it:
```bash
python manage.py runserver 192.168.1.4:8000
```

### Can't access from phone/other device
**Fix**: 
1. Make sure you're using the network IP: `192.168.1.4:8000`
2. Check firewall allows port 8000
3. Make sure both devices are on same WiFi network

---

## Next Development Tasks

### High Priority:
1. ⏳ Create `create_exchange.html` template
2. ⏳ Create `exchange_detail.html` template
3. ⏳ Create `exchange_print.html` template
4. ⏳ Add exchange link to navigation menu
5. ⏳ Test on mobile devices

### Medium Priority:
1. Update other pages with #1f43b4 color scheme
2. Add exchange statistics to dashboard
3. Create exchange reports

---

## Testing Checklist

After starting server:
- [ ] Access bills list - check new color scheme
- [ ] Access returns list - check new color scheme
- [ ] Run migrations for exchange system
- [ ] Test exchange list page
- [ ] Create test exchange (after templates done)
- [ ] Verify mobile responsive design
- [ ] Test on actual mobile device

---

## Command Reference

```bash
# Navigate to project
cd "c:\Users\LENOVO\Desktop\My Projects\zergo_distributors_sales_app"

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Start server (local)
python manage.py runserver

# Start server (network accessible)
python manage.py runserver 192.168.1.4:8000

# Create superuser (if needed)
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic
```
