from products.models import Product, StockMovement

print("Checking all products for stock discrepancies...")
print("=" * 70)

discrepancies = []

for product in Product.objects.all():
    last_movement = StockMovement.objects.filter(product=product).order_by('-created_at').first()
    
    if last_movement:
        if product.quantity_in_stock != last_movement.new_quantity:
            discrepancies.append({
                'id': product.id,
                'name': product.product_name,
                'current_db': product.quantity_in_stock,
                'should_be': last_movement.new_quantity,
                'difference': last_movement.new_quantity - product.quantity_in_stock
            })

if discrepancies:
    print(f"\nFound {len(discrepancies)} products with stock discrepancies:\n")
    for d in discrepancies:
        print(f"Product {d['id']}: {d['name']}")
        print(f"  DB shows: {d['current_db']}")
        print(f"  Should be: {d['should_be']}")
        print(f"  Difference: {d['difference']:+.0f}")
        print()
    
    print("=" * 70)
    print("Fixing discrepancies...")
    print()
    
    for d in discrepancies:
        product = Product.objects.get(id=d['id'])
        old_qty = product.quantity_in_stock
        product.quantity_in_stock = d['should_be']
        product.save()
        print(f"✓ Fixed Product {d['id']}: {old_qty} → {d['should_be']}")
    
    print()
    print(f"✓ Successfully fixed {len(discrepancies)} products!")
else:
    print("\n✓ All products are in sync. No discrepancies found.")
