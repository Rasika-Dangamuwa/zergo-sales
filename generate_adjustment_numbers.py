"""
Generate adjustment numbers for existing ProductStatusAdjustment records
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import ProductStatusAdjustment
from django.db import transaction

print("Generating adjustment numbers for existing records...")

with transaction.atomic():
    adjustments = ProductStatusAdjustment.objects.filter(adjustment_number='').order_by('adjustment_date')
    count = adjustments.count()
    
    print(f"Found {count} records without adjustment numbers")
    
    for adj in adjustments:
        # Use the model's generate method
        adj.adjustment_number = adj.generate_adjustment_number()
        adj.save(update_fields=['adjustment_number'])
        print(f"  Generated {adj.adjustment_number} for adjustment ID {adj.id}")

print("\nDone!")
