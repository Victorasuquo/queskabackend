"""
Queska Backend - Travel Search Endpoints
API routes for searching flights, hotels, activities, cars, and packages via Expedia
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.deps import get_current_active_user, get_current_user_optional
from app.core.exceptions import ServiceUnavailableError
from app.models.user import User
from app.schemas.travel import (
    # Request schemas
    HotelSearchRequest,
    HotelDetailsRequest,
    FlightSearchRequest,
    ActivitySearchRequest,
    CarSearchRequest,
    PackageSearchRequest,
    DestinationSearchRequest,
    HotelBookingRequest,
    BookingRetrieveRequest,
    BookingCancelRequest,
    # Response schemas
    HotelSearchResponse,
    HotelDetailsResponse,
    HotelSchema,
    FlightSearchResponse,
    FlightSchema,
    ActivitySearchResponse,
    ActivitySchema,
    CarSearchResponse,
    CarSchema,
    PackageSearchResponse,
    PackageSchema,
    DestinationSearchResponse,
    DestinationSchema,
    HotelBookingResponse,
    BookingCancelResponse,
    TravelServiceStatus,
    PriceSchema,
    LocationSchema,
    RatingSchema,
)
from app.services.travel_service import travel_service

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


# ================================================================
# HOTELS
# ================================================================

@router.post(
    "/hotels/search",
    response_model=HotelSearchResponse,
    summary="Search hotels",
    description="Search for available hotels using Expedia's global inventory",
)
async def search_hotels(
    data: HotelSearchRequest,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Search for hotels with comprehensive filtering options.
    
    Returns hotels from Expedia's inventory with:
    - Real-time availability and pricing
    - Room options and rates
    - Guest ratings and reviews
    - Amenities and features
    """
    customer_ip = get_client_ip(request)
    
    result = await travel_service.search_hotels(
        destination=data.destination,
        checkin=data.checkin,
        checkout=data.checkout,
        adults=data.adults,
        children=data.children,
        children_ages=data.children_ages,
        rooms=data.rooms,
        currency=data.currency,
        star_rating_min=data.star_rating_min,
        price_min=data.price_min,
        price_max=data.price_max,
        amenities=data.amenities,
        sort_by=data.sort_by,
        limit=data.limit,
        customer_ip=customer_ip
    )
    
    return HotelSearchResponse(
        success=result.get("success", False),
        hotels=result.get("hotels", []),
        total=result.get("total", 0),
        search_params=result.get("search_params"),
        error=result.get("error")
    )


