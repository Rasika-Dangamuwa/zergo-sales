"""
Shop Visit Utilities
====================
Handles automatic and manual visit marking with GPS proximity checks.

Business Rules:
  - One visit per shop per sales rep per day (regardless of type)
  - Manual visits require GPS proximity (≤ 500m)
  - Auto-visits require BOTH an activity AND GPS proximity
  - Bank transfers do NOT trigger auto-visits (done remotely)
"""
from decimal import Decimal
from django.utils import timezone

from shops.models import ShopVisit
from shops.location_utils import haversine_distance

# Maximum distance (in km) to consider "nearby" for visit marking
PROXIMITY_RADIUS_KM = 0.5  # 500 meters


def is_nearby(shop, latitude, longitude, radius_km=PROXIMITY_RADIUS_KM):
    """
    Check if given coordinates are within radius of the shop.
    Returns (is_near: bool, distance_km: float or None)
    """
    if not shop.latitude or not shop.longitude:
        # Shop has no GPS coordinates — cannot verify proximity
        return False, None
    if not latitude or not longitude:
        return False, None

    distance = haversine_distance(
        float(latitude), float(longitude),
        float(shop.latitude), float(shop.longitude)
    )
    return distance <= radius_km, round(distance, 3)


def try_mark_visit(shop, user, latitude=None, longitude=None,
                   visit_type='manual', notes='', force=False):
    """
    Attempt to create a ShopVisit record.

    Returns:
        (success: bool, message: str, visit: ShopVisit or None)

    Rules applied:
        1. Once per day per shop per rep (skip if already visited today)
        2. Proximity check when coordinates are provided
        3. `force=True` skips proximity check (for admin overrides)
    """
    # Rule 1 — once per day
    if ShopVisit.already_visited_today(shop, user):
        return False, 'already_visited', None

    # Rule 2 — proximity (unless forced or no coords given)
    if not force and latitude and longitude:
        near, distance = is_nearby(shop, latitude, longitude)
        if not near:
            dist_str = f'{int(distance * 1000)}m' if distance else 'unknown'
            return False, f'too_far:{dist_str}', None

    # Create visit
    visit = ShopVisit.objects.create(
        shop=shop,
        sales_rep=user,
        visit_type=visit_type,
        visit_latitude=Decimal(str(latitude)) if latitude else None,
        visit_longitude=Decimal(str(longitude)) if longitude else None,
        notes=notes,
    )
    return True, 'ok', visit


def auto_mark_visit(shop, user, visit_type, reference_number=''):
    """
    Called from activity views (create_bill, add_payment, etc.) to
    automatically mark a visit if the user is nearby.

    Uses the user's latest SalesRepLocation to determine proximity.
    Silently skips if:
      - Already visited today
      - No recent location data
      - User is not nearby
    """
    if not shop or not user:
        return None

    # Already visited today? Skip silently
    if ShopVisit.already_visited_today(shop, user):
        return None

    # Get user's latest tracked location (within last 30 minutes)
    from accounts.models import SalesRepLocation
    thirty_min_ago = timezone.now() - timezone.timedelta(minutes=30)
    latest_loc = SalesRepLocation.objects.filter(
        sales_rep=user,
        timestamp__gte=thirty_min_ago
    ).order_by('-timestamp').first()

    if not latest_loc:
        return None

    # Proximity check
    near, distance = is_nearby(shop, latest_loc.latitude, latest_loc.longitude)
    if not near:
        return None

    # Create the auto-visit
    notes = f'Auto-marked: {visit_type.replace("auto_", "").replace("_", " ").title()}'
    if reference_number:
        notes += f' ({reference_number})'

    visit = ShopVisit.objects.create(
        shop=shop,
        sales_rep=user,
        visit_type=visit_type,
        visit_latitude=latest_loc.latitude,
        visit_longitude=latest_loc.longitude,
        notes=notes,
    )
    return visit
