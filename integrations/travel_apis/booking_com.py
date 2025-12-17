"""
Queska Backend - Booking.com Integration
Comprehensive integration with Booking.com Demand API
for accommodations, car rentals, flights, and attractions
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

import httpx
from loguru import logger

from app.core.config import settings


class BookingComClient:
    """
    Booking.com Demand API Client
    
    The Demand API provides access to:
    - 28+ million accommodation listings worldwide
    - Car rentals
    - Flights
    - Attractions and activities
    - Airport taxis
    
    Documentation: https://developers.booking.com/demand
    
    API Features:
    - Search for accommodations
    - Check availability
    - Get property details
    - Book accommodations
    - Manage bookings
    - Get reviews
    """
    
    # API Endpoints
    BASE_URL = "https://demandapi.booking.com"
    SANDBOX_URL = "https://demandapi-sandbox.booking.com"
    
    # API Versions
    API_VERSION = "3.1"
    
    def __init__(self):
        self.api_key = settings.BOOKING_COM_API_KEY
        self.api_secret = settings.BOOKING_COM_API_SECRET
        self._client: Optional[httpx.AsyncClient] = None
        self._use_production = settings.ENVIRONMENT == "production"
    
    @property
    def base_url(self) -> str:
        return self.BASE_URL if self._use_production else self.SANDBOX_URL
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret)
    
    def _get_headers(self) -> Dict[str, str]:
        """Generate request headers with authentication."""
        # Basic auth with API key and secret
        credentials = f"{self.api_key}:{self.api_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Affiliate-Id": self.api_key,
            "User-Agent": "Queska/1.0",
        }
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to Booking.com API."""
        if not self.is_configured():
            return {"success": False, "error": "Booking.com API not configured"}
        
        url = f"{self.base_url}/api/v{self.API_VERSION}{endpoint}"
        headers = self._get_headers()
        
        try:
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = await self.client.post(url, headers=headers, json=data, params=params)
            elif method.upper() == "PUT":
                response = await self.client.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = await self.client.delete(url, headers=headers)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}
            
            if response.status_code in [200, 201]:
                return {"success": True, "data": response.json()}
            elif response.status_code == 204:
                return {"success": True, "data": None}
            else:
                error_data = response.json() if response.content else {}
                logger.error(f"Booking.com API error: {response.status_code} - {error_data}")
                return {
                    "success": False,
                    "error": error_data.get("message", f"HTTP {response.status_code}"),
                    "status_code": response.status_code,
                    "details": error_data
                }
                
        except httpx.HTTPError as e:
            logger.error(f"Booking.com HTTP error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Booking.com request error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # DESTINATIONS / LOCATIONS
    # ================================================================
    
    async def search_destinations(
        self,
        query: str,
        locale: str = "en-us",
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search for destinations (cities, regions, landmarks).
        
        Args:
            query: Search term
            locale: Locale for results
            limit: Max results
            
        Returns:
            List of matching destinations
        """
        params = {
            "text": query,
            "locale": locale,
            "limit": limit,
        }
        
        result = await self._request("GET", "/accommodations/locations", params=params)
        
        if result.get("success"):
            locations = result.get("data", {}).get("locations", [])
            return {
                "success": True,
                "destinations": [
                    {
                        "id": loc.get("dest_id"),
                        "name": loc.get("name"),
                        "type": loc.get("dest_type"),
                        "city": loc.get("city_name"),
                        "region": loc.get("region"),
                        "country": loc.get("country"),
                        "country_code": loc.get("country_code"),
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude"),
                        "image_url": loc.get("image_url"),
                        "hotels_count": loc.get("hotels_count"),
                    }
                    for loc in locations
                ]
            }
        
        return result
    
    async def get_popular_destinations(
        self,
        country_code: Optional[str] = None,
        locale: str = "en-us",
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get popular travel destinations."""
        params = {
            "locale": locale,
            "limit": limit,
        }
        if country_code:
            params["country"] = country_code
        
        result = await self._request("GET", "/accommodations/destinations/popular", params=params)
        
        if result.get("success"):
            return {
                "success": True,
                "destinations": result.get("data", {}).get("destinations", [])
            }
        
        return result
    
    # ================================================================
    # ACCOMMODATION SEARCH
    # ================================================================
    
    async def search_accommodations(
        self,
        dest_id: Optional[str] = None,
        dest_type: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = None,
        checkin: Union[str, date] = None,
        checkout: Union[str, date] = None,
        adults: int = 2,
        children: int = 0,
        children_ages: Optional[List[int]] = None,
        rooms: int = 1,
        currency: str = "USD",
        locale: str = "en-us",
        filter_by_class: Optional[List[int]] = None,
        filter_by_price_min: Optional[float] = None,
        filter_by_price_max: Optional[float] = None,
        filter_by_review_score: Optional[float] = None,
        filter_by_facilities: Optional[List[str]] = None,
        filter_by_property_type: Optional[List[str]] = None,
        filter_by_meal_plan: Optional[str] = None,
        filter_by_free_cancellation: bool = False,
        order_by: str = "popularity",
        page: int = 1,
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Search for available accommodations.
        
        Args:
            dest_id: Destination ID from location search
            dest_type: Destination type (city, region, landmark, etc.)
            latitude: For coordinate-based search
            longitude: For coordinate-based search
            radius_km: Search radius in km
            checkin: Check-in date
            checkout: Check-out date
            adults: Number of adults
            children: Number of children
            children_ages: Ages of children
            rooms: Number of rooms
            currency: Currency code
            locale: Locale for results
            filter_by_class: Star ratings (1-5)
            filter_by_price_min: Min price
            filter_by_price_max: Max price
            filter_by_review_score: Min review score
            filter_by_facilities: Required facilities
            filter_by_property_type: Property types (hotel, apartment, etc.)
            filter_by_meal_plan: Meal plan (breakfast_included, etc.)
            filter_by_free_cancellation: Only free cancellation
            order_by: Sort order (popularity, price, review_score, class, distance)
            page: Page number
            limit: Results per page
            
        Returns:
            Available accommodations
        """
        # Format dates
        if isinstance(checkin, date):
            checkin = checkin.strftime("%Y-%m-%d")
        if isinstance(checkout, date):
            checkout = checkout.strftime("%Y-%m-%d")
        
        # Build request
        request_data = {
            "checkin": checkin,
            "checkout": checkout,
            "guest_qty": {
                "adults": adults,
                "children": children,
            },
            "rooms": rooms,
            "currency": currency,
            "locale": locale,
            "sort": {"order_by": order_by},
            "pagination": {
                "page": page,
                "page_size": limit
            }
        }
        
        # Location
        if dest_id and dest_type:
            request_data["destination"] = {
                "dest_id": dest_id,
                "dest_type": dest_type
            }
        elif latitude and longitude:
            request_data["coordinates"] = {
                "latitude": latitude,
                "longitude": longitude,
                "radius": radius_km or 10
            }
        
        # Children ages
        if children_ages:
            request_data["guest_qty"]["children_ages"] = children_ages
        elif children > 0:
            request_data["guest_qty"]["children_ages"] = [8] * children
        
        # Filters
        filters = {}
        if filter_by_class:
            filters["class"] = filter_by_class
        if filter_by_price_min is not None:
            filters["price_min"] = filter_by_price_min
        if filter_by_price_max is not None:
            filters["price_max"] = filter_by_price_max
        if filter_by_review_score:
            filters["review_score_min"] = filter_by_review_score
        if filter_by_facilities:
            filters["facilities"] = filter_by_facilities
        if filter_by_property_type:
            filters["property_types"] = filter_by_property_type
        if filter_by_meal_plan:
            filters["meal_plan"] = filter_by_meal_plan
        if filter_by_free_cancellation:
            filters["free_cancellation"] = True
        
        if filters:
            request_data["filters"] = filters
        
        result = await self._request("POST", "/accommodations/search", data=request_data)
        
        if result.get("success"):
            data = result.get("data", {})
            hotels = data.get("hotels", [])
            
            return {
                "success": True,
                "hotels": self._parse_accommodations(hotels, currency),
                "total": data.get("total_count", len(hotels)),
                "page": page,
                "total_pages": data.get("total_pages", 1),
                "search_params": {
                    "checkin": checkin,
                    "checkout": checkout,
                    "adults": adults,
                    "children": children,
                    "rooms": rooms,
                    "currency": currency,
                },
                "filters_applied": data.get("filters_applied", {}),
            }
        
        return result
    
    def _parse_accommodations(self, hotels: List[Dict], currency: str) -> List[Dict[str, Any]]:
        """Parse accommodation results."""
        parsed = []
        
        for hotel in hotels:
            property_data = hotel.get("property", {})
            price_data = hotel.get("price", {})
            review_data = property_data.get("review", {})
            location = property_data.get("location", {})
            
            # Get primary image
            images = property_data.get("images", [])
            primary_image = images[0].get("url") if images else None
            
            parsed.append({
                "id": str(property_data.get("id")),
                "name": property_data.get("name"),
                "type": property_data.get("type"),
                "type_name": property_data.get("type_name"),
                "star_rating": property_data.get("class"),
                "guest_rating": {
                    "score": review_data.get("score"),
                    "count": review_data.get("count"),
                    "category": review_data.get("category"),
                },
                "location": {
                    "address": location.get("address"),
                    "city": location.get("city"),
                    "country": location.get("country"),
                    "country_code": location.get("country_code"),
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude"),
                    "distance_from_center": location.get("distance_from_center"),
                },
                "image_url": primary_image,
                "images": [img.get("url") for img in images[:5]],
                "price": {
                    "total": price_data.get("total"),
                    "currency": currency,
                    "per_night": price_data.get("per_night"),
                    "original_price": price_data.get("original_price"),
                    "discount_percentage": price_data.get("discount_percentage"),
                    "taxes_included": price_data.get("taxes_included", False),
                },
                "room": {
                    "name": hotel.get("room", {}).get("name"),
                    "description": hotel.get("room", {}).get("description"),
                    "bed_type": hotel.get("room", {}).get("bed_type"),
                    "max_occupancy": hotel.get("room", {}).get("max_occupancy"),
                },
                "amenities": property_data.get("facilities", []),
                "free_cancellation": hotel.get("policies", {}).get("free_cancellation", False),
                "pay_at_property": hotel.get("policies", {}).get("pay_at_property", False),
                "breakfast_included": hotel.get("policies", {}).get("breakfast_included", False),
                "sustainable_level": property_data.get("sustainability", {}).get("level"),
                "urgency_message": hotel.get("urgency_message"),
                "deep_link": hotel.get("deep_link"),
                "provider": "booking.com",
            })
        
        return parsed
    
    # ================================================================
    # PROPERTY DETAILS
    # ================================================================
    
    async def get_property_details(
        self,
        property_id: str,
        checkin: Optional[Union[str, date]] = None,
        checkout: Optional[Union[str, date]] = None,
        adults: int = 2,
        children: int = 0,
        rooms: int = 1,
        currency: str = "USD",
        locale: str = "en-us"
    ) -> Dict[str, Any]:
        """
        Get detailed property information.
        
        Args:
            property_id: Property/hotel ID
            checkin: Optional check-in for availability
            checkout: Optional checkout for availability
            adults: Number of adults
            children: Number of children
            rooms: Number of rooms
            currency: Currency code
            locale: Locale
            
        Returns:
            Property details
        """
        params = {
            "hotel_id": property_id,
            "currency": currency,
            "locale": locale,
        }
        
        if checkin and checkout:
            if isinstance(checkin, date):
                checkin = checkin.strftime("%Y-%m-%d")
            if isinstance(checkout, date):
                checkout = checkout.strftime("%Y-%m-%d")
            
            params["checkin"] = checkin
            params["checkout"] = checkout
            params["adults"] = adults
            params["children"] = children
            params["rooms"] = rooms
        
        result = await self._request("GET", "/accommodations/details", params=params)
        
        if result.get("success"):
            data = result.get("data", {})
            return {
                "success": True,
                "property": self._parse_property_details(data, currency)
            }
        
        return result
    
    def _parse_property_details(self, data: Dict, currency: str) -> Dict[str, Any]:
        """Parse detailed property information."""
        property_data = data.get("property", {})
        location = property_data.get("location", {})
        review = property_data.get("review", {})
        
        # Parse rooms if available
        rooms = []
        for room in data.get("rooms", []):
            price = room.get("price", {})
            rooms.append({
                "id": room.get("id"),
                "name": room.get("name"),
                "description": room.get("description"),
                "bed_type": room.get("bed_type"),
                "beds": room.get("beds"),
                "max_occupancy": room.get("max_occupancy"),
                "size_sqm": room.get("size"),
                "price": {
                    "total": price.get("total"),
                    "currency": currency,
                    "per_night": price.get("per_night"),
                },
                "amenities": room.get("facilities", []),
                "images": [img.get("url") for img in room.get("images", [])],
                "free_cancellation": room.get("free_cancellation", False),
                "pay_at_property": room.get("pay_at_property", False),
                "breakfast_included": room.get("breakfast_included", False),
                "available_count": room.get("available_count"),
            })
        
        return {
            "id": str(property_data.get("id")),
            "name": property_data.get("name"),
            "description": property_data.get("description"),
            "tagline": property_data.get("tagline"),
            "type": property_data.get("type"),
            "type_name": property_data.get("type_name"),
            "star_rating": property_data.get("class"),
            "guest_rating": {
                "score": review.get("score"),
                "count": review.get("count"),
                "category": review.get("category"),
                "cleanliness": review.get("cleanliness"),
                "comfort": review.get("comfort"),
                "location": review.get("location"),
                "facilities": review.get("facilities"),
                "staff": review.get("staff"),
                "value": review.get("value_for_money"),
            },
            "location": {
                "address": location.get("address"),
                "city": location.get("city"),
                "region": location.get("region"),
                "country": location.get("country"),
                "country_code": location.get("country_code"),
                "postal_code": location.get("postal_code"),
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
            },
            "images": [
                {
                    "url": img.get("url"),
                    "caption": img.get("caption"),
                    "category": img.get("category"),
                }
                for img in property_data.get("images", [])
            ],
            "facilities": property_data.get("facilities", []),
            "facilities_grouped": property_data.get("facilities_grouped", {}),
            "policies": {
                "checkin_time": property_data.get("policies", {}).get("checkin_time"),
                "checkout_time": property_data.get("policies", {}).get("checkout_time"),
                "cancellation": property_data.get("policies", {}).get("cancellation"),
                "children_policy": property_data.get("policies", {}).get("children"),
                "pets_policy": property_data.get("policies", {}).get("pets"),
            },
            "sustainability": property_data.get("sustainability"),
            "rooms": rooms,
            "nearby_attractions": property_data.get("nearby_attractions", []),
            "languages_spoken": property_data.get("languages_spoken", []),
            "deep_link": data.get("deep_link"),
            "provider": "booking.com",
        }
    
    # ================================================================
    # AVAILABILITY CHECK
    # ================================================================
    
    async def check_availability(
        self,
        property_id: str,
        checkin: Union[str, date],
        checkout: Union[str, date],
        adults: int = 2,
        children: int = 0,
        children_ages: Optional[List[int]] = None,
        rooms: int = 1,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Check room availability for a property.
        
        Args:
            property_id: Property ID
            checkin: Check-in date
            checkout: Check-out date
            adults: Number of adults
            children: Number of children
            children_ages: Ages of children
            rooms: Number of rooms
            currency: Currency code
            
        Returns:
            Available rooms with pricing
        """
        if isinstance(checkin, date):
            checkin = checkin.strftime("%Y-%m-%d")
        if isinstance(checkout, date):
            checkout = checkout.strftime("%Y-%m-%d")
        
        request_data = {
            "hotel_id": property_id,
            "checkin": checkin,
            "checkout": checkout,
            "guest_qty": {
                "adults": adults,
                "children": children,
            },
            "rooms": rooms,
            "currency": currency,
        }
        
        if children_ages:
            request_data["guest_qty"]["children_ages"] = children_ages
        elif children > 0:
            request_data["guest_qty"]["children_ages"] = [8] * children
        
        result = await self._request("POST", "/accommodations/availability", data=request_data)
        
        if result.get("success"):
            data = result.get("data", {})
            available_rooms = []
            
            for room in data.get("rooms", []):
                price = room.get("price", {})
                policies = room.get("policies", {})
                
                available_rooms.append({
                    "room_id": room.get("id"),
                    "name": room.get("name"),
                    "description": room.get("description"),
                    "bed_type": room.get("bed_type"),
                    "max_occupancy": room.get("max_occupancy"),
                    "price": {
                        "total": price.get("total"),
                        "currency": currency,
                        "per_night": price.get("per_night"),
                        "taxes": price.get("taxes"),
                        "fees": price.get("fees"),
                    },
                    "free_cancellation": policies.get("free_cancellation", False),
                    "cancellation_deadline": policies.get("cancellation_deadline"),
                    "pay_at_property": policies.get("pay_at_property", False),
                    "breakfast_included": policies.get("breakfast_included", False),
                    "meal_plan": policies.get("meal_plan"),
                    "available_count": room.get("available_count"),
                    "book_link": room.get("book_link"),
                })
            
            return {
                "success": True,
                "property_id": property_id,
                "checkin": checkin,
                "checkout": checkout,
                "rooms_available": available_rooms,
                "total_rooms": len(available_rooms),
            }
        
        return result
    
    # ================================================================
    # REVIEWS
    # ================================================================
    
    async def get_property_reviews(
        self,
        property_id: str,
        locale: str = "en-us",
        sort_by: str = "date",
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get reviews for a property.
        
        Args:
            property_id: Property ID
            locale: Locale for reviews
            sort_by: Sort order (date, score)
            page: Page number
            limit: Reviews per page
            
        Returns:
            Property reviews
        """
        params = {
            "hotel_id": property_id,
            "locale": locale,
            "sort": sort_by,
            "page": page,
            "page_size": limit,
        }
        
        result = await self._request("GET", "/accommodations/reviews", params=params)
        
        if result.get("success"):
            data = result.get("data", {})
            reviews = []
            
            for review in data.get("reviews", []):
                reviews.append({
                    "id": review.get("id"),
                    "score": review.get("score"),
                    "title": review.get("title"),
                    "positive": review.get("positive"),
                    "negative": review.get("negative"),
                    "author": {
                        "name": review.get("author", {}).get("name"),
                        "country": review.get("author", {}).get("country"),
                        "traveler_type": review.get("author", {}).get("traveler_type"),
                    },
                    "room_name": review.get("room_name"),
                    "stay_date": review.get("stay_date"),
                    "nights": review.get("nights"),
                    "created_at": review.get("created_at"),
                })
            
            return {
                "success": True,
                "property_id": property_id,
                "reviews": reviews,
                "total": data.get("total_count", len(reviews)),
                "average_score": data.get("average_score"),
                "page": page,
            }
        
        return result
    
    # ================================================================
    # CAR RENTALS
    # ================================================================
    
    async def search_car_rentals(
        self,
        pickup_location: str,
        pickup_date: Union[str, date],
        pickup_time: str,
        dropoff_date: Union[str, date],
        dropoff_time: str,
        dropoff_location: Optional[str] = None,
        driver_age: int = 30,
        currency: str = "USD",
        locale: str = "en-us",
        car_type: Optional[str] = None,
        supplier: Optional[str] = None,
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Search for car rentals.
        
        Args:
            pickup_location: Pickup location (city or airport code)
            pickup_date: Pickup date
            pickup_time: Pickup time (HH:MM)
            dropoff_date: Dropoff date
            dropoff_time: Dropoff time (HH:MM)
            dropoff_location: Dropoff location (if different)
            driver_age: Driver age
            currency: Currency
            locale: Locale
            car_type: Car type filter
            supplier: Supplier filter
            limit: Max results
            
        Returns:
            Available car rentals
        """
        if isinstance(pickup_date, date):
            pickup_date = pickup_date.strftime("%Y-%m-%d")
        if isinstance(dropoff_date, date):
            dropoff_date = dropoff_date.strftime("%Y-%m-%d")
        
        request_data = {
            "pickup": {
                "location": pickup_location,
                "date": pickup_date,
                "time": pickup_time,
            },
            "dropoff": {
                "location": dropoff_location or pickup_location,
                "date": dropoff_date,
                "time": dropoff_time,
            },
            "driver_age": driver_age,
            "currency": currency,
            "locale": locale,
            "limit": limit,
        }
        
        if car_type:
            request_data["car_type"] = car_type
        if supplier:
            request_data["supplier"] = supplier
        
        result = await self._request("POST", "/cars/search", data=request_data)
        
        if result.get("success"):
            cars = result.get("data", {}).get("cars", [])
            return {
                "success": True,
                "cars": self._parse_cars(cars, currency),
                "total": len(cars),
                "search_params": {
                    "pickup_location": pickup_location,
                    "pickup_date": pickup_date,
                    "dropoff_date": dropoff_date,
                },
            }
        
        return result
    
    def _parse_cars(self, cars: List[Dict], currency: str) -> List[Dict[str, Any]]:
        """Parse car rental results."""
        parsed = []
        
        for car in cars:
            vehicle = car.get("vehicle", {})
            price = car.get("price", {})
            supplier = car.get("supplier", {})
            
            parsed.append({
                "id": car.get("id"),
                "vehicle": {
                    "name": vehicle.get("name"),
                    "category": vehicle.get("category"),
                    "type": vehicle.get("type"),
                    "transmission": vehicle.get("transmission"),
                    "fuel_type": vehicle.get("fuel_type"),
                    "passengers": vehicle.get("passengers"),
                    "bags_large": vehicle.get("bags_large"),
                    "bags_small": vehicle.get("bags_small"),
                    "doors": vehicle.get("doors"),
                    "air_conditioning": vehicle.get("air_conditioning", True),
                    "image_url": vehicle.get("image_url"),
                },
                "supplier": {
                    "name": supplier.get("name"),
                    "logo": supplier.get("logo"),
                    "rating": supplier.get("rating"),
                    "reviews_count": supplier.get("reviews_count"),
                },
                "pickup_location": car.get("pickup", {}).get("location"),
                "dropoff_location": car.get("dropoff", {}).get("location"),
                "price": {
                    "total": price.get("total"),
                    "currency": currency,
                    "per_day": price.get("per_day"),
                },
                "mileage": car.get("mileage"),
                "insurance": car.get("insurance", {}),
                "fuel_policy": car.get("fuel_policy"),
                "free_cancellation": car.get("free_cancellation", False),
                "deep_link": car.get("deep_link"),
                "provider": "booking.com",
            })
        
        return parsed
    
    # ================================================================
    # FLIGHTS
    # ================================================================
    
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: Union[str, date],
        return_date: Optional[Union[str, date]] = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "economy",
        direct_only: bool = False,
        currency: str = "USD",
        locale: str = "en-us",
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search for flights.
        
        Args:
            origin: Origin airport code
            destination: Destination airport code
            departure_date: Departure date
            return_date: Return date (for round trips)
            adults: Number of adults
            children: Number of children
            infants: Number of infants
            cabin_class: Cabin class
            direct_only: Only direct flights
            currency: Currency
            locale: Locale
            limit: Max results
            
        Returns:
            Available flights
        """
        if isinstance(departure_date, date):
            departure_date = departure_date.strftime("%Y-%m-%d")
        if return_date and isinstance(return_date, date):
            return_date = return_date.strftime("%Y-%m-%d")
        
        request_data = {
            "origin": origin.upper(),
            "destination": destination.upper(),
            "departure_date": departure_date,
            "passengers": {
                "adults": adults,
                "children": children,
                "infants": infants,
            },
            "cabin_class": cabin_class,
            "currency": currency,
            "locale": locale,
            "limit": limit,
        }
        
        if return_date:
            request_data["return_date"] = return_date
        if direct_only:
            request_data["direct_only"] = True
        
        result = await self._request("POST", "/flights/search", data=request_data)
        
        if result.get("success"):
            flights = result.get("data", {}).get("flights", [])
            return {
                "success": True,
                "flights": self._parse_flights(flights, currency),
                "total": len(flights),
                "search_params": {
                    "origin": origin.upper(),
                    "destination": destination.upper(),
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "trip_type": "round_trip" if return_date else "one_way",
                },
            }
        
        return result
    
    def _parse_flights(self, flights: List[Dict], currency: str) -> List[Dict[str, Any]]:
        """Parse flight results."""
        parsed = []
        
        for flight in flights:
            price = flight.get("price", {})
            outbound = flight.get("outbound", {})
            inbound = flight.get("inbound")
            
            parsed.append({
                "id": flight.get("id"),
                "price": {
                    "total": price.get("total"),
                    "currency": currency,
                    "per_person": price.get("per_person"),
                    "taxes": price.get("taxes"),
                },
                "outbound": self._parse_flight_leg(outbound),
                "return": self._parse_flight_leg(inbound) if inbound else None,
                "trip_type": "round_trip" if inbound else "one_way",
                "cabin_class": flight.get("cabin_class"),
                "baggage": flight.get("baggage", {}),
                "refundable": flight.get("refundable", False),
                "changeable": flight.get("changeable", False),
                "deep_link": flight.get("deep_link"),
                "provider": "booking.com",
            })
        
        return parsed
    
    def _parse_flight_leg(self, leg: Dict) -> Optional[Dict[str, Any]]:
        """Parse flight leg."""
        if not leg:
            return None
        
        segments = []
        for seg in leg.get("segments", []):
            segments.append({
                "carrier": seg.get("carrier", {}).get("name"),
                "carrier_code": seg.get("carrier", {}).get("code"),
                "carrier_logo": seg.get("carrier", {}).get("logo"),
                "flight_number": seg.get("flight_number"),
                "aircraft": seg.get("aircraft"),
                "departure": {
                    "airport": seg.get("departure", {}).get("airport"),
                    "airport_code": seg.get("departure", {}).get("code"),
                    "terminal": seg.get("departure", {}).get("terminal"),
                    "datetime": seg.get("departure", {}).get("datetime"),
                },
                "arrival": {
                    "airport": seg.get("arrival", {}).get("airport"),
                    "airport_code": seg.get("arrival", {}).get("code"),
                    "terminal": seg.get("arrival", {}).get("terminal"),
                    "datetime": seg.get("arrival", {}).get("datetime"),
                },
                "duration_minutes": seg.get("duration"),
            })
        
        return {
            "departure": leg.get("departure"),
            "arrival": leg.get("arrival"),
            "duration_minutes": leg.get("duration"),
            "stops": leg.get("stops", len(segments) - 1),
            "segments": segments,
        }
    
    # ================================================================
    # ATTRACTIONS
    # ================================================================
    
    async def search_attractions(
        self,
        destination: str,
        date: Optional[Union[str, date]] = None,
        category: Optional[str] = None,
        currency: str = "USD",
        locale: str = "en-us",
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Search for attractions and activities.
        
        Args:
            destination: City or destination
            date: Activity date
            category: Category filter
            currency: Currency
            locale: Locale
            limit: Max results
            
        Returns:
            Available attractions
        """
        if date and isinstance(date, type(date)):
            date = date.strftime("%Y-%m-%d")
        
        params = {
            "destination": destination,
            "currency": currency,
            "locale": locale,
            "limit": limit,
        }
        
        if date:
            params["date"] = date
        if category:
            params["category"] = category
        
        result = await self._request("GET", "/attractions/search", params=params)
        
        if result.get("success"):
            attractions = result.get("data", {}).get("attractions", [])
            return {
                "success": True,
                "attractions": self._parse_attractions(attractions, currency),
                "total": len(attractions),
            }
        
        return result
    
    def _parse_attractions(self, attractions: List[Dict], currency: str) -> List[Dict[str, Any]]:
        """Parse attraction results."""
        parsed = []
        
        for attr in attractions:
            price = attr.get("price", {})
            
            parsed.append({
                "id": attr.get("id"),
                "name": attr.get("name"),
                "description": attr.get("short_description"),
                "category": attr.get("category"),
                "duration": attr.get("duration"),
                "rating": attr.get("rating"),
                "reviews_count": attr.get("reviews_count"),
                "image_url": attr.get("image_url"),
                "images": attr.get("images", []),
                "price": {
                    "amount": price.get("amount"),
                    "currency": currency,
                    "from_price": price.get("from_price", True),
                },
                "location": attr.get("location"),
                "highlights": attr.get("highlights", []),
                "inclusions": attr.get("inclusions", []),
                "free_cancellation": attr.get("free_cancellation", False),
                "instant_confirmation": attr.get("instant_confirmation", False),
                "mobile_ticket": attr.get("mobile_ticket", False),
                "deep_link": attr.get("deep_link"),
                "provider": "booking.com",
            })
        
        return parsed
    
    # ================================================================
    # AIRPORT TAXI
    # ================================================================
    
    async def search_airport_taxi(
        self,
        pickup_location: str,
        dropoff_location: str,
        pickup_date: Union[str, date],
        pickup_time: str,
        passengers: int = 2,
        currency: str = "USD",
        locale: str = "en-us"
    ) -> Dict[str, Any]:
        """
        Search for airport taxi transfers.
        
        Args:
            pickup_location: Pickup location/airport
            dropoff_location: Dropoff location/address
            pickup_date: Pickup date
            pickup_time: Pickup time
            passengers: Number of passengers
            currency: Currency
            locale: Locale
            
        Returns:
            Available taxi options
        """
        if isinstance(pickup_date, date):
            pickup_date = pickup_date.strftime("%Y-%m-%d")
        
        request_data = {
            "pickup": {
                "location": pickup_location,
                "date": pickup_date,
                "time": pickup_time,
            },
            "dropoff": {
                "location": dropoff_location,
            },
            "passengers": passengers,
            "currency": currency,
            "locale": locale,
        }
        
        result = await self._request("POST", "/taxi/search", data=request_data)
        
        if result.get("success"):
            taxis = result.get("data", {}).get("vehicles", [])
            return {
                "success": True,
                "vehicles": [
                    {
                        "id": taxi.get("id"),
                        "type": taxi.get("type"),
                        "name": taxi.get("name"),
                        "description": taxi.get("description"),
                        "max_passengers": taxi.get("max_passengers"),
                        "max_bags": taxi.get("max_bags"),
                        "image_url": taxi.get("image_url"),
                        "price": {
                            "total": taxi.get("price", {}).get("total"),
                            "currency": currency,
                        },
                        "duration_minutes": taxi.get("duration"),
                        "distance_km": taxi.get("distance"),
                        "free_cancellation": taxi.get("free_cancellation", False),
                        "meet_and_greet": taxi.get("meet_and_greet", False),
                        "deep_link": taxi.get("deep_link"),
                        "provider": "booking.com",
                    }
                    for taxi in taxis
                ],
                "total": len(taxis),
            }
        
        return result
    
    # ================================================================
    # UTILITIES
    # ================================================================
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Check API service status."""
        return {
            "configured": self.is_configured(),
            "production": self._use_production,
            "services": [
                "accommodations",
                "car_rentals",
                "flights",
                "attractions",
                "airport_taxi",
            ],
        }


# Global client instance
booking_com_client = BookingComClient()

