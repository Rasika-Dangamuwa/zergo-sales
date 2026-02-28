# Zergo Distributors Sales Management System

A comprehensive Django-based web application for managing distribution business operations, including sales, inventory, payments, and customer management.

## Features

### Core Functionality
- **User Management**: Multi-role system (Admin, Office Staff, Sales Representatives)
- **Shop/Customer Management**: Complete customer database with geolocation tracking
- **Product Management**: Track products from multiple companies with inventory management
- **Sales & Billing**: Create bills, print invoices, manage returns
- **Payment Management**: Track cash, cheques, bank transfers, and credit payments
- **Dashboard**: Separate dashboards for sales reps and office staff with analytics
- **Geolocation**: Map view of all shops with location tracking
- **Reports**: Sales reports, payment reports, and stock alerts
- **Mobile Bluetooth Printing**: Direct printing to portable thermal printers via Bluetooth

### Key Features for Sales Representatives
- Mobile-friendly interface for on-field use
- Quick bill creation with barcode support
- **Print bills directly to Bluetooth thermal printers from mobile**
- Track daily, weekly, and monthly sales
- View assigned shops on map
- Record shop visits with photos and notes
- Manage payments and outstanding balances
- **HTTPS/SSL support for secure mobile Bluetooth access**

### Key Features for Office Staff
- Comprehensive dashboard with business analytics
- Monitor all sales representatives' performance
- Payment verification and reconciliation
- Cheque management
- Stock management and low stock alerts
- Credit note management
- Detailed reports and analytics

## Technology Stack

- **Backend**: Django 5.0
- **Database**: PostgreSQL with PostGIS (for geolocation features)
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **Maps**: Leaflet.js with OpenStreetMap
- **PDF Generation**: ReportLab
- **Forms**: Django Crispy Forms with Bootstrap 5

## Installation

### Prerequisites

1. **Python 3.10 or higher**
2. **PostgreSQL** (already installed on your computer)
3. **PostGIS Extension** for PostgreSQL

### Step 1: Install PostGIS Extension

Open PostgreSQL command line (psql) and run:

```sql
CREATE EXTENSION postgis;
```

### Step 2: Create Virtual Environment

```powershell
# Navigate to project directory
cd "c:\Users\LENOVO\Desktop\My Projects\zergo_distributors_sales_app"

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

1. Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```

2. Edit `.env` file and update the following:
```
SECRET_KEY=your-secret-key-here-generate-a-random-one
DEBUG=True
DB_NAME=zergo_sales_db
DB_USER=postgres
DB_PASSWORD=your-postgresql-password
DB_HOST=localhost
DB_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Step 5: Create Database

Open PostgreSQL and create the database:

```sql
CREATE DATABASE zergo_sales_db;
```

Or use psql command:
```powershell
psql -U postgres -c "CREATE DATABASE zergo_sales_db;"
```

### Step 6: Run Migrations

```powershell
python manage.py makemigrations
python manage.py migrate
```

### Step 7: Create Superuser

```powershell
python manage.py createsuperuser
```

Follow the prompts to create an admin account.

### Step 8: Create Static Files Directory

```powershell
mkdir static
python manage.py collectstatic --noinput
```

### Step 9: Run Development Server

**Standard HTTP Server:**
```powershell
python manage.py runserver
```
The application will be available at: `http://127.0.0.1:8000/`

**HTTPS Server (Required for Mobile Bluetooth Printing):**
```powershell
# Quick setup with one command
.\setup_https.ps1

# Or use the simple script
.\run_https.ps1

# Or run manually
python manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:8000
```
The HTTPS application will be available at:
- Desktop: `https://localhost:8000`
- Mobile: `https://192.168.1.4:8000` (your local IP)

> **Note**: HTTPS is **required** for mobile Bluetooth printing. See [HTTPS_BLUETOOTH_SETUP.md](HTTPS_BLUETOOTH_SETUP.md) for detailed setup instructions.

## Initial Setup

### 1. Access Admin Panel

Navigate to `http://127.0.0.1:8000/admin/` and login with your superuser credentials.

### 2. Create Users

1. Go to **Users** section
2. Click **Add User**
3. Fill in details and select user type:
   - **Admin**: Full system access
   - **Office Staff**: Access to reports and management
   - **Sales Representative**: Field access for sales

