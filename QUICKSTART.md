# Quick Start Guide - Zergo Distributors Sales App

## Installation Steps

1. **Create Virtual Environment**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. **Install Dependencies**
```powershell
pip install -r requirements.txt
```

3. **Setup Environment Variables**
```powershell
Copy-Item .env.example .env
# Edit .env with your database credentials
```

4. **Create Database**
```sql
-- In PostgreSQL
CREATE DATABASE zergo_sales_db;
CREATE EXTENSION postgis;
```

5. **Run Migrations**
```powershell
python manage.py makemigrations
python manage.py migrate
```

6. **Create Superuser**
```powershell
python manage.py createsuperuser
```

7. **Create Static Directory**
```powershell
mkdir static
python manage.py collectstatic --noinput
```

8. **Run Server**
```powershell
python manage.py runserver
```

9. **Access Application**
- Main App: http://127.0.0.1:8000/
- Admin Panel: http://127.0.0.1:8000/admin/

## First Time Setup

1. Login to admin panel
2. Create users (sales reps, office staff)
3. Add companies
4. Add product categories
5. Add products
6. Add shops
7. Assign sales reps to shops

## Default Login

Use the superuser credentials you created during installation.

## Key URLs

- Dashboard: `/`
- Shops: `/shops/`
- Shop Map: `/shops/map/`
- Products: `/products/`
- Create Bill: `/sales/create/`
- Bills List: `/sales/`
- Payments: `/payments/`
- Admin: `/admin/`

## Tips

- Use Chrome or Firefox for best experience
- Enable location services for shop geolocation
- Test printing bills before field use
- Backup database regularly

## Need Help?

Check README.md for detailed documentation.
