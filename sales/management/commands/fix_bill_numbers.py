from django.core.management.base import BaseCommand
from sales.models import Bill
from django.utils import timezone


class Command(BaseCommand):
    help = 'Fix empty bill numbers in the database'

    def handle(self, *args, **options):
        # Find bills with empty bill_number
        empty_bills = Bill.objects.filter(bill_number='')

        self.stdout.write(f"Found {empty_bills.count()} bills with empty bill numbers")

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
            self.stdout.write(self.style.SUCCESS(f"Fixed bill ID {bill.id}: {bill_number}"))

        self.stdout.write(self.style.SUCCESS("Done!"))
