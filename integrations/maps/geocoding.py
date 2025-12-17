"""
Queska Backend - Geocoding Utilities
Common geocoding utilities and helpers
"""

from math import radians, sin, cos, sqrt, atan2
from typing import Dict, List, Optional, Tuple


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculate the great circle distance between two points on Earth.
    
    Args:
        lat1, lon1: First point (latitude, longitude) in degrees
        lat2, lon2: Second point (latitude, longitude) in degrees
        
    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c


def bearing_between_points(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculate the initial bearing from point 1 to point 2.
    
    Args:
        lat1, lon1: First point (latitude, longitude) in degrees
        lat2, lon2: Second point (latitude, longitude) in degrees
        
    Returns:
        Bearing in degrees (0-360)
    """
    from math import atan2, cos, sin, radians, degrees
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lon = radians(lon2 - lon1)
    
    x = sin(delta_lon) * cos(lat2_rad)
    y = cos(lat1_rad) * sin(lat2_rad) - sin(lat1_rad) * cos(lat2_rad) * cos(delta_lon)
    
    bearing = degrees(atan2(x, y))
    return (bearing + 360) % 360


def destination_point(
    lat: float,
    lon: float,
    distance_km: float,
    bearing_deg: float
) -> Tuple[float, float]:
    """
    Calculate destination point given start point, distance, and bearing.
    
    Args:
        lat, lon: Starting point (latitude, longitude) in degrees
        distance_km: Distance to travel in kilometers
        bearing_deg: Bearing in degrees
        
    Returns:
        Tuple of (latitude, longitude) of destination
    """
    from math import asin, cos, sin, radians, degrees, atan2
    
    R = 6371  # Earth's radius in km
    
    lat_rad = radians(lat)
    lon_rad = radians(lon)
    bearing_rad = radians(bearing_deg)
    
    angular_distance = distance_km / R
    
    new_lat = asin(
        sin(lat_rad) * cos(angular_distance) +
        cos(lat_rad) * sin(angular_distance) * cos(bearing_rad)
    )
    
    new_lon = lon_rad + atan2(
        sin(bearing_rad) * sin(angular_distance) * cos(lat_rad),
        cos(angular_distance) - sin(lat_rad) * sin(new_lat)
    )
    
    return degrees(new_lat), degrees(new_lon)


def point_in_polygon(
    lat: float,
    lon: float,
    polygon: List[Tuple[float, float]]
) -> bool:
    """
    Check if a point is inside a polygon using ray casting algorithm.
    
    Args:
        lat, lon: Point to check
        polygon: List of (lat, lon) vertices
        
    Returns:
        True if point is inside polygon
    """
    n = len(polygon)
    inside = False
    
    j = n - 1
    for i in range(n):
        if ((polygon[i][0] > lat) != (polygon[j][0] > lat)) and \
           (lon < (polygon[j][1] - polygon[i][1]) * (lat - polygon[i][0]) / (polygon[j][0] - polygon[i][0]) + polygon[i][1]):
            inside = not inside
        j = i
    
    return inside


def bounding_box(
    lat: float,
    lon: float,
    distance_km: float
) -> Dict[str, float]:
    """
    Calculate bounding box around a point.
    
    Args:
        lat, lon: Center point
        distance_km: Half-width of the box in km
        
    Returns:
        Dict with min_lat, max_lat, min_lon, max_lon
    """
    # Rough approximation
    lat_delta = distance_km / 111.0  # 1 degree latitude ≈ 111 km
    lon_delta = distance_km / (111.0 * cos(radians(lat)))
    
    return {
        "min_lat": lat - lat_delta,
        "max_lat": lat + lat_delta,
        "min_lon": lon - lon_delta,
        "max_lon": lon + lon_delta,
    }


def format_distance(meters: float) -> str:
    """Format distance in human-readable format."""
    if meters < 1000:
        return f"{int(meters)} m"
    elif meters < 10000:
        return f"{meters / 1000:.1f} km"
    else:
        return f"{int(meters / 1000)} km"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)} sec"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} min"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        if minutes > 0:
            return f"{hours} hr {minutes} min"
        return f"{hours} hr"


def friendly_distance_message(
    distance_km: float,
    driving_minutes: Optional[float] = None
) -> str:
    """Generate a friendly distance message."""
    if distance_km < 1:
        return f"Just {int(distance_km * 1000)} meters away!"
    elif distance_km < 5:
        return f"Only {distance_km:.1f} km away"
    elif distance_km < 50:
        if driving_minutes and driving_minutes < 60:
            return f"{int(driving_minutes)} minutes away"
        return f"{distance_km:.0f} km away"
    elif distance_km < 200:
        if driving_minutes:
            hours = driving_minutes / 60
            return f"About {hours:.1f} hours drive"
        return f"About {distance_km:.0f} km away"
    else:
        return f"{distance_km:.0f} km away"


def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate latitude and longitude values."""
    return -90 <= lat <= 90 and -180 <= lon <= 180


def normalize_longitude(lon: float) -> float:
    """Normalize longitude to -180 to 180 range."""
    while lon > 180:
        lon -= 360
    while lon < -180:
        lon += 360
    return lon


# Common place type mappings between providers
PLACE_TYPE_MAPPINGS = {
    # Mapbox types to Google types
    "mapbox_to_google": {
        "restaurant": "restaurant",
        "hotel": "lodging",
        "cafe": "cafe",
        "bar": "bar",
        "museum": "museum",
        "park": "park",
        "hospital": "hospital",
        "pharmacy": "pharmacy",
        "fuel": "gas_station",
        "parking": "parking",
        "atm": "atm",
        "airport": "airport",
        "train_station": "train_station",
        "bus_station": "bus_station",
        "shop": "store",
    },
    # Google types to Mapbox types
    "google_to_mapbox": {
        "restaurant": "restaurant",
        "lodging": "hotel",
        "cafe": "cafe",
        "bar": "bar",
        "museum": "museum",
        "park": "park",
        "hospital": "hospital",
        "pharmacy": "pharmacy",
        "gas_station": "fuel",
        "parking": "parking",
        "atm": "atm",
        "airport": "airport",
        "train_station": "train_station",
        "bus_station": "bus_station",
        "store": "shop",
    }
}


def convert_place_type(
    place_type: str,
    from_provider: str,
    to_provider: str
) -> str:
    """Convert place type between providers."""
    if from_provider == to_provider:
        return place_type
    
    mapping_key = f"{from_provider}_to_{to_provider}"
    mappings = PLACE_TYPE_MAPPINGS.get(mapping_key, {})
    
    return mappings.get(place_type, place_type)

