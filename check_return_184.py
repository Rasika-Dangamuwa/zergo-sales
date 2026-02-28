import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()
from django_tenants.utils import schema_context

with schema_context('dist_zergo001'):
    from sales.models import Return
    r = Return.objects.get(pk=184)
    print(f'Return 184: num={r.return_number} date={r.return_date}')
    print()
    print('Recent returns:')
    for ret in Return.objects.order_by('-id')[:10]:
        print(f'  id={ret.pk} num={ret.return_number} date={ret.return_date}')
