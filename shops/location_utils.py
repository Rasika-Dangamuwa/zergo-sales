"""
Utility functions for location-based features
"""
from math import radians, cos, sin, asin, sqrt
from decimal import Decimal


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


def get_nearby_shops(current_lat, current_lon, shops_queryset, radius_km=5):
    """
    Filter shops within specified radius from current location
    Returns list of tuples: (shop, distance_km)
    """
    nearby_shops = []
    
    for shop in shops_queryset:
        if shop.latitude and shop.longitude:
            distance = haversine_distance(
                current_lat, current_lon,
                shop.latitude, shop.longitude
            )
            
            if distance <= radius_km:
                nearby_shops.append((shop, round(distance, 2)))
    
    # Sort by distance (closest first)
    nearby_shops.sort(key=lambda x: x[1])
    
    return nearby_shops
