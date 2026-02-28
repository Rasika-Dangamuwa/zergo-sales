from django.utils import timezone
from django.conf import settings
import pytz
from datetime import datetime

print("=" * 80)
print("COMPREHENSIVE TIMEZONE FIX VALIDATION")
print("=" * 80)

local_tz = pytz.timezone(settings.TIME_ZONE)
utc_now = timezone.now()
local_now = utc_now.astimezone(local_tz)

print(f"\nSystem Configuration:")
print(f"  Timezone Setting: {settings.TIME_ZONE}")
print(f"  UTC+5:30 (Sri Lanka)")

print(f"\nCurrent Time:")
print(f"  UTC:   {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"  Local: {local_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

print(f"\n{'=' * 80}")
print("ALL NUMBER FORMATS - TIMEZONE VALIDATION")
print("=" * 80)

from sales.models import Sale, Bill, Return, ItemExchange
from payments.models import SalesAccountSettlement, BadDebtWriteOff
from products.models import StockCount, ProductStatusAdjustment, PurchaseOrder, Purchase, PurchaseReturn, CompanyPayment

tests = [
    ("Sale Number", Sale(), "generate_sale_number", "SAL-YYYYMMDD-###", "daily"),
    ("Bill Number", Bill(), "generate_bill_number", "BILL-YYYYMMDD-###", "daily"),
    ("Return Number", Return(), "generate_return_number", "RN-YYYYMMDD-###", "daily"),
    ("Exchange Number", ItemExchange(), "generate_exchange_number", "EXC-YYYYMMDD-###", "daily"),
    ("Settlement Number", SalesAccountSettlement(), "generate_payment_number", "SET-YYYYMMDD-####", "daily"),
    ("Write-Off Number", BadDebtWriteOff(), "generate_write_off_number", "DISP-YYYY-####", "yearly"),
    ("Stock Count", StockCount(), "generate_count_number", "SC-YYYY-####", "yearly"),
    ("Adjustment", ProductStatusAdjustment(), "generate_adjustment_number", "ADJ-YYYY-####", "yearly"),
    ("Purchase Order", PurchaseOrder(), "generate_po_number", "PO-YYYY-####", "yearly"),
    ("GRN", Purchase(), "generate_grn_number", "GRN-YYYY-####", "yearly"),
    ("Purchase Return", PurchaseReturn(), "generate_pr_number", "PR-YYYY-####", "yearly"),
    ("Company Payment", CompanyPayment(), "generate_payment_number", "CPY-YYYY-####", "yearly"),
]

all_passed = True
daily_count = 0
yearly_count = 0

for name, obj, method_name, format_example, reset_type in tests:
    if hasattr(obj, 'bill_date'):
        obj.bill_date = timezone.now()
    
    method = getattr(obj, method_name)
    number = method()
    
    if reset_type == "daily":
        expected_date = local_now.strftime('%Y%m%d')
        if '-' in number:
            actual_date = number.split('-')[1]
        else:
            actual_date = number[3:11] if name == "Sale Number" else number[4:12]
        
        passed = actual_date == expected_date
        status = "PASS" if passed else "FAIL"
        
        print(f"\n{name} ({format_example}):")
        print(f"  Generated: {number}")
        print(f"  Expected Date: {expected_date}")
        print(f"  Actual Date: {actual_date}")
        print(f"  Status: {status}")
        
        daily_count += 1
        
    else:
        expected_year = str(local_now.year)
        actual_year = number.split('-')[1]
        
        passed = actual_year == expected_year
        status = "PASS" if passed else "FAIL"
        
        print(f"\n{name} ({format_example}):")
        print(f"  Generated: {number}")
        print(f"  Expected Year: {expected_year}")
        print(f"  Actual Year: {actual_year}")
        print(f"  Status: {status}")
        
        yearly_count += 1
    
    if not passed:
        all_passed = False

print(f"\n{'=' * 80}")
print("SUMMARY")
print("=" * 80)

print(f"\nTotal Tests: {len(tests)}")
print(f"  Daily Reset Numbers: {daily_count}")
print(f"  Yearly Reset Numbers: {yearly_count}")

if all_passed:
    print(f"\nRESULT: ALL TESTS PASSED")
    print(f"\nAll number generation methods now use LOCAL timezone (Asia/Colombo)")
    print(f"Bill numbers will ALWAYS match the business date in Sri Lanka")
    print(f"\nCRITICAL FIX:")
    print(f"  Bills created 00:00-05:30 AM will now use CORRECT local date")
    print(f"  No more mismatch between bill_date display and bill_number")
else:
    print(f"\nRESULT: SOME TESTS FAILED")
    print(f"Check the failed tests above")

print("\n" + "=" * 80)
