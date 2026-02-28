import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import PurchaseOrder

po = PurchaseOrder.objects.filter(pk=12).first()
if po:
    print(f"PO #{po.pk}: {po.po_number}")
    print(f"Subtotal: Rs.{po.subtotal:,.2f}")
    print(f"Discount: Rs.{po.discount:,.2f}")
    print(f"Total: Rs.{po.total:,.2f}")
    print(f"Items count: {po.items.count()}")
else:
    print("PO #12 not found")
