"""
Queska Backend - Google Maps Client
Fallback integration with Google Maps APIs
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import asyncio

import httpx
from loguru import logger

from app.core.config import settings


class GoogleMapsClient:
    """
    Google Maps API client as fallback for Mapbox.
    
    Features:
    - Geocoding
    - Reverse geocoding
    - Directions
    - Distance matrix
    - Places search
    - Place details
    """
    
    BASE_URL = "https://maps.googleapis.com/maps/api"
    
    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    # ================================================================
    # GEOCODING
    # ================================================================
    
    async def geocode(
        self,
        address: str,
        components: Optional[Dict[str, str]] = None,
        bounds: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None,
        region: Optional[str] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Convert address to coordinates.
        
        Args:
            address: Address to geocode
            components: Component filtering (country, postal_code, etc.)
            bounds: Bounding box bias
            region: Region bias (country code)
            language: Result language
            
        Returns:
            Geocoding results
        """
        if not self.is_configured():
            raise ValueError("Google Maps API key not configured")
        
        params = {
            "address": address,
            "key": self.api_key,
            "language": language,
        }
        
        if components:
            params["components"] = "|".join([f"{k}:{v}" for k, v in components.items()])
        if bounds:
            params["bounds"] = f"{bounds[0][0]},{bounds[0][1]}|{bounds[1][0]},{bounds[1][1]}"
        if region:
            params["region"] = region
        
        url = f"{self.BASE_URL}/geocode/json"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "OK":
                return {
                    "success": False,
                    "error": data.get("status"),
                    "results": []
                }
            
            return {
                "success": True,
                "results": self._parse_geocode_results(data),
                "raw": data
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Google Maps geocoding error: {e}")
            return {"success": False, "error": str(e), "results": []}
    
    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        result_type: Optional[List[str]] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Convert coordinates to address.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            result_type: Filter by result types
            language: Result language
            
        Returns:
            Reverse geocoding results
        """
        if not self.is_configured():
            raise ValueError("Google Maps API key not configured")
        
        params = {
            "latlng": f"{latitude},{longitude}",
            "key": self.api_key,
            "language": language,
        }
        
        if result_type:
            params["result_type"] = "|".join(result_type)
        
        url = f"{self.BASE_URL}/geocode/json"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "OK":
                return {
                    "success": False,
                    "error": data.get("status"),
                    "results": []
                }
            
            return {
                "success": True,
                "results": self._parse_geocode_results(data),
                "raw": data
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Google Maps reverse geocoding error: {e}")
            return {"success": False, "error": str(e), "results": []}
    
    def _parse_geocode_results(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse geocoding results"""
        results = []
        
        for result in data.get("results", []):
            location = result.get("geometry", {}).get("location", {})
            
            # Parse address components
            address_components = {}
            for component in result.get("address_components", []):
                for comp_type in component.get("types", []):
                    address_components[comp_type] = component.get("long_name")
            
            parsed = {
                "place_id": result.get("place_id"),
                "name": result.get("formatted_address"),
                "full_name": result.get("formatted_address"),
                "coordinates": {
                    "latitude": location.get("lat"),
                    "longitude": location.get("lng"),
                },
                "type": result.get("types", [None])[0],
                "address": {
                    "street_number": address_components.get("street_number"),
                    "street": address_components.get("route"),
                    "city": address_components.get("locality") or address_components.get("administrative_area_level_2"),
                    "region": address_components.get("administrative_area_level_1"),
                    "state": address_components.get("administrative_area_level_1"),
                    "country": address_components.get("country"),
                    "postal_code": address_components.get("postal_code"),
                },
                "viewport": result.get("geometry", {}).get("viewport"),
            }
            results.append(parsed)
        
        return results
    
    # ================================================================
    # DIRECTIONS
    # ================================================================
    
    async def get_directions(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        waypoints: Optional[List[Tuple[float, float]]] = None,
        mode: str = "driving",
        alternatives: bool = True,
        avoid: Optional[List[str]] = None,
        departure_time: Optional[datetime] = None,
        traffic_model: str = "best_guess",
        language: str = "en",
        units: str = "metric"
    ) -> Dict[str, Any]:
        """
        Get directions between points.
        
        Args:
            origin: Starting point (lat, lng)
            destination: End point (lat, lng)
            waypoints: Intermediate points
            mode: Travel mode (driving, walking, bicycling, transit)
            alternatives: Include alternative routes
            avoid: Features to avoid (tolls, highways, ferries)
            departure_time: For traffic-based routing
            traffic_model: How to predict traffic (best_guess, pessimistic, optimistic)
            language: Result language
            units: Distance units (metric, imperial)
            
        Returns:
            Route data
        """
        if not self.is_configured():
            raise ValueError("Google Maps API key not configured")
        
        params = {
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{destination[0]},{destination[1]}",
            "mode": mode,
            "alternatives": str(alternatives).lower(),
            "key": self.api_key,
            "language": language,
            "units": units,
        }
        
        if waypoints:
            wp_str = "|".join([f"{wp[0]},{wp[1]}" for wp in waypoints])
            params["waypoints"] = wp_str
        if avoid:
            params["avoid"] = "|".join(avoid)
        if departure_time:
            params["departure_time"] = int(departure_time.timestamp())
            params["traffic_model"] = traffic_model
        
        url = f"{self.BASE_URL}/directions/json"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "OK":
                return {
                    "success": False,
                    "error": data.get("status"),
                    "routes": []
                }
            
            return {
                "success": True,
                "routes": self._parse_routes(data),
                "raw": data
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Google Maps directions error: {e}")
            return {"success": False, "error": str(e), "routes": []}
    
    def _parse_routes(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse route results"""
        routes = []
        
        for route in data.get("routes", []):
            # Sum up all legs
            total_duration = 0
            total_distance = 0
            legs = []
            
            for leg in route.get("legs", []):
                duration = leg.get("duration", {}).get("value", 0)
                distance = leg.get("distance", {}).get("value", 0)
                total_duration += duration
                total_distance += distance
                
                leg_data = {
                    "start_address": leg.get("start_address"),
                    "end_address": leg.get("end_address"),
                    "start_location": leg.get("start_location"),
                    "end_location": leg.get("end_location"),
                    "duration_seconds": duration,
                    "duration_text": leg.get("duration", {}).get("text"),
                    "distance_meters": distance,
                    "distance_text": leg.get("distance", {}).get("text"),
                    "steps": [
                        {
                            "instruction": step.get("html_instructions"),
                            "distance_meters": step.get("distance", {}).get("value"),
                            "duration_seconds": step.get("duration", {}).get("value"),
                            "travel_mode": step.get("travel_mode"),
                            "maneuver": step.get("maneuver"),
                        }
                        for step in leg.get("steps", [])
                    ],
                }
                
                # Traffic duration if available
                if "duration_in_traffic" in leg:
                    leg_data["duration_in_traffic_seconds"] = leg["duration_in_traffic"]["value"]
                    leg_data["duration_in_traffic_text"] = leg["duration_in_traffic"]["text"]
                
                legs.append(leg_data)
            
            parsed = {
                "summary": route.get("summary"),
                "duration_seconds": total_duration,
                "duration_minutes": round(total_duration / 60, 1),
                "duration_text": self._format_duration(total_duration),
                "distance_meters": total_distance,
                "distance_km": round(total_distance / 1000, 2),
                "distance_text": self._format_distance(total_distance),
                "overview_polyline": route.get("overview_polyline", {}).get("points"),
                "bounds": route.get("bounds"),
                "warnings": route.get("warnings", []),
                "copyrights": route.get("copyrights"),
                "legs": legs,
            }
            
            routes.append(parsed)
        
        return routes
    
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
    
    def _format_distance(self, meters: float) -> str:
        """Format distance"""
        if meters < 1000:
            return f"{int(meters)} m"
        return f"{meters / 1000:.1f} km"
    
    # ================================================================
    # DISTANCE MATRIX
    # ================================================================
    
    async def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]],
        mode: str = "driving",
        avoid: Optional[List[str]] = None,
        departure_time: Optional[datetime] = None,
        units: str = "metric"
    ) -> Dict[str, Any]:
        """
        Get distance matrix between origins and destinations.
        """
        if not self.is_configured():
            raise ValueError("Google Maps API key not configured")
        
        origins_str = "|".join([f"{o[0]},{o[1]}" for o in origins])
        destinations_str = "|".join([f"{d[0]},{d[1]}" for d in destinations])
        
        params = {
            "origins": origins_str,
            "destinations": destinations_str,
            "mode": mode,
            "key": self.api_key,
            "units": units,
        }
        
        if avoid:
            params["avoid"] = "|".join(avoid)
        if departure_time:
            params["departure_time"] = int(departure_time.timestamp())
        
        url = f"{self.BASE_URL}/distancematrix/json"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "OK":
                return {"success": False, "error": data.get("status")}
            
            # Parse matrix
            matrix = []
            for i, row in enumerate(data.get("rows", [])):
                row_data = []
                for j, element in enumerate(row.get("elements", [])):
                    if element.get("status") == "OK":
                        row_data.append({
                            "duration_seconds": element.get("duration", {}).get("value"),
                            "duration_text": element.get("duration", {}).get("text"),
                            "distance_meters": element.get("distance", {}).get("value"),
                            "distance_text": element.get("distance", {}).get("text"),
                        })
                    else:
                        row_data.append({"status": element.get("status")})
                matrix.append(row_data)
            
            return {
                "success": True,
                "origin_addresses": data.get("origin_addresses", []),
                "destination_addresses": data.get("destination_addresses", []),
                "matrix": matrix,
                "raw": data
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Google Maps distance matrix error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # PLACES
    # ================================================================
    
    async def search_places_nearby(
        self,
        latitude: float,
        longitude: float,
        radius: int = 5000,
        keyword: Optional[str] = None,
        place_type: Optional[str] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Search for places near a location.
        """
        if not self.is_configured():
            raise ValueError("Google Maps API key not configured")
        
        params = {
            "location": f"{latitude},{longitude}",
            "radius": radius,
            "key": self.api_key,
            "language": language,
        }
        
        if keyword:
            params["keyword"] = keyword
        if place_type:
            params["type"] = place_type
        
        url = f"{self.BASE_URL}/place/nearbysearch/json"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") not in ["OK", "ZERO_RESULTS"]:
                return {"success": False, "error": data.get("status"), "places": []}
            
            return {
                "success": True,
                "places": self._parse_places(data.get("results", [])),
                "next_page_token": data.get("next_page_token"),
                "raw": data
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Google Maps nearby search error: {e}")
            return {"success": False, "error": str(e), "places": []}
    
    async def search_places_text(
        self,
        query: str,
        location: Optional[Tuple[float, float]] = None,
        radius: Optional[int] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Search for places using text query.
        """
        if not self.is_configured():
            raise ValueError("Google Maps API key not configured")
        
        params = {
            "query": query,
            "key": self.api_key,
            "language": language,
        }
        
        if location:
            params["location"] = f"{location[0]},{location[1]}"
        if radius:
            params["radius"] = radius
        
        url = f"{self.BASE_URL}/place/textsearch/json"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") not in ["OK", "ZERO_RESULTS"]:
                return {"success": False, "error": data.get("status"), "places": []}
            
            return {
                "success": True,
                "places": self._parse_places(data.get("results", [])),
                "raw": data
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Google Maps text search error: {e}")
            return {"success": False, "error": str(e), "places": []}
    
    async def get_place_details(
        self,
        place_id: str,
        fields: Optional[List[str]] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Get detailed information about a place.
        """
        if not self.is_configured():
            raise ValueError("Google Maps API key not configured")
        
        default_fields = [
            "name", "formatted_address", "geometry", "place_id",
            "types", "opening_hours", "rating", "user_ratings_total",
            "photos", "formatted_phone_number", "website", "price_level"
        ]
        
        params = {
            "place_id": place_id,
            "fields": ",".join(fields or default_fields),
            "key": self.api_key,
            "language": language,
        }
        
        url = f"{self.BASE_URL}/place/details/json"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "OK":
                return {"success": False, "error": data.get("status")}
            
            result = data.get("result", {})
            location = result.get("geometry", {}).get("location", {})
            
            return {
                "success": True,
                "place": {
                    "place_id": result.get("place_id"),
                    "name": result.get("name"),
                    "formatted_address": result.get("formatted_address"),
                    "coordinates": {
                        "latitude": location.get("lat"),
                        "longitude": location.get("lng"),
                    },
                    "types": result.get("types", []),
                    "rating": result.get("rating"),
                    "user_ratings_total": result.get("user_ratings_total"),
                    "price_level": result.get("price_level"),
                    "opening_hours": result.get("opening_hours"),
                    "phone": result.get("formatted_phone_number"),
                    "website": result.get("website"),
                    "photos": result.get("photos", []),
                },
                "raw": data
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Google Maps place details error: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_places(self, places: List[Dict]) -> List[Dict[str, Any]]:
        """Parse places results"""
        parsed = []
        
        for place in places:
            location = place.get("geometry", {}).get("location", {})
            
            parsed.append({
                "place_id": place.get("place_id"),
                "name": place.get("name"),
                "vicinity": place.get("vicinity"),
                "formatted_address": place.get("formatted_address"),
                "coordinates": {
                    "latitude": location.get("lat"),
                    "longitude": location.get("lng"),
                },
                "types": place.get("types", []),
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total"),
                "price_level": place.get("price_level"),
                "open_now": place.get("opening_hours", {}).get("open_now"),
                "photos": [
                    {"reference": p.get("photo_reference")}
                    for p in place.get("photos", [])[:3]
                ],
                "icon": place.get("icon"),
            })
        
        return parsed
    
    def get_photo_url(
        self,
        photo_reference: str,
        max_width: int = 400,
        max_height: Optional[int] = None
    ) -> str:
        """
        Get URL for a place photo.
        """
        params = {
            "photoreference": photo_reference,
            "maxwidth": max_width,
            "key": self.api_key,
        }
        if max_height:
            params["maxheight"] = max_height
        
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.BASE_URL}/place/photo?{query}"


# Global client instance
google_maps_client = GoogleMapsClient()

