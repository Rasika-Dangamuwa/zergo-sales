from sales.models import CommissionRateHistory
from datetime import datetime
from django.utils import timezone

print("=" * 80)
print("COMMISSION RATE MILLISECOND PRECISION TEST")
print("=" * 80)

r1 = CommissionRateHistory.objects.get(rate=4.00)
r2 = CommissionRateHistory.objects.get(rate=5.00, is_active=True)

print(f"\nRate History on Jan 26, 2026:")
print(f"  4.00% created at: {r1.created_at}")
print(f"  5.00% created at: {r2.created_at}")

time_diff = (r2.created_at - r1.created_at).total_seconds()
print(f"\nTime difference: {time_diff:.0f} seconds ({time_diff/60:.1f} minutes)")

print(f"\n{'=' * 80}")
print("TEST: Rate lookup with precise timestamps")
print("=" * 80)

t1 = r1.created_at + timezone.timedelta(minutes=10)
t2 = r2.created_at - timezone.timedelta(minutes=5)
t3 = r2.created_at + timezone.timedelta(minutes=10)

result1 = CommissionRateHistory.get_rate_for_date(t1)
result2 = CommissionRateHistory.get_rate_for_date(t2)
result3 = CommissionRateHistory.get_rate_for_date(t3)

print(f"\n1. 10 minutes AFTER 4.00% created ({t1.strftime('%H:%M:%S')})")
print(f"   Expected: 4.00% (before 5.00% was created)")
print(f"   Actual: {result1}%")
print(f"   PASS" if result1 == 4.00 else "   FAIL")

print(f"\n2. 5 minutes BEFORE 5.00% created ({t2.strftime('%H:%M:%S')})")
print(f"   Expected: 4.00% (still before 5.00% was created)")
print(f"   Actual: {result2}%")
print(f"   PASS" if result2 == 4.00 else "   FAIL")

print(f"\n3. 10 minutes AFTER 5.00% created ({t3.strftime('%H:%M:%S')})")
print(f"   Expected: 5.00% (after 5.00% was created)")
print(f"   Actual: {result3}%")
print(f"   PASS" if result3 == 5.00 else "   FAIL")

print(f"\n{'=' * 80}")
print("CONCLUSION")
print("=" * 80)

if result1 == 4.00 and result2 == 4.00 and result3 == 5.00:
    print("\nSUCCESS! System now uses PRECISE TIMESTAMPS")
    print("Multiple rate changes on same day work correctly")
    print(f"\nOn Jan 26, 2026:")
    print(f"  Before {r2.created_at.strftime('%H:%M:%S')} -> 4.00%")
    print(f"  After {r2.created_at.strftime('%H:%M:%S')} -> 5.00%")
else:
    print("\nFAILED - Check logic")

print("=" * 80)
