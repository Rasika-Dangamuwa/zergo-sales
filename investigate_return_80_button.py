"""
Investigate why cancel button not showing for Return 80 (RN-20260125-008)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import Return
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from datetime import datetime
import zoneinfo

User = get_user_model()

print("=" * 80)
print("RETURN 80 (RN-20260125-008) - CANCEL BUTTON INVESTIGATION")
print("=" * 80)

try:
    return_obj = Return.objects.get(return_number='RN-20260125-008')
    
    print(f"\n📋 RETURN DETAILS:")
    print(f"   ID: {return_obj.id}")
    print(f"   Return Number: {return_obj.return_number}")
    print(f"   Shop: {return_obj.shop.shop_name}")
    print(f"   Created By: {return_obj.created_by.get_full_name()} (ID: {return_obj.created_by.id})")
    print(f"   User Type: {return_obj.created_by.user_type}")
    print(f"   Return Date: {return_obj.return_date}")
    print(f"   Created At: {return_obj.created_at}")
    print(f"   Settlement Status: {return_obj.settlement_status}")
    print(f"   Settlement Method: {return_obj.settlement_method}")
    print(f"   Is Verified: {return_obj.is_verified}")
    
    # Check same-day logic
    local_tz = zoneinfo.ZoneInfo(settings.TIME_ZONE)
    return_created_date = return_obj.return_date.astimezone(local_tz).date()
    today = timezone.now().astimezone(local_tz).date()
    is_same_day = (return_created_date == today)
    
    print(f"\n⏰ DATE CHECKS:")
    print(f"   Return Date (TZ aware): {return_obj.return_date}")
    print(f"   Return Date (local date): {return_created_date}")
    print(f"   Today (local date): {today}")
    print(f"   Is Same Day: {is_same_day}")
    
    # Check permissions for the creator
    creator = return_obj.created_by
    print(f"\n🔐 PERMISSION CHECKS (for creator: {creator.get_full_name()}):")
    print(f"   User Type: {creator.user_type}")
    print(f"   Is Sales Rep: {creator.is_sales_rep}")
    print(f"   Is Office Staff: {creator.is_office_staff}")
    print(f"   Is Admin: {creator.is_superuser}")
    
    # Check specific permission
    has_delete_perm = creator.has_perm('sales.delete_return')
    print(f"   Has 'sales.delete_return' permission: {has_delete_perm}")
    
    # Check all permissions for this user
    print(f"\n   All User Permissions:")
    user_perms = creator.get_all_permissions()
    sales_perms = [p for p in user_perms if 'sales' in p]
    if sales_perms:
        for perm in sales_perms:
            print(f"      - {perm}")
    else:
        print(f"      - NO SALES PERMISSIONS FOUND!")
    
    # Check button display conditions
    print(f"\n🔍 BUTTON DISPLAY CONDITIONS:")
    print(f"   ✓ Has delete_return permission: {has_delete_perm}")
    print(f"   ✓ Return not verified: {not return_obj.is_verified}")
    print(f"   ✓ Return not cancelled: {return_obj.settlement_status != 'cancelled'}")
    print(f"   ✓ Is sales rep: {creator.is_sales_rep}")
    print(f"   ✓ Is same day return: {is_same_day}")
    
    # Final verdict
    print(f"\n📊 FINAL VERDICT:")
    if has_delete_perm and not return_obj.is_verified and return_obj.settlement_status != 'cancelled':
        if creator.is_sales_rep:
            if is_same_day:
                print(f"   ✅ CANCEL BUTTON SHOULD BE VISIBLE (Active - Clickable)")
            else:
                print(f"   ⚠️ CANCEL BUTTON SHOULD BE DISABLED (Not same day)")
        else:
            print(f"   ✅ CANCEL BUTTON SHOULD BE VISIBLE (Office/Admin - No date restriction)")
    else:
        print(f"\n   ❌ CANCEL BUTTON SHOULD NOT SHOW:")
        if not has_delete_perm:
            print(f"      - Missing 'sales.delete_return' permission")
        if return_obj.is_verified:
            print(f"      - Return is verified")
        if return_obj.settlement_status == 'cancelled':
            print(f"      - Return already cancelled")
    
    # Check if there are other sales reps to compare
    print(f"\n👥 OTHER SALES REPS (for comparison):")
    other_reps = User.objects.filter(user_type='sales_rep').exclude(id=creator.id)[:3]
    for rep in other_reps:
        print(f"   - {rep.get_full_name()} (ID: {rep.id})")
        print(f"     Has delete_return: {rep.has_perm('sales.delete_return')}")
        
except Return.DoesNotExist:
    print(f"\n❌ Return RN-20260125-008 not found! Searching for Return ID 80...")
    try:
        return_obj = Return.objects.get(pk=80)
        print(f"   Found Return ID 80: {return_obj.return_number}")
    except Return.DoesNotExist:
        print(f"   Return ID 80 also not found!")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
