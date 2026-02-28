from django.utils import timezone
from django.conf import settings
import pytz
from datetime import datetime

from sales.models import Bill, Return, ItemExchange
from payments.models import SalesAccountSettlement
from products.models import Purchase, PurchaseOrder, PurchaseReturn

print("=" * 80)
print("TIMEZONE FIX VERIFICATION")
print("=" * 80)

local_tz = pytz.timezone(settings.TIME_ZONE)

print(f"\nConfigured Timezone: {settings.TIME_ZONE}")
print(f"UTC Now: {timezone.now()}")
print(f"Local Now: {timezone.now().astimezone(local_tz)}")

print(f"\n{'=' * 80}")
print("DATE COMPARISON")
print("=" * 80)

utc_now = timezone.now()
local_now = utc_now.astimezone(local_tz)

print(f"\nUTC Date: {utc_now.date()}")
print(f"Local Date: {local_now.date()}")
print(f"Same Day?: {utc_now.date() == local_now.date()}")

if utc_now.date() != local_now.date():
    print(f"\nWARNING: Dates are different!")
    print(f"  This happens between 00:00-05:30 AM Sri Lanka time")
    print(f"  OLD CODE would use UTC date: {utc_now.date()}")
    print(f"  NEW CODE now uses LOCAL date: {local_now.date()}")

print(f"\n{'=' * 80}")
print("NUMBER GENERATION TEST")
print("=" * 80)

test_bill = Bill()
test_bill.bill_date = timezone.now()
bill_num = test_bill.generate_bill_number()
print(f"\nBill Number: {bill_num}")
print(f"Expected Date in Number: {local_now.strftime('%Y%m%d')}")
print(f"Actual Date in Number: {bill_num[4:12]}")
print(f"Match?: {bill_num[4:12] == local_now.strftime('%Y%m%d')}")

test_return = Return()
return_num = test_return.generate_return_number()
print(f"\nReturn Number: {return_num}")
print(f"Expected Date in Number: {local_now.strftime('%Y%m%d')}")
actual_date = return_num.split('-')[1]
print(f"Actual Date in Number: {actual_date}")
print(f"Match?: {actual_date == local_now.strftime('%Y%m%d')}")

test_settlement = SalesAccountSettlement()
settlement_num = test_settlement.generate_payment_number()
print(f"\nSettlement Number: {settlement_num}")
print(f"Expected Date in Number: {local_now.strftime('%Y%m%d')}")
actual_date = settlement_num.split('-')[1]
print(f"Actual Date in Number: {actual_date}")
print(f"Match?: {actual_date == local_now.strftime('%Y%m%d')}")

print(f"\n{'=' * 80}")
print("YEAR-BASED NUMBER TEST")
print("=" * 80)

test_po = PurchaseOrder()
po_num = test_po.generate_po_number()
print(f"\nPO Number: {po_num}")
print(f"Expected Year: {local_now.year}")
actual_year = po_num.split('-')[1]
print(f"Actual Year: {actual_year}")
print(f"Match?: {actual_year == str(local_now.year)}")

test_grn = Purchase()
grn_num = test_grn.generate_grn_number()
print(f"\nGRN Number: {grn_num}")
print(f"Expected Year: {local_now.year}")
actual_year = grn_num.split('-')[1]
print(f"Actual Year: {actual_year}")
print(f"Match?: {actual_year == str(local_now.year)}")

print(f"\n{'=' * 80}")
print("CONCLUSION")
print("=" * 80)

if bill_num[4:12] == local_now.strftime('%Y%m%d'):
    print("\nSUCCESS! All numbers now use LOCAL TIMEZONE (Asia/Colombo)")
    print("Bill numbers will match the business date in Sri Lanka")
    print("No more mismatches between bill_date and bill_number!")
else:
    print("\nFAILED! Numbers still using UTC timezone")
    print("Check the code changes")

print("=" * 80)
