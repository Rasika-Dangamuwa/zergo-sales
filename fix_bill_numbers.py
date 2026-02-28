"""
Quick script to fix empty bill numbers in the database
"""
from sales.models import Bill
from django.utils import timezone

# Find bills with empty bill_number
empty_bills = Bill.objects.filter(bill_number='')

print(f"Found {empty_bills.count()} bills with empty bill numbers")

for bill in empty_bills:
    # Generate bill number
    today = bill.bill_date if bill.bill_date else timezone.now()
    prefix = f"BILL{today.strftime('%Y%m%d')}"
    
    last_bill = Bill.objects.filter(bill_number__startswith=prefix).exclude(pk=bill.pk).order_by('-bill_number').first()
    
    if last_bill:
        last_number = int(last_bill.bill_number[-3:])
        new_number = last_number + 1
    else:
        new_number = 1
    
    bill_number = f"{prefix}{new_number:03d}"
    bill.bill_number = bill_number
    bill.save()
    print(f"Fixed bill ID {bill.id}: {bill_number}")

print("Done!")
