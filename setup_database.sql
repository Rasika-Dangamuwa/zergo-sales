-- Database Setup SQL Script for Zergo Distributors Sales App
-- Run this script in pgAdmin or any PostgreSQL client

-- Step 1: Create the database
CREATE DATABASE zergo_sales_db
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'English_United States.1252'
    LC_CTYPE = 'English_United States.1252'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- Step 2: Connect to the newly created database (zergo_sales_db)
-- Then run the following command:

\c zergo_sales_db

-- Step 3: Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Step 4: Verify PostGIS installation
SELECT PostGIS_Version();

-- You should see PostGIS version information
-- If you see an error, you need to install PostGIS

-- Step 5: Verify the extension is enabled
SELECT * FROM pg_extension WHERE extname = 'postgis';

-- Expected output: You should see a row with postgis extension

-- Database setup is complete!
-- Now you can run Django migrations:
-- python manage.py makemigrations
-- python manage.py migrate
