import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Exchange

# Get exchange #24
e = Exchange.objects.prefetch_related(
    'items__in_product__category',
    'items__out_product__category',
    'shop',
    'created_by',
    'approved_by'
).get(pk=24)

print('=' * 60)
print('EXCHANGE DETAILS')
print('=' * 60)
print(f'Exchange No: {e.exchange_number}')
print(f'Date: {e.exchange_date}')
print(f'Status: {e.exchange_status}')
print(f'Shop: {e.shop.shop_code} - {e.shop.shop_name}')
print(f'Reason: {e.get_exchange_reason_display()}')
print(f'Created by: {e.created_by.username}')
if e.approved_by:
    print(f'Approved by: {e.approved_by.username}')
    print(f'Approved at: {e.approved_at}')
print(f'Notes: {e.notes or "None"}')

print('\n' + '=' * 60)
print('EXCHANGE ITEMS')
print('=' * 60)
items = list(e.items.all())
print(f'Total Pairs: {len(items)}\n')

for i, item in enumerate(items, 1):
    print(f'Pair #{i}:')
    print(f'  IN (Shop Returns - Stock ↑):')
    print(f'    Product: {item.in_product.product_name}')
    print(f'    Category: {item.in_product.category.name}')
    print(f'    Size: {item.in_product.size}ml')
    print(f'    Price: Rs.{item.in_product.marked_price}')
    print(f'    Current Stock: {item.in_product.quantity_in_stock}')
    
    print(f'  OUT (We Give - Stock ↓):')
    print(f'    Product: {item.out_product.product_name}')
    print(f'    Category: {item.out_product.category.name}')
    print(f'    Size: {item.out_product.size}ml')
    print(f'    Price: Rs.{item.out_product.marked_price}')
    print(f'    Current Stock: {item.out_product.quantity_in_stock}')
    
    print(f'  Quantity: {item.quantity}')
    
    # Check if same group
    same_category = item.in_product.category == item.out_product.category
    same_size = item.in_product.size == item.out_product.size
    same_price = item.in_product.marked_price == item.out_product.marked_price
    
    if same_category and same_size and same_price:
        print('  ✓ Valid Exchange Group')
    else:
        print('  ✗ INVALID - Not same group!')
        if not same_category:
            print('    - Different categories')
        if not same_size:
            print('    - Different sizes')
        if not same_price:
            print('    - Different prices')
    print()

# Check validation
print('=' * 60)
print('VALIDATION')
print('=' * 60)
try:
    e.validate_exchange_group()
    print('✓ Exchange validation passed')
except Exception as ex:
    print(f'✗ Validation failed: {ex}')
