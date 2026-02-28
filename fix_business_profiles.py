import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()
from django_tenants.utils import schema_context
from tenants.models import Distributor

for dist in Distributor.objects.exclude(schema_name='public'):
    with schema_context(dist.schema_name):
        from business.models import DistributorProfile
        if dist.schema_name != 'dist_zergo001':
            updated = DistributorProfile.objects.filter(
                business_name='Zergo Distributors'
            ).update(business_name=dist.name)
            if updated:
                print(f'{dist.schema_name}: Updated {updated} profile(s) to "{dist.name}"')
            else:
                print(f'{dist.schema_name}: OK (already correct)')
        else:
            print(f'{dist.schema_name}: Skipped (correct)')

# Verify
print('\nVerification:')
for dist in Distributor.objects.exclude(schema_name='public'):
    with schema_context(dist.schema_name):
        p = DistributorProfile.objects.filter(is_active=True).first()
        print(f'  {dist.schema_name}: business_name="{p.business_name if p else "NONE"}"')
