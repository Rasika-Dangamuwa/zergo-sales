# Zergo Distributors Sales Management System - AI Agent Instructions

## Project Overview
Django 5.0 distribution management system for field sales operations with mobile Bluetooth thermal printing, geolocation tracking, and multi-role access control. **Multi-tenant** via `django-tenants` (PostgreSQL schema-based isolation) — each distributor gets a separate schema.

## Multi-Tenancy Architecture (django-tenants)

### Overview
Uses `django-tenants==3.10.0` with **PostgreSQL schema-based multi-tenancy**. Each distributor has their own schema (e.g., `dist_zergo001`) containing all business tables. Shared tables (users, distributors, domains) live in the `public` schema. Tenant is resolved by **subdomain** via `TenantMainMiddleware`.

### Schema Layout
- **public** schema (~65 tables): Shared tables (users, distributors, domains, django admin/sessions) + PLUS duplicate business tables (legacy — original single-tenant data)
- **tenant** schemas (~54 tables each): Tenant-scoped business data (shops, products, sales, payments, business, etc.)

### Key Configuration (settings module)
```python
DATABASE_ENGINE = 'django_tenants.postgresql_backend'
TENANT_MODEL = 'tenants.Distributor'
TENANT_DOMAIN_MODEL = 'tenants.Domain'
PUBLIC_SCHEMA_URLCONF = 'zergo_sales.urls_public'     # localhost (platform + app)
ROOT_URLCONF = 'zergo_sales.urls'                      # *.localhost (tenant app)
# SHARED_APPS: django_tenants, tenants, django core, django_extensions, crispy_forms, accounts
# TENANT_APPS: contenttypes, auth, shops, products, sales, payments, dashboard, business
```

### Tenant App (tenants/)
- tenants models — `Distributor(TenantMixin)` + `Domain(DomainMixin)`, `auto_create_schema=False` (clone-based)
- tenants utils — `create_tenant_schema(schema_name, copy_data)` clones public schema structure; `get_shared_only_tables()` dynamically computes excluded tables; `delete_tenant_schema()`
- tenants views — `platform_admin_required` decorator, `platform_dashboard`, `distributor_list/create/detail/edit/toggle`, `platform_reports`, `sales_summary_report`
- tenants forms — `DistributorForm` with extra `subdomain` field
- tenants urls — 8 URL patterns under `app_name='tenants'`, mounted at `/platform/`

### URL Routing
- **zergo_sales/urls_public** — Public schema (main domain): `/platform/` (tenants CRUD) + ALL standard app URLs (backward compat)
- **zergo_sales/urls** — Tenant schema (subdomains): Standard app routes only

### Creating New Tenants
```python
# In views (distributor_create):
distributor = form.save(commit=False)
distributor.schema_name = f'dist_{code.lower()}'
distributor.auto_create_schema = True
distributor.save()  # django-tenants creates schema via clone
# Then create Domain(domain=f'{subdomain}.localhost', tenant=distributor, is_primary=True)
```

### Cross-Tenant Data Access (Platform Views)
```python
from django_tenants.utils import schema_context
for dist in Distributor.objects.filter(is_active=True):
    with schema_context(dist.schema_name):
        bills = Bill.objects.exclude(bill_status='cancelled').aggregate(...)
```

### User Model Changes
```python
# accounts/models.py — User model additions:
tenant = ForeignKey('tenants.Distributor', null=True, blank=True)  # Links user to distributor
is_platform_admin = BooleanField(default=False)                     # Central admin access
```

### Domain/Subdomain Setup
- Main domain: `localhost` → `public` schema (Platform Admin + backward-compat app)
- Tenant subdomains: `zergo001.localhost` → `dist_zergo001` schema
- ALLOWED_HOSTS includes `'.localhost'` for wildcard subdomain matching
- SSL cert includes `DNS:*.localhost` SAN for HTTPS on subdomains
- Hosts file entries required: `127.0.0.1 zergo001.localhost` per tenant

### Platform Admin Access
- Sidebar link "Platform Admin" visible to `is_superuser` or `is_platform_admin` users
- URL: `/platform/` → Platform dashboard with cross-tenant aggregation
- Template: `templates/tenants/base_platform.html` (extends Bootstrap 5, standalone layout)

