from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product, Company, Category


class Command(BaseCommand):
    help = 'Delete all products and reload Max products from the provided list'

    def handle(self, *args, **options):
        self.stdout.write('Starting product reload process...')
        
        with transaction.atomic():
            # Delete all existing products
            deleted_count = Product.objects.all().count()
            Product.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {deleted_count} existing products'))
            
            # Get or create Max company
            company, created = Company.objects.get_or_create(
                company_name='Max',
                defaults={'company_code': 'MAX001'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS('Created Max company'))
            
            # Get or create Beverages category
            category, created = Category.objects.get_or_create(
                name='Beverages',
                defaults={'description': 'Beverage products'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS('Created Beverages category'))
            
            # Max products data from the table (using Marked Price column)
            products_data = [
                # 250ML products
                {'name': '250ML Max Orange', 'size': '250ML', 'marked_price': 100.00, 'discount': 10},
                {'name': '250ML Max Nexta', 'size': '250ML', 'marked_price': 100.00, 'discount': 10},
                {'name': '250ML Max Cream Soda', 'size': '250ML', 'marked_price': 100.00, 'discount': 10},
                {'name': '250ML Max Cola', 'size': '250ML', 'marked_price': 100.00, 'discount': 10},
                {'name': '250ML Max Prite', 'size': '250ML', 'marked_price': 100.00, 'discount': 10},
                {'name': '250ML Max Ginger Beer', 'size': '250ML', 'marked_price': 100.00, 'discount': 10},
                
                # 500ML products
                {'name': '500ML Max Orange', 'size': '500ML', 'marked_price': 130.00, 'discount': 10},
                {'name': '500ML Max Nexta', 'size': '500ML', 'marked_price': 130.00, 'discount': 10},
                {'name': '500ML Max Cream Soda', 'size': '500ML', 'marked_price': 130.00, 'discount': 10},
                {'name': '500ML Max Cola', 'size': '500ML', 'marked_price': 150.00, 'discount': 10},
                {'name': '500ML Max Prite', 'size': '500ML', 'marked_price': 150.00, 'discount': 10},
                {'name': '500ML Max Ginger Beer', 'size': '500ML', 'marked_price': 150.00, 'discount': 10},
                {'name': '500ML Max Soda', 'size': '500ML', 'marked_price': 100.00, 'discount': 10},
                
                # 750ML products
                {'name': '750ML Max Orange', 'size': '750ML', 'marked_price': 150.00, 'discount': 10},
                {'name': '750ML Max Nexta', 'size': '750ML', 'marked_price': 150.00, 'discount': 10},
                {'name': '750ML Max Cream Soda', 'size': '750ML', 'marked_price': 150.00, 'discount': 10},
                
                # 1000ML products
                {'name': '1000ML Max Orange', 'size': '1000ML', 'marked_price': 250.00, 'discount': 10},
                {'name': '1000ML Max Nexta', 'size': '1000ML', 'marked_price': 250.00, 'discount': 10},
                {'name': '1000ML Max Cream Soda', 'size': '1000ML', 'marked_price': 250.00, 'discount': 10},
                {'name': '1000ML Max Cola', 'size': '1000ML', 'marked_price': 250.00, 'discount': 10},
                {'name': '1000ML Max Prite', 'size': '1000ML', 'marked_price': 250.00, 'discount': 10},
                
                # 1500ML products
                {'name': '1500ML Max Orange', 'size': '1500ML', 'marked_price': 330.00, 'discount': 10},
                {'name': '1500ML Max Nexta', 'size': '1500ML', 'marked_price': 330.00, 'discount': 10},
                {'name': '1500ML Max Cream Soda', 'size': '1500ML', 'marked_price': 330.00, 'discount': 10},
                {'name': '1500ML Max Cola', 'size': '1500ML', 'marked_price': 330.00, 'discount': 10},
                {'name': '1500ML Max Prite', 'size': '1500ML', 'marked_price': 330.00, 'discount': 10},
                
                # 220ML Aloe Vera
                {'name': '220ML Aloe Vera', 'size': '220ML', 'marked_price': 140.00, 'discount': 10},
            ]
            
            # Create products
            created_count = 0
            for idx, product_data in enumerate(products_data, start=1):
                product_code = f"MAX{idx:03d}"
                
                product = Product.objects.create(
                    product_code=product_code,
                    product_name=product_data['name'],
                    company=company,
                    category=category,
                    size=product_data['size'],
                    marked_price=product_data['marked_price'],
                    discount_percentage=product_data['discount'],
                    quantity_in_stock=0,  # Starting with 0 stock
                    minimum_stock_level=50,
                    display_order=idx,  # Set display order based on position in list
                    is_active=True,
                    description=f"{product_data['name']}"
                )
                created_count += 1
                self.stdout.write(f'Created: {product.product_code} - {product.product_name} ({product.size}) - Rs. {product.marked_price} (Disc: {product.discount_percentage}%)')
            
            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created {created_count} products'))
            self.stdout.write(self.style.SUCCESS('Product reload completed!'))
