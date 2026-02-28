import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import PurchaseReturn

try:
    pr = PurchaseReturn.objects.get(pk=6)
    print(f"PR Number: {pr.pr_number}")
    print(f"Current Status: {pr.status}")
    print(f"Status Display: {pr.get_status_display()}")
    print(f"\nTo enable new workflow, update status to 'sent_to_supplier'")
    
except PurchaseReturn.DoesNotExist:
    print("Purchase Return #6 not found!")
