"""
Business Settings Views — Full Rebuild

Unified tabbed settings page with inline AJAX section saves, progress bar,
branding live preview, and inline bank account / address management.

Author: GitHub Copilot
Date: January 30, 2026
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import DistributorProfile, BankAccount, BusinessAddress


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SECTION_FIELDS = {
    'basic': [
        'business_name', 'trade_name', 'tagline', 'description',
        'business_type', 'established_date',
    ],
    'registration': [
        'business_registration_number', 'tax_id', 'vat_number',
        'svat_number', 'trade_license_number', 'import_export_license',
    ],
    'contact': [
        'primary_phone', 'secondary_phone', 'mobile_phone', 'fax_number',
        'primary_email', 'secondary_email', 'support_email', 'accounts_email',
        'website',
    ],
    'address': [
        'address_line1', 'address_line2', 'city', 'district',
        'postal_code', 'country', 'latitude', 'longitude',
    ],
    'social': [
        'facebook_url', 'instagram_url', 'twitter_url',
        'linkedin_url', 'whatsapp_number',
    ],
    'branding': [
        'logo', 'logo_receipt', 'logo_document', 'favicon',
        'primary_color', 'secondary_color', 'accent_color',
    ],
    'operational': [
        'currency_code', 'currency_symbol', 'fiscal_year_start_month',
        'default_payment_terms_days', 'business_hours',
    ],
    'receipt': [
        'receipt_footer_line1', 'receipt_footer_line2', 'receipt_footer_line3',
        'terms_and_conditions', 'return_policy', 'warranty_info',
    ],
    'display': [
        'show_logo_on_receipts', 'show_tagline', 'show_address_on_receipts',
        'show_contact_on_receipts', 'show_social_media', 'show_tax_info',
    ],
    'appearance': [
        'navbar_title', 'navbar_brand_type', 'navbar_style', 'navbar_icon',
        'login_subtitle', 'login_brand_type', 'login_bg_style', 'login_bg_image',
        'sidebar_active_style',
    ],
    'documents': [
        'po_terms_and_conditions', 'po_show_signatures', 'po_show_terms',
        'authorized_signature', 'authorized_signatory_name', 'authorized_signatory_designation',
    ],
}

BOOLEAN_FIELDS = {
    'show_logo_on_receipts', 'show_tagline', 'show_address_on_receipts',
    'show_contact_on_receipts', 'show_social_media', 'show_tax_info',
    'po_show_signatures', 'po_show_terms',
}

FILE_FIELDS = {'logo', 'logo_receipt', 'logo_document', 'favicon', 'login_bg_image', 'authorized_signature'}

INTEGER_FIELDS = {'fiscal_year_start_month', 'default_payment_terms_days'}

REQUIRED_FIELDS = {'business_name', 'primary_phone', 'primary_email', 'address_line1', 'city'}


def _is_field_filled(profile, field_name):
    """Check if a field has a meaningful value (handles booleans, files, 0 correctly)."""
    val = getattr(profile, field_name, None)
    if val is None:
        return False
    if isinstance(val, bool):
        return True  # Booleans are always "set" (True or False is a choice)
    if isinstance(val, (int, float)):
        return True  # Numbers like 0 or fiscal_year_start_month=1 count as filled
    if hasattr(val, 'name'):  # FileField / ImageField
        return bool(val.name)
    return bool(val)


def _calculate_completion(profile):
    """Calculate profile completion percentage based on filled fields."""
    important_fields = [
        'business_name', 'trade_name', 'tagline', 'business_type',
        'business_registration_number', 'tax_id',
        'primary_phone', 'primary_email', 'website',
        'address_line1', 'city', 'district', 'postal_code',
        'logo', 'primary_color',
        'currency_code', 'currency_symbol', 'business_hours',
        'receipt_footer_line1',
    ]
    filled = sum(1 for f in important_fields if _is_field_filled(profile, f))
    return int((filled / len(important_fields)) * 100)


def _section_completion(profile, section_name):
    """Return (filled, total) for a section."""
    fields = SECTION_FIELDS.get(section_name, [])
    total = len(fields)
    filled = sum(1 for f in fields if _is_field_filled(profile, f))
    return filled, total


# ---------------------------------------------------------------------------
# Main Settings View
# ---------------------------------------------------------------------------

@login_required
def business_settings(request):
    """
    Unified tabbed business settings page.
    Serves both the display and inline-edit forms for every section.
    """
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied. Only admin and office staff can manage business settings.')
        return redirect('dashboard')

    profile = DistributorProfile.get_active()
    bank_accounts = profile.bank_accounts.all()
    addresses = profile.additional_addresses.all()

    completion = _calculate_completion(profile)
    section_stats = {}
    for sec in SECTION_FIELDS:
        f, t = _section_completion(profile, sec)
        section_stats[sec] = {'filled': f, 'total': t, 'pct': int((f / t) * 100) if t else 0}

    context = {
        'profile': profile,
        'bank_accounts': bank_accounts,
        'addresses': addresses,
        'completion': completion,
        'section_stats': section_stats,
        'business_types': DistributorProfile._meta.get_field('business_type').choices,
        'account_types': BankAccount._meta.get_field('account_type').choices,
        'address_types': BusinessAddress.ADDRESS_TYPE_CHOICES,
        'fiscal_months': DistributorProfile._meta.get_field('fiscal_year_start_month').choices,
        'navbar_styles': DistributorProfile.NAVBAR_STYLE_CHOICES,
        'login_bg_styles': DistributorProfile._meta.get_field('login_bg_style').choices,
        'sidebar_styles': DistributorProfile._meta.get_field('sidebar_active_style').choices,
    }
    return render(request, 'business/settings.html', context)


# ---------------------------------------------------------------------------
# AJAX – Save a whole section of the profile
# ---------------------------------------------------------------------------

@login_required
@require_POST
def save_section(request, section):
    """Save one section of the profile via AJAX. Returns JSON."""
    if request.user.user_type not in ['admin', 'office']:
        return JsonResponse({'ok': False, 'error': 'Access denied'}, status=403)

    fields = SECTION_FIELDS.get(section)
    if fields is None:
        return JsonResponse({'ok': False, 'error': 'Invalid section'}, status=400)

    profile = DistributorProfile.get_active()

    errors = {}
    for f in fields:
        if f in FILE_FIELDS:
            if f in request.FILES:
                setattr(profile, f, request.FILES[f])
            continue

        raw = request.POST.get(f)

        if f in BOOLEAN_FIELDS:
            setattr(profile, f, raw == 'on' or raw == 'true')
            continue

        if f in INTEGER_FIELDS:
            try:
                setattr(profile, f, int(raw) if raw else None)
            except (ValueError, TypeError):
                errors[f] = 'Must be a number'
            continue

        # For required text/email fields
        if f in REQUIRED_FIELDS and not raw:
            errors[f] = 'This field is required'
            continue

        setattr(profile, f, raw or '')

    if errors:
        return JsonResponse({'ok': False, 'errors': errors}, status=400)

    try:
        profile.save()
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

    completion = _calculate_completion(profile)
    filled, total = _section_completion(profile, section)
    return JsonResponse({
        'ok': True,
        'completion': completion,
        'section_pct': int((filled / total) * 100) if total else 0,
    })


# ---------------------------------------------------------------------------
# Legacy edit page (kept as fallback for non-JS browsers)
# ---------------------------------------------------------------------------

@login_required
def edit_business_profile(request):
    """Full-page edit form (fallback)."""
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    profile = DistributorProfile.get_active()

    if request.method == 'POST':
        for section, fields in SECTION_FIELDS.items():
            for f in fields:
                if f in FILE_FIELDS:
                    if f in request.FILES:
                        setattr(profile, f, request.FILES[f])
                    continue
                if f in BOOLEAN_FIELDS:
                    setattr(profile, f, request.POST.get(f) == 'on')
                    continue
                if f in INTEGER_FIELDS:
                    try:
                        setattr(profile, f, int(request.POST.get(f)) if request.POST.get(f) else None)
                    except (ValueError, TypeError):
                        pass
                    continue
                setattr(profile, f, request.POST.get(f, '') or '')

        try:
            profile.save()
            messages.success(request, 'Business profile updated successfully!')
            return redirect('business:settings')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')

    return render(request, 'business/edit_profile.html', {'profile': profile})


# ---------------------------------------------------------------------------
# Bank Accounts – AJAX CRUD
# ---------------------------------------------------------------------------

@login_required
@require_POST
def add_bank_account(request):
    """Add a new bank account (AJAX or form POST)."""
    if request.user.user_type not in ['admin', 'office']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'Access denied'}, status=403)
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    profile = DistributorProfile.get_active()
    account = BankAccount(distributor=profile)
    account.account_name = request.POST.get('account_name', '')
    account.bank_name = request.POST.get('bank_name', '')
    account.branch_name = request.POST.get('branch_name', '')
    account.account_number = request.POST.get('account_number', '')
    account.account_type = request.POST.get('account_type', 'current')
    account.swift_code = request.POST.get('swift_code', '')
    account.iban = request.POST.get('iban', '')
    account.currency = request.POST.get('currency', 'LKR')
    account.is_primary = request.POST.get('is_primary') in ('on', 'true')
    account.purpose = request.POST.get('purpose', '')

    try:
        account.save()
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
        messages.error(request, f'Error: {e}')
        return redirect('business:settings')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok': True,
            'account': {
                'id': account.pk,
                'bank_name': account.bank_name,
                'branch_name': account.branch_name,
                'account_number': account.account_number,
                'account_type': account.get_account_type_display(),
                'currency': account.currency,
                'is_primary': account.is_primary,
                'is_active': account.is_active,
            }
        })

    messages.success(request, f'Bank account added: {account.bank_name}')
    return redirect('business:settings')


@login_required
@require_POST
def edit_bank_account(request, pk):
    """Edit an existing bank account."""
    if request.user.user_type not in ['admin', 'office']:
        return JsonResponse({'ok': False, 'error': 'Access denied'}, status=403)

    profile = DistributorProfile.get_active()
    account = get_object_or_404(BankAccount, pk=pk, distributor=profile)

    account.account_name = request.POST.get('account_name', account.account_name)
    account.bank_name = request.POST.get('bank_name', account.bank_name)
    account.branch_name = request.POST.get('branch_name', account.branch_name)
    account.account_number = request.POST.get('account_number', account.account_number)
    account.account_type = request.POST.get('account_type', account.account_type)
    account.swift_code = request.POST.get('swift_code', '')
    account.iban = request.POST.get('iban', '')
    account.currency = request.POST.get('currency', account.currency)
    account.is_primary = request.POST.get('is_primary') in ('on', 'true')
    account.purpose = request.POST.get('purpose', '')

    try:
        account.save()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def delete_bank_account(request, pk):
    """Delete a bank account."""
    if request.user.user_type not in ['admin', 'office']:
        return JsonResponse({'ok': False, 'error': 'Access denied'}, status=403)

    profile = DistributorProfile.get_active()
    account = get_object_or_404(BankAccount, pk=pk, distributor=profile)
    account.delete()
    return JsonResponse({'ok': True})


# ---------------------------------------------------------------------------
# Business Addresses – AJAX CRUD
# ---------------------------------------------------------------------------

@login_required
@require_POST
def add_business_address(request):
    """Add a new business address."""
    if request.user.user_type not in ['admin', 'office']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'Access denied'}, status=403)
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    profile = DistributorProfile.get_active()
    address = BusinessAddress(distributor=profile)
    address.address_type = request.POST.get('address_type', 'branch')
    address.location_name = request.POST.get('location_name', '')
    address.address_line1 = request.POST.get('address_line1', '')
    address.address_line2 = request.POST.get('address_line2', '')
    address.city = request.POST.get('city', '')
    address.district = request.POST.get('district', '')
    address.postal_code = request.POST.get('postal_code', '')
    address.country = request.POST.get('country', 'Sri Lanka')
    address.contact_person = request.POST.get('contact_person', '')
    address.phone = request.POST.get('phone', '')
    address.email = request.POST.get('email', '')

    try:
        address.save()
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
        messages.error(request, f'Error: {e}')
        return redirect('business:settings')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok': True,
            'address': {
                'id': address.pk,
                'location_name': address.location_name,
                'address_type': address.get_address_type_display(),
                'full_address': address.get_full_address(),
                'phone': address.phone or '',
            }
        })

    messages.success(request, f'Location added: {address.location_name}')
    return redirect('business:settings')


@login_required
@require_POST
def edit_business_address(request, pk):
    """Edit an existing business address."""
    if request.user.user_type not in ['admin', 'office']:
        return JsonResponse({'ok': False, 'error': 'Access denied'}, status=403)

    profile = DistributorProfile.get_active()
    address = get_object_or_404(BusinessAddress, pk=pk, distributor=profile)

    address.address_type = request.POST.get('address_type', address.address_type)
    address.location_name = request.POST.get('location_name', address.location_name)
    address.address_line1 = request.POST.get('address_line1', address.address_line1)
    address.address_line2 = request.POST.get('address_line2', '')
    address.city = request.POST.get('city', address.city)
    address.district = request.POST.get('district', '')
    address.postal_code = request.POST.get('postal_code', '')
    address.country = request.POST.get('country', 'Sri Lanka')
    address.contact_person = request.POST.get('contact_person', '')
    address.phone = request.POST.get('phone', '')
    address.email = request.POST.get('email', '')

    try:
        address.save()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def delete_business_address(request, pk):
    """Delete a business address."""
    if request.user.user_type not in ['admin', 'office']:
        return JsonResponse({'ok': False, 'error': 'Access denied'}, status=403)

    profile = DistributorProfile.get_active()
    address = get_object_or_404(BusinessAddress, pk=pk, distributor=profile)
    address.delete()
    return JsonResponse({'ok': True})

