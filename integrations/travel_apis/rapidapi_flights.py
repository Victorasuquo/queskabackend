"""
Queska Backend - RapidAPI Flights Integration
Free flight search API via RapidAPI Sky Scrapper (Skyscanner)

Get your FREE API key at: https://rapidapi.com/apiheya/api/sky-scrapper
Free tier: 100 requests/month
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.core.config import settings


class RapidAPIFlightsClient:
    """
    RapidAPI Flights Client (Sky Scrapper / Skyscanner API)
    
    This is a FREE API that provides real flight data from Skyscanner
    through RapidAPI marketplace.
    
    Features:
    - Search airports and cities
    - Search one-way and round-trip flights
    - Get real-time prices from multiple airlines
    - Compare flight options
    
    Signup: https://rapidapi.com/apiheya/api/sky-scrapper
    Free tier: 100 requests/month
    """
    
    BASE_URL = "https://sky-scrapper.p.rapidapi.com/api/v1"
    ALT_BASE_URL = "https://sky-scrapper.p.rapidapi.com/api/v2"
    
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
            "X-RapidAPI-Host": "sky-scrapper.p.rapidapi.com"
        }
    
    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        version: str = "v1"
    ) -> Dict[str, Any]:
        """Make request to RapidAPI"""
        if not self.is_configured():
            return {
                "success": False,
                "error": "RapidAPI key not configured. Get one at https://rapidapi.com/apiheya/api/sky-scrapper"
            }
        
        base = self.ALT_BASE_URL if version == "v2" else self.BASE_URL
        url = f"{base}{endpoint}"
        
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
                logger.error(f"RapidAPI Flights error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                    "status_code": response.status_code,
                    "details": response.text
                }
                
        except httpx.TimeoutException:
            logger.error("RapidAPI Flights request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"RapidAPI Flights exception: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # AIRPORT / LOCATION SEARCH
    # ================================================================
    
    async def search_airports(
        self,
        query: str,
        locale: str = "en-US"
    ) -> Dict[str, Any]:
        """
        Search for airports and cities.
        
        Args:
            query: Search query (city name, airport code, etc.)
            locale: Language locale
            
        Returns:
            List of matching airports with skyId for flight search
        """
        result = await self._request(
            "/flights/searchAirport",
            params={
                "query": query,
                "locale": locale
            }
        )
        
        if result.get("success"):
            data = result.get("data", {})
            airports = data.get("data", [])
            return {
                "success": True,
                "airports": [
                    {
                        "skyId": apt.get("skyId"),
                        "entityId": apt.get("entityId"),
                        "name": apt.get("presentation", {}).get("title"),
                        "subtitle": apt.get("presentation", {}).get("subtitle"),
                        "suggestionTitle": apt.get("presentation", {}).get("suggestionTitle"),
                        "type": apt.get("navigation", {}).get("entityType"),
                        "iata": apt.get("navigation", {}).get("relevantFlightParams", {}).get("skyId"),
                        "country": apt.get("presentation", {}).get("subtitle", "").split(",")[-1].strip() if apt.get("presentation", {}).get("subtitle") else None,
                    }
                    for apt in airports
                ]
            }
        return result
    
    # ================================================================
    # FLIGHT SEARCH
    # ================================================================
    
    async def search_flights(
        self,
        origin_sky_id: str,
        destination_sky_id: str,
        origin_entity_id: str,
        destination_entity_id: str,
        departure_date: date,
        return_date: Optional[date] = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "economy",
        currency: str = "USD",
        market: str = "en-US",
        country_code: str = "US"
    ) -> Dict[str, Any]:
        """
        Search for flights.
        
        Args:
            origin_sky_id: Origin airport skyId (e.g., "LAGS" for Lagos)
            destination_sky_id: Destination airport skyId
            origin_entity_id: Origin entity ID from airport search
            destination_entity_id: Destination entity ID from airport search
            departure_date: Departure date
            return_date: Return date (optional, for round-trip)
            adults: Number of adults
            children: Number of children (2-11)
            infants: Number of infants (0-2)
            cabin_class: economy, premium_economy, business, first
            currency: Price currency
            
        Returns:
            List of flights with pricing
        """
        params = {
            "originSkyId": origin_sky_id,
            "destinationSkyId": destination_sky_id,
            "originEntityId": origin_entity_id,
            "destinationEntityId": destination_entity_id,
            "date": departure_date.strftime("%Y-%m-%d"),
            "adults": adults,
            "currency": currency,
            "market": market,
            "countryCode": country_code,
            "cabinClass": cabin_class
        }
        
        if return_date:
            params["returnDate"] = return_date.strftime("%Y-%m-%d")
        
        if children > 0:
            params["children"] = children
        
        if infants > 0:
            params["infants"] = infants
        
        result = await self._request(
            "/flights/searchFlights",
            params=params,
            version="v2"
        )
        
        if result.get("success"):
            data = result.get("data", {})
            context = data.get("context", {})
            itineraries = data.get("data", {}).get("itineraries", [])
            
            return {
                "success": True,
                "flights": [self._normalize_flight(f) for f in itineraries],
                "total": len(itineraries),
                "session_id": context.get("sessionId"),
                "status": context.get("status"),
                "search_params": {
                    "origin": origin_sky_id,
                    "destination": destination_sky_id,
                    "departure_date": departure_date.isoformat(),
                    "return_date": return_date.isoformat() if return_date else None,
                    "adults": adults,
                    "cabin_class": cabin_class,
                    "currency": currency
                }
            }
        return result
    
    def _normalize_flight(self, flight: Dict) -> Dict[str, Any]:
        """Normalize flight data to standard format"""
        price = flight.get("price", {})
        legs = flight.get("legs", [])
        
        normalized_legs = []
        for leg in legs:
            segments = leg.get("segments", [])
            normalized_segments = []
            
            for seg in segments:
                normalized_segments.append({
                    "flight_number": seg.get("flightNumber"),
                    "carrier": {
                        "code": seg.get("marketingCarrier", {}).get("alternateId"),
                        "name": seg.get("marketingCarrier", {}).get("name"),
                        "logo": seg.get("marketingCarrier", {}).get("logo")
                    },
                    "operating_carrier": {
                        "code": seg.get("operatingCarrier", {}).get("alternateId"),
                        "name": seg.get("operatingCarrier", {}).get("name"),
                        "logo": seg.get("operatingCarrier", {}).get("logo")
                    },
                    "origin": {
                        "code": seg.get("origin", {}).get("displayCode"),
                        "name": seg.get("origin", {}).get("name"),
                        "city": seg.get("origin", {}).get("city"),
                        "country": seg.get("origin", {}).get("country")
                    },
                    "destination": {
                        "code": seg.get("destination", {}).get("displayCode"),
                        "name": seg.get("destination", {}).get("name"),
                        "city": seg.get("destination", {}).get("city"),
                        "country": seg.get("destination", {}).get("country")
                    },
                    "departure": seg.get("departure"),
                    "arrival": seg.get("arrival"),
                    "duration_minutes": seg.get("durationInMinutes")
                })
            
            normalized_legs.append({
                "id": leg.get("id"),
                "origin": {
                    "code": leg.get("origin", {}).get("displayCode"),
                    "name": leg.get("origin", {}).get("name"),
                    "city": leg.get("origin", {}).get("city"),
                    "country": leg.get("origin", {}).get("country")
                },
                "destination": {
                    "code": leg.get("destination", {}).get("displayCode"),
                    "name": leg.get("destination", {}).get("name"),
                    "city": leg.get("destination", {}).get("city"),
                    "country": leg.get("destination", {}).get("country")
                },
                "departure": leg.get("departure"),
                "arrival": leg.get("arrival"),
                "duration_minutes": leg.get("durationInMinutes"),
                "stop_count": leg.get("stopCount"),
                "is_smallest_stops": leg.get("isSmallestStops"),
                "time_delta_in_days": leg.get("timeDeltaInDays"),
                "carriers": [
                    {
                        "code": c.get("alternateId"),
                        "name": c.get("name"),
                        "logo": c.get("logo")
                    }
                    for c in leg.get("carriers", {}).get("marketing", [])
                ],
                "segments": normalized_segments
            })
        
        return {
            "id": flight.get("id"),
            "price": {
                "amount": price.get("raw"),
                "formatted": price.get("formatted"),
                "currency": "USD"
            },
            "legs": normalized_legs,
            "is_self_transfer": flight.get("isSelfTransfer", False),
            "is_protected_self_connect": flight.get("isProtectedSelfConnect", False),
            "fare_policy": flight.get("farePolicy", {}),
            "eco_contender": flight.get("eco_contender", False),
            "score": flight.get("score"),
            "tags": flight.get("tags", []),
            "provider": "rapidapi_skyscanner"
        }
    
    # ================================================================
    # FLIGHT DETAILS
    # ================================================================
    
    async def get_flight_details(
        self,
        itinerary_id: str,
        legs: List[Dict],
        session_id: str,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific flight itinerary.
        
        Args:
            itinerary_id: Itinerary ID from search results
            legs: Legs data from search results
            session_id: Session ID from search
            
        Returns:
            Detailed flight information with booking options
        """
        params = {
            "itineraryId": itinerary_id,
            "sessionId": session_id,
            "adults": adults,
            "currency": currency
        }
        
        if children > 0:
            params["children"] = children
        if infants > 0:
            params["infants"] = infants
        
        # Add legs as JSON string
        import json
        params["legs"] = json.dumps(legs)
        
        result = await self._request(
            "/flights/getFlightDetails",
            params=params,
            version="v2"
        )
        
        if result.get("success"):
            data = result.get("data", {})
            return {
                "success": True,
                "itinerary": data.get("data", {}).get("itinerary"),
                "pricing_options": data.get("data", {}).get("pricingOptions", []),
                "status": data.get("context", {}).get("status")
            }
        return result
    
    # ================================================================
    # PRICE CALENDAR
    # ================================================================
    
    async def get_price_calendar(
        self,
        origin_sky_id: str,
        destination_sky_id: str,
        origin_entity_id: str,
        destination_entity_id: str,
        from_date: date,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Get price calendar showing cheapest prices by date.
        
        Args:
            origin_sky_id: Origin airport skyId
            destination_sky_id: Destination airport skyId
            origin_entity_id: Origin entity ID
            destination_entity_id: Destination entity ID
            from_date: Starting date for calendar
            
        Returns:
            Calendar with prices by date
        """
        result = await self._request(
            "/flights/getPriceCalendar",
            params={
                "originSkyId": origin_sky_id,
                "destinationSkyId": destination_sky_id,
                "originEntityId": origin_entity_id,
                "destinationEntityId": destination_entity_id,
                "fromDate": from_date.strftime("%Y-%m-%d"),
                "currency": currency
            }
        )
        
        if result.get("success"):
            data = result.get("data", {})
            flights = data.get("data", {}).get("flights", {})
            
            return {
                "success": True,
                "calendar": {
                    "days": flights.get("days", []),
                    "groups": flights.get("groups", [])
                }
            }
        return result
    
    # ================================================================
    # NEARBY AIRPORTS
    # ================================================================
    
    async def get_nearby_airports(
        self,
        latitude: float,
        longitude: float,
        locale: str = "en-US"
    ) -> Dict[str, Any]:
        """
        Get airports near a specific location.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            List of nearby airports
        """
        result = await self._request(
            "/flights/getNearByAirports",
            params={
                "lat": latitude,
                "lng": longitude,
                "locale": locale
            }
        )
        
        if result.get("success"):
            data = result.get("data", {})
            airports = data.get("data", {}).get("nearby", [])
            
            return {
                "success": True,
                "current": data.get("data", {}).get("current"),
                "nearby": [
                    {
                        "skyId": apt.get("skyId"),
                        "entityId": apt.get("entityId"),
                        "name": apt.get("presentation", {}).get("title"),
                        "subtitle": apt.get("presentation", {}).get("subtitle"),
                        "distance": apt.get("navigation", {}).get("relevantHotelParams", {}).get("distance")
                    }
                    for apt in airports
                ]
            }
        return result
    
    # ================================================================
    # POPULAR ROUTES
    # ================================================================
    
    async def get_config(self) -> Dict[str, Any]:
        """
        Get API configuration including supported currencies, locales, etc.
        """
        result = await self._request("/getConfig")
        
        if result.get("success"):
            data = result.get("data", {})
            return {
                "success": True,
                "currencies": data.get("data", {}).get("currencies", []),
                "locales": data.get("data", {}).get("locales", []),
                "markets": data.get("data", {}).get("markets", [])
            }
        return result
    
    # ================================================================
    # HELPER: QUICK SEARCH
    # ================================================================
    
    async def quick_search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date] = None,
        adults: int = 1,
        cabin_class: str = "economy",
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Convenience method: Search flights by city/airport name.
        Automatically resolves airport codes.
        
        Args:
            origin: Origin city or airport name (e.g., "Lagos" or "LOS")
            destination: Destination city or airport (e.g., "London" or "LHR")
            departure_date: Departure date
            return_date: Return date (optional)
            adults: Number of adults
            cabin_class: Cabin class
            currency: Currency code
            
        Returns:
            Flight search results
        """
        # Search for origin airport
        origin_result = await self.search_airports(origin)
        if not origin_result.get("success") or not origin_result.get("airports"):
            return {
                "success": False,
                "error": f"Could not find airport for: {origin}"
            }
        origin_apt = origin_result["airports"][0]
        
        # Search for destination airport
        dest_result = await self.search_airports(destination)
        if not dest_result.get("success") or not dest_result.get("airports"):
            return {
                "success": False,
                "error": f"Could not find airport for: {destination}"
            }
        dest_apt = dest_result["airports"][0]
        
        # Search flights
        return await self.search_flights(
            origin_sky_id=origin_apt["skyId"],
            destination_sky_id=dest_apt["skyId"],
            origin_entity_id=origin_apt["entityId"],
            destination_entity_id=dest_apt["entityId"],
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            cabin_class=cabin_class,
            currency=currency
        )


# Singleton instance
rapidapi_flights = RapidAPIFlightsClient()
