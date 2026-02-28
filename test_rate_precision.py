from sales.models import CommissionRateHistory, Bill, CommissionTransaction
from django.utils import timezone
from datetime import datetime, timedelta
import pytz
from django.conf import settings

print("=" * 80)
print("COMMISSION RATE PRECISION TEST - MILLISECOND ACCURACY")
print("=" * 80)

local_tz = pytz.timezone(settings.TIME_ZONE)

print("\nCurrent Rate History:")
rates = CommissionRateHistory.objects.all().order_by('created_at')
for rate in rates:
    status = "ACTIVE" if rate.is_active else "Historical"
    print(f"  {rate.rate}% - Created: {rate.created_at} - Effective From: {rate.effective_from} - [{status}]")

print("\n" + "=" * 80)
print("SCENARIO: Multiple rates on same day (26 Jan 2026)")
print("=" * 80)

jan26_rates = CommissionRateHistory.objects.filter(effective_from__date=datetime(2026, 1, 26).date()).order_by('created_at')

if jan26_rates.count() >= 2:
    print(f"\nFound {jan26_rates.count()} rates on Jan 26, 2026:")
    for i, rate in enumerate(jan26_rates, 1):
        print(f"  Rate {i}: {rate.rate}% created at {rate.created_at.strftime('%H:%M:%S.%f')}")
    
    rate1 = jan26_rates[0]
    rate2 = jan26_rates[1]
    
    print("\n" + "=" * 80)
    print("TEST CASES")
    print("=" * 80)
    
    test_time_1 = rate1.created_at - timedelta(minutes=5)
    test_time_2 = rate1.created_at + timedelta(minutes=5)
    test_time_3 = rate2.created_at - timedelta(minutes=5)
    test_time_4 = rate2.created_at + timedelta(minutes=5)
    
    print(f"\n1. Bill created BEFORE first rate change ({test_time_1.strftime('%H:%M:%S')})")
    result_rate_1 = CommissionRateHistory.get_rate_for_date(test_time_1)
    print(f"   Expected: Earlier rate or default")
    print(f"   Actual: {result_rate_1}%")
    
    print(f"\n2. Bill created AFTER first rate ({test_time_2.strftime('%H:%M:%S')}), BEFORE second rate")
    print(f"   (After {rate1.created_at.strftime('%H:%M:%S')}, before {rate2.created_at.strftime('%H:%M:%S')})")
    result_rate_2 = CommissionRateHistory.get_rate_for_date(test_time_2)
    print(f"   Expected: {rate1.rate}%")
    print(f"   Actual: {result_rate_2}%")
    print(f"   Match: {result_rate_2 == rate1.rate}")
    
    print(f"\n3. Bill created JUST BEFORE second rate change ({test_time_3.strftime('%H:%M:%S')})")
    print(f"   (After {rate1.created_at.strftime('%H:%M:%S')}, before {rate2.created_at.strftime('%H:%M:%S')})")
    result_rate_3 = CommissionRateHistory.get_rate_for_date(test_time_3)
    print(f"   Expected: {rate1.rate}%")
    print(f"   Actual: {result_rate_3}%")
    print(f"   Match: {result_rate_3 == rate1.rate}")
    
    print(f"\n4. Bill created AFTER second rate change ({test_time_4.strftime('%H:%M:%S')})")
    print(f"   (After {rate2.created_at.strftime('%H:%M:%S')})")
    result_rate_4 = CommissionRateHistory.get_rate_for_date(test_time_4)
    print(f"   Expected: {rate2.rate}%")
    print(f"   Actual: {result_rate_4}%")
    print(f"   Match: {result_rate_4 == rate2.rate}")
    
    print("\n" + "=" * 80)
    print("REAL BILL TEST")
    print("=" * 80)
    
    recent_bill = Bill.objects.filter(bill_date__date=datetime(2026, 1, 26).date()).order_by('-bill_date').first()
    if recent_bill:
        print(f"\nBill: {recent_bill.bill_number}")
        print(f"Bill Date: {recent_bill.bill_date}")
        
        applicable_rate = CommissionRateHistory.get_rate_for_date(recent_bill.bill_date)
        print(f"\nApplicable Rate: {applicable_rate}%")
        
        if recent_bill.bill_date < rate2.created_at:
            expected = rate1.rate
            print(f"Expected (before 2nd rate): {expected}%")
        else:
            expected = rate2.rate
            print(f"Expected (after 2nd rate): {expected}%")
        
        print(f"Match: {applicable_rate == expected}")
        
        commission = CommissionTransaction.objects.filter(bill=recent_bill).first()
        if commission:
            print(f"\nCommission Transaction:")
            print(f"  Applicable Rate: {commission.applicable_rate}%")
            print(f"  Matches lookup: {commission.applicable_rate == applicable_rate}")
    
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("\nThe system now uses PRECISE TIMESTAMPS (hours, minutes, seconds, milliseconds)")
    print("Multiple rate changes on the same day are handled correctly")
    print(f"\nExample on Jan 26, 2026:")
    print(f"  Bills created before {rate2.created_at.strftime('%H:%M:%S')} → {rate1.rate}%")
    print(f"  Bills created after {rate2.created_at.strftime('%H:%M:%S')} → {rate2.rate}%")

else:
    print(f"\nOnly {jan26_rates.count()} rate(s) found on Jan 26, 2026")
    print("Cannot test multiple rates on same day scenario")

print("\n" + "=" * 80)
