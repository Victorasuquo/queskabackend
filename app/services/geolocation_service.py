"""
Queska Backend - Geolocation Service
Business logic for all location-based services
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from math import radians, sin, cos, sqrt, atan2

from beanie import PydanticObjectId
from loguru import logger

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError, ServiceUnavailableError
from app.models.geolocation import (
    SavedPlace,
    LocationHistory,
    Route,
    Coordinates,
    Address,
)
from app.schemas.geolocation import (
    GeocodeRequest,
    GeocodeResult,
    ReverseGeocodeRequest,
    DirectionsRequest,
    RouteResult,
    PlaceSearchRequest,
    PlaceResult,
    SavedPlaceCreate,
    SavedPlaceUpdate,
    UpdateLocationRequest,
    CalculateDistanceRequest,
    DistanceResult,
    CoordinatesSchema,
    AddressSchema,
    NEARBY_CATEGORIES,
)
from integrations.maps.mapbox_client import mapbox_client
from integrations.maps.google_maps import google_maps_client


class GeolocationService:
    """
    Unified geolocation service providing:
    - Geocoding and reverse geocoding
    - Directions and routing
    - Distance calculations
    - Place search
    - Location tracking
    - Saved places management
    
    Uses Mapbox as primary provider with Google Maps fallback.
    """
    
    def __init__(self):
        self.mapbox = mapbox_client
        self.google = google_maps_client
    
    def _get_primary_provider(self) -> str:
        """Determine which provider to use"""
        if self.mapbox.is_configured():
            return "mapbox"
        elif self.google.is_configured():
            return "google"
        else:
            raise ServiceUnavailableError("No maps provider configured")
    
    # ================================================================
    # GEOCODING
    # ================================================================
    
    async def geocode(
        self,
        query: str,
        country: Optional[str] = None,
        limit: int = 5,
        proximity: Optional[Tuple[float, float]] = None,
        types: Optional[List[str]] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Convert address/place name to coordinates.
        """
        try:
            if self.mapbox.is_configured():
                result = await self.mapbox.geocode(
                    query=query,
                    country=country,
                    limit=limit,
                    proximity=proximity,
                    types=types,
                    language=language
                )
                if result.get("success"):
                    return result
            
            # Fallback to Google
            if self.google.is_configured():
                result = await self.google.geocode(
                    address=query,
                    components={"country": country} if country else None,
                    language=language
                )
                return result
            
            raise ServiceUnavailableError("No maps provider available")
            
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return {"success": False, "error": str(e), "results": []}
    
    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        types: Optional[List[str]] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Convert coordinates to address.
        """
        try:
            if self.mapbox.is_configured():
                result = await self.mapbox.reverse_geocode(
                    longitude=longitude,
                    latitude=latitude,
                    types=types,
                    language=language
                )
                if result.get("success"):
                    return result
            
            # Fallback to Google
            if self.google.is_configured():
                result = await self.google.reverse_geocode(
                    latitude=latitude,
                    longitude=longitude,
                    language=language
                )
                return result
            
            raise ServiceUnavailableError("No maps provider available")
            
        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
            return {"success": False, "error": str(e), "results": []}
    
    async def batch_geocode(
        self,
        addresses: List[str],
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Geocode multiple addresses.
        """
        if self.mapbox.is_configured():
            return await self.mapbox.batch_geocode(addresses, country)
        
        # Fallback: geocode one by one with Google
        results = []
        for address in addresses:
            result = await self.geocode(address, country=country, limit=1)
            if result.get("success") and result.get("results"):
                results.append({
                    "query": address,
                    "success": True,
                    "result": result["results"][0]
                })
            else:
                results.append({
                    "query": address,
                    "success": False,
                    "error": result.get("error", "No results")
                })
        
        return results
    
    # ================================================================
    # DIRECTIONS
    # ================================================================
    
    async def get_directions(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        waypoints: Optional[List[Tuple[float, float]]] = None,
        profile: str = "driving",
        alternatives: bool = True,
        steps: bool = True,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Get route directions between points.
        
        Args:
            origin: (latitude, longitude)
            destination: (latitude, longitude)
            waypoints: List of (lat, lng) intermediate points
            profile: driving, walking, cycling, transit
            alternatives: Include alternative routes
            steps: Include turn-by-turn instructions
            
        Returns:
            Routes with duration, distance, and geometry
        """
        try:
            # Convert lat,lng to lng,lat for Mapbox
            origin_mapbox = (origin[1], origin[0])
            destination_mapbox = (destination[1], destination[0])
            waypoints_mapbox = [(wp[1], wp[0]) for wp in waypoints] if waypoints else None
            
            if self.mapbox.is_configured():
                # Map profile names
                mapbox_profile = profile
                if profile == "transit":
                    mapbox_profile = "driving"  # Mapbox doesn't support transit
                
                result = await self.mapbox.get_directions(
                    origin=origin_mapbox,
                    destination=destination_mapbox,
                    waypoints=waypoints_mapbox,
                    profile=mapbox_profile,
                    alternatives=alternatives,
                    steps=steps,
                    language=language
                )
                if result.get("success"):
                    return result
            
            # Fallback to Google
            if self.google.is_configured():
                result = await self.google.get_directions(
                    origin=origin,
                    destination=destination,
                    waypoints=waypoints,
                    mode=profile,
                    alternatives=alternatives,
                    language=language
                )
                return result
            
            raise ServiceUnavailableError("No maps provider available")
            
        except Exception as e:
            logger.error(f"Directions error: {e}")
            return {"success": False, "error": str(e), "routes": []}
    
    async def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]],
        profile: str = "driving"
    ) -> Dict[str, Any]:
        """
        Calculate distances between multiple origins and destinations.
        """
        try:
            # Convert lat,lng to lng,lat for Mapbox
            origins_mapbox = [(o[1], o[0]) for o in origins]
            destinations_mapbox = [(d[1], d[0]) for d in destinations]
            
            if self.mapbox.is_configured():
                result = await self.mapbox.get_distance_matrix(
                    origins=origins_mapbox,
                    destinations=destinations_mapbox,
                    profile=profile
                )
                if result.get("success"):
                    return result
            
            # Fallback to Google
            if self.google.is_configured():
                result = await self.google.get_distance_matrix(
                    origins=origins,
                    destinations=destinations,
                    mode=profile
                )
                return result
            
            raise ServiceUnavailableError("No maps provider available")
            
        except Exception as e:
            logger.error(f"Distance matrix error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # DISTANCE CALCULATION
    # ================================================================
    
    def calculate_straight_line_distance(
        self,
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float
    ) -> float:
        """
        Calculate straight-line distance using Haversine formula.
        
        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth's radius in km
        
        lat1_rad, lng1_rad = radians(lat1), radians(lng1)
        lat2_rad, lng2_rad = radians(lat2), radians(lng2)
        
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    async def calculate_distance(
        self,
        from_lat: float,
        from_lng: float,
        to_lat: float,
        to_lng: float,
        profile: str = "driving"
    ) -> DistanceResult:
        """
        Calculate distance between two points with multiple modes.
        """
        # Straight line distance
        straight_km = self.calculate_straight_line_distance(from_lat, from_lng, to_lat, to_lng)
        
        result = DistanceResult(
            straight_line_km=round(straight_km, 2),
            straight_line_text=self._format_distance(straight_km * 1000)
        )
        
        # Get driving/walking distance
        try:
            directions = await self.get_directions(
                origin=(from_lat, from_lng),
                destination=(to_lat, to_lng),
                profile=profile,
                alternatives=False,
                steps=False
            )
            
            if directions.get("success") and directions.get("routes"):
                route = directions["routes"][0]
                result.driving_km = route.get("distance_km")
                result.driving_text = route.get("distance_text")
                result.driving_minutes = route.get("duration_minutes")
                result.driving_duration_text = route.get("duration_text")
            
            # Also get walking if profile is driving
            if profile == "driving":
                walking = await self.get_directions(
                    origin=(from_lat, from_lng),
                    destination=(to_lat, to_lng),
                    profile="walking",
                    alternatives=False,
                    steps=False
                )
                
                if walking.get("success") and walking.get("routes"):
                    walk_route = walking["routes"][0]
                    result.walking_km = walk_route.get("distance_km")
                    result.walking_minutes = walk_route.get("duration_minutes")
        
        except Exception as e:
            logger.warning(f"Error getting route distance: {e}")
        
        return result
    
    def _format_distance(self, meters: float) -> str:
        """Format distance"""
        if meters < 1000:
            return f"{int(meters)} m"
        return f"{meters / 1000:.1f} km"
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration"""
        if seconds < 60:
            return f"{int(seconds)} sec"
        elif seconds < 3600:
            return f"{int(seconds / 60)} min"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours} hr {minutes} min" if minutes else f"{hours} hr"
    
    # ================================================================
    # PLACE SEARCH
    # ================================================================
    
    async def search_places(
        self,
        query: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius: int = 5000,
        category: Optional[str] = None,
        limit: int = 10,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Search for places and points of interest.
        """
        try:
            # Get category types
            category_types = None
            if category:
                for cat in NEARBY_CATEGORIES:
                    if cat.id == category:
                        category_types = cat.mapbox_types if self.mapbox.is_configured() else cat.google_types
                        break
            
            if self.mapbox.is_configured():
                near = (longitude, latitude) if latitude and longitude else None
                
                search_query = query or (category_types[0] if category_types else "")
                
                result = await self.mapbox.search_places(
                    query=search_query,
                    near=near,
                    types=category_types,
                    limit=limit,
                    language=language
                )
                
                if result.get("success"):
                    # Add distance if we have a reference point
                    if latitude and longitude:
                        for place in result.get("places", []):
                            if place.get("coordinates"):
                                place_lat = place["coordinates"].get("latitude")
                                place_lng = place["coordinates"].get("longitude")
                                if place_lat and place_lng:
                                    distance = self.calculate_straight_line_distance(
                                        latitude, longitude, place_lat, place_lng
                                    )
                                    place["distance_meters"] = round(distance * 1000)
                    
                    return result
            
            # Fallback to Google
            if self.google.is_configured():
                if query:
                    result = await self.google.search_places_text(
                        query=query,
                        location=(latitude, longitude) if latitude and longitude else None,
                        radius=radius,
                        language=language
                    )
                elif latitude and longitude:
                    place_type = category_types[0] if category_types else None
                    result = await self.google.search_places_nearby(
                        latitude=latitude,
                        longitude=longitude,
                        radius=radius,
                        keyword=query,
                        place_type=place_type,
                        language=language
                    )
                else:
                    return {"success": False, "error": "Query or location required", "places": []}
                
                return result
            
            raise ServiceUnavailableError("No maps provider available")
            
        except Exception as e:
            logger.error(f"Place search error: {e}")
            return {"success": False, "error": str(e), "places": []}
    
    async def get_place_details(
        self,
        place_id: str,
        provider: str = "google"
    ) -> Dict[str, Any]:
        """
        Get detailed information about a place.
        """
        try:
            if provider == "google" and self.google.is_configured():
                return await self.google.get_place_details(place_id)
            
            # Mapbox doesn't have place details API, fallback to geocode
            if self.mapbox.is_configured():
                result = await self.mapbox.geocode(place_id, limit=1)
                if result.get("success") and result.get("results"):
                    return {"success": True, "place": result["results"][0]}
            
            return {"success": False, "error": "Provider not available"}
            
        except Exception as e:
            logger.error(f"Place details error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # ISOCHRONES
    # ================================================================
    
    async def get_isochrone(
        self,
        latitude: float,
        longitude: float,
        contours_minutes: List[int] = [15, 30, 60],
        profile: str = "driving"
    ) -> Dict[str, Any]:
        """
        Get isochrone polygons (areas reachable within time limits).
        """
        try:
            if self.mapbox.is_configured():
                result = await self.mapbox.get_isochrone(
                    longitude=longitude,
                    latitude=latitude,
                    contours_minutes=contours_minutes,
                    profile=profile
                )
                return result
            
            return {"success": False, "error": "Isochrone requires Mapbox"}
            
        except Exception as e:
            logger.error(f"Isochrone error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # STATIC MAPS
    # ================================================================
    
    async def get_static_map_url(
        self,
        latitude: float,
        longitude: float,
        zoom: int = 14,
        width: int = 600,
        height: int = 400,
        style: str = "streets-v12",
        markers: Optional[List[Dict[str, Any]]] = None,
        path: Optional[List[Tuple[float, float]]] = None
    ) -> str:
        """
        Get URL for a static map image.
        """
        if self.mapbox.is_configured():
            # Convert markers
            mapbox_markers = None
            if markers:
                mapbox_markers = [
                    {"lng": m.get("lng") or m.get("longitude"), 
                     "lat": m.get("lat") or m.get("latitude"),
                     "color": m.get("color", "ff0000"),
                     "label": m.get("label", "")}
                    for m in markers
                ]
            
            return await self.mapbox.get_static_map_url(
                longitude=longitude,
                latitude=latitude,
                zoom=zoom,
                width=width,
                height=height,
                style=style,
                markers=mapbox_markers
            )
        
        # Google Maps static fallback
        base_url = "https://maps.googleapis.com/maps/api/staticmap"
        params = {
            "center": f"{latitude},{longitude}",
            "zoom": zoom,
            "size": f"{width}x{height}",
            "key": settings.GOOGLE_MAPS_API_KEY
        }
        
        if markers:
            marker_strs = []
            for m in markers:
                lat = m.get("lat") or m.get("latitude")
                lng = m.get("lng") or m.get("longitude")
                marker_strs.append(f"{lat},{lng}")
            params["markers"] = "|".join(marker_strs)
        
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query}"
    
    # ================================================================
    # ROUTE OPTIMIZATION
    # ================================================================
    
    async def optimize_route(
        self,
        waypoints: List[Dict[str, Any]],
        profile: str = "driving",
        roundtrip: bool = True
    ) -> Dict[str, Any]:
        """
        Optimize route through multiple waypoints (traveling salesman).
        """
        try:
            if self.mapbox.is_configured():
                # Convert waypoints to (lng, lat) tuples
                coords = [
                    (wp.get("lng") or wp.get("longitude"), 
                     wp.get("lat") or wp.get("latitude"))
                    for wp in waypoints
                ]
                
                result = await self.mapbox.optimize_trip(
                    coordinates=coords,
                    profile=profile,
                    roundtrip=roundtrip
                )
                
                if result.get("success"):
                    # Add waypoint names to order
                    order = result.get("waypoint_order", [])
                    optimized_waypoints = [waypoints[i] for i in order]
                    result["optimized_waypoints"] = optimized_waypoints
                
                return result
            
            return {"success": False, "error": "Route optimization requires Mapbox"}
            
        except Exception as e:
            logger.error(f"Route optimization error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # SAVED PLACES
    # ================================================================
    
    async def save_place(
        self,
        user_id: str,
        data: SavedPlaceCreate
    ) -> SavedPlace:
        """
        Save a place to user's favorites.
        """
        # Get address if not provided
        address = None
        if data.address:
            address = Address(**data.address.model_dump())
        else:
            # Try to reverse geocode
            result = await self.reverse_geocode(data.latitude, data.longitude)
            if result.get("success") and result.get("results"):
                addr_data = result["results"][0].get("address", {})
                address = Address(
                    street=addr_data.get("street"),
                    city=addr_data.get("city"),
                    state=addr_data.get("state"),
                    country=addr_data.get("country"),
                    postal_code=addr_data.get("postal_code"),
                    formatted=result["results"][0].get("full_name")
                )
        
        place = SavedPlace(
            user_id=user_id,
            name=data.name,
            place_id=data.place_id,
            provider=self._get_primary_provider(),
            coordinates=Coordinates(
                latitude=data.latitude,
                longitude=data.longitude
            ),
            address=address,
            category=data.category,
            custom_category=data.custom_category,
            label=data.label,
            notes=data.notes,
            tags=data.tags,
            is_favorite=data.is_favorite
        )
        
        await place.insert()
        logger.info(f"Place saved for user {user_id}: {place.name}")
        
        return place
    
    async def get_saved_places(
        self,
        user_id: str,
        category: Optional[str] = None,
        is_favorite: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[SavedPlace], int]:
        """
        Get user's saved places.
        """
        query = {"user_id": user_id, "is_deleted": False}
        
        if category:
            query["category"] = category
        if is_favorite is not None:
            query["is_favorite"] = is_favorite
        
        total = await SavedPlace.find(query).count()
        places = await SavedPlace.find(query)\
            .sort("-is_favorite", "-created_at")\
            .skip(skip)\
            .limit(limit)\
            .to_list()
        
        return places, total
    
    async def update_saved_place(
        self,
        user_id: str,
        place_id: str,
        data: SavedPlaceUpdate
    ) -> SavedPlace:
        """
        Update a saved place.
        """
        place = await SavedPlace.find_one({
            "_id": PydanticObjectId(place_id),
            "user_id": user_id,
            "is_deleted": False
        })
        
        if not place:
            raise NotFoundError(f"Place {place_id} not found")
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(place, key, value)
        
        place.updated_at = datetime.utcnow()
        await place.save()
        
        return place
    
    async def delete_saved_place(
        self,
        user_id: str,
        place_id: str
    ) -> bool:
        """
        Delete a saved place.
        """
        place = await SavedPlace.find_one({
            "_id": PydanticObjectId(place_id),
            "user_id": user_id,
            "is_deleted": False
        })
        
        if not place:
            raise NotFoundError(f"Place {place_id} not found")
        
        await place.soft_delete()
        return True
    
    # ================================================================
    # LOCATION TRACKING
    # ================================================================
    
    async def update_user_location(
        self,
        user_id: str,
        data: UpdateLocationRequest
    ) -> LocationHistory:
        """
        Record user's current location.
        """
        # Reverse geocode for address
        address = None
        try:
            result = await self.reverse_geocode(data.latitude, data.longitude)
            if result.get("success") and result.get("results"):
                addr_data = result["results"][0].get("address", {})
                address = Address(
                    city=addr_data.get("city"),
                    state=addr_data.get("state"),
                    country=addr_data.get("country"),
                    formatted=result["results"][0].get("full_name")
                )
        except Exception as e:
            logger.warning(f"Could not reverse geocode: {e}")
        
        location = LocationHistory(
            user_id=user_id,
            experience_id=data.experience_id,
            coordinates=Coordinates(
                latitude=data.latitude,
                longitude=data.longitude,
                altitude=data.altitude,
                accuracy=data.accuracy,
                heading=data.heading,
                speed=data.speed
            ),
            address=address,
            shared_publicly=data.share_publicly,
            recorded_at=datetime.utcnow()
        )
        
        await location.insert()
        
        return location
    
    async def get_location_history(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        experience_id: Optional[str] = None,
        limit: int = 100
    ) -> List[LocationHistory]:
        """
        Get user's location history.
        """
        query: Dict[str, Any] = {"user_id": user_id}
        
        if experience_id:
            query["experience_id"] = experience_id
        
        if start_date or end_date:
            query["recorded_at"] = {}
            if start_date:
                query["recorded_at"]["$gte"] = start_date
            if end_date:
                query["recorded_at"]["$lte"] = end_date
        
        locations = await LocationHistory.find(query)\
            .sort("-recorded_at")\
            .limit(limit)\
            .to_list()
        
        return locations
    
    async def get_travel_summary(
        self,
        user_id: str,
        experience_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get summary of travel distances and locations.
        """
        locations = await self.get_location_history(
            user_id=user_id,
            experience_id=experience_id,
            limit=1000
        )
        
        if len(locations) < 2:
            return {
                "total_distance_km": 0,
                "locations_count": len(locations),
                "unique_cities": []
            }
        
        # Calculate total distance
        total_distance = 0
        for i in range(1, len(locations)):
            prev = locations[i-1].coordinates
            curr = locations[i].coordinates
            total_distance += self.calculate_straight_line_distance(
                prev.latitude, prev.longitude,
                curr.latitude, curr.longitude
            )
        
        # Get unique cities
        cities = set()
        for loc in locations:
            if loc.address and loc.address.city:
                cities.add(loc.address.city)
        
        return {
            "total_distance_km": round(total_distance, 2),
            "locations_count": len(locations),
            "unique_cities": list(cities),
            "start_time": locations[-1].recorded_at,
            "end_time": locations[0].recorded_at
        }
    
    # ================================================================
    # UTILITIES
    # ================================================================
    
    def get_nearby_categories(self) -> List[Dict[str, Any]]:
        """
        Get list of nearby search categories.
        """
        return [cat.model_dump() for cat in NEARBY_CATEGORIES]
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Check status of map services.
        """
        return {
            "mapbox": {
                "configured": self.mapbox.is_configured(),
                "primary": self.mapbox.is_configured()
            },
            "google_maps": {
                "configured": self.google.is_configured(),
                "fallback": not self.mapbox.is_configured() and self.google.is_configured()
            }
        }


# Global service instance
geolocation_service = GeolocationService()

