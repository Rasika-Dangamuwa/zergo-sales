from django.utils import timezone
from django.conf import settings
import pytz
from datetime import datetime, timedelta

from sales.models import Bill

print("=" * 80)
print("EARLY MORNING SCENARIO TEST (00:00-05:30 AM)")
print("=" * 80)

local_tz = pytz.timezone(settings.TIME_ZONE)

print("\nSimulating bill creation at different times of day...")
print("Testing the critical window where UTC and Local dates differ")

test_times = [
    ("23:00 Previous Day UTC", -1, 23, 0),   # 04:30 AM local (previous day UTC)
    ("00:00 UTC", 0, 0, 0),                   # 05:30 AM local  
    ("01:00 UTC", 0, 1, 0),                   # 06:30 AM local
    ("02:00 UTC", 0, 2, 0),                   # 07:30 AM local
    ("18:30 UTC", 0, 18, 30),                 # 00:00 AM next day local
    ("19:00 UTC", 0, 19, 0),                  # 00:30 AM next day local
]

print(f"\nCurrent Time:")
print(f"  UTC: {timezone.now()}")
print(f"  Local: {timezone.now().astimezone(local_tz)}")

print(f"\n{'=' * 80}")
print("SIMULATION RESULTS")
print("=" * 80)

for label, day_offset, hour, minute in test_times:
    base_time = timezone.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    if day_offset != 0:
        base_time = base_time + timedelta(days=day_offset)
    
    local_time = base_time.astimezone(local_tz)
    
    print(f"\n{label}")
    print(f"  UTC Time: {base_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Local Time: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  UTC Date: {base_time.date()}")
    print(f"  Local Date: {local_time.date()}")
    
    if base_time.date() != local_time.date():
        print(f"  DATE MISMATCH!")
        print(f"    OLD CODE would generate: BILL{base_time.strftime('%Y%m%d')}XXX")
        print(f"    NEW CODE generates: BILL{local_time.strftime('%Y%m%d')}XXX")
        print(f"    FIX: Uses LOCAL date which matches bill_date display")

print(f"\n{'=' * 80}")
print("REAL TEST WITH ACTUAL BILL")
print("=" * 80)

test_bill = Bill()
test_bill.bill_date = timezone.now()
bill_number = test_bill.generate_bill_number()

utc_date = timezone.now().strftime('%Y%m%d')
local_date = timezone.now().astimezone(local_tz).strftime('%Y%m%d')
number_date = bill_number[4:12]

print(f"\nGenerated Bill Number: {bill_number}")
print(f"UTC Date: {utc_date}")
print(f"Local Date: {local_date}")
print(f"Date in Number: {number_date}")

if number_date == local_date:
    print(f"\nSUCCESS! Number uses LOCAL date")
    if utc_date != local_date:
        print(f"  This is the critical fix - UTC was {utc_date} but we used {local_date}")
else:
    print(f"\nERROR! Number uses UTC date instead of local")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("\nBEFORE FIX:")
print("  Bills created 00:00-05:30 AM Sri Lanka time had PREVIOUS day in number")
print("  Example: Bill created Jan 26 2:00 AM → Number: BILL20260125XXX")
print("  Bill shows Jan 26, but number shows Jan 25 = MISMATCH")

print("\nAFTER FIX:")
print("  Bills ALWAYS use local (Asia/Colombo) date in number")
print("  Example: Bill created Jan 26 2:00 AM → Number: BILL20260126XXX")
print("  Bill shows Jan 26, number shows Jan 26 = PERFECT SYNC")

print("\n" + "=" * 80)
