from django.core.management.base import BaseCommand
from products.models import Product


class Command(BaseCommand):
    help = 'Update bottles_per_pack for products based on their size'

    def handle(self, *args, **options):
        # Update bottles per pack based on size
        size_mapping = {
            '250ML': 24,
            '500ML': 24,
            '750ML': 12,
            '1000ML': 12,
            '1500ML': 12,
        }
        
        total_updated = 0
        for size, bottles in size_mapping.items():
            count = Product.objects.filter(size=size).update(bottles_per_pack=bottles)
            if count > 0:
                self.stdout.write(f'Updated {count} products with size {size} to {bottles} bottles per pack')
                total_updated += count
        
        self.stdout.write(self.style.SUCCESS(f'\nTotal products updated: {total_updated}'))
        
        # Show summary
        self.stdout.write('\n=== Current Bottles Per Pack Summary ===')
        for size, bottles in size_mapping.items():
            count = Product.objects.filter(size=size).count()
            if count > 0:
                self.stdout.write(f'{size}: {bottles} bottles/pack ({count} products)')
