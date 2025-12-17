"""
Queska Backend - Mapbox Client
Integration with Mapbox APIs for geocoding, directions, and maps
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import asyncio

import httpx
from loguru import logger

from app.core.config import settings


class MapboxClient:
    """
    Mapbox API client for all location-based services.
    
    Features:
    - Geocoding (address to coordinates)
    - Reverse geocoding (coordinates to address)
    - Directions & routing
    - Distance/duration calculations
    - Place search
    - Static map images
    - Isochrones (travel time polygons)
    """
    
    BASE_URL = "https://api.mapbox.com"
    GEOCODING_URL = f"{BASE_URL}/geocoding/v5/mapbox.places"
    DIRECTIONS_URL = f"{BASE_URL}/directions/v5/mapbox"
    MATRIX_URL = f"{BASE_URL}/directions-matrix/v1/mapbox"
    ISOCHRONE_URL = f"{BASE_URL}/isochrone/v1/mapbox"
    STATIC_URL = f"{BASE_URL}/styles/v1/mapbox/streets-v12/static"
    OPTIMIZATION_URL = f"{BASE_URL}/optimized-trips/v1/mapbox"
    
    def __init__(self):
        self.access_token = settings.MAPBOX_ACCESS_TOKEN
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
        return bool(self.access_token)
    
    # ================================================================
    # GEOCODING
    # ================================================================
    
    async def geocode(
        self,
        query: str,
        country: Optional[str] = None,
        limit: int = 5,
        types: Optional[List[str]] = None,
        proximity: Optional[Tuple[float, float]] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Convert address/place name to coordinates.
        
        Args:
            query: Address or place name to search
            country: ISO 3166-1 alpha-2 country code to filter results
            limit: Maximum number of results (1-10)
            types: Filter by place types (address, poi, place, country, region, etc.)
            proximity: Bias results near this point (lng, lat)
            language: Language for results
            
        Returns:
            GeoJSON FeatureCollection with results
        """
        if not self.is_configured():
            raise ValueError("Mapbox access token not configured")
        
        params = {
            "access_token": self.access_token,
            "limit": min(limit, 10),
            "language": language,
        }
        
        if country:
            params["country"] = country
        if types:
            params["types"] = ",".join(types)
        if proximity:
            params["proximity"] = f"{proximity[0]},{proximity[1]}"
        
        url = f"{self.GEOCODING_URL}/{query}.json"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": True,
                "results": self._parse_geocode_results(data),
                "raw": data
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Mapbox geocoding error: {e}")
            return {"success": False, "error": str(e), "results": []}
    
    async def reverse_geocode(
        self,
        longitude: float,
        latitude: float,
        types: Optional[List[str]] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Convert coordinates to address/place name.
        
        Args:
            longitude: Longitude coordinate
            latitude: Latitude coordinate
            types: Filter by place types
            language: Language for results
            
        Returns:
            GeoJSON FeatureCollection with results
        """
        if not self.is_configured():
            raise ValueError("Mapbox access token not configured")
        
        params = {
            "access_token": self.access_token,
            "language": language,
        }
        
        if types:
            params["types"] = ",".join(types)
        
        url = f"{self.GEOCODING_URL}/{longitude},{latitude}.json"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": True,
                "results": self._parse_geocode_results(data),
                "raw": data
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Mapbox reverse geocoding error: {e}")
            return {"success": False, "error": str(e), "results": []}
    
    def _parse_geocode_results(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse geocoding results into simplified format"""
        results = []
        
        for feature in data.get("features", []):
            context = {item["id"].split(".")[0]: item["text"] for item in feature.get("context", [])}
            
            result = {
                "place_id": feature.get("id"),
                "name": feature.get("text"),
                "full_name": feature.get("place_name"),
                "coordinates": {
                    "longitude": feature["center"][0],
                    "latitude": feature["center"][1],
                },
                "type": feature.get("place_type", [None])[0],
                "relevance": feature.get("relevance", 0),
                "address": {
                    "street": feature.get("address"),
                    "city": context.get("place"),
                    "region": context.get("region"),
                    "state": context.get("region"),
                    "country": context.get("country"),
                    "postal_code": context.get("postcode"),
                },
                "bbox": feature.get("bbox"),
            }
            results.append(result)
        
        return results
    
    # ================================================================
    # DIRECTIONS & ROUTING
    # ================================================================
    
    async def get_directions(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        waypoints: Optional[List[Tuple[float, float]]] = None,
        profile: str = "driving",
        alternatives: bool = True,
        geometries: str = "geojson",
        steps: bool = True,
        overview: str = "full",
        annotations: Optional[List[str]] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Get driving/walking/cycling directions between points.
        
        Args:
            origin: Starting point (lng, lat)
            destination: End point (lng, lat)
            waypoints: Optional list of intermediate points
            profile: Routing profile (driving, driving-traffic, walking, cycling)
            alternatives: Include alternative routes
            geometries: Response format (geojson, polyline, polyline6)
            steps: Include turn-by-turn instructions
            overview: Route geometry detail (full, simplified, false)
            annotations: Additional data (duration, distance, speed, congestion)
            language: Language for instructions
            
        Returns:
            Route data with duration, distance, and geometry
        """
        if not self.is_configured():
            raise ValueError("Mapbox access token not configured")
        
        # Build coordinates string
        coords = [f"{origin[0]},{origin[1]}"]
        if waypoints:
            for wp in waypoints:
                coords.append(f"{wp[0]},{wp[1]}")
        coords.append(f"{destination[0]},{destination[1]}")
        
        coordinates = ";".join(coords)
        
        params = {
            "access_token": self.access_token,
            "alternatives": str(alternatives).lower(),
            "geometries": geometries,
            "steps": str(steps).lower(),
            "overview": overview,
            "language": language,
        }
        
        if annotations:
            params["annotations"] = ",".join(annotations)
        
        url = f"{self.DIRECTIONS_URL}/{profile}/{coordinates}"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": True,
                "routes": self._parse_routes(data),
                "waypoints": data.get("waypoints", []),
                "raw": data
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Mapbox directions error: {e}")
            return {"success": False, "error": str(e), "routes": []}
    
    def _parse_routes(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse route results"""
        routes = []
        
        for route in data.get("routes", []):
            parsed = {
                "duration_seconds": route.get("duration"),
                "duration_minutes": round(route.get("duration", 0) / 60, 1),
                "duration_text": self._format_duration(route.get("duration", 0)),
                "distance_meters": route.get("distance"),
                "distance_km": round(route.get("distance", 0) / 1000, 2),
                "distance_text": self._format_distance(route.get("distance", 0)),
                "geometry": route.get("geometry"),
                "weight": route.get("weight"),
                "weight_name": route.get("weight_name"),
                "legs": [],
            }
            
            for leg in route.get("legs", []):
                leg_data = {
                    "duration_seconds": leg.get("duration"),
                    "duration_text": self._format_duration(leg.get("duration", 0)),
                    "distance_meters": leg.get("distance"),
                    "distance_text": self._format_distance(leg.get("distance", 0)),
                    "summary": leg.get("summary"),
                    "steps": [],
                }
                
                for step in leg.get("steps", []):
                    step_data = {
                        "instruction": step.get("maneuver", {}).get("instruction"),
                        "distance_meters": step.get("distance"),
                        "duration_seconds": step.get("duration"),
                        "maneuver_type": step.get("maneuver", {}).get("type"),
                        "maneuver_modifier": step.get("maneuver", {}).get("modifier"),
                        "name": step.get("name"),
                        "mode": step.get("mode"),
                    }
                    leg_data["steps"].append(step_data)
                
                parsed["legs"].append(leg_data)
            
            routes.append(parsed)
        
        return routes
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
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
    
    def _format_distance(self, meters: float) -> str:
        """Format distance in human-readable format"""
        if meters < 1000:
            return f"{int(meters)} m"
        else:
            km = meters / 1000
            return f"{km:.1f} km"
    
    # ================================================================
    # DISTANCE MATRIX
    # ================================================================
    
    async def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]],
        profile: str = "driving"
    ) -> Dict[str, Any]:
        """
        Calculate distances/durations between multiple origins and destinations.
        
        Args:
            origins: List of origin points (lng, lat)
            destinations: List of destination points (lng, lat)
            profile: Routing profile
            
        Returns:
            Matrix of durations and distances
        """
        if not self.is_configured():
            raise ValueError("Mapbox access token not configured")
        
        # Combine all coordinates
        all_coords = origins + destinations
        coordinates = ";".join([f"{c[0]},{c[1]}" for c in all_coords])
        
        # Build source/destination indices
        sources = list(range(len(origins)))
        dests = list(range(len(origins), len(all_coords)))
        
        params = {
            "access_token": self.access_token,
            "sources": ";".join(map(str, sources)),
            "destinations": ";".join(map(str, dests)),
            "annotations": "duration,distance",
        }
        
        url = f"{self.MATRIX_URL}/{profile}/{coordinates}"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": True,
                "durations": data.get("durations", []),
                "distances": data.get("distances", []),
                "sources": data.get("sources", []),
                "destinations": data.get("destinations", []),
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Mapbox matrix error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # ISOCHRONE (Travel Time Polygon)
    # ================================================================
    
    async def get_isochrone(
        self,
        longitude: float,
        latitude: float,
        contours_minutes: List[int] = [15, 30, 60],
        profile: str = "driving",
        polygons: bool = True,
        denoise: float = 1.0,
        generalize: float = 500
    ) -> Dict[str, Any]:
        """
        Get isochrone (area reachable within time limit) from a point.
        
        Args:
            longitude: Center point longitude
            latitude: Center point latitude
            contours_minutes: List of time contours in minutes
            profile: Routing profile
            polygons: Return polygons instead of lines
            denoise: Noise reduction (0-1)
            generalize: Generalization tolerance in meters
            
        Returns:
            GeoJSON FeatureCollection with isochrone polygons
        """
        if not self.is_configured():
            raise ValueError("Mapbox access token not configured")
        
        params = {
            "access_token": self.access_token,
            "contours_minutes": ",".join(map(str, contours_minutes)),
            "polygons": str(polygons).lower(),
            "denoise": denoise,
            "generalize": generalize,
        }
        
        url = f"{self.ISOCHRONE_URL}/{profile}/{longitude},{latitude}"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": True,
                "isochrones": data.get("features", []),
                "raw": data
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Mapbox isochrone error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # STATIC MAP
    # ================================================================
    
    async def get_static_map_url(
        self,
        longitude: float,
        latitude: float,
        zoom: int = 14,
        width: int = 600,
        height: int = 400,
        style: str = "streets-v12",
        markers: Optional[List[Dict[str, Any]]] = None,
        path: Optional[List[Tuple[float, float]]] = None,
        retina: bool = True
    ) -> str:
        """
        Generate static map image URL.
        
        Args:
            longitude: Center longitude
            latitude: Center latitude
            zoom: Zoom level (0-22)
            width: Image width in pixels (max 1280)
            height: Image height in pixels (max 1280)
            style: Map style (streets-v12, outdoors-v12, light-v11, dark-v11, satellite-v9)
            markers: List of markers [{"lng": x, "lat": y, "color": "red", "label": "A"}]
            path: List of coordinates for a path overlay
            retina: Use 2x retina image
            
        Returns:
            URL to static map image
        """
        if not self.is_configured():
            raise ValueError("Mapbox access token not configured")
        
        # Build overlays
        overlays = []
        
        # Add markers
        if markers:
            for marker in markers:
                color = marker.get("color", "ff0000")
                label = marker.get("label", "")
                lng = marker["lng"]
                lat = marker["lat"]
                overlays.append(f"pin-s-{label}+{color}({lng},{lat})")
        
        # Add path
        if path and len(path) >= 2:
            path_str = ",".join([f"{p[0]},{p[1]}" for p in path])
            overlays.append(f"path-5+0066ff-0.5({path_str})")
        
        # Build URL
        overlay_str = ",".join(overlays) if overlays else ""
        center = f"{longitude},{latitude},{zoom}"
        size = f"{width}x{height}"
        retina_str = "@2x" if retina else ""
        
        if overlay_str:
            url = f"https://api.mapbox.com/styles/v1/mapbox/{style}/static/{overlay_str}/{center}/{size}{retina_str}"
        else:
            url = f"https://api.mapbox.com/styles/v1/mapbox/{style}/static/{center}/{size}{retina_str}"
        
        return f"{url}?access_token={self.access_token}"
    
    # ================================================================
    # OPTIMIZED TRIP
    # ================================================================
    
    async def optimize_trip(
        self,
        coordinates: List[Tuple[float, float]],
        profile: str = "driving",
        roundtrip: bool = True,
        source: str = "first",
        destination: str = "last"
    ) -> Dict[str, Any]:
        """
        Optimize route through multiple waypoints (traveling salesman).
        
        Args:
            coordinates: List of points to visit (lng, lat)
            profile: Routing profile
            roundtrip: Return to starting point
            source: Where to start (first, last, any)
            destination: Where to end (first, last, any)
            
        Returns:
            Optimized route with waypoint order
        """
        if not self.is_configured():
            raise ValueError("Mapbox access token not configured")
        
        coords_str = ";".join([f"{c[0]},{c[1]}" for c in coordinates])
        
        params = {
            "access_token": self.access_token,
            "roundtrip": str(roundtrip).lower(),
            "source": source,
            "destination": destination,
            "geometries": "geojson",
            "steps": "true",
            "overview": "full",
        }
        
        url = f"{self.OPTIMIZATION_URL}/{profile}/{coords_str}"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            trips = data.get("trips", [])
            if trips:
                trip = trips[0]
                return {
                    "success": True,
                    "waypoint_order": [wp.get("waypoint_index") for wp in data.get("waypoints", [])],
                    "duration_seconds": trip.get("duration"),
                    "duration_text": self._format_duration(trip.get("duration", 0)),
                    "distance_meters": trip.get("distance"),
                    "distance_text": self._format_distance(trip.get("distance", 0)),
                    "geometry": trip.get("geometry"),
                    "raw": data
                }
            
            return {"success": False, "error": "No trips found"}
            
        except httpx.HTTPError as e:
            logger.error(f"Mapbox optimization error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # PLACE SEARCH
    # ================================================================
    
    async def search_places(
        self,
        query: str,
        near: Optional[Tuple[float, float]] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        types: Optional[List[str]] = None,
        country: Optional[str] = None,
        limit: int = 10,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Search for places and points of interest.
        
        Args:
            query: Search query
            near: Bias results near this point (lng, lat)
            bbox: Bounding box to search within (min_lng, min_lat, max_lng, max_lat)
            types: Filter by types (poi, address, place, etc.)
            country: Filter by country code
            limit: Maximum results
            language: Result language
            
        Returns:
            List of matching places
        """
        params = {
            "access_token": self.access_token,
            "limit": min(limit, 10),
            "language": language,
        }
        
        if near:
            params["proximity"] = f"{near[0]},{near[1]}"
        if bbox:
            params["bbox"] = ",".join(map(str, bbox))
        if types:
            params["types"] = ",".join(types)
        if country:
            params["country"] = country
        
        url = f"{self.GEOCODING_URL}/{query}.json"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": True,
                "places": self._parse_geocode_results(data),
                "raw": data
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Mapbox place search error: {e}")
            return {"success": False, "error": str(e), "places": []}
    
    # ================================================================
    # BATCH GEOCODING
    # ================================================================
    
    async def batch_geocode(
        self,
        addresses: List[str],
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Geocode multiple addresses in parallel.
        
        Args:
            addresses: List of addresses to geocode
            country: Country filter
            
        Returns:
            List of geocoding results
        """
        tasks = [
            self.geocode(address, country=country, limit=1)
            for address in addresses
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        parsed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                parsed_results.append({
                    "query": addresses[i],
                    "success": False,
                    "error": str(result)
                })
            elif result.get("success") and result.get("results"):
                parsed_results.append({
                    "query": addresses[i],
                    "success": True,
                    "result": result["results"][0]
                })
            else:
                parsed_results.append({
                    "query": addresses[i],
                    "success": False,
                    "error": "No results found"
                })
        
        return parsed_results


# Global client instance
mapbox_client = MapboxClient()

