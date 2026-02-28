import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionRateHistory
from django.utils import timezone
import pytz

# Get local timezone
local_tz = pytz.timezone('Asia/Colombo')

print("Updating commission rate datetimes...")
print("=" * 60)

rates = CommissionRateHistory.objects.all().order_by('id')

for rate in rates:
    # Convert existing date to datetime at midnight local time
    if hasattr(rate.effective_from, 'date'):
        # Already a datetime
        print(f"Rate {rate.id}: Already datetime - {rate.effective_from}")
    else:
        # It's a date, convert to datetime using created_at time if possible
        # Otherwise use midnight
        if rate.created_at:
            # Use the time from created_at with the date from effective_from
            local_created = rate.created_at.astimezone(local_tz)
            new_datetime = local_tz.localize(
                rate.effective_from.replace(
                    hour=local_created.hour,
                    minute=local_created.minute,
                    second=local_created.second,
                    microsecond=local_created.microsecond
                )
            )
        else:
            # Fallback to midnight
            new_datetime = local_tz.localize(
                rate.effective_from.replace(hour=0, minute=0, second=0, microsecond=0)
            )
        
        rate.effective_from = new_datetime
        print(f"Rate {rate.id}: Updated effective_from to {new_datetime}")
    
    # Handle effective_to
    if rate.effective_to:
        if hasattr(rate.effective_to, 'date'):
            print(f"Rate {rate.id}: effective_to already datetime - {rate.effective_to}")
        else:
            # Convert to end of day (23:59:59.999999)
            new_datetime = local_tz.localize(
                rate.effective_to.replace(hour=23, minute=59, second=59, microsecond=999999)
            )
            rate.effective_to = new_datetime
            print(f"Rate {rate.id}: Updated effective_to to {new_datetime}")
    
    rate.save()

print("=" * 60)
print("Update complete!")
print()
print("Updated rates:")
for rate in CommissionRateHistory.objects.all().order_by('-created_at'):
    status = "Active" if rate.is_active else "Historical"
    print(f"{rate.rate}% ({status})")
    print(f"  From: {rate.effective_from}")
    print(f"  To: {rate.effective_to or 'Ongoing'}")
    print(f"  Created: {rate.created_at}")
    print()
