"""
Queska Backend - Geolocation Endpoints
API routes for maps, location services, and place management
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_active_user, get_current_user_optional
from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.models.user import User
from app.schemas.base import SuccessResponse
from app.schemas.geolocation import (
    # Requests
    GeocodeRequest,
    ReverseGeocodeRequest,
    DirectionsRequest,
    DistanceMatrixRequest,
    PlaceSearchRequest,
    IsochroneRequest,
    StaticMapRequest,
    OptimizeRouteRequest,
    SavedPlaceCreate,
    SavedPlaceUpdate,
    UpdateLocationRequest,
    CalculateDistanceRequest,
    LocationHistoryRequest,
    # Responses
    GeocodeResponse,
    GeocodeResult,
    DirectionsResponse,
    RouteResult,
    DistanceMatrixResponse,
    MatrixElement,
    PlaceSearchResponse,
    PlaceResult,
    PlaceDetailsResponse,
    IsochroneResponse,
    StaticMapResponse,
    OptimizeRouteResponse,
    SavedPlaceResponse,
    PaginatedSavedPlacesResponse,
    LocationUpdateResponse,
    LocationHistoryResponse,
    LocationHistoryPoint,
    DistanceResult,
    CoordinatesSchema,
    AddressSchema,
    NEARBY_CATEGORIES,
)
from app.services.geolocation_service import geolocation_service

router = APIRouter()


# ================================================================
# GEOCODING
# ================================================================

@router.post(
    "/geocode",
    response_model=GeocodeResponse,
    summary="Geocode address",
    description="Convert an address or place name to geographic coordinates",
)
async def geocode_address(data: GeocodeRequest):
    """
    Geocode an address to get coordinates.
    """
    try:
        result = await geolocation_service.geocode(
            query=data.query,
            country=data.country,
            limit=data.limit,
            proximity=(data.proximity_lng, data.proximity_lat) if data.proximity_lat and data.proximity_lng else None,
            types=data.types,
            language=data.language
        )
        
        return GeocodeResponse(
            success=result.get("success", False),
            results=[
                GeocodeResult(**r) for r in result.get("results", [])
            ],
            error=result.get("error")
        )
        
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.get(
    "/geocode",
    response_model=GeocodeResponse,
    summary="Geocode address (GET)",
    description="Convert an address or place name to coordinates (GET method)",
)
async def geocode_address_get(
    query: str = Query(..., min_length=2, max_length=500),
    country: Optional[str] = Query(None, max_length=2),
    limit: int = Query(5, ge=1, le=10),
    proximity_lat: Optional[float] = Query(None, ge=-90, le=90),
    proximity_lng: Optional[float] = Query(None, ge=-180, le=180),
    language: str = Query("en")
):
    """Geocode address via GET request."""
    data = GeocodeRequest(
        query=query,
        country=country,
        limit=limit,
        proximity_lat=proximity_lat,
        proximity_lng=proximity_lng,
        language=language
    )
    return await geocode_address(data)


@router.post(
    "/reverse-geocode",
    response_model=GeocodeResponse,
    summary="Reverse geocode",
    description="Convert coordinates to an address",
)
async def reverse_geocode(data: ReverseGeocodeRequest):
    """
    Reverse geocode coordinates to get an address.
    """
    try:
        result = await geolocation_service.reverse_geocode(
            latitude=data.latitude,
            longitude=data.longitude,
            types=data.types,
            language=data.language
        )
        
        return GeocodeResponse(
            success=result.get("success", False),
            results=[
                GeocodeResult(**r) for r in result.get("results", [])
            ],
            error=result.get("error")
        )
        
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.get(
    "/reverse-geocode",
    response_model=GeocodeResponse,
    summary="Reverse geocode (GET)",
)
async def reverse_geocode_get(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    language: str = Query("en")
):
    """Reverse geocode via GET request."""
    data = ReverseGeocodeRequest(latitude=latitude, longitude=longitude, language=language)
    return await reverse_geocode(data)


# ================================================================
# DIRECTIONS
# ================================================================

@router.post(
    "/directions",
    response_model=DirectionsResponse,
    summary="Get directions",
    description="Get route directions between two or more points",
)
async def get_directions(data: DirectionsRequest):
    """
    Get route directions with turn-by-turn navigation.
    """
    try:
        # Convert waypoints
        waypoints = None
        if data.waypoints:
            waypoints = [(wp["lat"], wp["lng"]) for wp in data.waypoints]
        
        result = await geolocation_service.get_directions(
            origin=(data.origin_lat, data.origin_lng),
            destination=(data.destination_lat, data.destination_lng),
            waypoints=waypoints,
            profile=data.profile,
            alternatives=data.alternatives,
            steps=data.steps,
            language=data.language
        )
        
        return DirectionsResponse(
            success=result.get("success", False),
            routes=[RouteResult(**r) for r in result.get("routes", [])],
            error=result.get("error")
        )
        
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.get(
    "/directions",
    response_model=DirectionsResponse,
    summary="Get directions (GET)",
)
async def get_directions_get(
    origin_lat: float = Query(..., ge=-90, le=90),
    origin_lng: float = Query(..., ge=-180, le=180),
    destination_lat: float = Query(..., ge=-90, le=90),
    destination_lng: float = Query(..., ge=-180, le=180),
    profile: str = Query("driving"),
    alternatives: bool = Query(True),
    language: str = Query("en")
):
    """Get directions via GET request."""
    data = DirectionsRequest(
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        destination_lat=destination_lat,
        destination_lng=destination_lng,
        profile=profile,
        alternatives=alternatives,
        language=language
    )
    return await get_directions(data)


# ================================================================
# DISTANCE
# ================================================================

@router.get(
    "/distance",
    response_model=DistanceResult,
    summary="Calculate distance",
    description="Calculate distance and travel time between two points",
)
async def calculate_distance(
    from_lat: float = Query(..., ge=-90, le=90),
    from_lng: float = Query(..., ge=-180, le=180),
    to_lat: float = Query(..., ge=-90, le=90),
    to_lng: float = Query(..., ge=-180, le=180),
    profile: str = Query("driving")
):
    """
    Calculate distance and travel time between two points.
    """
    return await geolocation_service.calculate_distance(
        from_lat=from_lat,
        from_lng=from_lng,
        to_lat=to_lat,
        to_lng=to_lng,
        profile=profile
    )


@router.post(
    "/distance-matrix",
    response_model=DistanceMatrixResponse,
    summary="Distance matrix",
    description="Calculate distances between multiple origins and destinations",
)
async def get_distance_matrix(data: DistanceMatrixRequest):
    """
    Get distance matrix between multiple points.
    """
    try:
        origins = [(o["lat"], o["lng"]) for o in data.origins]
        destinations = [(d["lat"], d["lng"]) for d in data.destinations]
        
        result = await geolocation_service.get_distance_matrix(
            origins=origins,
            destinations=destinations,
            profile=data.profile
        )
        
        # Parse matrix
        matrix = []
        raw_matrix = result.get("matrix", [])
        if raw_matrix:
            for row in raw_matrix:
                matrix.append([MatrixElement(**elem) if isinstance(elem, dict) else MatrixElement() for elem in row])
        
        return DistanceMatrixResponse(
            success=result.get("success", False),
            matrix=matrix,
            error=result.get("error")
        )
        
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


# ================================================================
# PLACE SEARCH
# ================================================================

@router.post(
    "/places/search",
    response_model=PlaceSearchResponse,
    summary="Search places",
    description="Search for places and points of interest",
)
async def search_places(data: PlaceSearchRequest):
    """
    Search for places near a location or by text query.
    """
    try:
        result = await geolocation_service.search_places(
            query=data.query,
            latitude=data.latitude,
            longitude=data.longitude,
            radius=data.radius,
            category=data.category,
            limit=data.limit,
            language=data.language
        )
        
        places = []
        for p in result.get("places", []):
            coords = p.get("coordinates", {})
            places.append(PlaceResult(
                place_id=p.get("place_id", ""),
                name=p.get("name", ""),
                formatted_address=p.get("formatted_address") or p.get("full_name"),
                vicinity=p.get("vicinity"),
                coordinates=CoordinatesSchema(
                    latitude=coords.get("latitude", 0),
                    longitude=coords.get("longitude", 0)
                ),
                types=p.get("types", []),
                rating=p.get("rating"),
                user_ratings_total=p.get("user_ratings_total"),
                price_level=p.get("price_level"),
                open_now=p.get("open_now"),
                distance_meters=p.get("distance_meters")
            ))
        
        return PlaceSearchResponse(
            success=result.get("success", False),
            places=places,
            error=result.get("error")
        )
        
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.get(
    "/places/search",
    response_model=PlaceSearchResponse,
    summary="Search places (GET)",
)
async def search_places_get(
    query: Optional[str] = Query(None),
    latitude: Optional[float] = Query(None, ge=-90, le=90),
    longitude: Optional[float] = Query(None, ge=-180, le=180),
    radius: int = Query(5000, ge=100, le=50000),
    category: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    language: str = Query("en")
):
    """Search places via GET."""
    data = PlaceSearchRequest(
        query=query,
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        category=category,
        limit=limit,
        language=language
    )
    return await search_places(data)


@router.get(
    "/places/nearby",
    response_model=PlaceSearchResponse,
    summary="Nearby places",
    description="Find places near a specific location",
)
async def get_nearby_places(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    category: Optional[str] = Query(None),
    radius: int = Query(5000, ge=100, le=50000),
    limit: int = Query(20, ge=1, le=50)
):
    """Get places near a location."""
    data = PlaceSearchRequest(
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        category=category,
        limit=limit
    )
    return await search_places(data)


@router.get(
    "/places/categories",
    response_model=List[Dict[str, Any]],
    summary="Place categories",
    description="Get available place categories for search",
)
async def get_place_categories():
    """Get list of place categories."""
    return geolocation_service.get_nearby_categories()


@router.get(
    "/places/{place_id}",
    response_model=PlaceDetailsResponse,
    summary="Place details",
    description="Get detailed information about a specific place",
)
async def get_place_details(
    place_id: str,
    provider: str = Query("google")
):
    """Get details for a specific place."""
    result = await geolocation_service.get_place_details(place_id, provider)
    return PlaceDetailsResponse(
        success=result.get("success", False),
        place=result.get("place"),
        error=result.get("error")
    )


# ================================================================
# ISOCHRONES
# ================================================================

@router.post(
    "/isochrone",
    response_model=IsochroneResponse,
    summary="Get isochrone",
    description="Get areas reachable within specified time limits",
)
async def get_isochrone(data: IsochroneRequest):
    """
    Get isochrone polygons showing reachable areas within time limits.
    """
    result = await geolocation_service.get_isochrone(
        latitude=data.latitude,
        longitude=data.longitude,
        contours_minutes=data.contours_minutes,
        profile=data.profile
    )
    
    return IsochroneResponse(
        success=result.get("success", False),
        isochrones=result.get("isochrones", []),
        error=result.get("error")
    )


@router.get(
    "/isochrone",
    response_model=IsochroneResponse,
    summary="Get isochrone (GET)",
)
async def get_isochrone_get(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    minutes: List[int] = Query([15, 30, 60]),
    profile: str = Query("driving")
):
    """Get isochrone via GET."""
    data = IsochroneRequest(
        latitude=latitude,
        longitude=longitude,
        contours_minutes=minutes,
        profile=profile
    )
    return await get_isochrone(data)


# ================================================================
# STATIC MAPS
# ================================================================

@router.post(
    "/static-map",
    response_model=StaticMapResponse,
    summary="Get static map",
    description="Generate a static map image URL",
)
async def get_static_map(data: StaticMapRequest):
    """
    Generate a static map image URL.
    """
    url = await geolocation_service.get_static_map_url(
        latitude=data.latitude,
        longitude=data.longitude,
        zoom=data.zoom,
        width=data.width,
        height=data.height,
        style=data.style,
        markers=data.markers
    )
    
    return StaticMapResponse(url=url, width=data.width, height=data.height)


@router.get(
    "/static-map",
    response_model=StaticMapResponse,
    summary="Get static map (GET)",
)
async def get_static_map_get(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    zoom: int = Query(14, ge=0, le=22),
    width: int = Query(600, ge=100, le=1280),
    height: int = Query(400, ge=100, le=1280),
    style: str = Query("streets-v12")
):
    """Get static map via GET."""
    data = StaticMapRequest(
        latitude=latitude,
        longitude=longitude,
        zoom=zoom,
        width=width,
        height=height,
        style=style
    )
    return await get_static_map(data)


# ================================================================
# ROUTE OPTIMIZATION
# ================================================================

@router.post(
    "/optimize-route",
    response_model=OptimizeRouteResponse,
    summary="Optimize route",
    description="Optimize route through multiple waypoints",
)
async def optimize_route(data: OptimizeRouteRequest):
    """
    Optimize route through multiple waypoints (traveling salesman problem).
    """
    result = await geolocation_service.optimize_route(
        waypoints=data.waypoints,
        profile=data.profile,
        roundtrip=data.roundtrip
    )
    
    return OptimizeRouteResponse(
        success=result.get("success", False),
        optimized_order=result.get("waypoint_order", []),
        duration_seconds=result.get("duration_seconds"),
        duration_text=result.get("duration_text"),
        distance_meters=result.get("distance_meters"),
        distance_text=result.get("distance_text"),
        geometry=result.get("geometry"),
        error=result.get("error")
    )


# ================================================================
# SAVED PLACES (Authenticated)
# ================================================================

@router.post(
    "/saved-places",
    response_model=SavedPlaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a place",
    description="Save a place to your favorites",
)
async def save_place(
    data: SavedPlaceCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Save a place to favorites."""
    place = await geolocation_service.save_place(
        user_id=str(current_user.id),
        data=data
    )
    
    return SavedPlaceResponse(
        id=str(place.id),
        name=place.name,
        place_id=place.place_id,
        coordinates=CoordinatesSchema(
            latitude=place.coordinates.latitude,
            longitude=place.coordinates.longitude
        ),
        address=AddressSchema(**place.address.model_dump()) if place.address else None,
        category=place.category,
        custom_category=place.custom_category,
        label=place.label,
        notes=place.notes,
        tags=place.tags,
        is_favorite=place.is_favorite,
        visit_count=place.visit_count,
        last_visited_at=place.last_visited_at,
        created_at=place.created_at,
        updated_at=place.updated_at
    )


