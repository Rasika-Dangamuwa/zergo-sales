import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from django.db.models.signals import post_save
from payments.models import SalesAccountSettlement
import inspect

print('=== SIGNAL HANDLERS FOR SalesAccountSettlement ===\n')

# Get all registered signal handlers
handlers = post_save._live_receivers(SalesAccountSettlement)
print(f'Found {len(list(handlers))} post_save signal handlers\n')

# Re-get the iterator since we consumed it
handlers = post_save._live_receivers(SalesAccountSettlement)
for receiver_ref in handlers:
    # receiver_ref is a weakref
    try:
        receiver_func = receiver_ref[1]()  # Dereference the weakref
        if receiver_func:
            print(f'Handler: {receiver_func.__name__}')
            print(f'  Module: {receiver_func.__module__}')
            print(f'  File: {inspect.getfile(receiver_func)}')
            
            # Try to get source
            try:
                source_lines = inspect.getsource(receiver_func).split('\n')[:10]
                print('  First 10 lines:')
                for line in source_lines:
                    print(f'    {line}')
            except:
                pass
            print()
    except Exception as e:
        print(f'Error processing receiver: {e}\n')
