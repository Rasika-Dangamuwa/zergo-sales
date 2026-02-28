"""
Context Processors for Business App

Makes distributor business profile and branding available globally
across all templates — including login page, navbar, sidebar.

Author: GitHub Copilot
Date: January 20, 2026  (updated February 25, 2026)
"""

from .models import DistributorProfile


def business_settings(request):
    """
    Add active business profile + branding helpers to every template context.

    Template usage examples:
        {{ business.business_name }}
        {{ brand_logo_url }}          ← safe URL or ''
        {{ brand_primary }}            ← '#667eea'
        {{ brand_secondary }}          ← '#764ba2'
        {{ navbar_bg }}                ← inline CSS for navbar background
        {{ navbar_title }}             ← short brand name for navbar
        {{ login_bg }}                 ← inline CSS for login page background
    """
    try:
        profile = DistributorProfile.get_active()

        # Resolve logo URLs safely
        logo_url = profile.logo.url if profile.logo else ''
        favicon_url = profile.favicon.url if profile.favicon else ''
        login_bg_image_url = profile.login_bg_image.url if profile.login_bg_image else ''

        # Navbar background CSS
        primary = profile.primary_color or '#667eea'
        secondary = profile.secondary_color or '#764ba2'
        style = getattr(profile, 'navbar_style', 'gradient')
        if style == 'solid':
            navbar_bg = f'background: {primary};'
        elif style == 'dark':
            navbar_bg = 'background: #1e1e2f;'
        else:
            navbar_bg = f'background: linear-gradient(135deg, {primary} 0%, {secondary} 100%);'

        # Login page background CSS
        login_style = getattr(profile, 'login_bg_style', 'gradient')
        if login_style == 'image' and login_bg_image_url:
            login_bg = f"background: url('{login_bg_image_url}') center/cover no-repeat;"
        elif login_style == 'solid':
            login_bg = f'background: {primary};'
        else:
            login_bg = f'background: linear-gradient(135deg, {primary} 0%, {secondary} 100%);'

        # Sidebar active style extra class
        sidebar_style = getattr(profile, 'sidebar_active_style', 'line')

        return {
            # Full profile object
            'business': profile,

            # Shortcut scalars (legacy compatibility)
            'business_name': profile.business_name,
            'business_phone': profile.primary_phone,
            'business_email': profile.primary_email,
            'business_address': profile.get_full_address(),
            'currency_symbol': profile.currency_symbol or 'Rs.',

            # Branding colours
            'brand_primary': primary,
            'brand_secondary': secondary,
            'brand_accent': profile.accent_color or '#f093fb',

            # Logo URLs (empty string when not set)
            'brand_logo_url': logo_url,
            'brand_favicon_url': favicon_url,

            # Navbar
            'navbar_title': getattr(profile, 'navbar_title', '') or profile.business_name,
            'navbar_icon': getattr(profile, 'navbar_icon', '') or 'fas fa-store',
            'navbar_brand_type': getattr(profile, 'navbar_brand_type', 'logo'),
            'navbar_bg': navbar_bg,

            # Login page
            'login_subtitle': getattr(profile, 'login_subtitle', '') or 'Sales Management System',
            'login_brand_type': getattr(profile, 'login_brand_type', 'logo'),
            'login_bg': login_bg,
            'login_bg_image_url': login_bg_image_url,

            # Sidebar
            'sidebar_active_style': sidebar_style,
        }
    except Exception:
        return {
            'business': None,
            'business_name': 'Zergo Distributors',
            'business_phone': '',
            'business_email': '',
            'business_address': '',
            'currency_symbol': 'Rs.',
            'brand_primary': '#667eea',
            'brand_secondary': '#764ba2',
            'brand_accent': '#f093fb',
            'brand_logo_url': '',
            'brand_favicon_url': '',
            'navbar_title': 'ZERGO',
            'navbar_icon': 'fas fa-store',
            'navbar_bg': 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);',
            'login_subtitle': 'Sales Management System',
            'login_bg': 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);',
            'login_bg_image_url': '',
            'sidebar_active_style': 'line',
        }
