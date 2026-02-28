import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

# Create purchase_orders table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_orders (
        id SERIAL PRIMARY KEY,
        po_number VARCHAR(50) UNIQUE NOT NULL,
        company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
        order_date DATE NOT NULL,
        expected_delivery_date DATE,
        received_date DATE,
        status VARCHAR(20) NOT NULL DEFAULT 'draft',
        subtotal DECIMAL(12, 2) DEFAULT 0,
        discount DECIMAL(12, 2) DEFAULT 0,
        total DECIMAL(12, 2) DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL
    )
""")

# Create purchase_order_items table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_order_items (
        id SERIAL PRIMARY KEY,
        purchase_order_id INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
        packs INTEGER DEFAULT 0,
        bottles_per_pack INTEGER DEFAULT 0,
        total_bottles INTEGER NOT NULL,
        foc_bottles INTEGER DEFAULT 0,
        unit_price DECIMAL(10, 2) NOT NULL,
        value_before_discount DECIMAL(12, 2) NOT NULL,
        discount_percentage DECIMAL(5, 2) DEFAULT 0,
        discount_amount DECIMAL(12, 2) DEFAULT 0,
        line_total DECIMAL(12, 2) NOT NULL,
        received_quantity INTEGER DEFAULT 0,
        received_foc INTEGER DEFAULT 0
    )
""")

print("✓ Created purchase_orders table")
print("✓ Created purchase_order_items table")

# Now add FK to purchases table
cursor.execute("""
    ALTER TABLE purchases 
    ADD COLUMN IF NOT EXISTS purchase_order_id INTEGER 
    REFERENCES purchase_orders(id) ON DELETE SET NULL
""")

print("✓ Added purchase_order_id FK to purchases table")

connection.commit()
print("\n✅ All database changes applied successfully!")
