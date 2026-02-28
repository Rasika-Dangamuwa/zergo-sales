"""Check bill 211 details"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill

try:
    bill = Bill.objects.get(id=211)
    print(f"Bill: {bill.bill_number}")
    print(f"Bill Date: {bill.bill_date}")
    print(f"Shop: {bill.shop}")
    
    if bill.shop:
        print(f"Shop Name: {bill.shop.shop_name}")
        print(f"Shop Code: {bill.shop.shop_code}")
        print(f"Shop Owner: {bill.shop.owner_name}")
    else:
        print("❌ No shop linked to this bill")
        print(f"Customer Name: {bill.customer_name or 'Not provided'}")
        print("⚠️  This is an UNREGISTERED CUSTOMER sale")
    
    print(f"\nSales Rep: {bill.sales_rep.get_full_name()}")
    print(f"Sales Rep Username: {bill.sales_rep.username}")
    
except Bill.DoesNotExist:
    print("❌ Bill 211 not found")
