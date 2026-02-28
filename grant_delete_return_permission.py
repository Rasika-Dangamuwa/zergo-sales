"""
Grant sales.delete_return permission to all sales reps
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from sales.models import Return

User = get_user_model()

print("=" * 80)
print("GRANTING DELETE_RETURN PERMISSION TO SALES REPS")
print("=" * 80)

# Get the permission
content_type = ContentType.objects.get_for_model(Return)
try:
    delete_perm = Permission.objects.get(
        content_type=content_type,
        codename='delete_return'
    )
    print(f"\n✅ Found permission: {delete_perm.name} (codename: {delete_perm.codename})")
except Permission.DoesNotExist:
    print(f"\n❌ Permission 'delete_return' does not exist!")
    print(f"   Available Return permissions:")
    return_perms = Permission.objects.filter(content_type=content_type)
    for perm in return_perms:
        print(f"      - {perm.codename}: {perm.name}")
    exit()

# Get all sales reps
sales_reps = User.objects.filter(user_type='sales_rep')
print(f"\n👥 Found {sales_reps.count()} sales representatives")

# Grant permission to each sales rep
granted_count = 0
already_had = 0

for rep in sales_reps:
    if not rep.user_permissions.filter(id=delete_perm.id).exists():
        rep.user_permissions.add(delete_perm)
        print(f"   ✅ Granted to: {rep.get_full_name()} (ID: {rep.id})")
        granted_count += 1
    else:
        print(f"   ⏭️ Already has: {rep.get_full_name()} (ID: {rep.id})")
        already_had += 1

print(f"\n📊 SUMMARY:")
print(f"   Total Sales Reps: {sales_reps.count()}")
print(f"   Newly Granted: {granted_count}")
print(f"   Already Had Permission: {already_had}")

# Verify
print(f"\n🔍 VERIFICATION:")
for rep in sales_reps:
    has_perm = rep.has_perm('sales.delete_return')
    status = "✅" if has_perm else "❌"
    print(f"   {status} {rep.get_full_name()}: {has_perm}")

print("\n" + "=" * 80)
