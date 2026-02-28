import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill

bills = Bill.objects.all().order_by('-id')[:5]
print("Latest 5 Bills:")
for b in bills:
    print(f"  Bill #{b.id}: {b.bill_number} - {b.shop.shop_name} - Rs. {b.total_amount}")

print(f"\nTotal Bills: {Bill.objects.count()}")
print(f"Bill #46 exists: {Bill.objects.filter(id=46).exists()}")
