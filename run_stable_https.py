#!/usr/bin/env python
"""
Stable HTTPS server runner that avoids werkzeug reloader issues.
Fixes compatibility between django-extensions runserver_plus and werkzeug 2.3+
"""
import os
import sys
import django

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')

# Clean any leftover werkzeug env vars
os.environ.pop('WERKZEUG_RUN_MAIN', None)
os.environ.pop('WERKZEUG_SERVER_FD', None)

# Setup Django
django.setup()

# Monkey-patch werkzeug to fix the WERKZEUG_SERVER_FD KeyError.
# The issue: django-extensions' runserver_plus sets WERKZEUG_RUN_MAIN='true'
# when --noreload is used, but werkzeug 2.3+ then expects WERKZEUG_SERVER_FD.
# Fix: Override is_running_from_reloader to always return False.
import werkzeug.serving
werkzeug.serving.is_running_from_reloader = lambda: False

# Also patch it in werkzeug._reloader if it exists
try:
    import werkzeug._reloader
    werkzeug._reloader.is_running_from_reloader = lambda: False
except (ImportError, AttributeError):
    pass

# Run the development server
if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    
    sys.argv = [
        'manage.py',
        'runserver_plus',
        '0.0.0.0:8000',
        '--cert-file', 'cert.pem',
        '--key-file', 'key.pem',
        '--noreload',
    ]
    
    execute_from_command_line(sys.argv)
