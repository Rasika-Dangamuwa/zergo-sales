"""
Sync existing tenant products into the Global Catalog.

Reads products from ZERGO001 (the original tenant with all product data),
creates matching GlobalCompany, GlobalCategory, GlobalProduct entries in the
public schema, then sets the global_product FK on each tenant product across
ALL tenant schemas.
"""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from catalog.models import GlobalCompany, GlobalCategory, GlobalProduct
from tenants.models import Distributor

SOURCE_SCHEMA = 'dist_zergo001'

print("=" * 60)
print("SYNC EXISTING PRODUCTS → GLOBAL CATALOG")
print("=" * 60)

# Step 1: Read all products from ZERGO001
with schema_context(SOURCE_SCHEMA):
    from products.models import Product, Company, Category

    companies = list(Company.objects.all().values(
        'id', 'company_name', 'company_code', 'tagline', 'description',
        'contact_person', 'phone_number', 'email', 'website',
        'address', 'city', 'country', 'is_active', 'notes'
    ))
    categories = list(Category.objects.all().values(
        'id', 'name', 'description', 'is_active'
    ))
    products = list(Product.objects.select_related('company', 'category').all())

    # Build lookup maps (tenant PK → data)
    company_data = {c['id']: c for c in companies}
    category_data = {c['id']: c for c in categories}

    product_list = []
    for p in products:
        product_list.append({
            'tenant_pk': p.pk,
            'product_code': p.product_code,
            'product_name': p.product_name,
            'description': p.description or '',
            'company_code': p.company.company_code,
            'category_name': p.category.name if p.category else None,
            'size': p.size,
            'marked_price': p.marked_price,
            'bottles_per_pack': p.bottles_per_pack,
            'barcode': p.barcode or '',
            'display_order': p.display_order,
            'is_active': p.is_active,
        })

print(f"\nSource: {SOURCE_SCHEMA}")
print(f"  Companies: {len(companies)}")
print(f"  Categories: {len(categories)}")
print(f"  Products:   {len(product_list)}")

# Step 2: Create GlobalCompany entries
print("\n--- Creating Global Companies ---")
company_map = {}  # company_code → GlobalCompany
for c in companies:
    gc, created = GlobalCompany.objects.get_or_create(
        company_code=c['company_code'],
        defaults={
            'company_name': c['company_name'],
            'tagline': c['tagline'] or '',
            'description': c['description'] or '',
            'contact_person': c['contact_person'] or '',
            'phone_number': c['phone_number'] or '',
            'email': c['email'] or '',
            'website': c['website'] or '',
            'address': c['address'] or '',
            'city': c['city'] or '',
            'country': c['country'] or 'Sri Lanka',
            'is_active': c['is_active'],
            'notes': c['notes'] or '',
        }
    )
    company_map[c['company_code']] = gc
    status = "CREATED" if created else "EXISTS"
    print(f"  {status}: {gc.company_name} ({gc.company_code})")

# Step 3: Create GlobalCategory entries
print("\n--- Creating Global Categories ---")
category_map = {}  # name → GlobalCategory
for c in categories:
    gcat, created = GlobalCategory.objects.get_or_create(
        name=c['name'],
        defaults={
            'description': c['description'] or '',
            'is_active': c['is_active'],
        }
    )
    category_map[c['name']] = gcat
    status = "CREATED" if created else "EXISTS"
    print(f"  {status}: {gcat.name}")

# Step 4: Create GlobalProduct entries
print("\n--- Creating Global Products ---")
product_map = {}  # product_code → GlobalProduct
for p in product_list:
    gp, created = GlobalProduct.objects.get_or_create(
        product_code=p['product_code'],
        defaults={
            'product_name': p['product_name'],
            'description': p['description'],
            'company': company_map[p['company_code']],
            'category': category_map.get(p['category_name']),
            'size': p['size'],
            'marked_price': p['marked_price'],
            'bottles_per_pack': p['bottles_per_pack'],
            'barcode': p['barcode'],
            'display_order': p['display_order'],
            'is_active': p['is_active'],
        }
    )
    product_map[p['product_code']] = gp
    status = "CREATED" if created else "EXISTS"
    print(f"  {status}: {gp.product_name} ({gp.product_code})")

# Step 5: Link tenant products → global products in ALL tenant schemas
print("\n--- Linking Tenant Products → Global Catalog ---")
for dist in Distributor.objects.filter(is_active=True).exclude(schema_name='public'):
    with schema_context(dist.schema_name):
        from products.models import Product as TenantProduct
        linked = 0
        for tp in TenantProduct.objects.filter(global_product__isnull=True):
            gp = product_map.get(tp.product_code)
            if gp:
                tp.global_product = gp
                tp.save(update_fields=['global_product'])
                linked += 1
        print(f"  {dist.schema_name}: {linked} products linked")

# Final summary
print("\n" + "=" * 60)
print("GLOBAL CATALOG SUMMARY")
print(f"  Companies:  {GlobalCompany.objects.count()}")
print(f"  Categories: {GlobalCategory.objects.count()}")
print(f"  Products:   {GlobalProduct.objects.count()}")
print("=" * 60)
print("Done!")
