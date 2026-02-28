"""
Check why settlement 76 doesn't show cancel button
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from payments.models import SalesAccountSettlement
from django.utils import timezone

# Get settlement 76
settlement = SalesAccountSettlement.objects.filter(pk=76).first()

if settlement:
    print(f"\n{'='*80}")
    print(f"SETTLEMENT #{settlement.pk}: {settlement.settlement_number}")
    print(f"{'='*80}")
    print(f"Status: {settlement.settlement_status}")
    print(f"Method: {settlement.settlement_method}")
    print(f"Amount: Rs. {settlement.amount}")
    print(f"Settlement Date: {settlement.settlement_date}")
    print(f"Settlement Date (date only): {settlement.settlement_date.date()}")
    print(f"Today: {timezone.now().date()}")
    print(f"Is same day?: {settlement.settlement_date.date() == timezone.now().date()}")
    print(f"Received by: {settlement.received_by.username if settlement.received_by else 'N/A'}")
    print(f"{'='*80}\n")
    
    print("Cancel Button Conditions:")
    print(f"1. Status not cancelled: {settlement.settlement_status != 'cancelled'}")
    print(f"2. Method not return_adjustment: {settlement.settlement_method != 'return_adjustment'}")
    print(f"3. Is same day: {settlement.settlement_date.date() == timezone.now().date()}")
    print()
    
    if settlement.settlement_status == 'cancelled':
        print("❌ Button hidden because settlement is already cancelled")
    elif settlement.settlement_method == 'return_adjustment':
        print("❌ Button hidden because this is a return adjustment settlement")
    elif settlement.settlement_date.date() != timezone.now().date():
        print(f"❌ Button hidden because settlement is from {settlement.settlement_date.date()}, not today ({timezone.now().date()})")
        print("   NOTE: Sales reps can only cancel same-day settlements")
        print("   Office/Admin users can cancel any settlement")
    else:
        print("✅ Cancel button should be visible!")
else:
    print("Settlement 76 not found!")
