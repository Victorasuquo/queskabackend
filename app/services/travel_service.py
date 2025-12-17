"""
Queska Backend - Travel Service
Unified service for travel search, booking, and experience integration
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from loguru import logger

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError, ServiceUnavailableError
from app.schemas.travel import (
    HotelSearchRequest,
    HotelSchema,
    HotelRoomSchema,
    FlightSearchRequest,
    FlightSchema,
    FlightLegSchema,
    FlightSegmentSchema,
    ActivitySearchRequest,
    ActivitySchema,
    CarSearchRequest,
    CarSchema,
    CarVehicleSchema,
    CarSupplierSchema,
    PackageSearchRequest,
    PackageSchema,
    PackageHotelSchema,
    PackageFlightSchema,
    DestinationSchema,
    PriceSchema,
    LocationSchema,
    RatingSchema,
    BookingContactSchema,
    TravelerSchema,
)
from integrations.travel_apis.expedia import expedia_client
from integrations.travel_apis.booking_com import booking_com_client
from integrations.travel_apis.rapidapi_hotels import rapidapi_hotels
from integrations.travel_apis.rapidapi_flights import rapidapi_flights


class TravelService:
    """
    Unified travel service providing:
    - Hotel search and booking
    - Flight search
    - Activity/tour search
    - Car rental search
    - Package (flight+hotel) search
    - Destination/region search
    
    Integrates with:
    - RapidAPI Hotels (FREE - primary for hotels)
    - RapidAPI Flights (FREE - primary for flights)
    - Expedia Rapid API and XAP APIs
    - Booking.com Demand API
    """
    
    def __init__(self):
        self.expedia = expedia_client
        self.booking_com = booking_com_client
        self.rapidapi_hotels = rapidapi_hotels
        self.rapidapi_flights = rapidapi_flights
    
    # ================================================================
    # HOTELS
    # ================================================================
    
    async def search_hotels(
        self,
        destination: str,
        checkin: date,
        checkout: date,
        adults: int = 2,
        children: int = 0,
        children_ages: Optional[List[int]] = None,
        rooms: int = 1,
        currency: str = "USD",
        star_rating_min: Optional[int] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        amenities: Optional[List[str]] = None,
        sort_by: str = "recommended",
        limit: int = 50,
        customer_ip: str = "127.0.0.1"
    ) -> Dict[str, Any]:
        """
        Search for hotels using available APIs.
        
        Priority: RapidAPI (FREE) -> Expedia -> Booking.com
        
        Returns standardized hotel results from available providers.
        """
        results = {
            "success": True,
            "hotels": [],
            "total": 0,
            "search_params": {
                "destination": destination,
                "checkin": checkin.isoformat(),
                "checkout": checkout.isoformat(),
                "adults": adults,
                "children": children,
                "rooms": rooms,
                "currency": currency,
            },
            "providers_used": []
        }
        
        # Map sort_by to RapidAPI order_by
        sort_mapping = {
            "recommended": "popularity",
            "price": "price",
            "price_asc": "price",
            "price_desc": "price",
            "rating": "review_score",
            "distance": "distance",
            "popularity": "popularity"
        }
        order_by = sort_mapping.get(sort_by, "popularity")
        
        # ============================================
        # TRY RAPIDAPI HOTELS FIRST (FREE!)
        # ============================================
        if self.rapidapi_hotels.is_configured():
            try:
                # First search for destination to get dest_id
                loc_result = await self.rapidapi_hotels.search_locations(query=destination)
                
                if loc_result.get("success") and loc_result.get("locations"):
                    location = loc_result["locations"][0]
                    dest_id = location.get("dest_id")
                    dest_type = location.get("dest_type", "city")
                    
                    # Search hotels
                    hotel_result = await self.rapidapi_hotels.search_hotels(
                        dest_id=dest_id,
                        dest_type=dest_type,
                        checkin=checkin,
                        checkout=checkout,
                        adults=adults,
                        children=children,
                        children_ages=children_ages,
                        rooms=rooms,
                        currency=currency,
                        order_by=order_by
                    )
                    
                    if hotel_result.get("success"):
                        hotels = hotel_result.get("hotels", [])
                        results["hotels"].extend(hotels)
                        results["providers_used"].append("rapidapi_booking")
                        results["total"] = hotel_result.get("total", len(hotels))
                        logger.info(f"RapidAPI returned {len(hotels)} hotels for {destination}")
                        
            except Exception as e:
                logger.warning(f"RapidAPI Hotels error: {e}")
        
        # If no results from RapidAPI, try other providers
        if not results["hotels"]:
            # Build occupancy for Expedia
            occupancy = [{"adults": adults}]
            if children_ages:
                occupancy[0]["children_ages"] = children_ages
            elif children > 0:
                occupancy[0]["children_ages"] = [8] * children
            
            # Build filters
            filters = {}
            if star_rating_min:
                filters["star_rating"] = star_rating_min
            if price_max:
                filters["price_max"] = price_max
            if amenities:
                filters["amenities"] = amenities
            
            # Try Expedia Rapid API
            if self.expedia.rapid.is_configured():
                try:
                    region_result = await self.expedia.rapid.search_regions(query=destination)
                    region_id = None
                    if region_result.get("success") and region_result.get("data"):
                        regions = region_result.get("data", [])
                        if regions:
                            region_id = regions[0].get("id")
                    
                    rapid_result = await self.expedia.rapid.get_availability(
                        checkin=checkin,
                        checkout=checkout,
                        currency=currency,
                        occupancy=occupancy,
                        region_id=region_id,
                        filter_by=filters if filters else None,
                        customer_ip=customer_ip,
                        limit=limit
                    )
                    
                    if rapid_result.get("success"):
                        hotels = self._normalize_expedia_hotels(rapid_result.get("properties", []))
                        results["hotels"].extend(hotels)
                        results["providers_used"].append("expedia_rapid")
                        
                except Exception as e:
                    logger.warning(f"Expedia Rapid API error: {e}")
            
            # Try XAP API for additional results
            if self.expedia.xap.is_configured():
                try:
                    xap_result = await self.expedia.xap.search_lodging(
                        destination=destination,
                        checkin=checkin,
                        checkout=checkout,
                        adults=adults,
                        children=children,
                        rooms=rooms,
                        star_rating=star_rating_min,
                        price_min=price_min,
                        price_max=price_max,
                        currency=currency,
                        sort_by=self._map_sort_order(sort_by),
                        limit=limit
                    )
                    
                    if xap_result.get("success"):
                        hotels = self._normalize_xap_hotels(xap_result.get("hotels", []))
                        existing_ids = {h.get("id") for h in results["hotels"]}
                        for hotel in hotels:
                            if hotel.get("id") not in existing_ids:
                                results["hotels"].append(hotel)
                        results["providers_used"].append("expedia_xap")
                        
                except Exception as e:
                    logger.warning(f"Expedia XAP API error: {e}")
        
        # Try Booking.com API
        if self.booking_com.is_configured():
            try:
                # First search for destination
                dest_result = await self.booking_com.search_destinations(query=destination)
                dest_id = None
                dest_type = None
                
                if dest_result.get("success") and dest_result.get("destinations"):
                    dest = dest_result["destinations"][0]
                    dest_id = dest.get("id")
                    dest_type = dest.get("type", "city")
                
                # Search accommodations
                booking_result = await self.booking_com.search_accommodations(
                    dest_id=dest_id,
                    dest_type=dest_type,
                    checkin=checkin,
                    checkout=checkout,
                    adults=adults,
                    children=children,
                    children_ages=children_ages,
                    rooms=rooms,
                    currency=currency,
                    filter_by_class=[star_rating_min] if star_rating_min else None,
                    filter_by_price_min=price_min,
                    filter_by_price_max=price_max,
                    order_by=self._map_booking_sort_order(sort_by),
                    limit=limit
                )
                
                if booking_result.get("success"):
                    hotels = self._normalize_booking_com_hotels(booking_result.get("hotels", []))
                    # Merge with existing results, avoiding duplicates
                    existing_ids = {h.id for h in results["hotels"]}
                    for hotel in hotels:
                        if hotel.id not in existing_ids:
                            results["hotels"].append(hotel)
                    results["providers_used"].append("booking.com")
                    
            except Exception as e:
                logger.warning(f"Booking.com API error: {e}")
        
        # Sort results
        results["hotels"] = self._sort_hotels(results["hotels"], sort_by)
        results["total"] = len(results["hotels"])
        
        if not results["hotels"]:
            results["success"] = False
            results["error"] = "No hotels found for the specified criteria"
        
        return results
    
    def _normalize_expedia_hotels(self, properties: List[Dict]) -> List[HotelSchema]:
        """Normalize Expedia Rapid API hotel results."""
        hotels = []
        
        for prop in properties:
            # Get lowest price room
            rooms = []
            lowest_price = None
            
            for room in prop.get("rooms", []):
                price = room.get("price", {})
                room_schema = HotelRoomSchema(
                    room_id=room.get("room_id"),
                    room_name=room.get("room_name", "Standard Room"),
                    description=room.get("room_description"),
                    rate_id=room.get("rate_id"),
                    price=PriceSchema(
                        total=price.get("total"),
                        currency=price.get("currency", "USD"),
                        per_night=price.get("nightly_avg"),
                        fees=price.get("fees"),
                    ),
                    amenities=room.get("amenities", []),
                    cancellation_policy=room.get("cancellation_policy"),
                    refundable=room.get("refundable", False),
                    book_link=room.get("book_link"),
                )
                rooms.append(room_schema)
                
                if price.get("total"):
                    if lowest_price is None or price.get("total") < lowest_price:
                        lowest_price = price.get("total")
            
            # Build hotel schema
            coords = prop.get("coordinates", {})
            address = prop.get("address", {})
            
            hotel = HotelSchema(
                id=prop.get("id", ""),
                name=prop.get("name", ""),
                star_rating=prop.get("star_rating"),
                guest_rating=RatingSchema(
                    score=prop.get("guest_rating"),
                    count=prop.get("review_count"),
                ) if prop.get("guest_rating") else None,
                location=LocationSchema(
                    address=address.get("line1"),
                    city=address.get("city"),
                    state=address.get("state"),
                    country=address.get("country"),
                    postal_code=address.get("postal_code"),
                    latitude=coords.get("latitude"),
                    longitude=coords.get("longitude"),
                ),
                image_url=prop.get("image_url"),
                images=prop.get("images", []),
                amenities=prop.get("amenities", []),
                category=prop.get("category"),
                price=PriceSchema(
                    total=lowest_price,
                    currency=prop.get("price", {}).get("currency", "USD"),
                ) if lowest_price else None,
                rooms=rooms,
                provider="expedia",
            )
            hotels.append(hotel)
        
        return hotels
    
    def _normalize_xap_hotels(self, hotels_data: List[Dict]) -> List[HotelSchema]:
        """Normalize Expedia XAP API hotel results."""
        hotels = []
        
        for h in hotels_data:
            coords = h.get("coordinates", {})
            address = h.get("address", {})
            price = h.get("price", {})
            
            hotel = HotelSchema(
                id=h.get("id", ""),
                name=h.get("name", ""),
                star_rating=h.get("star_rating"),
                guest_rating=RatingSchema(
                    score=h.get("guest_rating"),
                    count=h.get("review_count"),
                ) if h.get("guest_rating") else None,
                location=LocationSchema(
                    address=address.get("line1"),
                    city=address.get("city"),
                    country=address.get("country"),
                    latitude=coords.get("latitude"),
                    longitude=coords.get("longitude"),
                ),
                image_url=h.get("image_url"),
                amenities=h.get("amenities", []),
                price=PriceSchema(
                    total=price.get("total"),
                    currency=price.get("currency", "USD"),
                    per_night=price.get("nightly"),
                ),
                free_cancellation=h.get("free_cancellation", False),
                pay_later=h.get("pay_later", False),
                vip_access=h.get("vip_access", False),
                book_url=h.get("book_url"),
                provider="expedia",
            )
            hotels.append(hotel)
        
        return hotels
    
    def _sort_hotels(self, hotels: List[HotelSchema], sort_by: str) -> List[HotelSchema]:
        """Sort hotel results."""
        if sort_by == "price":
            return sorted(hotels, key=lambda h: h.price.total if h.price and h.price.total else float('inf'))
        elif sort_by == "star_rating":
            return sorted(hotels, key=lambda h: h.star_rating or 0, reverse=True)
        elif sort_by == "guest_rating":
            return sorted(hotels, key=lambda h: h.guest_rating.score if h.guest_rating else 0, reverse=True)
        return hotels
    
    def _map_sort_order(self, sort_by: str) -> str:
        """Map sort order to Expedia API format."""
        mapping = {
            "recommended": "recommended",
            "price": "price",
            "star_rating": "starRating",
            "guest_rating": "guestRating",
            "distance": "distance",
        }
        return mapping.get(sort_by, "recommended")
    
    def _map_booking_sort_order(self, sort_by: str) -> str:
        """Map sort order to Booking.com API format."""
        mapping = {
            "recommended": "popularity",
            "price": "price",
            "star_rating": "class",
            "guest_rating": "review_score",
            "distance": "distance",
        }
        return mapping.get(sort_by, "popularity")
    
    def _normalize_booking_com_hotels(self, hotels_data: List[Dict]) -> List[HotelSchema]:
        """Normalize Booking.com hotel results to standard schema."""
        hotels = []
        
        for h in hotels_data:
            location = h.get("location", {})
            price = h.get("price", {})
            guest_rating = h.get("guest_rating", {})
            room = h.get("room", {})
            
            hotel = HotelSchema(
                id=f"bcom_{h.get('id', '')}",  # Prefix to distinguish provider
                name=h.get("name", ""),
                star_rating=h.get("star_rating"),
                guest_rating=RatingSchema(
                    score=guest_rating.get("score"),
                    count=guest_rating.get("count"),
                    category=guest_rating.get("category"),
                ) if guest_rating.get("score") else None,
                location=LocationSchema(
                    address=location.get("address"),
                    city=location.get("city"),
                    country=location.get("country"),
                    latitude=location.get("latitude"),
                    longitude=location.get("longitude"),
                ),
                image_url=h.get("image_url"),
                images=h.get("images", []),
                amenities=h.get("amenities", []),
                category=h.get("type_name"),
                price=PriceSchema(
                    total=price.get("total"),
                    currency=price.get("currency", "USD"),
                    per_night=price.get("per_night"),
                ),
                rooms=[HotelRoomSchema(
                    room_name=room.get("name", "Standard Room"),
                    description=room.get("description"),
                    bed_type=room.get("bed_type"),
                    price=PriceSchema(
                        total=price.get("total"),
                        currency=price.get("currency", "USD"),
                    ),
                    refundable=h.get("free_cancellation", False),
                    pay_later=h.get("pay_at_property", False),
                )] if room else [],
                free_cancellation=h.get("free_cancellation", False),
                pay_later=h.get("pay_at_property", False),
                book_url=h.get("deep_link"),
                provider="booking.com",
            )
            hotels.append(hotel)
        
        return hotels
    
    async def get_hotel_details(
        self,
        property_id: str,
        checkin: Optional[date] = None,
        checkout: Optional[date] = None,
        adults: int = 2,
        rooms: int = 1,
        customer_ip: str = "127.0.0.1"
    ) -> Dict[str, Any]:
        """
        Get detailed hotel information.
        """
        if self.expedia.rapid.is_configured():
            try:
                result = await self.expedia.rapid.get_property_content(
                    property_id=property_id,
                    include=["all_rates", "room_content"]
                )
                
                if result.get("success"):
                    prop = result.get("property", {})
                    
                    # If dates provided, also get availability
                    rooms_data = []
                    if checkin and checkout:
                        avail = await self.expedia.rapid.get_availability(
                            checkin=checkin,
                            checkout=checkout,
                            property_id=[property_id],
                            occupancy=[{"adults": adults}],
                            customer_ip=customer_ip
                        )
                        if avail.get("success"):
                            for p in avail.get("properties", []):
                                rooms_data.extend(p.get("rooms", []))
                    
                    return {
                        "success": True,
                        "hotel": self._build_hotel_details(prop, rooms_data)
                    }
                    
            except Exception as e:
                logger.error(f"Error getting hotel details: {e}")
        
        return {"success": False, "error": "Could not retrieve hotel details"}
    
    def _build_hotel_details(self, prop: Dict, rooms_data: List[Dict]) -> HotelSchema:
        """Build detailed hotel schema."""
        coords = prop.get("coordinates", {})
        address = prop.get("address", {})
        
        # Parse rooms
        rooms = []
        for room in rooms_data:
            price = room.get("price", {})
            rooms.append(HotelRoomSchema(
                room_id=room.get("room_id"),
                room_name=room.get("room_name", ""),
                description=room.get("room_description"),
                rate_id=room.get("rate_id"),
                price=PriceSchema(
                    total=price.get("total"),
                    currency=price.get("currency", "USD"),
                ),
                amenities=room.get("amenities", []),
                cancellation_policy=room.get("cancellation_policy"),
                refundable=room.get("refundable", False),
            ))
        
        return HotelSchema(
            id=prop.get("id", ""),
            name=prop.get("name", ""),
            description=prop.get("description"),
            star_rating=prop.get("star_rating"),
            guest_rating=RatingSchema(
                score=prop.get("reviews", {}).get("score"),
                count=prop.get("reviews", {}).get("count"),
            ) if prop.get("reviews") else None,
            location=LocationSchema(
                address=address.get("line_1") if isinstance(address, dict) else None,
                city=address.get("city") if isinstance(address, dict) else None,
                state=address.get("state_province_name") if isinstance(address, dict) else None,
                country=address.get("country_code") if isinstance(address, dict) else None,
                latitude=coords.get("latitude"),
                longitude=coords.get("longitude"),
            ),
            image_url=prop.get("images", [{}])[0].get("url") if prop.get("images") else None,
            images=[img.get("url") for img in prop.get("images", []) if img.get("url")],
            amenities=[a.get("name") for a in prop.get("amenities", [])],
            category=prop.get("category", {}).get("name") if isinstance(prop.get("category"), dict) else None,
            chain=prop.get("chain", {}).get("name") if isinstance(prop.get("chain"), dict) else None,
            brand=prop.get("brand", {}).get("name") if isinstance(prop.get("brand"), dict) else None,
            rooms=rooms,
            provider="expedia",
        )
    
    # ================================================================
    # FLIGHTS
    # ================================================================
    
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date] = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "economy",
        nonstop_only: bool = False,
        max_price: Optional[float] = None,
        currency: str = "USD",
        sort_by: str = "price",
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search for flights using Expedia XAP API.
        """
        results = {
            "success": True,
            "flights": [],
            "total": 0,
            "search_params": {
                "origin": origin.upper(),
                "destination": destination.upper(),
                "departure_date": departure_date.isoformat(),
                "return_date": return_date.isoformat() if return_date else None,
                "adults": adults,
                "children": children,
                "infants": infants,
                "cabin_class": cabin_class,
                "trip_type": "round_trip" if return_date else "one_way",
            },
            "providers_used": []
        }
        
        if self.expedia.xap.is_configured():
            try:
                xap_result = await self.expedia.xap.search_flights(
                    origin=origin.upper(),
                    destination=destination.upper(),
                    departure_date=departure_date,
                    return_date=return_date,
                    adults=adults,
                    children=children,
                    infants=infants,
                    cabin_class=cabin_class,
                    nonstop=nonstop_only,
                    max_price=max_price,
                    currency=currency,
                    sort_by=sort_by,
                    limit=limit
                )
                
                if xap_result.get("success"):
                    flights = self._normalize_flights(xap_result.get("flights", []))
                    results["flights"] = flights
                    results["providers_used"].append("expedia_xap")
                    
            except Exception as e:
                logger.warning(f"Expedia XAP flights error: {e}")
        
        # Try Booking.com flights
        if self.booking_com.is_configured():
            try:
                booking_result = await self.booking_com.search_flights(
                    origin=origin.upper(),
                    destination=destination.upper(),
                    departure_date=departure_date,
                    return_date=return_date,
                    adults=adults,
                    children=children,
                    infants=infants,
                    cabin_class=cabin_class,
                    direct_only=nonstop_only,
                    currency=currency,
                    limit=limit
                )
                
                if booking_result.get("success"):
                    flights = self._normalize_booking_flights(booking_result.get("flights", []))
                    # Merge results
                    existing_ids = {f.id for f in results["flights"]}
                    for flight in flights:
                        if flight.id not in existing_ids:
                            results["flights"].append(flight)
                    results["providers_used"].append("booking.com")
                    
            except Exception as e:
                logger.warning(f"Booking.com flights error: {e}")
        
        # Sort results
        results["flights"] = self._sort_flights(results["flights"], sort_by)
        results["total"] = len(results["flights"])
        
        if not results["flights"]:
            results["success"] = False
            results["error"] = "No flights found for the specified route and dates"
        
        return results
    
    def _normalize_booking_flights(self, flights_data: List[Dict]) -> List[FlightSchema]:
        """Normalize Booking.com flight results."""
        flights = []
        
        for f in flights_data:
            price = f.get("price", {})
            outbound = f.get("outbound")
            return_leg = f.get("return")
            
            outbound_schema = self._parse_booking_flight_leg(outbound) if outbound else None
            return_schema = self._parse_booking_flight_leg(return_leg) if return_leg else None
            
            if outbound_schema:
                flight = FlightSchema(
                    id=f"bcom_{f.get('id', '')}",
                    price=PriceSchema(
                        total=price.get("total"),
                        currency=price.get("currency", "USD"),
                        per_person=price.get("per_person"),
                        taxes=price.get("taxes"),
                    ),
                    outbound=outbound_schema,
                    return_leg=return_schema,
                    trip_type=f.get("trip_type", "one_way"),
                    cabin_class=f.get("cabin_class"),
                    refundable=f.get("refundable", False),
                    changeable=f.get("changeable", False),
                    book_url=f.get("deep_link"),
                    provider="booking.com",
                )
                flights.append(flight)
        
        return flights
    
    def _parse_booking_flight_leg(self, leg: Dict) -> Optional[FlightLegSchema]:
        """Parse Booking.com flight leg."""
        if not leg:
            return None
        
        segments = []
        for seg in leg.get("segments", []):
            dep = seg.get("departure", {})
            arr = seg.get("arrival", {})
            
            segment = FlightSegmentSchema(
                carrier=seg.get("carrier", ""),
                carrier_code=seg.get("carrier_code"),
                flight_number=seg.get("flight_number", ""),
                aircraft=seg.get("aircraft"),
                departure_airport=dep.get("airport", ""),
                departure_airport_code=dep.get("airport_code", ""),
                departure_terminal=dep.get("terminal"),
                departure_datetime=self._parse_datetime(dep.get("datetime")),
                arrival_airport=arr.get("airport", ""),
                arrival_airport_code=arr.get("airport_code", ""),
                arrival_terminal=arr.get("terminal"),
                arrival_datetime=self._parse_datetime(arr.get("datetime")),
                duration_minutes=seg.get("duration_minutes", 0),
                duration_text=self._format_duration(seg.get("duration_minutes", 0)),
            )
            segments.append(segment)
        
        return FlightLegSchema(
            departure_airport=leg.get("departure", {}).get("airport", ""),
            departure_airport_code=leg.get("departure", {}).get("code", ""),
            arrival_airport=leg.get("arrival", {}).get("airport", ""),
            arrival_airport_code=leg.get("arrival", {}).get("code", ""),
            departure_time=self._parse_datetime(leg.get("departure")),
            arrival_time=self._parse_datetime(leg.get("arrival")),
            duration_minutes=leg.get("duration_minutes", 0),
            duration_text=self._format_duration(leg.get("duration_minutes", 0)),
            stops=leg.get("stops", 0),
            segments=segments,
        )
    
    def _format_duration(self, minutes: int) -> str:
        """Format duration in hours and minutes."""
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"
    
    def _normalize_flights(self, flights_data: List[Dict]) -> List[FlightSchema]:
        """Normalize flight results."""
        flights = []
        
        for f in flights_data:
            price = f.get("price", {})
            outbound = f.get("outbound", {})
            return_leg = f.get("return")
            
            # Parse outbound leg
            outbound_schema = self._parse_flight_leg(outbound) if outbound else None
            return_schema = self._parse_flight_leg(return_leg) if return_leg else None
            
            if outbound_schema:
                flight = FlightSchema(
                    id=f.get("id", ""),
                    price=PriceSchema(
                        total=price.get("total"),
                        currency=price.get("currency", "USD"),
                        per_person=price.get("per_person"),
                        fees=price.get("fees"),
                    ),
                    outbound=outbound_schema,
                    return_leg=return_schema,
                    trip_type=f.get("trip_type", "one_way"),
                    cabin_class=f.get("cabin_class"),
                    fare_class=f.get("fare_class"),
                    seats_remaining=f.get("seats_remaining"),
                    refundable=f.get("refundable", False),
                    changeable=f.get("changeable", False),
                    book_url=f.get("book_url"),
                    provider=f.get("provider", "expedia"),
                )
                flights.append(flight)
        
        return flights
    
    def _parse_flight_leg(self, leg: Dict) -> Optional[FlightLegSchema]:
        """Parse a flight leg."""
        if not leg:
            return None
        
        segments = []
        for seg in leg.get("segments", []):
            dep = seg.get("departure", {})
            arr = seg.get("arrival", {})
            
            segment = FlightSegmentSchema(
                carrier=seg.get("carrier", ""),
                carrier_code=seg.get("carrier_code"),
                flight_number=seg.get("flight_number", ""),
                aircraft=seg.get("aircraft"),
                departure_airport=dep.get("airport", ""),
                departure_airport_code=dep.get("airport_code", ""),
                departure_terminal=dep.get("terminal"),
                departure_datetime=self._parse_datetime(dep.get("datetime")),
                arrival_airport=arr.get("airport", ""),
                arrival_airport_code=arr.get("airport_code", ""),
                arrival_terminal=arr.get("terminal"),
                arrival_datetime=self._parse_datetime(arr.get("datetime")),
                duration_minutes=seg.get("duration_minutes", 0),
                duration_text=seg.get("duration_text", ""),
            )
            segments.append(segment)
        
        return FlightLegSchema(
            departure_airport=leg.get("departure_airport", ""),
            departure_airport_code=leg.get("departure_airport", ""),
            arrival_airport=leg.get("arrival_airport", ""),
            arrival_airport_code=leg.get("arrival_airport", ""),
            departure_time=self._parse_datetime(leg.get("departure_time")),
            arrival_time=self._parse_datetime(leg.get("arrival_time")),
            duration_minutes=leg.get("duration_minutes", 0),
            duration_text=leg.get("duration_text", ""),
            stops=leg.get("stops", 0),
            segments=segments,
        )
    
    def _parse_datetime(self, dt_str: Optional[str]) -> datetime:
        """Parse datetime string."""
        if not dt_str:
            return datetime.now()
        try:
            if "T" in dt_str:
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        except:
            return datetime.now()
    
    def _sort_flights(self, flights: List[FlightSchema], sort_by: str) -> List[FlightSchema]:
        """Sort flight results."""
        if sort_by == "price":
            return sorted(flights, key=lambda f: f.price.total if f.price and f.price.total else float('inf'))
        elif sort_by == "duration":
            return sorted(flights, key=lambda f: f.outbound.duration_minutes if f.outbound else 0)
        elif sort_by == "departure_time":
            return sorted(flights, key=lambda f: f.outbound.departure_time if f.outbound else datetime.max)
        return flights
    
    # ================================================================
    # ACTIVITIES
    # ================================================================
    
    async def search_activities(
        self,
        destination: str,
        activity_date: date,
        category: Optional[str] = None,
        price_max: Optional[float] = None,
        currency: str = "USD",
        sort_by: str = "recommended",
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search for activities and tours.
        """
        results = {
            "success": True,
            "activities": [],
            "total": 0,
            "search_params": {
                "destination": destination,
                "date": activity_date.isoformat(),
                "category": category,
            },
            "providers_used": []
        }
        
        if self.expedia.xap.is_configured():
            try:
                xap_result = await self.expedia.xap.search_activities(
                    destination=destination,
                    date=activity_date,
                    category=category,
                    price_max=price_max,
                    currency=currency,
                    sort_by=sort_by,
                    limit=limit
                )
                
                if xap_result.get("success"):
                    activities = self._normalize_activities(xap_result.get("activities", []))
                    results["activities"] = activities
                    results["providers_used"].append("expedia_xap")
                    
            except Exception as e:
                logger.warning(f"Expedia XAP activities error: {e}")
        
        # Try Booking.com attractions
        if self.booking_com.is_configured():
            try:
                booking_result = await self.booking_com.search_attractions(
                    destination=destination,
                    date=activity_date,
                    category=category,
                    currency=currency,
                    limit=limit
                )
                
                if booking_result.get("success"):
                    activities = self._normalize_booking_activities(booking_result.get("attractions", []))
                    # Merge results
                    existing_ids = {a.id for a in results["activities"]}
                    for activity in activities:
                        if activity.id not in existing_ids:
                            results["activities"].append(activity)
                    results["providers_used"].append("booking.com")
                    
            except Exception as e:
                logger.warning(f"Booking.com attractions error: {e}")
        
        results["total"] = len(results["activities"])
        
        if not results["activities"]:
            results["success"] = False
            results["error"] = "No activities found for the specified destination and date"
        
        return results
    
    def _normalize_booking_activities(self, attractions_data: List[Dict]) -> List[ActivitySchema]:
        """Normalize Booking.com attraction results."""
        activities = []
        
        for a in attractions_data:
            price = a.get("price", {})
            
            activity = ActivitySchema(
                id=f"bcom_{a.get('id', '')}",
                name=a.get("name", ""),
                description=a.get("description"),
                category=a.get("category"),
                duration=a.get("duration"),
                rating=a.get("rating"),
                review_count=a.get("reviews_count"),
                image_url=a.get("image_url"),
                images=a.get("images", []),
                price=PriceSchema(
                    total=price.get("amount"),
                    currency=price.get("currency", "USD"),
                ),
                location=a.get("location"),
                highlights=a.get("highlights", []),
                inclusions=a.get("inclusions", []),
                free_cancellation=a.get("free_cancellation", False),
                instant_confirmation=a.get("instant_confirmation", False),
                mobile_ticket=a.get("mobile_ticket", False),
                book_url=a.get("deep_link"),
                provider="booking.com",
            )
            activities.append(activity)
        
        return activities
    
    def _normalize_activities(self, activities_data: List[Dict]) -> List[ActivitySchema]:
        """Normalize activity results."""
        activities = []
        
        for a in activities_data:
            price = a.get("price", {})
            
            activity = ActivitySchema(
                id=a.get("id", ""),
                name=a.get("name", ""),
                description=a.get("description"),
                category=a.get("category"),
                duration=a.get("duration"),
                duration_text=a.get("duration_text"),
                rating=a.get("rating"),
                review_count=a.get("review_count"),
                image_url=a.get("image_url"),
                images=a.get("images", []),
                price=PriceSchema(
                    total=price.get("amount"),
                    currency=price.get("currency", "USD"),
                ),
                location=a.get("location"),
                highlights=a.get("highlights", []),
                inclusions=a.get("inclusions", []),
                free_cancellation=a.get("free_cancellation", False),
                instant_confirmation=a.get("instant_confirmation", False),
                mobile_ticket=a.get("mobile_ticket", False),
                book_url=a.get("book_url"),
                provider=a.get("provider", "expedia"),
            )
            activities.append(activity)
        
        return activities
    
    # ================================================================
    # CAR RENTALS
    # ================================================================
    
    async def search_cars(
        self,
        pickup_location: str,
        pickup_date: date,
        pickup_time: str,
        dropoff_date: date,
        dropoff_time: str,
        dropoff_location: Optional[str] = None,
        car_class: Optional[str] = None,
        currency: str = "USD",
        sort_by: str = "price",
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search for car rentals.
        """
        results = {
            "success": True,
            "cars": [],
            "total": 0,
            "search_params": {
                "pickup_location": pickup_location,
                "pickup_date": pickup_date.isoformat(),
                "pickup_time": pickup_time,
                "dropoff_date": dropoff_date.isoformat(),
                "dropoff_time": dropoff_time,
                "dropoff_location": dropoff_location,
            },
            "providers_used": []
        }
        
        if self.expedia.xap.is_configured():
            try:
                xap_result = await self.expedia.xap.search_cars(
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
                
                if xap_result.get("success"):
                    cars = self._normalize_cars(xap_result.get("cars", []))
                    results["cars"] = cars
                    results["providers_used"].append("expedia_xap")
                    
            except Exception as e:
                logger.warning(f"Expedia XAP cars error: {e}")
        
        # Try Booking.com car rentals
        if self.booking_com.is_configured():
            try:
                booking_result = await self.booking_com.search_car_rentals(
                    pickup_location=pickup_location,
                    pickup_date=pickup_date,
                    pickup_time=pickup_time,
                    dropoff_date=dropoff_date,
                    dropoff_time=dropoff_time,
                    dropoff_location=dropoff_location,
                    car_type=car_class,
                    currency=currency,
                    limit=limit
                )
                
                if booking_result.get("success"):
                    cars = self._normalize_booking_cars(booking_result.get("cars", []))
                    # Merge results
                    existing_ids = {c.id for c in results["cars"]}
                    for car in cars:
                        if car.id not in existing_ids:
                            results["cars"].append(car)
                    results["providers_used"].append("booking.com")
                    
            except Exception as e:
                logger.warning(f"Booking.com car rentals error: {e}")
        
        results["total"] = len(results["cars"])
        
        if not results["cars"]:
            results["success"] = False
            results["error"] = "No car rentals found for the specified dates and location"
        
        return results
    
    def _normalize_booking_cars(self, cars_data: List[Dict]) -> List[CarSchema]:
        """Normalize Booking.com car rental results."""
        cars = []
        
        for c in cars_data:
            vehicle = c.get("vehicle", {})
            supplier = c.get("supplier", {})
            price = c.get("price", {})
            
            car = CarSchema(
                id=f"bcom_{c.get('id', '')}",
                vehicle=CarVehicleSchema(
                    name=vehicle.get("name", ""),
                    car_class=vehicle.get("category"),
                    car_type=vehicle.get("type"),
                    transmission=vehicle.get("transmission"),
                    fuel_type=vehicle.get("fuel_type"),
                    passengers=vehicle.get("passengers"),
                    bags=vehicle.get("bags_large"),
                    doors=vehicle.get("doors"),
                    air_conditioning=vehicle.get("air_conditioning", True),
                    image_url=vehicle.get("image_url"),
                ),
                supplier=CarSupplierSchema(
                    name=supplier.get("name", ""),
                    logo=supplier.get("logo"),
                    rating=supplier.get("rating"),
                ),
                pickup_location=c.get("pickup_location"),
                dropoff_location=c.get("dropoff_location"),
                price=PriceSchema(
                    total=price.get("total"),
                    currency=price.get("currency", "USD"),
                    per_night=price.get("per_day"),
                ),
                mileage=c.get("mileage"),
                insurance_included=bool(c.get("insurance")),
                free_cancellation=c.get("free_cancellation", False),
                book_url=c.get("deep_link"),
                provider="booking.com",
            )
            cars.append(car)
        
        return cars
    
    def _normalize_cars(self, cars_data: List[Dict]) -> List[CarSchema]:
        """Normalize car rental results."""
        cars = []
        
        for c in cars_data:
            vehicle = c.get("vehicle", {})
            supplier = c.get("supplier", {})
            price = c.get("price", {})
            
            car = CarSchema(
                id=c.get("id", ""),
                vehicle=CarVehicleSchema(
                    name=vehicle.get("name", ""),
                    make=vehicle.get("make"),
                    model=vehicle.get("model"),
                    car_class=vehicle.get("class"),
                    car_type=vehicle.get("type"),
                    transmission=vehicle.get("transmission"),
                    fuel_type=vehicle.get("fuel_type"),
                    passengers=vehicle.get("passengers"),
                    bags=vehicle.get("bags"),
                    doors=vehicle.get("doors"),
                    air_conditioning=vehicle.get("air_conditioning", True),
                    image_url=vehicle.get("image_url"),
                ),
                supplier=CarSupplierSchema(
                    name=supplier.get("name", ""),
                    logo=supplier.get("logo"),
                    rating=supplier.get("rating"),
                ),
                pickup_location=c.get("pickup_location"),
                dropoff_location=c.get("dropoff_location"),
                price=PriceSchema(
                    total=price.get("total"),
                    currency=price.get("currency", "USD"),
                    per_night=price.get("daily"),
                ),
                mileage=c.get("mileage"),
                insurance_included=c.get("insurance_included", False),
                free_cancellation=c.get("free_cancellation", False),
                features=c.get("features", []),
                book_url=c.get("book_url"),
                provider=c.get("provider", "expedia"),
            )
            cars.append(car)
        
        return cars
    
    # ================================================================
    # PACKAGES
    # ================================================================
    
    async def search_packages(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: date,
        adults: int = 2,
        children: int = 0,
        rooms: int = 1,
        currency: str = "USD",
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Search for vacation packages (flight + hotel).
        """
        results = {
            "success": True,
            "packages": [],
            "total": 0,
            "search_params": {
                "origin": origin.upper(),
                "destination": destination,
                "departure_date": departure_date.isoformat(),
                "return_date": return_date.isoformat(),
                "adults": adults,
                "children": children,
                "rooms": rooms,
            },
            "providers_used": []
        }
        
        if self.expedia.xap.is_configured():
            try:
                xap_result = await self.expedia.xap.search_packages(
                    origin=origin.upper(),
                    destination=destination,
                    departure_date=departure_date,
                    return_date=return_date,
                    adults=adults,
                    children=children,
                    rooms=rooms,
                    currency=currency,
                    limit=limit
                )
                
                if xap_result.get("success"):
                    packages = self._normalize_packages(xap_result.get("packages", []))
                    results["packages"] = packages
                    results["providers_used"].append("expedia_xap")
                    
            except Exception as e:
                logger.warning(f"Expedia XAP packages error: {e}")
        
        results["total"] = len(results["packages"])
        
        if not results["packages"]:
            results["success"] = False
            results["error"] = "No packages found for the specified criteria"
        
        return results
    
    def _normalize_packages(self, packages_data: List[Dict]) -> List[PackageSchema]:
        """Normalize package results."""
        packages = []
        
        for p in packages_data:
            hotel = p.get("hotel", {})
            flight = p.get("flight", {})
            price = p.get("price", {})
            
            package = PackageSchema(
                id=p.get("id", ""),
                hotel=PackageHotelSchema(
                    name=hotel.get("name", ""),
                    star_rating=hotel.get("star_rating"),
                    guest_rating=hotel.get("guest_rating"),
                    image_url=hotel.get("image_url"),
                    address=hotel.get("address"),
                ),
                outbound_flight=PackageFlightSchema(
                    carrier=flight.get("outbound", {}).get("carrier"),
                    departure_time=self._parse_datetime(flight.get("outbound", {}).get("departure_time")),
                    arrival_time=self._parse_datetime(flight.get("outbound", {}).get("arrival_time")),
                    stops=flight.get("outbound", {}).get("stops", 0),
                ),
                return_flight=PackageFlightSchema(
                    carrier=flight.get("return", {}).get("carrier"),
                    departure_time=self._parse_datetime(flight.get("return", {}).get("departure_time")),
                    arrival_time=self._parse_datetime(flight.get("return", {}).get("arrival_time")),
                    stops=flight.get("return", {}).get("stops", 0),
                ),
                price=PriceSchema(
                    total=price.get("total"),
                    currency=price.get("currency", "USD"),
                    per_person=price.get("per_person"),
                    savings=price.get("savings"),
                ),
                free_cancellation=p.get("free_cancellation", False),
                book_url=p.get("book_url"),
                provider=p.get("provider", "expedia"),
            )
            packages.append(package)
        
        return packages
    
    # ================================================================
    # DESTINATIONS
    # ================================================================
    
    async def search_destinations(
        self,
        query: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search for destinations/regions.
        """
        results = {
            "success": True,
            "destinations": [],
        }
        
        if self.expedia.rapid.is_configured():
            try:
                result = await self.expedia.rapid.search_regions(
                    query=query,
                    limit=limit
                )
                
                if result.get("success"):
                    for r in result.get("data", []):
                        results["destinations"].append(DestinationSchema(
                            id=r.get("id", ""),
                            name=r.get("name", ""),
                            full_name=r.get("full_name"),
                            type=r.get("type"),
                            country=r.get("country"),
                            country_code=r.get("country_code"),
                            coordinates=r.get("coordinates"),
                        ))
                        
            except Exception as e:
                logger.warning(f"Destination search error: {e}")
        
        if not results["destinations"]:
            results["success"] = False
            results["error"] = "No destinations found"
        
        return results
    
    # ================================================================
    # SERVICE STATUS
    # ================================================================
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get status of travel API services.
        """
        expedia_status = await self.expedia.get_status()
        booking_status = await self.booking_com.get_service_status()
        
        return {
            "expedia": expedia_status,
            "booking_com": booking_status,
            "providers_available": [
                name for name, status in [
                    ("expedia_rapid", self.expedia.rapid.is_configured()),
                    ("expedia_xap", self.expedia.xap.is_configured()),
                    ("booking.com", self.booking_com.is_configured()),
                ] if status
            ]
        }


# Global service instance
travel_service = TravelService()

