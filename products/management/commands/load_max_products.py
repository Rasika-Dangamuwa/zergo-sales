from django.core.management.base import BaseCommand
from products.models import Company, Category, StockKeepingUnit, Product


class Command(BaseCommand):
    help = 'Load Max Beverages sample products into the database'

    def handle(self, *args, **options):
        self.stdout.write('Loading Max Beverages products...')
        
        # Create or get company
        company, created = Company.objects.get_or_create(
            company_code='MAX',
            defaults={
                'company_name': 'Max Beverages (PVT) Ltd.',
                'contact_person': 'Sales Manager',
                'phone_number': '0112345678',
                'email': 'sales@maxbeverages.lk',
                'address': 'Colombo, Sri Lanka',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created company: {company.company_name}'))
        else:
            self.stdout.write(f'Using existing company: {company.company_name}')
        
        # Create or get category
        category, created = Category.objects.get_or_create(
            name='Soft Drinks',
            defaults={
                'description': 'Carbonated soft drinks',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
        
        # Product data from the image
        products_data = [
            # 250ML products - Marked Price: 100.00
            ('250ML Max Orange', '250ML', 100.00, 'Orange'),
            ('250ML Max Nexta', '250ML', 100.00, 'Nexta'),
            ('250ML Max Cream Soda', '250ML', 100.00, 'Cream Soda'),
            ('250ML Max Cola', '250ML', 100.00, 'Cola'),
            ('250ML Max Prite', '250ML', 100.00, 'Prite'),
            ('250ML Max Ginger Beer', '250ML', 100.00, 'Ginger Beer'),
            
            # 500ML products - Different marked prices
            ('500ML Max Orange', '500ML', 130.00, 'Orange'),
            ('500ML Max Nexta', '500ML', 130.00, 'Nexta'),
            ('500ML Max Cream Soda', '500ML', 130.00, 'Cream Soda'),
            ('500ML Max Cola', '500ML', 150.00, 'Cola'),
            ('500ML Max Prite', '500ML', 150.00, 'Prite'),
            ('500ML Max Ginger Beer', '500ML', 150.00, 'Ginger Beer'),
            ('500ML Max Soda', '500ML', 100.00, 'Soda'),
            
            # 750ML products - Marked Price: 150.00
            ('750ML Max Orange', '750ML', 150.00, 'Orange'),
            ('750ML Max Nexta', '750ML', 150.00, 'Nexta'),
            ('750ML Max Cream Soda', '750ML', 150.00, 'Cream Soda'),
            
            # 1000ML products - Marked Price: 250.00
            ('1000ML Max Orange', '1000ML', 250.00, 'Orange'),
            ('1000ML Max Nexta', '1000ML', 250.00, 'Nexta'),
            ('1000ML Max Cream Soda', '1000ML', 250.00, 'Cream Soda'),
            ('1000ML Max Cola', '1000ML', 250.00, 'Cola'),
            ('1000ML Max Prite', '1000ML', 250.00, 'Prite'),
            
            # 1500ML products - Marked Price: 330.00
            ('1500ML Max Orange', '1500ML', 330.00, 'Orange'),
            ('1500ML Max Nexta', '1500ML', 330.00, 'Nexta'),
            ('1500ML Max Cream Soda', '1500ML', 330.00, 'Cream Soda'),
            ('1500ML Max Cola', '1500ML', 330.00, 'Cola'),
            ('1500ML Max Prite', '1500ML', 330.00, 'Prite'),
        ]
        
        # Create SKUs and Products
        skus_created = 0
        products_created = 0
        products_updated = 0
        
        # Track unique SKUs
        sku_map = {}
        
        for product_name, size, marked_price, flavor in products_data:
            # Create or get SKU (size + marked_price combination)
            sku_key = f"{size}-{marked_price}"
            
            if sku_key not in sku_map:
                sku, sku_created = StockKeepingUnit.objects.get_or_create(
                    company=company,
                    size=size,
                    marked_price=marked_price,
                    defaults={
                        'quantity_in_stock': 0,  # Start with 0, will be updated via purchase orders
                        'minimum_stock_level': 50,
                        'is_active': True
                    }
                )
                sku_map[sku_key] = sku
                if sku_created:
                    skus_created += 1
                    self.stdout.write(f'  Created SKU: {sku.sku_code}')
            else:
                sku = sku_map[sku_key]
            
            # Create or update product
            product_code = f"MAX-{size}-{flavor.upper().replace(' ', '')}"
            
            product, product_created = Product.objects.update_or_create(
                product_code=product_code,
                defaults={
                    'product_name': product_name,
                    'company': company,
                    'category': category,
                    'sku': sku,
                    'flavor': flavor,
                    'discount_percentage': 10.00,  # 10% discount (changeable)
                    'is_active': True
                }
            )
            
            if product_created:
                products_created += 1
                self.stdout.write(f'  Created product: {product.product_name}')
            else:
                products_updated += 1
                self.stdout.write(f'  Updated product: {product.product_name}')
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== Summary ==='))
        self.stdout.write(self.style.SUCCESS(f'SKUs created: {skus_created}'))
        self.stdout.write(self.style.SUCCESS(f'Products created: {products_created}'))
        self.stdout.write(self.style.SUCCESS(f'Products updated: {products_updated}'))
        self.stdout.write(self.style.SUCCESS(f'Total products: {products_created + products_updated}'))
        
        # Show discount calculation example
        sample_product = Product.objects.filter(product_code='MAX-250ML-ORANGE').first()
        if sample_product:
            self.stdout.write(self.style.SUCCESS(f'\n=== Example: {sample_product.product_name} ==='))
            self.stdout.write(f'Marked Price (MRP): Rs. {sample_product.marked_price}')
            self.stdout.write(f'Shop Discount: {sample_product.discount_percentage}%')
            self.stdout.write(f'Discount Amount: Rs. {sample_product.discount_amount}')
            self.stdout.write(f'Final Price to Shop: Rs. {sample_product.final_price}')
            self.stdout.write(f'Stock Level: {sample_product.available_stock} (from SKU: {sample_product.sku.sku_code})')
            self.stdout.write(self.style.WARNING('\nNote: Discount percentage can be changed per product in admin.'))
