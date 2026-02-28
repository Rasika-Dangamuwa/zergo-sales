import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Bill
from payments.models import SalesAccountSettlement
from decimal import Decimal
from django.db import connection
from django.db.backends.signals import connection_created

# Enable SQL logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('django.db.backends')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

# Patch Bill.calculate_totals to log execution
original_calculate_totals = Bill.calculate_totals

call_count = 0

def logged_calculate_totals(self):
    global call_count
    call_count += 1
    print(f"\n{'='*60}")
    print(f"calculate_totals() CALL #{call_count} for Bill {self.bill_number}")
    print(f"  BEFORE: paid_amount = {self.paid_amount}")
    
    # Show call stack
    import traceback
    print("  Call stack:")
    for line in traceback.format_stack()[:-1]:
        if 'site-packages' not in line and 'django' not in line:
            print(f"    {line.strip()}")
    
    result = original_calculate_totals(self)
    print(f"  AFTER: paid_amount = {self.paid_amount}")
    print(f"{'='*60}\n")
    return result

Bill.calculate_totals = logged_calculate_totals

# Now simulate creating a settlement
print("Creating test bill...")
from shops.models import Shop
from accounts.models import User

shop = Shop.objects.first()
user = User.objects.first()

# Create a test bill
bill = Bill.objects.create(
    shop=shop,
    sales_rep=user,
    bill_status='confirmed',
    subtotal=Decimal('900'),
    total_amount=Decimal('900'),
    paid_amount=Decimal('0'),
    balance_amount=Decimal('900')
)
print(f"Created Bill {bill.bill_number} with total Rs. 900\n")

# Create a settlement
print("Creating settlement...")
settlement = SalesAccountSettlement(
    settlement_number=f"TEST-{bill.id}",
    shop=shop,
    bill=bill,
    settlement_method='cash',
    amount=Decimal('900'),
    settlement_status='completed',
    received_by=user,
    verified_by=user
)

print("\nCalling settlement.save()...")
settlement.save()

print(f"\n{'='*60}")
print("FINAL RESULT:")
bill.refresh_from_db()
print(f"Bill {bill.bill_number}:")
print(f"  paid_amount: Rs. {bill.paid_amount}")
print(f"  Expected: Rs. 900")
print(f"  calculate_totals() was called {call_count} times")
print(f"{'='*60}")

# Cleanup
settlement.delete()
bill.delete()
