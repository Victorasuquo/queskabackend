"""
Queska Backend - Expedia Integration
Comprehensive integration with Expedia's Rapid API and XAP APIs
for hotels, flights, activities, and car rentals
"""

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

import httpx
from loguru import logger

from app.core.config import settings


class ExpediaRapidAPI:
    """
    Expedia Rapid API Client for hotel/lodging services.
    
    The Rapid API provides access to:
    - 750,000+ properties across 310,000+ destinations
    - Real-time availability and pricing
    - Complete booking flow
    - Post-booking services
    
    Documentation: https://developers.expediagroup.com/docs/products/rapid
    """
    
    # API Endpoints
    BASE_URL = "https://test.ean.com/v3"  # Production: https://api.ean.com/v3
    PROD_URL = "https://api.ean.com/v3"
    
    def __init__(self):
        self.api_key = settings.EXPEDIA_API_KEY
        self.api_secret = settings.EXPEDIA_API_SECRET
        self._client: Optional[httpx.AsyncClient] = None
        self._use_production = settings.ENVIRONMENT == "production"
    
    @property
    def base_url(self) -> str:
        return self.PROD_URL if self._use_production else self.BASE_URL
    
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
    
    def _generate_signature(self) -> Tuple[str, str]:
        """
        Generate authentication signature for Expedia Rapid API.
        
        The signature is computed as:
        SHA512(api_key + api_secret + timestamp)
        
        Returns:
            Tuple of (signature, timestamp)
        """
        timestamp = str(int(time.time()))
        signature_raw = f"{self.api_key}{self.api_secret}{timestamp}"
        signature = hashlib.sha512(signature_raw.encode()).hexdigest()
        return signature, timestamp
    
    def _get_headers(self, customer_ip: str = "127.0.0.1") -> Dict[str, str]:
        """Generate request headers with authentication."""
        signature, timestamp = self._generate_signature()
        
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
            "Authorization": f"EAN apikey={self.api_key},signature={signature},timestamp={timestamp}",
            "Customer-Ip": customer_ip,
            "User-Agent": "Queska/1.0",
        }
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        customer_ip: str = "127.0.0.1"
    ) -> Dict[str, Any]:
        """Make authenticated request to Expedia API."""
        if not self.is_configured():
            return {"success": False, "error": "Expedia API not configured"}
        
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(customer_ip)
        
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
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            elif response.status_code == 204:
                return {"success": True, "data": None}
            else:
                error_data = response.json() if response.content else {}
                logger.error(f"Expedia API error: {response.status_code} - {error_data}")
                return {
                    "success": False,
                    "error": error_data.get("message", f"HTTP {response.status_code}"),
                    "status_code": response.status_code,
                    "details": error_data
                }
                
        except httpx.HTTPError as e:
            logger.error(f"Expedia HTTP error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Expedia request error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # GEOGRAPHY / REGIONS
    # ================================================================
    
    async def get_regions(
        self,
        country_code: str = "US",
        include: Optional[List[str]] = None,
        language: str = "en-US",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get regions (destinations) for property search.
        
        Args:
            country_code: ISO country code
            include: Additional data to include (e.g., "details", "property_ids")
            language: Response language
            limit: Max results
            
        Returns:
            List of regions/destinations
        """
        params = {
            "country_code": country_code,
            "language": language,
            "limit": limit,
        }
        if include:
            params["include"] = ",".join(include)
        
        return await self._request("GET", "/regions", params=params)
    
    async def search_regions(
        self,
        query: str,
        language: str = "en-US",
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search for regions/destinations by name.
        
        Args:
            query: Search term (city, airport code, POI name)
            language: Response language
            limit: Max results
            
        Returns:
            Matching regions
        """
        params = {
            "query": query,
            "language": language,
            "limit": limit,
        }
        
        return await self._request("GET", "/regions", params=params)
    
    # ================================================================
    # PROPERTY AVAILABILITY / SHOPPING
    # ================================================================
    
    async def get_availability(
        self,
        checkin: Union[str, date],
        checkout: Union[str, date],
        currency: str = "USD",
        country_code: str = "US",
        language: str = "en-US",
        occupancy: List[Dict[str, Any]] = None,
        property_id: Optional[List[str]] = None,
        region_id: Optional[str] = None,
        rate_option: str = "member",
        sales_channel: str = "website",
        sales_environment: str = "hotel_only",
        sort_type: str = "preferred",
        filter_by: Optional[Dict[str, Any]] = None,
        customer_ip: str = "127.0.0.1",
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search for available properties (hotels).
        
        This is the main shopping endpoint that returns properties
        with available rooms, rates, and pricing.
        
        Args:
            checkin: Check-in date (YYYY-MM-DD)
            checkout: Check-out date (YYYY-MM-DD)
            currency: Currency code (USD, EUR, etc.)
            country_code: Guest's country
            language: Response language
            occupancy: Room occupancy details [{"adults": 2, "children_ages": [5, 8]}]
            property_id: Specific property IDs to search
            region_id: Region/destination ID
            rate_option: Rate type (member, net, public)
            sales_channel: Channel (website, agent_tool, mobile_app, etc.)
            sales_environment: Environment (hotel_only, hotel_package, etc.)
            sort_type: Sort order (preferred, price, star_rating, review_score)
            filter_by: Additional filters (star_rating, price, amenities, etc.)
            customer_ip: Customer's IP for geo pricing
            limit: Max properties
            
        Returns:
            Available properties with rates
        """
        # Format dates
        if isinstance(checkin, date):
            checkin = checkin.strftime("%Y-%m-%d")
        if isinstance(checkout, date):
            checkout = checkout.strftime("%Y-%m-%d")
        
        # Default occupancy
        if not occupancy:
            occupancy = [{"adults": 2}]
        
        # Build occupancy string
        occupancy_str = "|".join([
            f"{occ.get('adults', 2)}" + 
            (f"-{','.join(map(str, occ.get('children_ages', [])))}" if occ.get('children_ages') else "")
            for occ in occupancy
        ])
        
        params = {
            "checkin": checkin,
            "checkout": checkout,
            "currency": currency,
            "country_code": country_code,
            "language": language,
            "occupancy": occupancy_str,
            "rate_option": rate_option,
            "sales_channel": sales_channel,
            "sales_environment": sales_environment,
            "sort_type": sort_type,
        }
        
        if property_id:
            params["property_id"] = ",".join(property_id)
        if region_id:
            params["region_id"] = region_id
        
        # Apply filters
        if filter_by:
            if filter_by.get("star_rating"):
                params["filter"] = f"star_rating:gte:{filter_by['star_rating']}"
            if filter_by.get("price_max"):
                params["price_max"] = filter_by["price_max"]
            if filter_by.get("amenities"):
                params["amenity_id"] = ",".join(map(str, filter_by["amenities"]))
        
        result = await self._request(
            "GET", 
            "/properties/availability", 
            params=params,
            customer_ip=customer_ip
        )
        
        if result.get("success"):
            # Parse and enhance the response
            properties = result.get("data", [])
            return {
                "success": True,
                "properties": self._parse_properties(properties),
                "search_params": {
                    "checkin": checkin,
                    "checkout": checkout,
                    "occupancy": occupancy,
                    "currency": currency,
                },
                "total": len(properties)
            }
        
        return result
    
    def _parse_properties(self, properties: List[Dict]) -> List[Dict[str, Any]]:
        """Parse property results into standardized format."""
        parsed = []
        
        for prop in properties:
            property_data = {
                "id": prop.get("property_id"),
                "name": prop.get("name"),
                "address": {
                    "line1": prop.get("address", {}).get("line_1"),
                    "line2": prop.get("address", {}).get("line_2"),
                    "city": prop.get("address", {}).get("city"),
                    "state": prop.get("address", {}).get("state_province_name"),
                    "country": prop.get("address", {}).get("country_code"),
                    "postal_code": prop.get("address", {}).get("postal_code"),
                },
                "coordinates": {
                    "latitude": prop.get("coordinates", {}).get("latitude"),
                    "longitude": prop.get("coordinates", {}).get("longitude"),
                },
                "star_rating": prop.get("star_rating"),
                "guest_rating": prop.get("reviews", {}).get("score"),
                "review_count": prop.get("reviews", {}).get("count"),
                "category": prop.get("category", {}).get("name"),
                "image_url": self._get_primary_image(prop.get("images", [])),
                "images": [img.get("links", {}).get("350px", {}).get("href") for img in prop.get("images", [])[:5]],
                "amenities": [a.get("name") for a in prop.get("amenities", [])[:10]],
                "rooms": self._parse_rooms(prop.get("rooms", [])),
            }
            
            # Get lowest price
            if property_data["rooms"]:
                prices = [r.get("price", {}).get("total") for r in property_data["rooms"] if r.get("price", {}).get("total")]
                if prices:
                    property_data["price"] = {
                        "lowest": min(prices),
                        "currency": property_data["rooms"][0].get("price", {}).get("currency", "USD")
                    }
            
            parsed.append(property_data)
        
        return parsed
    
    def _get_primary_image(self, images: List[Dict]) -> Optional[str]:
        """Get the primary/hero image URL."""
        for img in images:
            if img.get("hero_image"):
                return img.get("links", {}).get("1000px", {}).get("href")
        if images:
            return images[0].get("links", {}).get("1000px", {}).get("href")
        return None
    
    def _parse_rooms(self, rooms: List[Dict]) -> List[Dict[str, Any]]:
        """Parse room/rate information."""
        parsed = []
        
        for room in rooms:
            for rate in room.get("rates", []):
                parsed.append({
                    "room_id": room.get("id"),
                    "room_name": room.get("name"),
                    "room_description": room.get("descriptions", {}).get("overview"),
                    "rate_id": rate.get("id"),
                    "price": {
                        "total": rate.get("totals", {}).get("inclusive", {}).get("billable_currency", {}).get("value"),
                        "nightly_avg": rate.get("totals", {}).get("inclusive", {}).get("billable_currency", {}).get("value"),
                        "currency": rate.get("totals", {}).get("inclusive", {}).get("billable_currency", {}).get("currency"),
                        "fees": rate.get("totals", {}).get("exclusive", {}).get("billable_currency", {}).get("value"),
                    },
                    "occupancy": rate.get("occupancy_pricing", {}),
                    "bed_groups": room.get("bed_groups", []),
                    "amenities": [a.get("name") for a in room.get("amenities", [])[:5]],
                    "cancellation_policy": self._parse_cancellation(rate.get("cancel_policies", [])),
                    "payment_options": rate.get("merchant_of_record"),
                    "refundable": rate.get("refundable"),
                    "book_link": rate.get("links", {}).get("book", {}).get("href"),
                })
        
        return parsed
    
    def _parse_cancellation(self, policies: List[Dict]) -> Dict[str, Any]:
        """Parse cancellation policy."""
        if not policies:
            return {"free_cancellation": False}
        
        policy = policies[0]
        return {
            "free_cancellation": policy.get("free_cancellation"),
            "deadline": policy.get("start"),
            "penalty_amount": policy.get("penalty", {}).get("amount"),
            "penalty_currency": policy.get("penalty", {}).get("currency"),
        }
    
    # ================================================================
    # PROPERTY CONTENT / DETAILS
    # ================================================================
    
    async def get_property_content(
        self,
        property_id: str,
        language: str = "en-US",
        include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get detailed property content (descriptions, images, amenities).
        
        Args:
            property_id: Property ID
            language: Response language
            include: Additional data (all_rates, room_content, etc.)
            
        Returns:
            Property details
        """
        params = {
            "language": language,
        }
        if include:
            params["include"] = ",".join(include)
        
        result = await self._request(
            "GET",
            f"/properties/content",
            params={"property_id": property_id, **params}
        )
        
        if result.get("success"):
            content = result.get("data", {})
            if property_id in content:
                return {
                    "success": True,
                    "property": self._parse_property_content(content[property_id])
                }
        
        return result
    
    def _parse_property_content(self, content: Dict) -> Dict[str, Any]:
        """Parse detailed property content."""
        return {
            "id": content.get("property_id"),
            "name": content.get("name"),
            "description": content.get("descriptions", {}).get("overview"),
            "tagline": content.get("descriptions", {}).get("tagline"),
            "amenities_description": content.get("descriptions", {}).get("amenities"),
            "location_description": content.get("descriptions", {}).get("location"),
            "dining_description": content.get("descriptions", {}).get("dining"),
            "business_description": content.get("descriptions", {}).get("business_amenities"),
            "address": content.get("address"),
            "coordinates": content.get("coordinates"),
            "star_rating": content.get("star_rating"),
            "category": content.get("category"),
            "chain": content.get("chain"),
            "brand": content.get("brand"),
            "themes": content.get("themes", []),
            "images": [
                {
                    "url": img.get("links", {}).get("1000px", {}).get("href"),
                    "caption": img.get("caption"),
                    "category": img.get("category"),
                    "hero": img.get("hero_image"),
                }
                for img in content.get("images", [])
            ],
            "amenities": [
                {
                    "id": a.get("id"),
                    "name": a.get("name"),
                    "value": a.get("value"),
                }
                for a in content.get("amenities", [])
            ],
            "rooms": [
                {
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "description": r.get("descriptions", {}).get("overview"),
                    "occupancy": r.get("occupancy"),
                    "bed_groups": r.get("bed_groups"),
                    "area": r.get("area"),
                    "views": r.get("views"),
                    "amenities": r.get("amenities"),
                    "images": r.get("images"),
                }
                for r in content.get("rooms", [])
            ],
            "policies": content.get("policies", {}),
            "attributes": content.get("attributes", {}),
            "fees": content.get("fees", {}),
            "inclusions": content.get("inclusions", {}),
            "statistics": content.get("statistics", {}),
            "reviews": content.get("reviews", {}),
        }
    
    # ================================================================
    # PRICE CHECK
    # ================================================================
    
    async def price_check(
        self,
        property_id: str,
        room_id: str,
        rate_id: str,
        token: str,
        customer_ip: str = "127.0.0.1"
    ) -> Dict[str, Any]:
        """
        Verify current price and availability before booking.
        
        This endpoint must be called before creating a booking
        to ensure the rate is still available.
        
        Args:
            property_id: Property ID
            room_id: Room ID
            rate_id: Rate ID
            token: Price check token from availability response
            customer_ip: Customer IP
            
        Returns:
            Current price and availability status
        """
        params = {
            "property_id": property_id,
            "room_id": room_id,
            "rate_id": rate_id,
            "token": token,
        }
        
        result = await self._request(
            "GET",
            "/properties/availability/price-check",
            params=params,
            customer_ip=customer_ip
        )
        
        return result
    
    # ================================================================
    # BOOKING
    # ================================================================
    
    async def create_booking(
        self,
        property_id: str,
        room_id: str,
        rate_id: str,
        token: str,
        affiliate_reference_id: str,
        contact: Dict[str, Any],
        rooms: List[Dict[str, Any]],
        payments: List[Dict[str, Any]],
        hold: bool = False,
        customer_ip: str = "127.0.0.1"
    ) -> Dict[str, Any]:
        """
        Create a hotel booking.
        
        Args:
            property_id: Property ID
            room_id: Room ID
            rate_id: Rate ID
            token: Token from price check
            affiliate_reference_id: Your internal booking reference
            contact: Contact info {"given_name", "family_name", "email", "phone"}
            rooms: Room occupancy [{"given_name", "family_name", "smoking": false}]
            payments: Payment details
            hold: If True, hold booking for later confirmation
            customer_ip: Customer IP
            
        Returns:
            Booking confirmation
        """
        data = {
            "affiliate_reference_id": affiliate_reference_id,
            "hold": hold,
            "contact": contact,
            "rooms": rooms,
            "payments": payments,
        }
        
        params = {
            "property_id": property_id,
            "room_id": room_id,
            "rate_id": rate_id,
            "token": token,
        }
        
        result = await self._request(
            "POST",
            "/itineraries",
            params=params,
            data=data,
            customer_ip=customer_ip
        )
        
        if result.get("success"):
            booking = result.get("data", {})
            return {
                "success": True,
                "booking": {
                    "itinerary_id": booking.get("itinerary_id"),
                    "status": booking.get("status"),
                    "confirmation_id": booking.get("links", {}).get("retrieve", {}).get("href"),
                    "rooms": booking.get("rooms", []),
                    "contact": booking.get("contact"),
                    "total_price": booking.get("totals"),
                }
            }
        
        return result
    
    async def get_booking(
        self,
        itinerary_id: str,
        email: str,
        customer_ip: str = "127.0.0.1"
    ) -> Dict[str, Any]:
        """
        Retrieve booking details.
        
        Args:
            itinerary_id: Expedia itinerary ID
            email: Contact email used in booking
            customer_ip: Customer IP
            
        Returns:
            Booking details
        """
        return await self._request(
            "GET",
            f"/itineraries/{itinerary_id}",
            params={"email": email},
            customer_ip=customer_ip
        )
    
    async def cancel_booking(
        self,
        itinerary_id: str,
        room_id: str,
        email: str,
        customer_ip: str = "127.0.0.1"
    ) -> Dict[str, Any]:
        """
        Cancel a booking.
        
        Args:
            itinerary_id: Expedia itinerary ID
            room_id: Room to cancel
            email: Contact email
            customer_ip: Customer IP
            
        Returns:
            Cancellation confirmation
        """
        return await self._request(
            "DELETE",
            f"/itineraries/{itinerary_id}/rooms/{room_id}",
            params={"email": email},
            customer_ip=customer_ip
        )
    
    # ================================================================
    # REVIEWS
    # ================================================================
    
    async def get_property_reviews(
        self,
        property_id: str,
        language: str = "en-US",
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get guest reviews for a property.
        """
        params = {
            "property_id": property_id,
            "language": language,
            "limit": limit,
        }
        
        return await self._request("GET", "/reviews", params=params)


class ExpediaXAPAPI:
    """
    Expedia XAP API Client for flights and packages.
    
    XAP (Expedia Affiliate Program) APIs provide:
    - Flight search
    - Package search
    - Lodging listings
    - Deep linking to Expedia for booking
    
    Note: XAP is an affiliate API - users complete booking on Expedia
    """
    
    BASE_URL = "https://apim.expedia.com/xap/v2"
    
    def __init__(self):
        self.api_key = settings.EXPEDIA_API_KEY
        self.api_secret = settings.EXPEDIA_API_SECRET
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def _get_headers(self) -> Dict[str, str]:
        """Generate request headers."""
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Expedia-API-Key": self.api_key,
            "User-Agent": "Queska/1.0",
        }
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make request to XAP API."""
        if not self.is_configured():
            return {"success": False, "error": "Expedia XAP API not configured"}
        
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()
        
        try:
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = await self.client.post(url, headers=headers, json=data)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                error_data = response.json() if response.content else {}
                logger.error(f"Expedia XAP API error: {response.status_code} - {error_data}")
                return {
                    "success": False,
                    "error": error_data.get("message", f"HTTP {response.status_code}"),
                    "status_code": response.status_code,
                    "details": error_data
                }
                
        except httpx.HTTPError as e:
            logger.error(f"Expedia XAP HTTP error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Expedia XAP request error: {e}")
            return {"success": False, "error": str(e)}
    
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
        nonstop: bool = False,
        max_price: Optional[float] = None,
        currency: str = "USD",
        sort_by: str = "price",
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search for flights.
        
        Args:
            origin: Origin airport code (e.g., "LAX")
            destination: Destination airport code (e.g., "JFK")
            departure_date: Departure date
            return_date: Return date (for round trips)
            adults: Number of adults
            children: Number of children (2-11)
            infants: Number of infants (<2)
            cabin_class: Cabin class (economy, premium_economy, business, first)
            nonstop: Only nonstop flights
            max_price: Maximum price filter
            currency: Currency code
            sort_by: Sort order (price, duration, departure_time)
            limit: Max results
            
        Returns:
            Flight options
        """
        # Format dates
        if isinstance(departure_date, date):
            departure_date = departure_date.strftime("%Y-%m-%d")
        if return_date and isinstance(return_date, date):
            return_date = return_date.strftime("%Y-%m-%d")
        
        params = {
            "origin": origin,
            "destination": destination,
            "departureDate": departure_date,
            "adults": adults,
            "currency": currency,
            "cabinClass": cabin_class,
            "limit": limit,
        }
        
        if return_date:
            params["returnDate"] = return_date
        if children > 0:
            params["children"] = children
        if infants > 0:
            params["infants"] = infants
        if nonstop:
            params["nonstopOnly"] = "true"
        if max_price:
            params["maxPrice"] = max_price
        
        result = await self._request("GET", "/flights/listings", params=params)
        
        if result.get("success"):
            flights = result.get("data", {}).get("listings", [])
            return {
                "success": True,
                "flights": self._parse_flights(flights),
                "search_params": {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "passengers": {"adults": adults, "children": children, "infants": infants},
                },
                "total": len(flights)
            }
        
        return result
    
    def _parse_flights(self, flights: List[Dict]) -> List[Dict[str, Any]]:
        """Parse flight results."""
        parsed = []
        
        for flight in flights:
            offer = flight.get("offer", {})
            
            # Parse outbound leg
            outbound = self._parse_flight_leg(flight.get("outboundLeg", {}))
            
            # Parse return leg (if round trip)
            return_leg = None
            if flight.get("inboundLeg"):
                return_leg = self._parse_flight_leg(flight.get("inboundLeg", {}))
            
            parsed.append({
                "id": flight.get("offerId"),
                "price": {
                    "total": offer.get("totalPrice", {}).get("value"),
                    "currency": offer.get("totalPrice", {}).get("currency"),
                    "per_person": offer.get("pricePerTraveler", {}).get("value"),
                    "fees": offer.get("taxes", {}).get("value"),
                },
                "outbound": outbound,
                "return": return_leg,
                "trip_type": "round_trip" if return_leg else "one_way",
                "cabin_class": flight.get("cabinClass"),
                "fare_class": flight.get("fareClass"),
                "seats_remaining": flight.get("seatsRemaining"),
                "refundable": flight.get("refundable"),
                "changeable": flight.get("changeable"),
                "book_url": flight.get("deepLinks", {}).get("bookUrl"),
                "provider": "expedia",
            })
        
        return parsed
    
    def _parse_flight_leg(self, leg: Dict) -> Dict[str, Any]:
        """Parse a flight leg (outbound or return)."""
        segments = []
        
        for segment in leg.get("segments", []):
            segments.append({
                "carrier": segment.get("carrier", {}).get("name"),
                "carrier_code": segment.get("carrier", {}).get("code"),
                "flight_number": segment.get("flightNumber"),
                "aircraft": segment.get("aircraft", {}).get("name"),
                "departure": {
                    "airport": segment.get("departureAirport", {}).get("name"),
                    "airport_code": segment.get("departureAirport", {}).get("code"),
                    "terminal": segment.get("departureTerminal"),
                    "datetime": segment.get("departureDateTime"),
                },
                "arrival": {
                    "airport": segment.get("arrivalAirport", {}).get("name"),
                    "airport_code": segment.get("arrivalAirport", {}).get("code"),
                    "terminal": segment.get("arrivalTerminal"),
                    "datetime": segment.get("arrivalDateTime"),
                },
                "duration_minutes": segment.get("durationMinutes"),
                "duration_text": self._format_duration(segment.get("durationMinutes", 0)),
            })
        
        return {
            "departure_airport": leg.get("departureAirport", {}).get("code"),
            "arrival_airport": leg.get("arrivalAirport", {}).get("code"),
            "departure_time": leg.get("departureDateTime"),
            "arrival_time": leg.get("arrivalDateTime"),
            "duration_minutes": leg.get("durationMinutes"),
            "duration_text": self._format_duration(leg.get("durationMinutes", 0)),
            "stops": len(segments) - 1,
            "segments": segments,
        }
    
    def _format_duration(self, minutes: int) -> str:
        """Format duration in hours and minutes."""
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"
    
    # ================================================================
    # LODGING (Hotels via XAP)
    # ================================================================
    
    async def search_lodging(
        self,
        destination: str,
        checkin: Union[str, date],
        checkout: Union[str, date],
        adults: int = 2,
        children: int = 0,
        rooms: int = 1,
        star_rating: Optional[int] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        amenities: Optional[List[str]] = None,
        currency: str = "USD",
        sort_by: str = "recommended",
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search for hotels/lodging via XAP.
        
        Args:
            destination: Destination (city, address, or coordinates)
            checkin: Check-in date
            checkout: Check-out date
            adults: Adults per room
            children: Children per room
            rooms: Number of rooms
            star_rating: Minimum star rating
            price_min: Minimum price
            price_max: Maximum price
            amenities: Required amenities
            currency: Currency
            sort_by: Sort order (recommended, price, star_rating, guest_rating)
            limit: Max results
            
        Returns:
            Hotel listings
        """
        if isinstance(checkin, date):
            checkin = checkin.strftime("%Y-%m-%d")
        if isinstance(checkout, date):
            checkout = checkout.strftime("%Y-%m-%d")
        
        params = {
            "destination": destination,
            "checkIn": checkin,
            "checkOut": checkout,
            "adults": adults,
            "rooms": rooms,
            "currency": currency,
            "sortBy": sort_by,
            "limit": limit,
        }
        
        if children > 0:
            params["children"] = children
        if star_rating:
            params["starRating"] = star_rating
        if price_min:
            params["priceMin"] = price_min
        if price_max:
            params["priceMax"] = price_max
        if amenities:
            params["amenities"] = ",".join(amenities)
        
        result = await self._request("GET", "/lodging/listings", params=params)
        
        if result.get("success"):
            listings = result.get("data", {}).get("listings", [])
            return {
                "success": True,
                "hotels": self._parse_lodging(listings),
                "search_params": {
                    "destination": destination,
                    "checkin": checkin,
                    "checkout": checkout,
                    "guests": {"adults": adults, "children": children},
                    "rooms": rooms,
                },
                "total": len(listings)
            }
        
        return result
    
    def _parse_lodging(self, listings: List[Dict]) -> List[Dict[str, Any]]:
        """Parse lodging listings."""
        parsed = []
        
        for listing in listings:
            property_data = listing.get("property", {})
            offer = listing.get("offer", {})
            
            parsed.append({
                "id": property_data.get("id"),
                "name": property_data.get("name"),
                "star_rating": property_data.get("starRating"),
                "guest_rating": property_data.get("guestRating", {}).get("rating"),
                "review_count": property_data.get("guestRating", {}).get("totalCount"),
                "address": {
                    "line1": property_data.get("address", {}).get("line1"),
                    "city": property_data.get("address", {}).get("city"),
                    "country": property_data.get("address", {}).get("countryCode"),
                },
                "coordinates": {
                    "latitude": property_data.get("coordinates", {}).get("latitude"),
                    "longitude": property_data.get("coordinates", {}).get("longitude"),
                },
                "image_url": property_data.get("heroImage"),
                "amenities": property_data.get("amenities", []),
                "price": {
                    "total": offer.get("totalPrice", {}).get("value"),
                    "currency": offer.get("totalPrice", {}).get("currency"),
                    "nightly": offer.get("nightlyPrice", {}).get("value"),
                },
                "free_cancellation": offer.get("freeCancellation"),
                "pay_later": offer.get("payLater"),
                "vip_access": property_data.get("vipAccess"),
                "book_url": listing.get("deepLinks", {}).get("bookUrl"),
                "provider": "expedia",
            })
        
        return parsed
    
    # ================================================================
    # ACTIVITIES
    # ================================================================
    
    async def search_activities(
        self,
        destination: str,
        date: Union[str, date],
        category: Optional[str] = None,
        price_max: Optional[float] = None,
        currency: str = "USD",
        sort_by: str = "recommended",
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search for activities and tours.
        
        Args:
            destination: Destination
            date: Activity date
            category: Category filter (tours, attractions, outdoor, etc.)
            price_max: Max price
            currency: Currency
            sort_by: Sort order
            limit: Max results
            
        Returns:
            Activity listings
        """
        if isinstance(date, date):
            date = date.strftime("%Y-%m-%d")
        
        params = {
            "destination": destination,
            "date": date,
            "currency": currency,
            "sortBy": sort_by,
            "limit": limit,
        }
        
        if category:
            params["category"] = category
        if price_max:
            params["priceMax"] = price_max
        
        result = await self._request("GET", "/activities/listings", params=params)
        
        if result.get("success"):
            activities = result.get("data", {}).get("listings", [])
            return {
                "success": True,
                "activities": self._parse_activities(activities),
                "search_params": {
                    "destination": destination,
                    "date": date,
                },
                "total": len(activities)
            }
        
        return result
    
    def _parse_activities(self, activities: List[Dict]) -> List[Dict[str, Any]]:
        """Parse activity listings."""
        parsed = []
        
        for activity in activities:
            parsed.append({
                "id": activity.get("id"),
                "name": activity.get("name"),
                "description": activity.get("description"),
                "category": activity.get("category"),
                "duration": activity.get("duration"),
                "duration_text": activity.get("durationText"),
                "rating": activity.get("rating"),
                "review_count": activity.get("reviewCount"),
                "image_url": activity.get("heroImage"),
                "images": activity.get("images", []),
                "price": {
                    "amount": activity.get("price", {}).get("value"),
                    "currency": activity.get("price", {}).get("currency"),
                    "per": "person",
                },
                "location": activity.get("location"),
                "highlights": activity.get("highlights", []),
                "inclusions": activity.get("inclusions", []),
                "free_cancellation": activity.get("freeCancellation"),
                "instant_confirmation": activity.get("instantConfirmation"),
                "mobile_ticket": activity.get("mobileTicket"),
                "book_url": activity.get("deepLinks", {}).get("bookUrl"),
                "provider": "expedia",
            })
        
        return parsed
    
    # ================================================================
    # CAR RENTALS
    # ================================================================
    
    async def search_cars(
        self,
        pickup_location: str,
        pickup_date: Union[str, date],
        pickup_time: str,
        dropoff_date: Union[str, date],
        dropoff_time: str,
        dropoff_location: Optional[str] = None,
        car_class: Optional[str] = None,
        currency: str = "USD",
        sort_by: str = "price",
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search for car rentals.
        
        Args:
            pickup_location: Pickup location (airport code or city)
            pickup_date: Pickup date
            pickup_time: Pickup time (HH:MM)
            dropoff_date: Dropoff date
            dropoff_time: Dropoff time (HH:MM)
            dropoff_location: Dropoff location (if different)
            car_class: Car class filter (economy, compact, midsize, full, luxury, suv, van)
            currency: Currency
            sort_by: Sort order
            limit: Max results
            
        Returns:
            Car rental options
        """
        if isinstance(pickup_date, date):
            pickup_date = pickup_date.strftime("%Y-%m-%d")
        if isinstance(dropoff_date, date):
            dropoff_date = dropoff_date.strftime("%Y-%m-%d")
        
        params = {
            "pickupLocation": pickup_location,
            "pickupDate": pickup_date,
            "pickupTime": pickup_time,
            "dropoffDate": dropoff_date,
            "dropoffTime": dropoff_time,
            "currency": currency,
            "sortBy": sort_by,
            "limit": limit,
        }
        
        if dropoff_location:
            params["dropoffLocation"] = dropoff_location
        if car_class:
            params["carClass"] = car_class
        
        result = await self._request("GET", "/cars/listings", params=params)
        
        if result.get("success"):
            cars = result.get("data", {}).get("listings", [])
            return {
                "success": True,
                "cars": self._parse_cars(cars),
                "search_params": {
                    "pickup_location": pickup_location,
                    "pickup_date": pickup_date,
                    "dropoff_date": dropoff_date,
                },
                "total": len(cars)
            }
        
        return result
    
    def _parse_cars(self, cars: List[Dict]) -> List[Dict[str, Any]]:
        """Parse car rental listings."""
        parsed = []
        
        for car in cars:
            vehicle = car.get("vehicle", {})
            offer = car.get("offer", {})
            
            parsed.append({
                "id": car.get("id"),
                "vehicle": {
                    "name": vehicle.get("name"),
                    "make": vehicle.get("make"),
                    "model": vehicle.get("model"),
                    "class": vehicle.get("class"),
                    "type": vehicle.get("type"),
                    "transmission": vehicle.get("transmission"),
                    "fuel_type": vehicle.get("fuelType"),
                    "passengers": vehicle.get("passengers"),
                    "bags": vehicle.get("bags"),
                    "doors": vehicle.get("doors"),
                    "air_conditioning": vehicle.get("airConditioning"),
                    "image_url": vehicle.get("image"),
                },
                "supplier": {
                    "name": car.get("supplier", {}).get("name"),
                    "logo": car.get("supplier", {}).get("logo"),
                    "rating": car.get("supplier", {}).get("rating"),
                },
                "pickup_location": car.get("pickupLocation"),
                "dropoff_location": car.get("dropoffLocation"),
                "price": {
                    "total": offer.get("totalPrice", {}).get("value"),
                    "currency": offer.get("totalPrice", {}).get("currency"),
                    "daily": offer.get("dailyPrice", {}).get("value"),
                },
                "mileage": offer.get("mileage"),
                "insurance_included": offer.get("insuranceIncluded"),
                "free_cancellation": offer.get("freeCancellation"),
                "features": car.get("features", []),
                "book_url": car.get("deepLinks", {}).get("bookUrl"),
                "provider": "expedia",
            })
        
        return parsed
    
    # ================================================================
    # PACKAGES (Flight + Hotel)
    # ================================================================
    
    async def search_packages(
        self,
        origin: str,
        destination: str,
        departure_date: Union[str, date],
        return_date: Union[str, date],
        adults: int = 2,
        children: int = 0,
        rooms: int = 1,
        currency: str = "USD",
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Search for vacation packages (flight + hotel).
        
        Args:
            origin: Origin airport code
            destination: Destination
            departure_date: Departure date
            return_date: Return date
            adults: Number of adults
            children: Number of children
            rooms: Number of rooms
            currency: Currency
            limit: Max results
            
        Returns:
            Package options
        """
        if isinstance(departure_date, date):
            departure_date = departure_date.strftime("%Y-%m-%d")
        if isinstance(return_date, date):
            return_date = return_date.strftime("%Y-%m-%d")
        
        params = {
            "origin": origin,
            "destination": destination,
            "departureDate": departure_date,
            "returnDate": return_date,
            "adults": adults,
            "rooms": rooms,
            "currency": currency,
            "limit": limit,
        }
        
        if children > 0:
            params["children"] = children
        
        result = await self._request("GET", "/packages/listings", params=params)
        
        if result.get("success"):
            packages = result.get("data", {}).get("listings", [])
            return {
                "success": True,
                "packages": self._parse_packages(packages),
                "search_params": {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                    "return_date": return_date,
                },
                "total": len(packages)
            }
        
        return result
    
    def _parse_packages(self, packages: List[Dict]) -> List[Dict[str, Any]]:
        """Parse package listings."""
        parsed = []
        
        for pkg in packages:
            hotel = pkg.get("hotel", {})
            flight = pkg.get("flight", {})
            offer = pkg.get("offer", {})
            
            parsed.append({
                "id": pkg.get("id"),
                "hotel": {
                    "name": hotel.get("name"),
                    "star_rating": hotel.get("starRating"),
                    "guest_rating": hotel.get("guestRating"),
                    "image_url": hotel.get("heroImage"),
                    "address": hotel.get("address"),
                },
                "flight": {
                    "outbound": {
                        "carrier": flight.get("outbound", {}).get("carrier"),
                        "departure_time": flight.get("outbound", {}).get("departureTime"),
                        "arrival_time": flight.get("outbound", {}).get("arrivalTime"),
                        "stops": flight.get("outbound", {}).get("stops"),
                    },
                    "return": {
                        "carrier": flight.get("inbound", {}).get("carrier"),
                        "departure_time": flight.get("inbound", {}).get("departureTime"),
                        "arrival_time": flight.get("inbound", {}).get("arrivalTime"),
                        "stops": flight.get("inbound", {}).get("stops"),
                    },
                },
                "price": {
                    "total": offer.get("totalPrice", {}).get("value"),
                    "currency": offer.get("totalPrice", {}).get("currency"),
                    "savings": offer.get("savings", {}).get("value"),
                    "per_person": offer.get("pricePerPerson", {}).get("value"),
                },
                "free_cancellation": offer.get("freeCancellation"),
                "book_url": pkg.get("deepLinks", {}).get("bookUrl"),
                "provider": "expedia",
            })
        
        return parsed


class ExpediaClient:
    """
    Unified Expedia API client providing access to all services.
    """
    
    def __init__(self):
        self.rapid = ExpediaRapidAPI()
        self.xap = ExpediaXAPAPI()
    
    @property
    def hotels(self) -> ExpediaRapidAPI:
        """Access Rapid API for hotel services."""
        return self.rapid
    
    @property
    def flights(self) -> ExpediaXAPAPI:
        """Access XAP API for flight services."""
        return self.xap
    
    @property
    def activities(self) -> ExpediaXAPAPI:
        """Access XAP API for activities."""
        return self.xap
    
    @property
    def cars(self) -> ExpediaXAPAPI:
        """Access XAP API for car rentals."""
        return self.xap
    
    @property
    def packages(self) -> ExpediaXAPAPI:
        """Access XAP API for packages."""
        return self.xap
    
    def is_configured(self) -> bool:
        return self.rapid.is_configured() or self.xap.is_configured()
    
    async def close(self):
        await self.rapid.close()
        await self.xap.close()
    
    async def get_status(self) -> Dict[str, Any]:
        """Get configuration status of all APIs."""
        return {
            "rapid_api": {
                "configured": self.rapid.is_configured(),
                "services": ["hotels", "booking"],
            },
            "xap_api": {
                "configured": self.xap.is_configured(),
                "services": ["flights", "lodging", "activities", "cars", "packages"],
            }
        }


# Global client instance
expedia_client = ExpediaClient()