### 3. Add Companies

1. Go to **Companies** section
2. Add companies you have dealerships with

### 4. Add Product Categories

1. Go to **Categories** section
2. Add product categories (e.g., Beverages, Snacks, etc.)

### 5. Add Products

1. Go to **Products** section
2. Add products with pricing and stock information

### 6. Add Shops/Customers

1. Go to **Shops** section
2. Add customer shops with complete details
3. Assign sales representatives to shops

## Usage Guide

### For Sales Representatives

1. **Login**: Use provided credentials
2. **View Dashboard**: See today's sales, weekly/monthly performance
3. **View Assigned Shops**: Access shop list or map view
4. **Create Bill**:
   - Select shop
   - Add products
   - Apply discounts if needed
   - Generate and print bill
5. **Mobile Bluetooth Printing** (New!):
   - Navigate to any bill detail page
   - Click "Mobile Print (Bluetooth)" button
   - Connect to your Bluetooth thermal printer
   - Print automatically!
   - **Requires HTTPS** - use `https://192.168.1.4:8000`
6. **Record Payment**: Record cash/cheque/bank transfer payments
7. **Track Shop Visits**: Add visit notes and photos

### For Office Staff

1. **Login**: Use office staff credentials
2. **Monitor Dashboard**: View overall business performance
3. **Review Sales**: Check all sales by representatives
4. **Verify Payments**: Verify bank transfers and cheques
5. **Generate Reports**: Access sales and payment reports
6. **Manage Inventory**: Monitor stock levels and alerts
7. **Credit Management**: Handle credit notes and adjustments

## Printing Bills

The system generates PDF bills that can be printed on:
- Regular A4 printers
- Portable thermal printers (58mm, 80mm)
- Receipt printers

Configure your printer and use the browser's print function or save as PDF.

## Database Schema

### Main Tables
- **users**: System users (admins, office staff, sales reps)
- **shops**: Customer shops with geolocation
- **companies**: Companies with dealerships
- **products**: Product catalog with inventory
- **bills**: Sales invoices
- **bill_items**: Line items in bills
- **payments**: Payment records
- **credit_notes**: Credit notes for returns/adjustments
- **shop_visits**: Track field visits

## Security Features

- Password hashing with Django's built-in authentication
- CSRF protection on all forms
- SQL injection protection via Django ORM
- XSS protection
- Role-based access control
- Session management

## API Endpoints

- `/shops/api/shops-geojson/`: GeoJSON data for map markers
- Additional REST API can be added using Django REST Framework

## Backup

### Database Backup

```powershell
pg_dump -U postgres zergo_sales_db > backup.sql
```

### Database Restore

```powershell
psql -U postgres zergo_sales_db < backup.sql
```

## Troubleshooting

### PostgreSQL Connection Error
- Verify PostgreSQL is running
- Check database credentials in `.env`
- Ensure database exists

### PostGIS Not Found
- Install PostGIS extension: `CREATE EXTENSION postgis;`
- Restart PostgreSQL service

### Static Files Not Loading
- Run `python manage.py collectstatic`
- Check `STATIC_ROOT` in settings

### Port Already in Use
- Change port: `python manage.py runserver 8080`
- Or stop the process using port 8000

## Development

### Adding New Features

1. Create new models in respective app's `models.py`
2. Create migrations: `python manage.py makemigrations`
3. Apply migrations: `python manage.py migrate`
4. Update views and templates
5. Add URL patterns

### Running Tests

```powershell
python manage.py test
```

## Production Deployment

For production deployment:

1. Set `DEBUG=False` in `.env`
2. Update `ALLOWED_HOSTS` with your domain
3. Use a production-grade server (Gunicorn + Nginx)
4. Enable HTTPS with SSL certificate
5. Use a production database server
6. Configure email backend for notifications
7. Set up regular database backups

## Support

For issues or questions:
- Check the Django documentation: https://docs.djangoproject.com/
- Review PostgreSQL documentation: https://www.postgresql.org/docs/
- Check Leaflet documentation: https://leafletjs.com/

## License

This is a proprietary system for Zergo Distributors.

## Version

Version 1.0.0 - Initial Release

---

**Built with Django Framework**

For internal use at Zergo Distributors