@router.get(
    "/saved-places",
    response_model=PaginatedSavedPlacesResponse,
    summary="Get saved places",
    description="Get your saved places",
)
async def get_saved_places(
    current_user: User = Depends(get_current_active_user),
    category: Optional[str] = Query(None),
    is_favorite: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Get saved places."""
    places, total = await geolocation_service.get_saved_places(
        user_id=str(current_user.id),
        category=category,
        is_favorite=is_favorite,
        skip=skip,
        limit=limit
    )
    
    return PaginatedSavedPlacesResponse(
        data=[
            SavedPlaceResponse(
                id=str(p.id),
                name=p.name,
                place_id=p.place_id,
                coordinates=CoordinatesSchema(
                    latitude=p.coordinates.latitude,
                    longitude=p.coordinates.longitude
                ),
                address=AddressSchema(**p.address.model_dump()) if p.address else None,
                category=p.category,
                custom_category=p.custom_category,
                label=p.label,
                notes=p.notes,
                tags=p.tags,
                is_favorite=p.is_favorite,
                visit_count=p.visit_count,
                last_visited_at=p.last_visited_at,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in places
        ],
        total=total,
        skip=skip,
        limit=limit
    )


@router.put(
    "/saved-places/{place_id}",
    response_model=SavedPlaceResponse,
    summary="Update saved place",
)
async def update_saved_place(
    place_id: str,
    data: SavedPlaceUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update a saved place."""
    try:
        place = await geolocation_service.update_saved_place(
            user_id=str(current_user.id),
            place_id=place_id,
            data=data
        )
        
        return SavedPlaceResponse(
            id=str(place.id),
            name=place.name,
            place_id=place.place_id,
            coordinates=CoordinatesSchema(
                latitude=place.coordinates.latitude,
                longitude=place.coordinates.longitude
            ),
            address=AddressSchema(**place.address.model_dump()) if place.address else None,
            category=place.category,
            custom_category=place.custom_category,
            label=place.label,
            notes=place.notes,
            tags=place.tags,
            is_favorite=place.is_favorite,
            visit_count=place.visit_count,
            last_visited_at=place.last_visited_at,
            created_at=place.created_at,
            updated_at=place.updated_at
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/saved-places/{place_id}",
    response_model=SuccessResponse,
    summary="Delete saved place",
)
async def delete_saved_place(
    place_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete a saved place."""
    try:
        await geolocation_service.delete_saved_place(
            user_id=str(current_user.id),
            place_id=place_id
        )
        return SuccessResponse(message="Place deleted successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ================================================================
# LOCATION TRACKING (Authenticated)
# ================================================================

@router.post(
    "/location/update",
    response_model=LocationUpdateResponse,
    summary="Update my location",
    description="Record current location for tracking",
)
async def update_my_location(
    data: UpdateLocationRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Record user's current location."""
    location = await geolocation_service.update_user_location(
        user_id=str(current_user.id),
        data=data
    )
    
    # Get nearby places
    nearby_result = await geolocation_service.search_places(
        latitude=data.latitude,
        longitude=data.longitude,
        radius=500,
        limit=5
    )
    
    nearby_places = []
    for p in nearby_result.get("places", []):
        coords = p.get("coordinates", {})
        nearby_places.append(PlaceResult(
            place_id=p.get("place_id", ""),
            name=p.get("name", ""),
            coordinates=CoordinatesSchema(
                latitude=coords.get("latitude", 0),
                longitude=coords.get("longitude", 0)
            ),
            types=p.get("types", []),
            distance_meters=p.get("distance_meters")
        ))
    
    return LocationUpdateResponse(
        success=True,
        recorded_at=location.recorded_at,
        address=AddressSchema(**location.address.model_dump()) if location.address else None,
        nearby_places=nearby_places
    )


@router.get(
    "/location/history",
    response_model=LocationHistoryResponse,
    summary="Get location history",
)
async def get_location_history(
    current_user: User = Depends(get_current_active_user),
    experience_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get location history."""
    locations = await geolocation_service.get_location_history(
        user_id=str(current_user.id),
        experience_id=experience_id,
        limit=limit
    )
    
    # Calculate total distance
    total_distance = 0
    if len(locations) >= 2:
        for i in range(1, len(locations)):
            prev = locations[i-1].coordinates
            curr = locations[i].coordinates
            total_distance += geolocation_service.calculate_straight_line_distance(
                prev.latitude, prev.longitude,
                curr.latitude, curr.longitude
            )
    
    return LocationHistoryResponse(
        success=True,
        points=[
            LocationHistoryPoint(
                coordinates=CoordinatesSchema(
                    latitude=loc.coordinates.latitude,
                    longitude=loc.coordinates.longitude
                ),
                address=AddressSchema(**loc.address.model_dump()) if loc.address else None,
                recorded_at=loc.recorded_at,
                activity_type=loc.activity_type
            )
            for loc in locations
        ],
        total_distance_km=round(total_distance, 2)
    )


# ================================================================
# SERVICE STATUS
# ================================================================

@router.get(
    "/status",
    response_model=Dict[str, Any],
    summary="Service status",
    description="Check status of map service providers",
)
async def get_service_status():
    """Get status of map services."""
    return await geolocation_service.get_service_status()