### Common Pitfalls — Multi-Tenancy
1. **Schema Creation**: Uses clone-based approach (NOT `migrate_schemas`). Never set `auto_create_schema=True` permanently on the model — toggle it in the create view only
2. **Shared Tables**: Users, distributors, domains live ONLY in `public` schema. Don't query `User` inside `schema_context` — it resolves to the tenant schema's auth tables
3. **Bill Model Fields**: Use `bill_status` (not `is_cancelled`), `total_amount` (not `grand_total`), `balance_amount` (not `balance_due`)
4. **New Hosts File Entries**: Each new tenant subdomain needs a hosts file entry (`127.0.0.1 subdomain.localhost`)

## Architecture

### App Structure & Responsibilities
- **tenants/** - Multi-tenant management (Distributor, Domain models, platform admin views, schema utilities)
- **accounts/** - Custom User model with 3 roles: `admin`, `office`, `sales_rep`. Role checked via `user.user_type` property. User has `tenant` FK and `is_platform_admin` flag
- **shops/** - Customer/Shop management with geolocation (`latitude`/`longitude` fields, NOT PostGIS Point), shop visits tracking
- **products/** - Direct stock tracking per product (no SKU complexity). Each Product has `quantity_in_stock`, FOC ratios, company/shop discounts
- **sales/** - Bills, Returns, and Exchanges. Contains specialized print modules: print_engine, print_manager, paper_config, receipt_optimizer. Exchange module: exchange_views handles product swaps
- **payments/** - Multi-method payments (Cash, Cheque, Bank Transfer, Credit). Includes verification workflow
- **dashboard/** - Role-specific dashboards and reporting

### Key Domain Models & Number Formats (Standardized: PREFIX-YYYYMMDD-###)
```python
# Sales Bills: "SAL-20260110-001" (sale_number auto-generated)
# Old Bills: "BILL-20260110-001" (bill_number auto-generated)
# Sales Returns: "RN-20260110-001" (return_number auto-generated)
# Exchanges: "EXC-20260110-001" (exchange_number auto-generated)
# Payment Vouchers: "CPV-20260110-001" (cash_receipt_number auto-generated)
# Regular Payments: "PAY-20260110-001" (payment_number auto-generated)
# Company Returns: "CR-20260110-001" (return_number to company auto-generated)
# Shop Codes: "SHOP000001" (auto-generated 6 digits, no date)
```

### Print System Architecture (World-Class Unified Design)
**Critical**: The print system was completely rebuilt on January 4, 2026. DO NOT use old models (BillSettings, BillTemplate, CompanyBranding, PrinterProfile).

**Use Only**:
- `PrintManager` model in sales app's print_manager module (520 lines, single unified config per user/receipt type)
- `UnifiedPrintEngine` class in sales app's print_engine module (generates ESC/POS, handles all receipt types)
- `PaperSizeConfig` enum in sales app's paper_config module (9 standard paper sizes: 80mm, 58mm, A4, etc.)
- `ReceiptOptimizer` in sales app's receipt_optimizer module (dynamic font sizing, logo optimization)

**Print Profile Access**:
```python
from sales.print_manager import PrintManager
profile = PrintManager.get_user_default(user, 'bill')  # Auto-creates if missing
# Receipt types: 'bill', 'payment', 'return_cash', 'field_receipt'
```

### Return System Terminology (Standardized January 5, 2026)
Reference: RETURN_SYSTEM_TERMINOLOGY_STANDARDIZATION doc in project root

**Status Fields**:
- `return_status`: `pending`, `approved`, `rejected`
- `settlement_method`: `cash`, `credit_note`, `next_bill`
- `settlement_status`: `unsettled`, `settled_cash`, `available`, `partially_applied`, `fully_applied`

**UI Labels**: Use "Sales Return Note" (not "Product Return"), "Voucher No." (not "Receipt No."), "Payment Status" (not "Settlement Status")

### Exchange System (Product Swaps)
**Purpose**: Shops swap damaged/expired/slow-moving items for different products in same category-size-price group **without affecting sales**.

**Business Logic**:
- OUT items (returning to stock): Adds to `Product.quantity_in_stock`
- IN items (taking from stock): Subtracts from `Product.quantity_in_stock`
- Exchange group validation: All items (OUT + IN) must match category, size, and marked_price
- No financial calculations - pure inventory swap

**Models**:
```python
Exchange:
  - exchange_number: "EXC-20260107-001" (auto-generated)
  - exchange_status: pending/approved/rejected
  - exchange_reason: damaged/expired/slow_moving/customer_request/other
  - shop FK, created_by FK, approved_by FK
  
ExchangeItem:
  - item_type: 'out' (returning) or 'in' (taking)
  - product FK, quantity, foc_quantity
  - exchange_ref FK to Exchange
```

**Workflow**:
1. Create exchange (2-step): Select OUT items → Select IN items from same group
2. Admin/office approves → Creates StockMovement with `movement_type='exchange'`
3. Stock updated automatically (OUT +stock, IN -stock)

**Views**: sales/exchange_views — exchange_list, create_exchange, exchange_detail, approve_exchange, reject_exchange

### Commission & Money Account System (January 27, 2026)
**Purpose**: Automated commission tracking and payout to user money accounts with configurable scheduling.

**Commission Tracking**:
- `CommissionTransaction`: Auto-created via Django signals when bills/payments/returns occur
- `CommissionRateHistory`: Stores commission rate changes with effective dates
- `get_rep_balance(user)`: Calculates current commission balance for a sales rep

**Money Account System** (accounts/money_account_models):
- `UserMoneyAccount`: Tracks earnings, disbursements, advances for each user
- `MoneyTransaction`: Individual credit/debit transactions (types: commission_payment, manual_credit, disbursement, advance)
- `AdvanceRequest`: Sales reps can request advances against future earnings
- **Balance Formula**: current_balance = opening_balance + total_credited - total_debited - total_advance_given

**Automated Payout Scheduler** (sales/commission_schedule_models):
```python
CommissionPayoutSchedule:
  - frequency: monthly/weekly/biweekly/custom
  - payout_day_of_month: 1-28 or 0 for last day
  - payout_time: Time of day to execute (HH:MM)
  - minimum_payout_amount: Only pay if balance exceeds this
  - is_active: Enable/disable automation
  - next_run_date: Auto-calculated next execution
  
CommissionPayoutHistory:
  - execution_date, status (success/partial/failed/skipped)
  - total_users_processed, total_amount_credited
  - period_start/end, duration_seconds, details (JSON)
  
UserCommissionPayout:
  - Links: history → user → money_transaction
  - commission_balance, amount_credited, status
```

**Management Command**: `python manage process_commission_payouts`
- Flags: `--dry-run` (test mode), `--force` (ignore schedule), `--schedule-id` (specific schedule)
- Workflow: Check schedule → Get user balances → Create MoneyTransactions → Log history
- **Windows Task Scheduler**: Run `run_commission_payouts.bat` every minute (command checks if it's time)

**URLs**:
- `/sales/commissions/settings/` - Configure schedule, view payout history
- `/accounts/money-account/` - User money account dashboard
- `/accounts/all-money-accounts/` - Office view of all accounts

**Professional Terminology**:
- "Balance Due" (not "Account Balance")
- "Total Earned" (not "Total Credits")
- "Payments Disbursed" (not "Total Debits")
- "Advances Drawn" (not "Advance Paid")

**Documentation**: See COMMISSION_PAYOUT_SCHEDULER doc in project root for complete details

## Development Workflows

### Running the Server

**Standard HTTP**:
```powershell
.\venv\Scripts\Activate.ps1
python manage.py runserver
```

**HTTPS (for mobile Bluetooth printing)**:
```powershell
# Option 1: Stable script (recommended)
.\venv\Scripts\python.exe run_stable_https.py

# Option 2: PowerShell launcher
.\run_https.ps1

# Option 3: django-extensions
python manage.py runserver_plus 0.0.0.0:8000 --cert-file cert.pem --key-file key.pem --noreload
```

**SSL Certificates**: Auto-generated via generate_cert script. Must regenerate if local IP changes. Required for Web Bluetooth API on mobile devices.

### Database Migrations
```powershell
python manage.py makemigrations
python manage.py migrate
```

**Note**: PostGIS is installed but currently disabled in settings (see `INSTALLED_APPS` commented sections). Using `latitude`/`longitude` DecimalFields instead of PointField.

### Common Development Scripts
- sync_all_product_stock — Recalculate all product stock from movements
- check_*, fix_*, investigate_* — Ad-hoc data investigation/repair scripts (not production code)

## Code Conventions

### View Decorators & Permissions
All views use `@login_required`. NO custom decorators for role checks - use inline conditionals:
```python
@login_required
def view_name(request):
    if request.user.user_type != 'sales_rep':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
```

### Model Save Patterns
Auto-generate unique numbers in `save()`:
```python
def save(self, *args, **kwargs):
    if not self.sale_number:
        self.sale_number = self.generate_sale_number()
    super().save(*args, **kwargs)
```

### Money Calculations
Always use `Decimal` from `decimal` module for currency:
```python
from decimal import Decimal
total = sum(item.line_total for item in items)  # Items use DecimalField
```

### Template Patterns
- Base template: `templates/base.html`
- Role-specific includes: Check `user.is_sales_rep` or `user.is_office_staff` in templates
- Forms: Use `crispy_forms` with `crispy_bootstrap5` (already configured)

## Integration Points

### Mobile Bluetooth Printing
- **Entry**: sales/urls → `<int:pk>/mobile-print/` → `mobile_print()` view
- **Template**: `templates/sales/mobile_print.html` (uses Web Bluetooth API)
- **ESC/POS Generation**: `UnifiedPrintEngine.generate_escpos_commands()` in the sales app print_engine module
- **HTTPS Required**: Bluetooth API only works over HTTPS. Use run_stable_https script

### Geolocation/Maps
- **Frontend**: Leaflet.js with OpenStreetMap (NOT Google Maps)
- **Shop Map**: `/shops/map/` - Shows all shops with markers
- **Location Storage**: `Shop.latitude`/`longitude`, `SalesRepLocation.latitude`/`longitude`

### PDF Generation
- **Library**: ReportLab (see `requirements.txt`)
- **Usage**: Bill PDFs in sales/views (search for ReportLab imports)

## Common Pitfalls

1. **Don't Mix Print Systems**: Only use `PrintManager` + `UnifiedPrintEngine`. Old models removed January 4, 2026
2. **Number Format Changes**: Return numbers changed from `RET20260105001` → `RN-20260105-001`. Check docs before generating
3. **HTTPS Port Conflicts**: Port 8000 often conflicts. Use `netstat -ano | findstr ":8000"` and `taskkill /F /PID <pid>` if needed
4. **Werkzeug Reloader Issues**: Use run_stable_https script which sets `WERKZEUG_RUN_MAIN='true'` to avoid double-reload bugs
5. **Role Access**: Don't create custom decorators. Use `user.user_type` inline checks per existing codebase pattern

## Reference Documentation (all in project root)
- PROJECT_SUMMARY — Complete feature list, models, URLs
- PRINT_MANAGEMENT_REBUILD — Print system architecture rebuild notes
- RETURN_SYSTEM_TERMINOLOGY_STANDARDIZATION — Return status/label standards
- HTTPS_SSL_IMPLEMENTATION — SSL setup for mobile Bluetooth
- QUICKSTART — Installation steps, first-time setup
- COMMISSION_PAYOUT_SCHEDULER — Commission schedule architecture

## Testing & Validation
No automated test suite. Manual testing via:
1. Login as different user types (admin, office, sales_rep)
2. Test mobile Bluetooth print: Access via HTTPS on mobile → Connect to thermal printer
3. Create bills → Verify stock updates → Check return flows
4. **Multi-tenancy**: Access `https://localhost:8000/platform/` as platform admin
5. **Tenant isolation**: Access `https://zergo001.localhost:8000/` and verify separate data
