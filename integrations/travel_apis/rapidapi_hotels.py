"""
Queska Backend - RapidAPI Hotels Integration
Free hotel search API via RapidAPI Booking.com endpoint

Get your FREE API key at: https://rapidapi.com/tipsters/api/booking-com
Free tier: 500 requests/month
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.core.config import settings


class RapidAPIHotelsClient:
    """
    RapidAPI Hotels Client (Booking.com API)
    
    This is a FREE API that provides real hotel data from Booking.com
    through RapidAPI marketplace.
    
    Features:
    - Search destinations/locations
    - Search hotels by destination
    - Get hotel details, photos, reviews
    - Real-time availability and pricing
    
    Signup: https://rapidapi.com/tipsters/api/booking-com
    Free tier: 500 requests/month
    """
    
    BASE_URL = "https://booking-com.p.rapidapi.com/v1"
    
    def __init__(self):
        self.api_key = getattr(settings, 'RAPIDAPI_KEY', None)
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
        """Check if RapidAPI key is configured"""
        return bool(self.api_key)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key"""
        return {
            "X-RapidAPI-Key": self.api_key or "",
            "X-RapidAPI-Host": "booking-com.p.rapidapi.com"
        }
    
    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make request to RapidAPI"""
        if not self.is_configured():
            return {
                "success": False,
                "error": "RapidAPI key not configured. Get one at https://rapidapi.com/tipsters/api/booking-com"
            }
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = await self.client.get(
                url,
                headers=self._get_headers(),
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                return {"success": True, "data": data}
            elif response.status_code == 429:
                return {
                    "success": False,
                    "error": "Rate limit exceeded. Upgrade your RapidAPI plan.",
                    "status_code": 429
                }
            elif response.status_code == 403:
                return {
                    "success": False,
                    "error": "Invalid API key or subscription required",
                    "status_code": 403
                }
            else:
                logger.error(f"RapidAPI error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                    "status_code": response.status_code
                }
                
        except httpx.TimeoutException:
            logger.error("RapidAPI request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"RapidAPI exception: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # LOCATIONS / DESTINATIONS
    # ================================================================
    
    async def search_locations(
        self,
        query: str,
        locale: str = "en-us"
    ) -> Dict[str, Any]:
        """
        Search for locations/destinations.
        
        Args:
            query: Search query (city, region, hotel name, etc.)
            locale: Language locale
            
        Returns:
            List of matching destinations with dest_id for hotel search
        """
        result = await self._request(
            "/hotels/locations",
            params={
                "name": query,
                "locale": locale
            }
        )
        
        if result.get("success"):
            locations = result.get("data", [])
            return {
                "success": True,
                "locations": [
                    {
                        "dest_id": loc.get("dest_id"),
                        "dest_type": loc.get("dest_type"),
                        "name": loc.get("name"),
                        "label": loc.get("label"),
                        "city_name": loc.get("city_name"),
                        "country": loc.get("country"),
                        "region": loc.get("region"),
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude"),
                        "hotels": loc.get("hotels"),
                        "image_url": loc.get("image_url")
                    }
                    for loc in locations
                ]
            }
        return result
    
    # ================================================================
    # HOTEL SEARCH
    # ================================================================
    
    async def search_hotels(
        self,
        dest_id: str,
        dest_type: str = "city",
        checkin: Optional[date] = None,
        checkout: Optional[date] = None,
        adults: int = 2,
        children: int = 0,
        children_ages: Optional[List[int]] = None,
        rooms: int = 1,
        currency: str = "USD",
        units: str = "metric",
        locale: str = "en-us",
        order_by: str = "popularity",
        filter_by_currency: str = "USD",
        page: int = 0,
        include_adjacency: bool = True
    ) -> Dict[str, Any]:
        """
        Search hotels by destination.
        
        Args:
            dest_id: Destination ID from search_locations
            dest_type: Type (city, region, landmark, hotel, etc.)
            checkin: Check-in date
            checkout: Check-out date
            adults: Number of adults
            children: Number of children
            children_ages: List of children ages
            rooms: Number of rooms
            currency: Price currency
            order_by: Sort order (popularity, price, distance, review_score, etc.)
            page: Page number (0-indexed)
            
        Returns:
            List of hotels with pricing and details
        """
        # Default dates if not provided
        if not checkin:
            checkin = date.today()
        if not checkout:
            checkout = date.today().replace(day=date.today().day + 1)
        
        params = {
            "dest_id": dest_id,
            "dest_type": dest_type,
            "checkin_date": checkin.strftime("%Y-%m-%d"),
            "checkout_date": checkout.strftime("%Y-%m-%d"),
            "adults_number": adults,
            "room_number": rooms,
            "units": units,
            "locale": locale,
            "order_by": order_by,
            "filter_by_currency": filter_by_currency,
            "page_number": page,
            "include_adjacency": str(include_adjacency).lower()
        }
        
        # Add children if present
        if children > 0:
            params["children_number"] = children
            if children_ages:
                params["children_ages"] = ",".join(str(age) for age in children_ages)
        
        result = await self._request("/hotels/search", params)
        
        if result.get("success"):
            data = result.get("data", {})
            hotels = data.get("result", [])
            
            return {
                "success": True,
                "hotels": [self._normalize_hotel(h) for h in hotels],
                "total": data.get("count", len(hotels)),
                "primary_count": data.get("primary_count"),
                "search_params": {
                    "dest_id": dest_id,
                    "checkin": checkin.isoformat(),
                    "checkout": checkout.isoformat(),
                    "adults": adults,
                    "rooms": rooms
                }
            }
        return result
    
    def _normalize_hotel(self, hotel: Dict) -> Dict[str, Any]:
        """Normalize hotel data to standard format"""
        # Get price info
        price_info = hotel.get("composite_price_breakdown", {}) or {}
        gross_amount = price_info.get("gross_amount_per_night", {})
        
        # Get main photo
        main_photo = hotel.get("main_photo_url") or hotel.get("max_photo_url") or ""
        if main_photo and not main_photo.startswith("http"):
            main_photo = f"https://cf.bstatic.com{main_photo}"
        
        # Get review score details
        review_score = hotel.get("review_score")
        review_word = hotel.get("review_score_word", "")
        
        return {
            "id": str(hotel.get("hotel_id")),
            "name": hotel.get("hotel_name") or hotel.get("hotel_name_trans"),
            "description": hotel.get("unit_configuration_label"),
            "address": hotel.get("address") or hotel.get("address_trans"),
            "city": hotel.get("city") or hotel.get("city_trans"),
            "country": hotel.get("country_trans"),
            "zip": hotel.get("zip"),
            "location": {
                "latitude": hotel.get("latitude"),
                "longitude": hotel.get("longitude"),
                "distance_from_center": hotel.get("distance"),
                "distance_unit": hotel.get("distance_unit", "km")
            },
            "star_rating": hotel.get("class"),
            "rating": {
                "score": review_score,
                "word": review_word,
                "reviews_count": hotel.get("review_nr", 0)
            },
            "price": {
                "amount": gross_amount.get("value") or hotel.get("min_total_price"),
                "currency": gross_amount.get("currency") or hotel.get("currency_code", "USD"),
                "per_night": True,
                "original_amount": hotel.get("price_breakdown", {}).get("gross_price"),
                "discount_percentage": hotel.get("price_breakdown", {}).get("has_incalculable_charges")
            },
            "images": {
                "main": main_photo,
                "thumbnail": hotel.get("main_photo_url"),
            },
            "amenities": hotel.get("hotel_facilities") or [],
            "booking_url": hotel.get("url"),
            "is_free_cancellation": hotel.get("is_free_cancellable", False),
            "is_no_prepayment": hotel.get("is_no_prepayment_block", False),
            "badges": hotel.get("ribbon_text"),
            "accommodation_type": hotel.get("accommodation_type_name"),
            "checkin": hotel.get("checkin", {}),
            "checkout": hotel.get("checkout", {}),
            "provider": "rapidapi_booking"
        }
    
    # ================================================================
    # HOTEL DETAILS
    # ================================================================
    
    async def get_hotel_details(
        self,
        hotel_id: str,
        locale: str = "en-us",
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific hotel.
        
        Args:
            hotel_id: Hotel ID from search results
            locale: Language locale
            
        Returns:
            Detailed hotel information
        """
        result = await self._request(
            "/hotels/data",
            params={
                "hotel_id": hotel_id,
                "locale": locale
            }
        )
        
        if result.get("success"):
            data = result.get("data", {})
            return {
                "success": True,
                "hotel": {
                    "id": str(data.get("hotel_id")),
                    "name": data.get("name"),
                    "description": data.get("hotel_description"),
                    "address": data.get("address"),
                    "city": data.get("city"),
                    "country": data.get("country_trans"),
                    "zip": data.get("zip"),
                    "location": {
                        "latitude": data.get("location", {}).get("latitude") or data.get("latitude"),
                        "longitude": data.get("location", {}).get("longitude") or data.get("longitude")
                    },
                    "star_rating": data.get("class"),
                    "rating": {
                        "score": data.get("review_score"),
                        "word": data.get("review_score_word"),
                        "reviews_count": data.get("review_nr")
                    },
                    "checkin": data.get("checkin"),
                    "checkout": data.get("checkout"),
                    "email": data.get("email"),
                    "phone": data.get("phone"),
                    "url": data.get("url"),
                    "facilities": data.get("hotel_facilities"),
                    "languages_spoken": data.get("languages_spoken"),
                    "currency": data.get("currencycode", currency),
                    "booking_home": data.get("booking_home"),
                    "provider": "rapidapi_booking"
                }
            }
        return result
    
    # ================================================================
    # HOTEL PHOTOS
    # ================================================================
    
    async def get_hotel_photos(
        self,
        hotel_id: str,
        locale: str = "en-us"
    ) -> Dict[str, Any]:
        """
        Get photos for a specific hotel.
        
        Args:
            hotel_id: Hotel ID
            
        Returns:
            List of hotel photos
        """
        result = await self._request(
            "/hotels/photos",
            params={
                "hotel_id": hotel_id,
                "locale": locale
            }
        )
        
        if result.get("success"):
            photos = result.get("data", [])
            return {
                "success": True,
                "photos": [
                    {
                        "id": photo.get("photo_id"),
                        "url_original": photo.get("url_original") or photo.get("url_max"),
                        "url_max": photo.get("url_max"),
                        "url_square60": photo.get("url_square60"),
                        "url_1440": photo.get("url_1440"),
                        "description": photo.get("tag_name"),
                        "tags": photo.get("tags", [])
                    }
                    for photo in photos
                ]
            }
        return result
    
    # ================================================================
    # HOTEL REVIEWS
    # ================================================================
    
    async def get_hotel_reviews(
        self,
        hotel_id: str,
        locale: str = "en-us",
        sort_type: str = "SORT_MOST_RELEVANT",
        page: int = 0
    ) -> Dict[str, Any]:
        """
        Get reviews for a specific hotel.
        
        Args:
            hotel_id: Hotel ID
            sort_type: Sort order (SORT_MOST_RELEVANT, SORT_NEWEST, etc.)
            page: Page number
            
        Returns:
            List of hotel reviews
        """
        result = await self._request(
            "/hotels/reviews",
            params={
                "hotel_id": hotel_id,
                "locale": locale,
                "sort_type": sort_type,
                "page_number": page
            }
        )
        
        if result.get("success"):
            data = result.get("data", {})
            reviews = data.get("result", [])
            return {
                "success": True,
                "reviews": [
                    {
                        "author": {
                            "name": r.get("author", {}).get("name"),
                            "country": r.get("author", {}).get("countrycode"),
                            "type": r.get("author", {}).get("type_string"),
                            "age_group": r.get("author", {}).get("age_group"),
                            "avatar": r.get("author", {}).get("avatar")
                        },
                        "date": r.get("date"),
                        "title": r.get("title"),
                        "pros": r.get("pros"),
                        "cons": r.get("cons"),
                        "average_score": r.get("average_score"),
                        "helpful_vote_count": r.get("helpful_vote_count"),
                        "stayed_rooms": r.get("stayed_room_info"),
                        "travel_purpose": r.get("travel_purpose")
                    }
                    for r in reviews
                ],
                "total": data.get("count", len(reviews)),
                "average_score": data.get("score")
            }
        return result
    
    # ================================================================
    # HOTEL FACILITIES / AMENITIES
    # ================================================================
    
    async def get_hotel_facilities(
        self,
        hotel_id: str,
        locale: str = "en-us"
    ) -> Dict[str, Any]:
        """
        Get facilities/amenities for a specific hotel.
        
        Args:
            hotel_id: Hotel ID
            
        Returns:
            List of hotel facilities grouped by category
        """
        result = await self._request(
            "/hotels/facilities",
            params={
                "hotel_id": hotel_id,
                "locale": locale
            }
        )
        
        if result.get("success"):
            facilities = result.get("data", [])
            return {
                "success": True,
                "facilities": facilities
            }
        return result
    
    # ================================================================
    # ROOM LIST / AVAILABILITY
    # ================================================================
    
    async def get_room_list(
        self,
        hotel_id: str,
        checkin: date,
        checkout: date,
        adults: int = 2,
        children: int = 0,
        children_ages: Optional[List[int]] = None,
        currency: str = "USD",
        locale: str = "en-us"
    ) -> Dict[str, Any]:
        """
        Get available rooms for a hotel with pricing.
        
        Args:
            hotel_id: Hotel ID
            checkin: Check-in date
            checkout: Check-out date
            adults: Number of adults
            children: Number of children
            children_ages: List of children ages
            currency: Price currency
            
        Returns:
            List of available rooms with rates
        """
        params = {
            "hotel_id": hotel_id,
            "checkin_date": checkin.strftime("%Y-%m-%d"),
            "checkout_date": checkout.strftime("%Y-%m-%d"),
            "adults_number_by_rooms": str(adults),
            "currency": currency,
            "locale": locale
        }
        
        if children > 0 and children_ages:
            params["children_number_by_rooms"] = str(children)
            params["children_ages"] = ",".join(str(age) for age in children_ages)
        
        result = await self._request("/hotels/room-list", params)
        
        if result.get("success"):
            data = result.get("data", [])
            rooms = []
            
            for block in data:
                for room in block.get("block", []):
                    rooms.append({
                        "id": room.get("block_id"),
                        "room_id": room.get("room_id"),
                        "name": room.get("room_name"),
                        "name_without_policy": room.get("name_without_policy"),
                        "photos": block.get("photos", []),
                        "facilities": block.get("facilities", []),
                        "description": block.get("room_description"),
                        "highlights": block.get("room_highlights", []),
                        "max_occupancy": room.get("max_occupancy"),
                        "price": {
                            "amount": room.get("product_price_breakdown", {}).get("gross_amount", {}).get("value"),
                            "currency": room.get("product_price_breakdown", {}).get("gross_amount", {}).get("currency"),
                            "all_inclusive": room.get("product_price_breakdown", {}).get("all_inclusive_amount", {}).get("value"),
                            "taxes": room.get("product_price_breakdown", {}).get("included_taxes_and_charges_amount", {}).get("value")
                        },
                        "refundable": room.get("refundable"),
                        "is_flash_deal": room.get("is_flash_deal"),
                        "free_cancellation": room.get("block_text", {}).get("policies", []),
                        "mealplan": room.get("mealplan"),
                        "paymentterms": room.get("paymentterms", {})
                    })
            
            return {
                "success": True,
                "rooms": rooms,
                "hotel_id": hotel_id,
                "currency": currency
            }
        return result
    
    # ================================================================
    # POPULAR DESTINATIONS
    # ================================================================
    
    async def get_popular_destinations(
        self,
        locale: str = "en-us"
    ) -> Dict[str, Any]:
        """
        Get popular travel destinations.
        
        Returns:
            List of popular destinations with images
        """
        # This endpoint might need adjustment based on actual API
        result = await self._request(
            "/hotels/locations",
            params={
                "name": "popular",
                "locale": locale
            }
        )
        
        # Return some default popular destinations if API doesn't support this
        if not result.get("success"):
            return {
                "success": True,
                "destinations": [
                    {"name": "Lagos", "country": "Nigeria", "dest_id": "-1372565", "dest_type": "city"},
                    {"name": "Abuja", "country": "Nigeria", "dest_id": "-1366088", "dest_type": "city"},
                    {"name": "Dubai", "country": "UAE", "dest_id": "-782831", "dest_type": "city"},
                    {"name": "London", "country": "UK", "dest_id": "-2601889", "dest_type": "city"},
                    {"name": "Paris", "country": "France", "dest_id": "-1456928", "dest_type": "city"},
                    {"name": "New York", "country": "USA", "dest_id": "20088325", "dest_type": "city"},
                ]
            }
        return result
    
    # ================================================================
    # FILTERS & METADATA
    # ================================================================
    
    async def get_search_filters(
        self,
        dest_id: str,
        dest_type: str = "city",
        checkin: Optional[date] = None,
        checkout: Optional[date] = None,
        adults: int = 2,
        rooms: int = 1,
        locale: str = "en-us"
    ) -> Dict[str, Any]:
        """
        Get available search filters for a destination.
        
        Returns:
            List of filter options (price ranges, amenities, ratings, etc.)
        """
        if not checkin:
            checkin = date.today()
        if not checkout:
            checkout = date.today().replace(day=date.today().day + 1)
        
        result = await self._request(
            "/hotels/search-filters",
            params={
                "dest_id": dest_id,
                "dest_type": dest_type,
                "checkin_date": checkin.strftime("%Y-%m-%d"),
                "checkout_date": checkout.strftime("%Y-%m-%d"),
                "adults_number": adults,
                "room_number": rooms,
                "locale": locale
            }
        )
        return result


# Singleton instance
rapidapi_hotels = RapidAPIHotelsClient()
