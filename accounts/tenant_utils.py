"""
Tenant-aware query helpers for shared-app models.

Since the `accounts` app is in SHARED_APPS, its tables (User, AdvanceRequest,
UserMoneyAccount, MoneyTransaction) live in the `public` schema and are visible
from all tenant subdomains. These helpers ensure queries are properly scoped
to the current tenant.

Usage:
    from accounts.tenant_utils import get_tenant_users, get_tenant_filter
    
    # Get users for the current tenant
    users = get_tenant_users()
    
    # Filter any shared-app queryset by tenant
    advances = AdvanceRequest.objects.filter(**get_tenant_filter('user__tenant'))
"""

from django.db import connection


def get_current_tenant():
    """
    Get the current tenant from django-tenants middleware.
    Returns None if on the public schema or if tenant middleware hasn't run.
    """
    tenant = getattr(connection, 'tenant', None)
    if tenant and tenant.schema_name != 'public':
        return tenant
    return None


def _get_user_tenant():
    """
    Fallback for public-schema queries: return the logged-in user's tenant.
    Platform admins / superusers (no tenant) get None → no extra filtering.
    """
    from accounts.middleware import get_current_user
    user = get_current_user()
    if user and getattr(user, 'tenant_id', None):
        return user.tenant
    return None


def get_tenant_filter(field_path='tenant'):
    """
    Return a dict suitable for .filter(**kwargs) to scope queries by tenant.
    
    On tenant subdomains: returns {field_path: current_tenant}
    On public domain: falls back to logged-in user's tenant.
                      Platform admins (no tenant) get {} → unfiltered.
    
    Args:
        field_path: The FK path to the tenant field (e.g., 'tenant', 'user__tenant')
    
    Returns:
        dict for use in .filter(**result)
    
    Example:
        # Filter users by tenant
        User.objects.filter(**get_tenant_filter('tenant'))
        
        # Filter advance requests by tenant  
        AdvanceRequest.objects.filter(**get_tenant_filter('user__tenant'))
    """
    tenant = get_current_tenant()
    if tenant:
        return {field_path: tenant}
    # Public schema: scope to logged-in user's tenant
    tenant = _get_user_tenant()
    if tenant:
        return {field_path: tenant}
    return {}


def get_tenant_users():
    """
    Get User queryset scoped to the current tenant.
    On public schema, scopes to the logged-in user's tenant.
    Platform admins (no tenant) see all users.
    """
    from accounts.models import User
    tenant = get_current_tenant()
    if tenant:
        return User.objects.filter(tenant=tenant)
    # Public schema: scope to logged-in user's tenant
    tenant = _get_user_tenant()
    if tenant:
        return User.objects.filter(tenant=tenant)
    return User.objects.all()
