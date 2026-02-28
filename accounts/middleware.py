"""
Tenant Access Middleware

Ensures authenticated users can only access their assigned tenant's subdomain.
- Platform admins/superusers can access any tenant
- Regular users must match the tenant they're assigned to
- Public schema (localhost) allows all authenticated users (backward compat)
- Login/logout pages are always accessible
- **Deactivated tenants** are fully blocked: users are logged out and shown
  a suspension message; the login page itself shows the error.

Also stores the current request in thread-local storage so that
tenant_utils can scope shared-model queries by the logged-in user's tenant
when on the public schema.
"""

import threading

from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect, render
from django.db import connection


# ── Thread-local request storage ─────────────────────────────────────────
_thread_locals = threading.local()


def get_current_request():
    """Return the current request stored by CurrentRequestMiddleware."""
    return getattr(_thread_locals, 'request', None)


def get_current_user():
    """
    Return the authenticated user from the current request, or None.
    Used by tenant_utils to scope shared-model queries on the public schema.
    """
    request = get_current_request()
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    return None


class TenantAccessMiddleware:
    """
    Restricts authenticated users to their assigned tenant subdomain.
    Must be placed AFTER AuthenticationMiddleware in MIDDLEWARE.
    """
    
    # URLs that are always accessible (login, logout, static)
    EXEMPT_PATHS = ('/login/', '/logout/', '/admin/', '/static/', '/media/')
    # Paths that are always allowed even on deactivated tenants
    ALWAYS_ALLOWED_PATHS = ('/logout/', '/static/', '/media/')
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Store request in thread-local for tenant_utils fallback
        _thread_locals.request = request

        # Get current tenant from django-tenants middleware
        tenant = getattr(connection, 'tenant', None)

        # ── Block deactivated tenant subdomains ──────────────────────
        if tenant and tenant.schema_name != 'public':
            if not getattr(tenant, 'is_active', True):
                # Always allow logout and static files
                if any(request.path.startswith(p) for p in self.ALWAYS_ALLOWED_PATHS):
                    return self.get_response(request)

                # Log out any authenticated user on a suspended tenant
                if hasattr(request, 'user') and request.user.is_authenticated:
                    logout(request)

                # Show suspended page (renders login template with error)
                messages.error(
                    request,
                    'This distributor account has been suspended. '
                    'Please contact the platform administrator.'
                )
                return redirect('login')

        # Skip check for unauthenticated users (they'll hit login page)
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip check for exempt paths (login, logout, etc.)
        if any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
            return self.get_response(request)
        
        if not tenant:
            return self.get_response(request)
        
        # Public schema — route to user's tenant schema so ALL model
        # queries (Shop, Product, Bill, etc.) hit the correct schema
        # instead of the legacy public-schema tables.
        if tenant.schema_name == 'public':
            user = request.user
            user_tenant = getattr(user, 'tenant', None)

            # Block users whose tenant is deactivated even on public schema
            if user_tenant and not user_tenant.is_active:
                platform_paths = ('/platform/', '/admin/')
                if not any(request.path.startswith(p) for p in platform_paths):
                    logout(request)
                    messages.error(
                        request,
                        'Your distributor account has been suspended. '
                        'Please contact the platform administrator.'
                    )
                    return redirect('login')

            # Skip schema switch for platform admin pages & django admin
            platform_paths = ('/platform/', '/admin/')
            if user_tenant and not any(request.path.startswith(p) for p in platform_paths):
                connection.set_tenant(user_tenant)
            return self.get_response(request)
        
        # Platform admins and superusers can access any tenant
        user = request.user
        if user.is_superuser or getattr(user, 'is_platform_admin', False):
            return self.get_response(request)
        
        # Check if user belongs to this tenant
        user_tenant = getattr(user, 'tenant', None)
        if user_tenant and user_tenant.pk == tenant.pk:
            return self.get_response(request)
        
        # User does not belong to this tenant — log them out and show error
        logout(request)
        messages.error(
            request,
            'Access denied. Your account is not registered with this distributor.'
        )
        return redirect('login')
