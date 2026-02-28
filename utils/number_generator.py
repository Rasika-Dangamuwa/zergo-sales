"""
Central Document Number Generator
===================================
Unified numbering for all document types across all tenants.

Format: PREFIX-DISTCODE-YYYYMMDD-NNNN
  - PREFIX    : Document type identifier (SAL, BILL, RN, EXC, SET, etc.)
  - DISTCODE  : Distributor code from the current tenant (e.g., ZERGO001, 002)
  - YYYYMMDD  : Date (local timezone)
  - NNNN      : 4-digit daily sequential number (0001–9999)

Special cases:
  - Shop codes use: SHOP-DISTCODE-NNNNNN (no date, 6-digit sequence)
  - Yearly-reset types use: PREFIX-DISTCODE-YYYY-NNNN

Usage:
    from utils.number_generator import generate_number
    number = generate_number('SAL', SaleModel, 'sale_number')
    number = generate_number('SHOP', ShopModel, 'shop_code', mode='global')
    number = generate_number('PO', POModel, 'po_number', mode='yearly')
"""

from django.utils import timezone
from django.conf import settings
import pytz


def get_distributor_code():
    """
    Get the current tenant's distributor code.
    Returns 'PUB' for public schema (backward compatibility).
    """
    try:
        from django.db import connection
        tenant = connection.tenant
        if tenant and hasattr(tenant, 'code') and tenant.code:
            code = tenant.code.upper()
            # Skip 'PLATFORM' for public schema
            if code == 'PLATFORM':
                return 'PUB'
            return code
    except Exception:
        pass
    return 'PUB'


def get_local_now():
    """Get the current datetime in the project's local timezone."""
    local_tz = pytz.timezone(settings.TIME_ZONE)
    return timezone.now().astimezone(local_tz)


def generate_number(prefix, model_class, field_name, mode='daily',
                    date_value=None, seq_digits=4):
    """
    Generate a unique document number.

    Args:
        prefix (str): Document type prefix (e.g., 'SAL', 'BILL', 'RN', 'EXC')
        model_class: Django model class to query for existing numbers
        field_name (str): Name of the field storing the number on the model
        mode (str): Sequencing mode:
            - 'daily'  : PREFIX-DIST-YYYYMMDD-NNNN (resets daily)
            - 'yearly' : PREFIX-DIST-YYYY-NNNN (resets yearly)
            - 'global' : PREFIX-DIST-NNNNNN (never resets, 6-digit)
        date_value (datetime, optional): Override date (for bill_date etc.)
        seq_digits (int): Number of digits for sequence (default 4)

    Returns:
        str: Generated document number
    """
    dist_code = get_distributor_code()
    now = get_local_now()

    if mode == 'daily':
        if date_value:
            if timezone.is_aware(date_value):
                local_tz = pytz.timezone(settings.TIME_ZONE)
                date_value = date_value.astimezone(local_tz)
            date_str = date_value.strftime('%Y%m%d')
        else:
            date_str = now.strftime('%Y%m%d')

        # PREFIX-DISTCODE-YYYYMMDD-
        number_prefix = f"{prefix}-{dist_code}-{date_str}-"

    elif mode == 'yearly':
        if date_value:
            if timezone.is_aware(date_value):
                local_tz = pytz.timezone(settings.TIME_ZONE)
                date_value = date_value.astimezone(local_tz)
            year = date_value.strftime('%Y')
        else:
            year = str(now.year)

        # PREFIX-DISTCODE-YYYY-
        number_prefix = f"{prefix}-{dist_code}-{year}-"

    elif mode == 'global':
        # PREFIX-DISTCODE- (no date component)
        number_prefix = f"{prefix}-{dist_code}-"
        seq_digits = max(seq_digits, 6)  # Minimum 6 for globals

    else:
        raise ValueError(f"Unknown mode: {mode}")

    # Find the last number with this prefix
    filter_kwargs = {f'{field_name}__startswith': number_prefix}
    last_obj = model_class.objects.filter(
        **filter_kwargs
    ).order_by(f'-{field_name}').first()

    if last_obj:
        last_number_str = getattr(last_obj, field_name)
        # Extract the sequence part (everything after the last dash)
        try:
            last_seq = int(last_number_str.split('-')[-1])
        except (ValueError, IndexError):
            last_seq = 0
        new_seq = last_seq + 1
    else:
        new_seq = 1

    return f"{number_prefix}{new_seq:0{seq_digits}d}"
