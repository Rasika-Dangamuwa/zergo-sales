"""
Find the return linked to settlement 76
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from payments.models import SalesAccountSettlement
from sales.models import Return

# Get settlement 76
settlement = SalesAccountSettlement.objects.filter(pk=76).first()

if settlement:
    print(f"\n{'='*80}")
    print(f"SETTLEMENT #{settlement.pk}: {settlement.settlement_number}")
    print(f"{'='*80}")
    print(f"Method: {settlement.settlement_method}")
    print(f"Amount: Rs. {settlement.amount}")
    
    if settlement.return_ref:
        return_obj = settlement.return_ref
        print(f"\nLinked Return:")
        print(f"  Return ID: {return_obj.pk}")
        print(f"  Return Number: {return_obj.return_number}")
        print(f"  Settlement Status: {return_obj.settlement_status}")
        print(f"  Settlement Method: {return_obj.settlement_method}")
        print(f"  Return Date: {return_obj.return_date}")
        print(f"  Created By: {return_obj.created_by.username if return_obj.created_by else 'N/A'}")
        print(f"  Is Verified: {return_obj.is_verified}")
        print(f"  Verified By: {return_obj.verified_by.username if return_obj.verified_by else 'N/A'}")
        
        print(f"\n  Return Detail URL: /sales/returns/{return_obj.pk}/")
        
        # Check if can be deleted
        from django.utils import timezone
        import pytz
        from django.conf import settings
        
        local_tz = pytz.timezone(settings.TIME_ZONE)
        return_created_date = return_obj.return_date.astimezone(local_tz).date()
        today = timezone.now().astimezone(local_tz).date()
        
        print(f"\n{'='*80}")
        print("CAN THIS RETURN BE DELETED?")
        print(f"{'='*80}")
        print(f"1. Is verified: {return_obj.is_verified} ({'❌ Cannot delete' if return_obj.is_verified else '✅ Can delete'})")
        print(f"2. Same day: {return_created_date == today} ({'✅ Created today' if return_created_date == today else f'❌ Created {return_created_date}'})")
        print(f"3. Has settlements: {SalesAccountSettlement.objects.filter(return_ref=return_obj).exists()}")
        
        if return_obj.is_verified:
            print("\n❌ CANNOT DELETE: Return has been verified (locked)")
        elif return_created_date != today:
            print(f"\n❌ CANNOT DELETE: Return created on {return_created_date}, not today ({today})")
            print("   Returns can only be deleted on the same day they were created.")
        else:
            print("\n✅ CAN DELETE: Return is unverified and created today")
    else:
        print("\n⚠️  No return linked to this settlement!")
else:
    print("Settlement 76 not found!")