@router.get(
    "/hotels/search",
    response_model=HotelSearchResponse,
    summary="Search hotels (GET)",
    description="Search hotels via GET request with query parameters",
)
async def search_hotels_get(
    request: Request,
    destination: str = Query(..., description="City or destination"),
    checkin: date = Query(..., description="Check-in date"),
    checkout: date = Query(..., description="Check-out date"),
    adults: int = Query(2, ge=1, le=10),
    children: int = Query(0, ge=0, le=6),
    rooms: int = Query(1, ge=1, le=8),
    currency: str = Query("USD", max_length=3),
    star_rating_min: Optional[int] = Query(None, ge=1, le=5),
    price_max: Optional[float] = Query(None),
    sort_by: str = Query("recommended"),
    limit: int = Query(50, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Search hotels via GET."""
    data = HotelSearchRequest(
        destination=destination,
        checkin=checkin,
        checkout=checkout,
        adults=adults,
        children=children,
        rooms=rooms,
        currency=currency,
        star_rating_min=star_rating_min,
        price_max=price_max,
        sort_by=sort_by,
        limit=limit
    )
    return await search_hotels(data, request, current_user)


@router.get(
    "/hotels/{property_id}",
    response_model=HotelDetailsResponse,
    summary="Get hotel details",
    description="Get detailed information about a specific hotel",
)
async def get_hotel_details(
    property_id: str,
    request: Request,
    checkin: Optional[date] = Query(None),
    checkout: Optional[date] = Query(None),
    adults: int = Query(2, ge=1),
    rooms: int = Query(1, ge=1),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get detailed hotel information including:
    - Full property description
    - All images
    - Complete amenity list
    - Room types and rates (if dates provided)
    - Guest reviews
    - Policies
    """
    customer_ip = get_client_ip(request)
    
    result = await travel_service.get_hotel_details(
            property_id=property_id,
        checkin=checkin,
        checkout=checkout,
        adults=adults,
            rooms=rooms,
        customer_ip=customer_ip
    )
    
    return HotelDetailsResponse(
        success=result.get("success", False),
        hotel=result.get("hotel"),
        error=result.get("error")
    )


# ================================================================
# FLIGHTS
# ================================================================

@router.post(
    "/flights/search",
    response_model=FlightSearchResponse,
    summary="Search flights",
    description="Search for available flights",
)
async def search_flights(
    data: FlightSearchRequest,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Search for flights with options for:
    - One-way or round-trip
    - Multiple cabin classes
    - Nonstop filtering
    - Price filtering
    
    Returns deep links to Expedia for booking.
    """
    result = await travel_service.search_flights(
        origin=data.origin,
        destination=data.destination,
        departure_date=data.departure_date,
        return_date=data.return_date,
        adults=data.adults,
        children=data.children,
        infants=data.infants,
        cabin_class=data.cabin_class,
        nonstop_only=data.nonstop_only,
        max_price=data.max_price,
        currency=data.currency,
        sort_by=data.sort_by,
        limit=data.limit
    )
    
    return FlightSearchResponse(
        success=result.get("success", False),
        flights=result.get("flights", []),
        total=result.get("total", 0),
        search_params=result.get("search_params"),
        error=result.get("error")
    )


@router.get(
    "/flights/search",
    response_model=FlightSearchResponse,
    summary="Search flights (GET)",
)
async def search_flights_get(
    request: Request,
    origin: str = Query(..., min_length=3, max_length=3, description="Origin airport code"),
    destination: str = Query(..., min_length=3, max_length=3, description="Destination airport code"),
    departure_date: date = Query(...),
    return_date: Optional[date] = Query(None),
    adults: int = Query(1, ge=1, le=9),
    children: int = Query(0, ge=0, le=8),
    infants: int = Query(0, ge=0, le=4),
    cabin_class: str = Query("economy"),
    nonstop_only: bool = Query(False),
    max_price: Optional[float] = Query(None),
    currency: str = Query("USD"),
    sort_by: str = Query("price"),
    limit: int = Query(50, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Search flights via GET."""
    data = FlightSearchRequest(
        origin=origin,
        destination=destination,
            departure_date=departure_date,
            return_date=return_date,
        adults=adults,
        children=children,
        infants=infants,
            cabin_class=cabin_class,
        nonstop_only=nonstop_only,
        max_price=max_price,
        currency=currency,
        sort_by=sort_by,
        limit=limit
    )
    return await search_flights(data, request, current_user)


# ================================================================
# ACTIVITIES
# ================================================================

@router.post(
    "/activities/search",
    response_model=ActivitySearchResponse,
    summary="Search activities",
    description="Search for activities, tours, and things to do",
)
async def search_activities(
    data: ActivitySearchRequest,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Search for activities and tours including:
    - Tours and sightseeing
    - Attractions and tickets
    - Outdoor activities
    - Food and dining experiences
    - Workshops and classes
    """
    result = await travel_service.search_activities(
        destination=data.destination,
        activity_date=data.date,
        category=data.category,
        price_max=data.price_max,
        currency=data.currency,
        sort_by=data.sort_by,
        limit=data.limit
    )
    
    return ActivitySearchResponse(
        success=result.get("success", False),
        activities=result.get("activities", []),
        total=result.get("total", 0),
        search_params=result.get("search_params"),
        error=result.get("error")
    )


@router.get(
    "/activities/search",
    response_model=ActivitySearchResponse,
    summary="Search activities (GET)",
)
async def search_activities_get(
    request: Request,
    destination: str = Query(...),
    date: date = Query(..., alias="activity_date"),
    category: Optional[str] = Query(None),
    price_max: Optional[float] = Query(None),
    currency: str = Query("USD"),
    sort_by: str = Query("recommended"),
    limit: int = Query(50, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Search activities via GET."""
    data = ActivitySearchRequest(
        destination=destination,
        date=date,
        category=category,
        price_max=price_max,
        currency=currency,
        sort_by=sort_by,
        limit=limit
    )
    return await search_activities(data, request, current_user)


@router.get(
    "/activities/categories",
    response_model=List[Dict[str, str]],
    summary="Get activity categories",
)
async def get_activity_categories():
    """Get available activity categories."""
    return [
        {"id": "tours", "name": "Tours & Sightseeing", "icon": "🗺️"},
        {"id": "attractions", "name": "Attractions & Tickets", "icon": "🎭"},
        {"id": "outdoor", "name": "Outdoor Activities", "icon": "🏔️"},
        {"id": "adventure", "name": "Adventure & Sports", "icon": "🚴"},
        {"id": "water", "name": "Water Activities", "icon": "🚤"},
        {"id": "food", "name": "Food & Dining", "icon": "🍽️"},
        {"id": "nightlife", "name": "Nightlife & Entertainment", "icon": "🎉"},
        {"id": "cultural", "name": "Cultural Experiences", "icon": "🏛️"},
        {"id": "wellness", "name": "Wellness & Spa", "icon": "💆"},
        {"id": "workshops", "name": "Workshops & Classes", "icon": "🎨"},
        {"id": "day_trips", "name": "Day Trips", "icon": "🚌"},
        {"id": "cruises", "name": "Cruises & Water Tours", "icon": "🚢"},
    ]


# ================================================================
# CAR RENTALS
# ================================================================

@router.post(
    "/cars/search",
    response_model=CarSearchResponse,
    summary="Search car rentals",
    description="Search for available car rentals",
)
async def search_cars(
    data: CarSearchRequest,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Search for car rentals with:
    - Various vehicle classes
    - Different suppliers
    - Flexible pickup/dropoff locations
    - Insurance options
    """
    result = await travel_service.search_cars(
        pickup_location=data.pickup_location,
        pickup_date=data.pickup_date,
        pickup_time=data.pickup_time,
        dropoff_date=data.dropoff_date,
        dropoff_time=data.dropoff_time,
        dropoff_location=data.dropoff_location,
        car_class=data.car_class,
        currency=data.currency,
        sort_by=data.sort_by,
        limit=data.limit
    )
    
    return CarSearchResponse(
        success=result.get("success", False),
        cars=result.get("cars", []),
        total=result.get("total", 0),
        search_params=result.get("search_params"),
        error=result.get("error")
    )


@router.get(
    "/cars/search",
    response_model=CarSearchResponse,
    summary="Search car rentals (GET)",
)
async def search_cars_get(
    request: Request,
    pickup_location: str = Query(..., description="Airport code or city"),
    pickup_date: date = Query(...),
    pickup_time: str = Query(..., description="HH:MM format"),
    dropoff_date: date = Query(...),
    dropoff_time: str = Query(..., description="HH:MM format"),
    dropoff_location: Optional[str] = Query(None),
    car_class: Optional[str] = Query(None),
    currency: str = Query("USD"),
    sort_by: str = Query("price"),
    limit: int = Query(50, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Search car rentals via GET."""
    data = CarSearchRequest(
            pickup_location=pickup_location,
            pickup_date=pickup_date,
            pickup_time=pickup_time,
            dropoff_date=dropoff_date,
            dropoff_time=dropoff_time,
        dropoff_location=dropoff_location,
        car_class=car_class,
        currency=currency,
        sort_by=sort_by,
        limit=limit
    )
    return await search_cars(data, request, current_user)


@router.get(
    "/cars/classes",
    response_model=List[Dict[str, str]],
    summary="Get car classes",
)
async def get_car_classes():
    """Get available car classes."""
    return [
        {"id": "economy", "name": "Economy", "description": "Small, fuel-efficient cars", "icon": "🚗"},
        {"id": "compact", "name": "Compact", "description": "Slightly larger than economy", "icon": "🚗"},
        {"id": "midsize", "name": "Midsize", "description": "Comfortable for families", "icon": "🚙"},
        {"id": "full", "name": "Full Size", "description": "Spacious sedan", "icon": "🚙"},
        {"id": "luxury", "name": "Luxury", "description": "Premium vehicles", "icon": "🏎️"},
        {"id": "suv", "name": "SUV", "description": "Sport utility vehicles", "icon": "🚐"},
        {"id": "van", "name": "Van/Minivan", "description": "Large capacity vehicles", "icon": "🚐"},
        {"id": "convertible", "name": "Convertible", "description": "Open-top vehicles", "icon": "🏎️"},
    ]


# ================================================================
# PACKAGES (Flight + Hotel)
# ================================================================

@router.post(
    "/packages/search",
    response_model=PackageSearchResponse,
    summary="Search vacation packages",
    description="Search for flight + hotel vacation packages",
)
async def search_packages(
    data: PackageSearchRequest,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Search for vacation packages that combine:
    - Round-trip flights
    - Hotel accommodation
    
    Often provides savings vs booking separately.
    """
    result = await travel_service.search_packages(
        origin=data.origin,
        destination=data.destination,
        departure_date=data.departure_date,
        return_date=data.return_date,
        adults=data.adults,
        children=data.children,
        rooms=data.rooms,
        currency=data.currency,
        limit=data.limit
    )
    
    return PackageSearchResponse(
        success=result.get("success", False),
        packages=result.get("packages", []),
        total=result.get("total", 0),
        search_params=result.get("search_params"),
        error=result.get("error")
    )


@router.get(
    "/packages/search",
    response_model=PackageSearchResponse,
    summary="Search vacation packages (GET)",
)
async def search_packages_get(
    request: Request,
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(...),
    departure_date: date = Query(...),
    return_date: date = Query(...),
    adults: int = Query(2, ge=1, le=8),
    children: int = Query(0, ge=0, le=6),
    rooms: int = Query(1, ge=1, le=4),
    currency: str = Query("USD"),
    limit: int = Query(30, ge=1, le=50),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Search packages via GET."""
    data = PackageSearchRequest(
        origin=origin,
            destination=destination,
        departure_date=departure_date,
        return_date=return_date,
            adults=adults,
            children=children,
        rooms=rooms,
        currency=currency,
        limit=limit
    )
    return await search_packages(data, request, current_user)


# ================================================================
# DESTINATIONS
# ================================================================

@router.get(
    "/destinations/search",
    response_model=DestinationSearchResponse,
    summary="Search destinations",
    description="Search for cities, airports, and points of interest",
)
async def search_destinations(
    query: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Search for destinations to use in other searches.
    
    Returns:
    - Cities
    - Airports
    - Regions
    - Points of interest
    """
    result = await travel_service.search_destinations(
        query=query,
        limit=limit
    )
    
    return DestinationSearchResponse(
        success=result.get("success", False),
        destinations=result.get("destinations", []),
        error=result.get("error")
    )


@router.get(
    "/destinations/popular",
    response_model=List[Dict[str, Any]],
    summary="Get popular destinations",
)
async def get_popular_destinations():
    """Get list of popular travel destinations."""
    return [
        {
            "id": "nyc",
            "name": "New York City",
            "country": "United States",
            "code": "NYC",
            "image": "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9",
            "category": "city"
        },
        {
            "id": "paris",
            "name": "Paris",
            "country": "France",
            "code": "PAR",
            "image": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34",
            "category": "city"
        },
        {
            "id": "london",
            "name": "London",
            "country": "United Kingdom",
            "code": "LON",
            "image": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad",
            "category": "city"
        },
        {
            "id": "tokyo",
            "name": "Tokyo",
            "country": "Japan",
            "code": "TYO",
            "image": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf",
            "category": "city"
        },
        {
            "id": "dubai",
            "name": "Dubai",
            "country": "United Arab Emirates",
            "code": "DXB",
            "image": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c",
            "category": "city"
        },
        {
            "id": "bali",
            "name": "Bali",
            "country": "Indonesia",
            "code": "DPS",
            "image": "https://images.unsplash.com/photo-1537996194471-e657df975ab4",
            "category": "island"
        },
        {
            "id": "rome",
            "name": "Rome",
            "country": "Italy",
            "code": "ROM",
            "image": "https://images.unsplash.com/photo-1552832230-c0197dd311b5",
            "category": "city"
        },
        {
            "id": "cancun",
            "name": "Cancún",
            "country": "Mexico",
            "code": "CUN",
            "image": "https://images.unsplash.com/photo-1552074284-5e88ef1aef18",
            "category": "beach"
        },
        {
            "id": "lagos",
            "name": "Lagos",
            "country": "Nigeria",
            "code": "LOS",
            "image": "https://images.unsplash.com/photo-1618828665011-0abd973f7bb8",
            "category": "city"
        },
        {
            "id": "cape_town",
            "name": "Cape Town",
            "country": "South Africa",
            "code": "CPT",
            "image": "https://images.unsplash.com/photo-1580060839134-75a5edca2e99",
            "category": "city"
        },
    ]


# ================================================================
# SERVICE STATUS
# ================================================================


@router.get(
    "/status",
    response_model=Dict[str, Any],
    summary="Get service status",
    description="Check status of travel API providers",
)
async def get_service_status():
    """Get status of all travel API services."""
    return await travel_service.get_service_status()


@router.get(
    "/airports",
    response_model=List[Dict[str, str]],
    summary="Get popular airports",
)
async def get_popular_airports():
    """Get list of popular airports."""
    return [
        {"code": "JFK", "name": "John F. Kennedy International", "city": "New York", "country": "US"},
        {"code": "LAX", "name": "Los Angeles International", "city": "Los Angeles", "country": "US"},
        {"code": "LHR", "name": "London Heathrow", "city": "London", "country": "GB"},
        {"code": "CDG", "name": "Charles de Gaulle", "city": "Paris", "country": "FR"},
        {"code": "DXB", "name": "Dubai International", "city": "Dubai", "country": "AE"},
        {"code": "SIN", "name": "Singapore Changi", "city": "Singapore", "country": "SG"},
        {"code": "HND", "name": "Tokyo Haneda", "city": "Tokyo", "country": "JP"},
        {"code": "NRT", "name": "Tokyo Narita", "city": "Tokyo", "country": "JP"},
        {"code": "SYD", "name": "Sydney Kingsford Smith", "city": "Sydney", "country": "AU"},
        {"code": "LOS", "name": "Murtala Muhammed International", "city": "Lagos", "country": "NG"},
        {"code": "JNB", "name": "O.R. Tambo International", "city": "Johannesburg", "country": "ZA"},
        {"code": "CPT", "name": "Cape Town International", "city": "Cape Town", "country": "ZA"},
        {"code": "NBO", "name": "Jomo Kenyatta International", "city": "Nairobi", "country": "KE"},
        {"code": "ACC", "name": "Kotoka International", "city": "Accra", "country": "GH"},
        {"code": "CAI", "name": "Cairo International", "city": "Cairo", "country": "EG"},
    ]


# ================================================================
# RAPIDAPI HOTELS - FREE TIER (Direct Access)
# ================================================================

from integrations.travel_apis.rapidapi_hotels import rapidapi_hotels


@router.get(
    "/rapidapi/locations",
    summary="Search locations (RapidAPI)",
    description="Search for destinations/locations to get dest_id for hotel search",
)
async def rapidapi_search_locations(
    query: str = Query(..., description="City, region, or hotel name"),
    locale: str = Query("en-us", description="Language locale")
):
    """
    Search for locations using RapidAPI Booking.com.
    Returns dest_id needed for hotel search.
    
    FREE: 500 requests/month
    """
    result = await rapidapi_hotels.search_locations(query=query, locale=locale)
    return result


@router.get(
    "/rapidapi/hotels",
    summary="Search hotels (RapidAPI FREE)",
    description="Search hotels with REAL data from Booking.com via RapidAPI",
)
async def rapidapi_search_hotels(
    dest_id: str = Query(..., description="Destination ID from /rapidapi/locations"),
    dest_type: str = Query("city", description="Type: city, region, landmark, hotel"),
    checkin: date = Query(..., description="Check-in date (YYYY-MM-DD)"),
    checkout: date = Query(..., description="Check-out date (YYYY-MM-DD)"),
    adults: int = Query(2, ge=1, le=10, description="Number of adults"),
    children: int = Query(0, ge=0, le=6, description="Number of children"),
    rooms: int = Query(1, ge=1, le=8, description="Number of rooms"),
    currency: str = Query("USD", description="Currency code"),
    order_by: str = Query("popularity", description="Sort: popularity, price, distance, review_score"),
    page: int = Query(0, ge=0, description="Page number")
):
    """
    Search hotels with REAL pricing data.
    
    FREE: 500 requests/month on RapidAPI
    
    Steps:
    1. First call /rapidapi/locations?query=Lagos to get dest_id
    2. Then call this endpoint with the dest_id
    """
    result = await rapidapi_hotels.search_hotels(
        dest_id=dest_id,
        dest_type=dest_type,
        checkin=checkin,
        checkout=checkout,
        adults=adults,
        children=children,
        rooms=rooms,
        currency=currency,
        order_by=order_by,
        page=page
    )
    return result


@router.get(
    "/rapidapi/hotels/{hotel_id}",
    summary="Get hotel details (RapidAPI)",
    description="Get detailed information about a specific hotel",
)
async def rapidapi_get_hotel_details(
    hotel_id: str,
    locale: str = Query("en-us"),
    currency: str = Query("USD")
):
    """Get detailed hotel information."""
    result = await rapidapi_hotels.get_hotel_details(
        hotel_id=hotel_id,
        locale=locale,
        currency=currency
    )
    return result


@router.get(
    "/rapidapi/hotels/{hotel_id}/photos",
    summary="Get hotel photos (RapidAPI)",
)
async def rapidapi_get_hotel_photos(
    hotel_id: str,
    locale: str = Query("en-us")
):
    """Get all photos for a hotel."""
    result = await rapidapi_hotels.get_hotel_photos(
        hotel_id=hotel_id,
        locale=locale
    )
    return result


@router.get(
    "/rapidapi/hotels/{hotel_id}/reviews",
    summary="Get hotel reviews (RapidAPI)",
)
async def rapidapi_get_hotel_reviews(
    hotel_id: str,
    locale: str = Query("en-us"),
    sort: str = Query("SORT_MOST_RELEVANT"),
    page: int = Query(0)
):
    """Get guest reviews for a hotel."""
    result = await rapidapi_hotels.get_hotel_reviews(
        hotel_id=hotel_id,
        locale=locale,
        sort_type=sort,
        page=page
    )
    return result


@router.get(
    "/rapidapi/hotels/{hotel_id}/rooms",
    summary="Get available rooms (RapidAPI)",
)
async def rapidapi_get_rooms(
    hotel_id: str,
    checkin: date = Query(...),
    checkout: date = Query(...),
    adults: int = Query(2),
    children: int = Query(0),
    currency: str = Query("USD"),
    locale: str = Query("en-us")
):
    """Get available rooms with pricing for specific dates."""
    result = await rapidapi_hotels.get_room_list(
        hotel_id=hotel_id,
        checkin=checkin,
        checkout=checkout,
        adults=adults,
        children=children,
        currency=currency,
        locale=locale
    )
    return result


@router.get(
    "/rapidapi/popular-destinations",
    summary="Get popular destinations",
)
async def rapidapi_popular_destinations():
    """Get popular travel destinations with dest_ids ready to use."""
    result = await rapidapi_hotels.get_popular_destinations()
    return result


# ================================================================
# RAPIDAPI FLIGHTS - FREE TIER (Sky Scrapper / Skyscanner)
# ================================================================

from integrations.travel_apis.rapidapi_flights import rapidapi_flights


@router.get(
    "/rapidapi/flights/airports",
    summary="Search airports (RapidAPI)",
    description="Search for airports and cities to get skyId and entityId for flight search",
)
async def rapidapi_search_airports(
    query: str = Query(..., description="City or airport name (e.g., 'Lagos', 'LOS', 'London')"),
    locale: str = Query("en-US", description="Language locale")
):
    """
    Search for airports using RapidAPI Sky Scrapper.
    Returns skyId and entityId needed for flight search.
    
    FREE: Uses same RapidAPI key as hotels
    """
    result = await rapidapi_flights.search_airports(query=query, locale=locale)
    return result


@router.get(
    "/rapidapi/flights/search",
    summary="Search flights (RapidAPI FREE)",
    description="Search flights with REAL data from Skyscanner via RapidAPI",
)
async def rapidapi_search_flights(
    origin_sky_id: str = Query(..., description="Origin skyId from /rapidapi/flights/airports"),
    destination_sky_id: str = Query(..., description="Destination skyId"),
    origin_entity_id: str = Query(..., description="Origin entityId from airport search"),
    destination_entity_id: str = Query(..., description="Destination entityId"),
    departure_date: date = Query(..., description="Departure date (YYYY-MM-DD)"),
    return_date: Optional[date] = Query(None, description="Return date for round-trip (optional)"),
    adults: int = Query(1, ge=1, le=9, description="Number of adults"),
    children: int = Query(0, ge=0, le=8, description="Number of children (2-11)"),
    infants: int = Query(0, ge=0, le=4, description="Number of infants (0-2)"),
    cabin_class: str = Query("economy", description="Cabin: economy, premium_economy, business, first"),
    currency: str = Query("USD", description="Currency code")
):
    """
    Search flights with REAL pricing from multiple airlines.
    
    FREE: Uses same RapidAPI key as hotels
    
    Steps:
    1. First call /rapidapi/flights/airports?query=Lagos to get skyId & entityId
    2. Then call this endpoint with the IDs
    """
    result = await rapidapi_flights.search_flights(
        origin_sky_id=origin_sky_id,
        destination_sky_id=destination_sky_id,
        origin_entity_id=origin_entity_id,
        destination_entity_id=destination_entity_id,
        departure_date=departure_date,
        return_date=return_date,
        adults=adults,
        children=children,
        infants=infants,
        cabin_class=cabin_class,
        currency=currency
    )
    return result


@router.get(
    "/rapidapi/flights/quick-search",
    summary="Quick flight search by city name (RapidAPI)",
    description="Search flights by city/airport name - automatically resolves airport codes",
)
async def rapidapi_quick_flight_search(
    origin: str = Query(..., description="Origin city or airport (e.g., 'Lagos', 'LOS')"),
    destination: str = Query(..., description="Destination city or airport (e.g., 'London', 'LHR')"),
    departure_date: date = Query(..., description="Departure date (YYYY-MM-DD)"),
    return_date: Optional[date] = Query(None, description="Return date for round-trip (optional)"),
    adults: int = Query(1, ge=1, le=9),
    cabin_class: str = Query("economy"),
    currency: str = Query("USD")
):
    """
    Convenient endpoint that automatically resolves airport codes.
    Just provide city names!
    
    Example: /rapidapi/flights/quick-search?origin=Lagos&destination=Dubai&departure_date=2025-12-25
    """
    result = await rapidapi_flights.quick_search(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        adults=adults,
        cabin_class=cabin_class,
        currency=currency
    )
    return result


@router.get(
    "/rapidapi/flights/price-calendar",
    summary="Get flight price calendar (RapidAPI)",
    description="Get cheapest prices by date for planning",
)
async def rapidapi_flight_price_calendar(
    origin_sky_id: str = Query(..., description="Origin skyId"),
    destination_sky_id: str = Query(..., description="Destination skyId"),
    origin_entity_id: str = Query(..., description="Origin entityId"),
    destination_entity_id: str = Query(..., description="Destination entityId"),
    from_date: date = Query(..., description="Start date for calendar"),
    currency: str = Query("USD")
):
    """Get price calendar showing cheapest flights by date."""
    result = await rapidapi_flights.get_price_calendar(
        origin_sky_id=origin_sky_id,
        destination_sky_id=destination_sky_id,
        origin_entity_id=origin_entity_id,
        destination_entity_id=destination_entity_id,
        from_date=from_date,
        currency=currency
    )
    return result


@router.get(
    "/rapidapi/flights/nearby-airports",
    summary="Get nearby airports (RapidAPI)",
)
async def rapidapi_nearby_airports(
    latitude: float = Query(..., description="Latitude"),
    longitude: float = Query(..., description="Longitude"),
    locale: str = Query("en-US")
):
    """Get airports near a specific location."""
    result = await rapidapi_flights.get_nearby_airports(
        latitude=latitude,
        longitude=longitude,
        locale=locale
    )
    return result


@router.get(
    "/rapidapi/flights/config",
    summary="Get supported currencies and locales",
)
async def rapidapi_flights_config():
    """Get API configuration (currencies, locales, markets)."""
    result = await rapidapi_flights.get_config()
    return result

